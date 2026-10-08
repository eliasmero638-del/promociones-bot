#!/usr/bin/env python3
"""
Verificación del catch-all de texto libre con IA (ventas/sales_ai.py):
ejecuta las funciones REALES del módulo (no una reimplementación) contra
un cliente de Anthropic simulado - nunca golpea la red real.

Corre como script plano (no requiere pytest):
    python3 test_sales_ai.py

Escenarios cubiertos:
  1. is_enabled() es False sin ANTHROPIC_API_KEY.
  2. draft_reply_ai() devuelve None si no está habilitada (sin llamar al
     cliente).
  3. handle_free_text_fallback() muestra el menú principal (WELCOME_TEXT +
     welcome_keyboard) cuando la IA no está habilitada - nunca se queda en
     silencio.
  4. handle_free_text_fallback() con IA habilitada: incluye la respuesta
     redactada por la IA junto con el mismo menú principal.
  5. draft_reply_ai() devuelve None (sin lanzar excepción) si el cliente
     de Anthropic falla.
  6. handle_free_text_fallback() ignora updates sin texto (ej. una foto)
     sin lanzar excepción.
"""
import asyncio
import os
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

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


async def main():
    # 1. Sin ANTHROPIC_API_KEY, is_enabled() es False.
    record("1. is_enabled() es False sin ANTHROPIC_API_KEY", sales_ai.is_enabled() is False)

    # 2. draft_reply_ai() devuelve None sin llamar al cliente.
    reply = await sales_ai.draft_reply_ai("hola, cuánto cuesta?")
    record("2. draft_reply_ai() devuelve None si no está habilitada", reply is None, f"reply={reply!r}")

    # 3. handle_free_text_fallback() sin IA: muestra el menú principal.
    update, message = make_update("hola")
    ctx = MagicMock()
    await sales_ai.handle_free_text_fallback(update, ctx)
    ok_menu = message.reply_text.await_count == 1
    sent_text = message.reply_text.call_args.args[0] if ok_menu else ""
    sent_markup = message.reply_text.call_args.kwargs.get("reply_markup")
    from ventas.handlers import WELCOME_TEXT
    from ventas import keyboards
    ok_text = sent_text == WELCOME_TEXT
    ok_markup = sent_markup is not None and sent_markup.inline_keyboard == keyboards.welcome_keyboard().inline_keyboard
    record(
        "3. handle_free_text_fallback() sin IA muestra el menú principal",
        ok_menu and ok_text and ok_markup,
        f"await_count={message.reply_text.await_count}, text={sent_text!r}",
    )

    # 4. Con IA habilitada (cliente simulado): incluye la respuesta de la IA.
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy"
    sales_ai._client = None  # fuerza reconstruir el cliente con la key simulada

    fake_response = SimpleNamespace(content=[SimpleNamespace(text="¡Hola! Mira los botones de abajo 😊")])
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_response)
    sales_ai._client = fake_client

    update, message = make_update("hola, qué tal")
    await sales_ai.handle_free_text_fallback(update, ctx)
    ok_call = message.reply_text.await_count == 1
    sent_text = message.reply_text.call_args.args[0] if ok_call else ""
    ok_ai_text = "¡Hola! Mira los botones de abajo 😊" in sent_text and WELCOME_TEXT in sent_text
    record(
        "4. handle_free_text_fallback() con IA incluye la respuesta redactada + el menú",
        ok_call and ok_ai_text,
        f"text={sent_text!r}",
    )

    # 5. Si el cliente de Anthropic falla, draft_reply_ai() degrada a None
    #    sin lanzar excepción (y handle_free_text_fallback sigue mostrando
    #    el menú, nunca se queda en silencio).
    failing_client = MagicMock()
    failing_client.messages.create = AsyncMock(side_effect=RuntimeError("fallo simulado de red"))
    sales_ai._client = failing_client
    reply = await sales_ai.draft_reply_ai("algo")
    record("5. draft_reply_ai() degrada a None si el cliente falla (sin excepción)", reply is None, f"reply={reply!r}")

    update, message = make_update("algo")
    await sales_ai.handle_free_text_fallback(update, ctx)
    ok_fallback_menu = message.reply_text.await_count == 1 and message.reply_text.call_args.args[0] == WELCOME_TEXT
    record(
        "5b. handle_free_text_fallback() sigue mostrando el menú si la IA falla",
        ok_fallback_menu,
        f"await_count={message.reply_text.await_count}",
    )

    # Limpieza: vuelve a deshabilitar la IA para no afectar otros escenarios.
    os.environ.pop("ANTHROPIC_API_KEY", None)
    sales_ai._client = None

    # 6. Update sin texto (ej. una foto): no debe lanzar excepción ni responder.
    message_no_text = MagicMock()
    message_no_text.text = None
    message_no_text.reply_text = AsyncMock()
    update_no_text = SimpleNamespace(effective_message=message_no_text)
    try:
        await sales_ai.handle_free_text_fallback(update_no_text, ctx)
        ok_no_text = message_no_text.reply_text.await_count == 0
    except Exception as e:
        ok_no_text = False
        record("6. update sin texto no lanza excepción", False, f"excepción: {e}")
    else:
        record("6. update sin texto no lanza excepción ni responde", ok_no_text, f"await_count={message_no_text.reply_text.await_count}")

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
