#!/usr/bin/env python3
"""
Verificación del asistente de texto libre de 3 capas (ventas/sales_ai.py):
ejecuta las funciones REALES del módulo (no una reimplementación) contra
un cliente de Anthropic simulado y los módulos reales de ventas - nunca
golpea la red real.

Corre como script plano (no requiere pytest):
    python3 test_sales_ai.py

Escenarios cubiertos:
  1. normalize_phrase() quita tildes y pasa a minúsculas.
  2-13. classify_text() reconoce cada intent por palabras clave -
        incluye "INF"/"información"/"info" y "agregame al grupo" (pedido
        explícito) - y devuelve None si no reconoce nada.
  13c-13f. is_emoji_only() reconoce un mensaje compuesto solo de emoji.
  9-14. _dispatch_intent() ejecuta la acción real de cada intent
        (greeting/ack responden texto fijo; groups/payment/info muestran
        el menú multisale - info además con los precios REALES de
        PRICE_TABLE; free/sell/faq reusan el texto+teclado real).
  15. handle_free_text_fallback() con una palabra clave: resuelve por
      palabras clave y NUNCA llama a la IA (ni para clasificar ni para
      redactar) - el punto central de este cambio: ahorrar créditos.
  15b. Un mensaje de solo emoji se trata como "info", también sin IA.
  16. handle_free_text_fallback() sin palabra clave y la IA deshabilitada:
      muestra el menú principal - nunca se queda en silencio.
  17. handle_free_text_fallback() sin palabra clave, IA habilitada,
      classify_intent_ai reconoce un intent: ejecuta esa acción real y
      NUNCA llama a draft_reply_ai.
  18. handle_free_text_fallback() sin palabra clave, IA no reconoce nada
      (fallback/None): usa draft_reply_ai() para la respuesta genérica.
  19. handle_free_text_fallback() sin palabra clave y la IA falla en
      ambos pasos: muestra el menú principal (nunca se queda en
      silencio).
  20. update sin texto (ej. una foto): no lanza excepción ni responde.
"""
import asyncio
import os
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

TMP_DATA_DIR = tempfile.mkdtemp(prefix="sales_ai_test_")
os.environ["BOT_TOKEN"] = "dummy:token"
os.environ["GROUP_ID"] = "-100123456789"
os.environ["DATA_DIR"] = TMP_DATA_DIR
os.environ.pop("UPSTASH_REDIS_REST_URL", None)
os.environ.pop("UPSTASH_REDIS_REST_TOKEN", None)
os.environ.pop("ANTHROPIC_API_KEY", None)

sys.path.insert(0, REPO_ROOT)
import bot  # noqa: E402,F401 - solo para que ventas.handlers pueda importarse
import ventas.multisale_handlers as multisale_handlers  # noqa: E402
import ventas.config as ventas_config  # noqa: E402
from ventas import sales_ai  # noqa: E402

PASS = []
FAIL = []


def record(name, ok, detail=""):
    (PASS if ok else FAIL).append(f"{name}: {'OK' if ok else 'FALLÓ'} ({detail})")


def make_update(text):
    message = MagicMock()
    message.text = text
    message.reply_text = AsyncMock()
    update = SimpleNamespace(effective_message=message)
    return update, message


class FakeSalesConfig:
    def __init__(self, free_link="https://t.me/+freegroup", faq_text="FAQ de prueba"):
        self._free_link = free_link
        self._faq_text = faq_text

    def get_free_group_link(self):
        return self._free_link

    def get_faq_text(self):
        return self._faq_text


async def main():
    # 1. normalize_phrase().
    record(
        "1. normalize_phrase() quita tildes y pasa a minúsculas",
        sales_ai.normalize_phrase("¿CUÁNTO CUESTA?") == "¿cuanto cuesta?",
        f"resultado={sales_ai.normalize_phrase('¿CUÁNTO CUESTA?')!r}",
    )

    # 2-13. classify_text() por palabras clave.
    cases = [
        ("hola buenas", "greeting"),
        ("muchas gracias", "ack"),
        ("tienen grupo free?", "free"),
        ("quiero vender mi contenido", "sell"),
        ("tienen preguntas frecuentes?", "faq"),
        ("como puedo pagar", "payment"),
        ("que grupos tienen", "groups"),
        ("agregame al grupo", "groups"),
        ("como me uno?", "groups"),
        ("cuanto cuesta", "info"),  # precio -> "info" (responde con la lista real de precios)
        ("INF", "info"),
        ("información", "info"),
        ("info porfa", "info"),
    ]
    for i, (text, expected) in enumerate(cases, start=2):
        got = sales_ai.classify_text(sales_ai.normalize_phrase(text))
        record(f"{i}. classify_text({text!r}) == {expected!r}", got == expected, f"got={got!r}")

    record(
        "13b. classify_text() devuelve None si no reconoce nada",
        sales_ai.classify_text(sales_ai.normalize_phrase("asdkjaslkdj qwe")) is None,
    )

    # Detección de mensajes compuestos solo de emoji.
    record("13c. is_emoji_only('😍') es True", sales_ai.is_emoji_only("😍") is True)
    record("13d. is_emoji_only('🔥🔥🔥') es True", sales_ai.is_emoji_only("🔥🔥🔥") is True)
    record("13e. is_emoji_only('hola 😍') es False (tiene texto)", sales_ai.is_emoji_only("hola 😍") is False)
    record("13f. is_emoji_only('hola') es False", sales_ai.is_emoji_only("hola") is False)

    # 9-14. _dispatch_intent() ejecuta la acción real de cada intent.
    with patch.object(multisale_handlers, "send_multisale_welcome", new=AsyncMock()) as mock_welcome:
        update, message = make_update("hola")
        await sales_ai._dispatch_intent("greeting", update, None)
        record("9. greeting responde un texto fijo (no el menú)", message.reply_text.await_count == 1 and mock_welcome.await_count == 0)

        update, message = make_update("gracias")
        await sales_ai._dispatch_intent("ack", update, None)
        record("10. ack responde un texto fijo (no el menú)", message.reply_text.await_count == 1 and mock_welcome.await_count == 0)

        update, message = make_update("grupos")
        ctx = MagicMock()
        await sales_ai._dispatch_intent("groups", update, ctx)
        record("11. groups llama a send_multisale_welcome() real", mock_welcome.await_count == 1)

        mock_welcome.reset_mock()
        update, message = make_update("como pago")
        await sales_ai._dispatch_intent("payment", update, ctx)
        record(
            "12. payment avisa que primero hay que elegir grupos y llama a send_multisale_welcome()",
            message.reply_text.await_count == 1 and mock_welcome.await_count == 1,
        )

        mock_welcome.reset_mock()
        update, message = make_update("info")
        await sales_ai._dispatch_intent("info", update, ctx)
        from ventas.multisale_config import GROUP_KEYS, PRICE_TABLE
        sent_text = message.reply_text.call_args.args[0]
        ok_prices = all(f"${PRICE_TABLE[c]:.2f}" in sent_text for c in range(1, len(GROUP_KEYS) + 1))
        record(
            "12b. info responde con los precios REALES de PRICE_TABLE y llama a send_multisale_welcome()",
            ok_prices and mock_welcome.await_count == 1,
            f"text={sent_text!r}",
        )

    with patch.object(ventas_config, "SalesConfigManager", new=lambda: FakeSalesConfig(free_link="https://t.me/+freegroup")):
        update, message = make_update("grupo free")
        await sales_ai._dispatch_intent("free", update, None)
        sent_text = message.reply_text.call_args.args[0]
        record("13. free reusa el texto real del Grupo Free", "Grupo Free" in sent_text and message.reply_text.call_args.kwargs.get("reply_markup") is not None)

    with patch.object(ventas_config, "SalesConfigManager", new=lambda: FakeSalesConfig(faq_text="Respuestas a dudas comunes")):
        update, message = make_update("preguntas frecuentes")
        await sales_ai._dispatch_intent("faq", update, None)
        sent_text = message.reply_text.call_args.args[0]
        record("14. faq reusa el texto real configurado por el admin", sent_text == "Respuestas a dudas comunes")

    update, message = make_update("quiero vender mi contenido")
    await sales_ai._dispatch_intent("sell", update, None)
    sent_text = message.reply_text.call_args.args[0]
    record("14b. sell reusa el texto real de vender contenido", "vender tu contenido" in sent_text)

    # 15. Con palabra clave: resuelve SIN llamar nunca a la IA (ahorro de
    #     créditos - el punto central de este cambio).
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy"
    sales_ai._client = MagicMock()
    sales_ai._client.messages.create = AsyncMock(side_effect=AssertionError("la IA NO debía llamarse"))
    with patch.object(multisale_handlers, "send_multisale_welcome", new=AsyncMock()) as mock_welcome:
        update, message = make_update("hola, que grupos tienen")
        await sales_ai.handle_free_text_fallback(update, MagicMock())
        record(
            "15. Con palabra clave reconocida, nunca se llama a la IA",
            mock_welcome.await_count == 1 and sales_ai._client.messages.create.await_count == 0,
            f"welcome_calls={mock_welcome.await_count}, ai_calls={sales_ai._client.messages.create.await_count}",
        )
    os.environ.pop("ANTHROPIC_API_KEY", None)
    sales_ai._client = None

    # 15b. Un mensaje de SOLO emoji se trata como "info" directamente, sin
    #      pasar nunca por la IA (ni para clasificar ni para redactar).
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy"
    sales_ai._client = MagicMock()
    sales_ai._client.messages.create = AsyncMock(side_effect=AssertionError("la IA NO debía llamarse"))
    with patch.object(multisale_handlers, "send_multisale_welcome", new=AsyncMock()) as mock_welcome:
        update, message = make_update("🔥😍")
        await sales_ai.handle_free_text_fallback(update, MagicMock())
        sent_text = message.reply_text.call_args.args[0] if message.reply_text.await_count else ""
        record(
            "15b. Un emoji solo se trata como 'info' (precios) sin llamar a la IA",
            "precios" in sent_text.lower() and mock_welcome.await_count == 1 and sales_ai._client.messages.create.await_count == 0,
            f"text={sent_text!r}",
        )
    os.environ.pop("ANTHROPIC_API_KEY", None)
    sales_ai._client = None

    # 16. Sin palabra clave y la IA deshabilitada: muestra el menú.
    with patch.object(multisale_handlers, "send_multisale_welcome", new=AsyncMock()) as mock_welcome:
        update, message = make_update("asdkjaslkdj qwe")
        await sales_ai.handle_free_text_fallback(update, MagicMock())
        record("16. Sin palabra clave y sin IA, muestra el menú principal", mock_welcome.await_count == 1)

    # 17. Sin palabra clave, IA habilitada, classify_intent_ai reconoce un
    #     intent -> ejecuta esa acción real y nunca llama a draft_reply_ai.
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy"
    fake_classify_response = SimpleNamespace(content=[SimpleNamespace(text="free")])
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_classify_response)
    sales_ai._client = fake_client
    with patch.object(ventas_config, "SalesConfigManager", new=lambda: FakeSalesConfig(free_link="https://t.me/+freegroup")):
        update, message = make_update("oe tienen algo sin pagar?")
        await sales_ai.handle_free_text_fallback(update, MagicMock())
        sent_text = message.reply_text.call_args.args[0] if message.reply_text.await_count else ""
        record(
            "17. IA clasifica a 'free' -> ejecuta la acción real (1 sola llamada a la IA)",
            "Grupo Free" in sent_text and fake_client.messages.create.await_count == 1,
            f"text={sent_text!r}, ai_calls={fake_client.messages.create.await_count}",
        )

    # 18. IA no reconoce nada (classify -> fallback) -> usa draft_reply_ai.
    call_count = {"n": 0}

    async def fake_create(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return SimpleNamespace(content=[SimpleNamespace(text="fallback")])
        return SimpleNamespace(content=[SimpleNamespace(text="¡Qué bueno verte! Escribí grupos para ver las opciones.")])

    fake_client2 = MagicMock()
    fake_client2.messages.create = AsyncMock(side_effect=fake_create)
    sales_ai._client = fake_client2
    update, message = make_update("jaja que onda todo bien?")
    await sales_ai.handle_free_text_fallback(update, MagicMock())
    sent_text = message.reply_text.call_args.args[0] if message.reply_text.await_count else ""
    record(
        "18. IA no reconoce intent -> usa draft_reply_ai() para la respuesta genérica",
        sent_text == "¡Qué bueno verte! Escribí grupos para ver las opciones." and call_count["n"] == 2,
        f"text={sent_text!r}, llamadas_ia={call_count['n']}",
    )

    # 19. La IA falla en ambos pasos -> muestra el menú principal.
    failing_client = MagicMock()
    failing_client.messages.create = AsyncMock(side_effect=RuntimeError("fallo simulado de red"))
    sales_ai._client = failing_client
    with patch.object(multisale_handlers, "send_multisale_welcome", new=AsyncMock()) as mock_welcome:
        update, message = make_update("algo random sin sentido comercial")
        await sales_ai.handle_free_text_fallback(update, MagicMock())
        record("19. Si la IA falla en todo, muestra el menú principal (nunca silencio)", mock_welcome.await_count == 1)

    os.environ.pop("ANTHROPIC_API_KEY", None)
    sales_ai._client = None

    # 20. Update sin texto (ej. una foto): no debe lanzar excepción ni responder.
    message_no_text = MagicMock()
    message_no_text.text = None
    message_no_text.reply_text = AsyncMock()
    update_no_text = SimpleNamespace(effective_message=message_no_text)
    try:
        await sales_ai.handle_free_text_fallback(update_no_text, MagicMock())
        ok_no_text = message_no_text.reply_text.await_count == 0
    except Exception as e:
        ok_no_text = False
        record("20. update sin texto no lanza excepción", False, f"excepción: {e}")
    else:
        record("20. update sin texto no lanza excepción ni responde", ok_no_text, f"await_count={message_no_text.reply_text.await_count}")

    print("\n=== RESULTADOS ===")
    for line in PASS:
        print("✅", line)
    for line in FAIL:
        print("❌", line)

    import shutil
    shutil.rmtree(TMP_DATA_DIR, ignore_errors=True)

    if FAIL:
        print(f"\n{len(FAIL)} escenario(s) fallaron de {len(PASS) + len(FAIL)}.")
        sys.exit(1)

    print(f"\nTodos los escenarios pasaron ({len(PASS)}/{len(PASS)}).")


if __name__ == "__main__":
    asyncio.run(main())
