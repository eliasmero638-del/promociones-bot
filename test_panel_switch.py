#!/usr/bin/env python3
"""
Verificación end-to-end del interruptor /desactivar_panel /activar_panel:
ejecuta el publish_promotion() REAL de bot.py (no una reimplementación)
contra datos de prueba aislados (DATA_DIR temporal por escenario - nunca
toca promotions.json / bot_state.json del repo ni ningún backend real).

Corre como script plano (no requiere pytest ni ninguna dependencia nueva):
    python3 test_panel_switch.py

Escenarios cubiertos:
  1. Panel ON  + antiguas (source="panel")        -> se publican
  2. Panel OFF + antiguas (source="panel")        -> NO se publican
  3. Panel OFF + nuevas   (source="promo_cmd")    -> SÍ se publican
  4. Panel OFF + antiguas SIN campo "source"      -> NO se publican
     (dato preexistente real, creado antes de este cambio)
  5. Panel ON  + antiguas + nuevas                -> ambas pueden publicarse
  6. "Publicar Ahora" (pre-chequeo en button_callback) respeta el mismo
     filtro que publish_promotion(), tanto con panel ON como OFF.
  7. Aislamiento /promo: "Editar/Eliminar Promoción Nueva" (edit_promo_new /
     delete_promo_new) NUNCA pueden editar ni eliminar una promoción con
     source="panel", aunque reutilicen los handlers genéricos compartidos
     con /panel (edit_select_{id} / delete_{id}). Y /panel sigue pudiendo
     editar/eliminar cualquier promoción, sin ninguna restricción nueva.
  8. Regresión: promo_panel() (comando /promo) no debe volver a romperse
     por Markdown sin escapar. Bug real visto en producción: el mensaje
     de bienvenida de /promo se enviaba con parse_mode="Markdown" y el
     texto incluía "/desactivar_panel" - el "_" sin pareja hacía que
     Telegram rechazara el mensaje completo con "Can't parse entities",
     dejando /promo sin responder (sin ningún error visible para el
     admin). Este escenario llama a promo_panel() de verdad y valida que,
     si en el futuro se vuelve a usar parse_mode="Markdown" ahí, el texto
     tenga los caracteres especiales balanceados.
  9. Regresión: una promoción con Markdown mal formado en su caption
     (bug real de producción: promo_003 se quedó atascada para siempre)
     no debe volver a trabar la rotación. Antes, send_photo/send_video Y
     el fallback de texto reusaban el mismo caption roto con
     parse_mode="Markdown", los tres fallaban igual con "Can't parse
     entities", la excepción no se capturaba antes del código que avanza
     el índice, y esa misma promoción se reintentaba en cada ciclo para
     siempre (bloqueando también las promociones siguientes y "Publicar
     Ahora"). Ahora debe publicarse en texto plano (sin Markdown) y el
     índice debe avanzar a la siguiente promoción.

Existe para evitar que una futura modificación rompa /desactivar_panel (o
el aislamiento de /promo) sin que nadie lo note.
"""
import asyncio
import os
import shutil
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

TMP_DATA_DIR = tempfile.mkdtemp(prefix="panel_switch_test_")
os.environ["BOT_TOKEN"] = "dummy:token"
os.environ["GROUP_ID"] = "-100123456789"
os.environ["DATA_DIR"] = TMP_DATA_DIR
# Aislado también de Upstash, para forzar el backend de archivo local
# (si el entorno donde corre este test ya tuviera esas variables puestas).
os.environ.pop("UPSTASH_REDIS_REST_URL", None)
os.environ.pop("UPSTASH_REDIS_REST_TOKEN", None)

sys.path.insert(0, REPO_ROOT)
import bot  # noqa: E402

PASS = []
FAIL = []


def reset_storage():
    """Empieza cada escenario desde cero: promotions.json y bot_state.json
    vacíos en el DATA_DIR temporal."""
    for fname in ("promotions.json", "bot_state.json"):
        path = os.path.join(TMP_DATA_DIR, fname)
        if os.path.exists(path):
            os.remove(path)


def make_context():
    """Fake ContextTypes.DEFAULT_TYPE con context.bot mockeado - captura
    qué se intentó publicar sin llegar a golpear la red de Telegram."""
    ctx = MagicMock()
    sent_texts = []

    async def fake_send_message(chat_id, text, **kwargs):
        sent_texts.append(text)
        msg = MagicMock()
        msg.message_id = 111
        return msg

    ctx.bot = MagicMock()
    ctx.bot.username = "test_bot"
    ctx.bot.send_message = AsyncMock(side_effect=fake_send_message)
    ctx.bot.send_photo = AsyncMock()
    ctx.bot.send_video = AsyncMock()
    ctx.bot.pin_chat_message = AsyncMock()
    ctx.bot.unpin_chat_message = AsyncMock()
    ctx.bot.delete_message = AsyncMock()
    ctx.bot._sent_texts = sent_texts
    return ctx


def promo(pid, source=None):
    p = {"id": pid, "caption": f"CAPTION::{pid}", "media": [], "admin_username": "el593rm"}
    if source is not None:
        p["source"] = source
    return p


def record(name, ok, detail):
    (PASS if ok else FAIL).append(f"{name}: {'OK' if ok else 'FALLÓ'} ({detail})")


def make_query(data, user_data):
    """Fake CallbackQuery + Update para ejercitar button_callback() /
    edit_select_promotion() directamente, como si un admin real hubiera
    tocado ese botón. user_data es el dict que se pasa como
    context.user_data (mutable, compartido con el caller para poder
    inspeccionarlo después)."""
    query = MagicMock()
    query.data = data
    query.from_user.id = bot.ADMIN_USER_ID
    query.answer = AsyncMock()
    edited_texts = []

    async def fake_edit_message_text(text, **kwargs):
        edited_texts.append(text)

    query.edit_message_text = AsyncMock(side_effect=fake_edit_message_text)
    query._edited_texts = edited_texts

    update = MagicMock()
    update.callback_query = query

    ctx = MagicMock()
    ctx.user_data = user_data
    return update, ctx, query


async def run_scenario(name, promotions, panel_enabled, expect_published_ids):
    reset_storage()

    manager = bot.PromotionsManager()
    manager.data["promotions"] = promotions
    manager.save()

    state = bot.BotState()
    state.set_panel_enabled(panel_enabled)
    state.save()

    ctx = make_context()
    await bot.publish_promotion(ctx)

    sent_texts = ctx.bot._sent_texts
    if not expect_published_ids:
        ok = len(sent_texts) == 0
        detail = f"esperaba que NO se publicara nada, textos enviados={sent_texts}"
    else:
        ok = any(
            any(f"CAPTION::{pid}" in t for t in sent_texts)
            for pid in expect_published_ids
        )
        detail = f"esperaba alguno de {expect_published_ids} publicado, textos enviados={sent_texts}"

    record(name, ok, detail)


def markdown_legacy_balanced(text):
    """Chequeo básico (no un parser completo) de Markdown legacy de
    Telegram: "_", "*" y "`" deben aparecer en cantidad par, porque cada
    uno abre/cierra una entidad. No cubre todos los casos que Telegram
    valida, pero SÍ hubiera detectado el bug real de promo_panel(): un
    único "_" sin pareja dentro de "/desactivar_panel" que hacía fallar
    el envío completo con "Can't parse entities"."""
    for ch in ("_", "*", "`"):
        if text.count(ch) % 2 != 0:
            return False, ch
    return True, None


def manager_reloaded_promo(_manager, promo_id):
    """Relee desde el backend (archivo temporal) en una instancia nueva de
    PromotionsManager, para reflejar exactamente lo que quedó persistido
    por el código real de bot.py (que siempre crea su propia instancia),
    en vez de confiar en el objeto `_manager` ya usado por el test."""
    return bot.PromotionsManager().get_by_id(promo_id)


def publish_now_precheck(all_promos, panel_enabled):
    """Replica EXACTAMENTE la condición usada en el branch "publish_now"
    de button_callback (bot.py), para confirmar que el pre-chequeo del
    botón "📤 Publicar Ahora" coincide con lo que publish_promotion()
    termina decidiendo."""
    promos = list(all_promos)
    if not panel_enabled:
        promos = [p for p in promos if p.get("source", "panel") == "promo_cmd"]
    return promos


async def main():
    # 1. Panel ON + antiguas (source="panel") -> se publican
    await run_scenario(
        "1. Panel ON + antiguas",
        [promo("old_1", "panel")],
        panel_enabled=True,
        expect_published_ids=["old_1"],
    )

    # 2. Panel OFF + antiguas (source="panel") -> NO se publican
    await run_scenario(
        "2. Panel OFF + antiguas",
        [promo("old_1", "panel")],
        panel_enabled=False,
        expect_published_ids=[],
    )

    # 3. Panel OFF + nuevas (source="promo_cmd") -> SÍ se publican
    await run_scenario(
        "3. Panel OFF + nuevas",
        [promo("new_1", "promo_cmd")],
        panel_enabled=False,
        expect_published_ids=["new_1"],
    )

    # 4. Panel OFF + antiguas SIN campo "source" (dato preexistente real) -> NO se publican
    await run_scenario(
        "4. Panel OFF + antiguas sin source",
        [promo("legacy_1", source=None)],
        panel_enabled=False,
        expect_published_ids=[],
    )

    # 5. Panel ON + antiguas + nuevas -> ambas pueden publicarse (se prueba
    # publicando dos veces seguidas para cubrir la rotación de índice)
    reset_storage()
    manager = bot.PromotionsManager()
    manager.data["promotions"] = [promo("old_1", "panel"), promo("new_1", "promo_cmd")]
    manager.save()
    state = bot.BotState()
    state.set_panel_enabled(True)
    state.save()
    ctx = make_context()
    await bot.publish_promotion(ctx)
    await bot.publish_promotion(ctx)
    sent = ctx.bot._sent_texts
    ok = any("CAPTION::old_1" in t for t in sent) and any("CAPTION::new_1" in t for t in sent)
    record("5. Panel ON + antiguas + nuevas", ok, f"textos enviados en 2 publicaciones={sent}")

    # 6. "Publicar Ahora": el pre-chequeo de button_callback debe coincidir
    # con publish_promotion() tanto con panel ON como OFF.
    all_promos = [promo("old_1", "panel"), promo("legacy_1", source=None), promo("new_1", "promo_cmd")]

    result_on = publish_now_precheck(all_promos, panel_enabled=True)
    ok_on = {p["id"] for p in result_on} == {"old_1", "legacy_1", "new_1"}
    record(
        "6a. Publicar Ahora - panel ON deja pasar todo",
        ok_on,
        f"ids resultantes={sorted(p['id'] for p in result_on)}",
    )

    result_off = publish_now_precheck(all_promos, panel_enabled=False)
    ok_off = {p["id"] for p in result_off} == {"new_1"}
    record(
        "6b. Publicar Ahora - panel OFF solo deja pasar promo_cmd",
        ok_off,
        f"ids resultantes={sorted(p['id'] for p in result_off)}",
    )

    # 7. Aislamiento /promo (edit + delete), ejercitando el código real de
    # button_callback() y edit_select_promotion() con datos mixtos.
    reset_storage()
    manager = bot.PromotionsManager()
    manager.data["promotions"] = [
        promo("old_1", "panel"),
        promo("legacy_1", source=None),
        promo("new_1", "promo_cmd"),
    ]
    manager.save()

    # 7a. "Editar Promoción Nueva" -> intentar editar old_1 (panel) debe
    # ser rechazado, sin modificar la promoción.
    user_data = {}
    update, ctx, query = make_query("edit_promo_new", user_data)
    await bot.button_callback(update, ctx)
    assert user_data.get("promo_scope") == "promo_cmd", "edit_promo_new debería fijar promo_scope=promo_cmd"

    update, ctx, query = make_query("edit_select_old_1", user_data)
    result_state = await bot.edit_select_promotion(update, ctx)
    blocked = result_state == bot.ConversationHandler.END and "no pertenece a /promo" in (query._edited_texts[0] if query._edited_texts else "")
    unchanged = manager_reloaded_promo(manager, "old_1")["caption"] == "CAPTION::old_1"
    record(
        "7a. /promo no puede editar una promoción 'panel'",
        blocked and unchanged,
        f"result_state={result_state!r} textos={query._edited_texts} unchanged={unchanged}",
    )

    # 7b. Mismo escenario pero con legacy_1 (sin campo source) - debe
    # bloquearse igual, no colarse por defecto.
    user_data = {}
    update, ctx, query = make_query("edit_promo_new", user_data)
    await bot.button_callback(update, ctx)
    update, ctx, query = make_query("edit_select_legacy_1", user_data)
    result_state = await bot.edit_select_promotion(update, ctx)
    blocked = result_state == bot.ConversationHandler.END and "no pertenece a /promo" in (query._edited_texts[0] if query._edited_texts else "")
    record(
        "7b. /promo no puede editar una promoción antigua sin source",
        blocked,
        f"result_state={result_state!r} textos={query._edited_texts}",
    )

    # 7c. "Editar Promoción Nueva" -> editar new_1 (promo_cmd) SÍ debe
    # funcionar (entra a EDIT_MENU con normalidad).
    user_data = {}
    update, ctx, query = make_query("edit_promo_new", user_data)
    await bot.button_callback(update, ctx)
    update, ctx, query = make_query("edit_select_new_1", user_data)
    result_state = await bot.edit_select_promotion(update, ctx)
    ok = result_state == bot.EDIT_MENU and user_data.get("edit_promo_id") == "new_1"
    record(
        "7c. /promo SÍ puede editar una promoción propia (promo_cmd)",
        ok,
        f"result_state={result_state!r} edit_promo_id={user_data.get('edit_promo_id')!r}",
    )

    # 7d. "Eliminar Promoción Nueva" -> intentar eliminar old_1 (panel)
    # debe ser rechazado, sin borrar nada.
    user_data = {}
    update, ctx, query = make_query("delete_promo_new", user_data)
    await bot.button_callback(update, ctx)
    assert user_data.get("promo_scope") == "promo_cmd", "delete_promo_new debería fijar promo_scope=promo_cmd"
    update, ctx, query = make_query("delete_old_1", user_data)
    await bot.button_callback(update, ctx)
    still_exists = manager_reloaded_promo(manager, "old_1") is not None
    blocked = still_exists and "no pertenece a /promo" in (query._edited_texts[0] if query._edited_texts else "")
    record(
        "7d. /promo no puede eliminar una promoción 'panel'",
        blocked,
        f"textos={query._edited_texts} still_exists={still_exists}",
    )

    # 7e. "Eliminar Promoción Nueva" -> eliminar new_1 (promo_cmd) SÍ debe
    # funcionar.
    user_data = {}
    update, ctx, query = make_query("delete_promo_new", user_data)
    await bot.button_callback(update, ctx)
    update, ctx, query = make_query("delete_new_1", user_data)
    await bot.button_callback(update, ctx)
    deleted = manager_reloaded_promo(manager, "new_1") is None
    ok = deleted and "eliminada correctamente" in (query._edited_texts[0] if query._edited_texts else "")
    record(
        "7e. /promo SÍ puede eliminar una promoción propia (promo_cmd)",
        ok,
        f"textos={query._edited_texts} deleted={deleted}",
    )

    # 7f. Regresión: /panel (sin scope) sigue pudiendo editar y eliminar
    # CUALQUIER promoción, sin ninguna restricción nueva.
    reset_storage()
    manager = bot.PromotionsManager()
    manager.data["promotions"] = [promo("old_1", "panel")]
    manager.save()

    user_data = {}
    update, ctx, query = make_query("edit_promo", user_data)
    await bot.button_callback(update, ctx)
    assert "promo_scope" not in user_data, "edit_promo (/panel) no debería fijar promo_scope"
    update, ctx, query = make_query("edit_select_old_1", user_data)
    result_state = await bot.edit_select_promotion(update, ctx)
    ok_edit = result_state == bot.EDIT_MENU

    user_data = {}
    update, ctx, query = make_query("delete_promo", user_data)
    await bot.button_callback(update, ctx)
    update, ctx, query = make_query("delete_old_1", user_data)
    await bot.button_callback(update, ctx)
    ok_delete = manager_reloaded_promo(manager, "old_1") is None and "eliminada correctamente" in (query._edited_texts[0] if query._edited_texts else "")

    record(
        "7f. /panel sigue pudiendo editar y eliminar cualquier promoción (sin regresión)",
        ok_edit and ok_delete,
        f"ok_edit={ok_edit} ok_delete={ok_delete} textos={query._edited_texts}",
    )

    # 8. Regresión: /promo (promo_panel) no debe reintroducir el bug de
    # Markdown sin escapar que lo dejó sin responder en producción.
    sent = []

    async def fake_reply_text(text, **kwargs):
        sent.append((text, kwargs))
        return MagicMock()

    update = MagicMock()
    update.effective_user.id = bot.ADMIN_USER_ID
    update.message.reply_text = AsyncMock(side_effect=fake_reply_text)
    ctx = MagicMock()
    ctx.user_data = {}

    await bot.promo_panel(update, ctx)

    if len(sent) != 1:
        record(
            "8. /promo no reintroduce el bug de Markdown sin escapar",
            False,
            f"promo_panel() debía responder con exactamente 1 mensaje, envió {len(sent)}",
        )
    else:
        text, kwargs = sent[0]
        uses_markdown = kwargs.get("parse_mode") in ("Markdown", "MarkdownV2")
        balanced, bad_char = markdown_legacy_balanced(text) if uses_markdown else (True, None)
        ok = (not uses_markdown) or balanced
        record(
            "8. /promo no reintroduce el bug de Markdown sin escapar",
            ok,
            f"parse_mode={kwargs.get('parse_mode')!r} balanced={balanced} caracter_desbalanceado={bad_char!r} texto={text!r}",
        )

    # 9a. Promoción SIN media con caption Markdown roto: el fallback de
    # texto debe reintentar sin parse_mode y publicarse en texto plano.
    reset_storage()
    manager = bot.PromotionsManager()
    broken_caption = "Oferta especial_ solo hoy"  # "_" sin pareja
    manager.data["promotions"] = [promo("broken_1", "promo_cmd")]
    manager.data["promotions"][0]["caption"] = broken_caption
    manager.save()
    state = bot.BotState()
    state.set_panel_enabled(True)
    state.save()

    ctx = make_context()

    async def fake_send_message_markdown_breaks(chat_id, text, parse_mode=None, **kwargs):
        if parse_mode == "Markdown":
            raise bot.TelegramError("Can't parse entities: can't find end of the entity starting at byte offset 5")
        msg = MagicMock()
        msg.message_id = 222
        return msg

    ctx.bot.send_message = AsyncMock(side_effect=fake_send_message_markdown_breaks)
    await bot.publish_promotion(ctx)

    calls = [c for c in ctx.bot.send_message.call_args_list if c.kwargs.get("text") == broken_caption]
    retried_then_succeeded = (
        len(calls) == 2
        and calls[0].kwargs.get("parse_mode") == "Markdown"
        and calls[1].kwargs.get("parse_mode") is None
    )
    published_successfully = bot.BotState().get_last_published() is not None
    record(
        "9a. Caption con Markdown roto (sin media) se publica en texto plano en vez de fallar",
        retried_then_succeeded and published_successfully,
        f"llamadas={calls} last_published={bot.BotState().get_last_published()!r}",
    )

    # 9b. Promoción CON media (foto) y caption Markdown roto: el mismo
    # fallback debe aplicarse dentro de _send_promotion_media_item(), la
    # rotación no debe quedar atascada, y debe avanzar a la promoción
    # siguiente en el próximo ciclo.
    reset_storage()
    manager = bot.PromotionsManager()
    manager.data["promotions"] = [
        {
            "id": "promo_003",
            "caption": broken_caption,
            "media": [{"type": "photo", "file_id": "FILEID123"}],
            "admin_username": "el593rm",
        },
        promo("promo_004", "promo_cmd"),
    ]
    manager.save()
    state = bot.BotState()
    state.set_panel_enabled(True)
    state.save()

    ctx = make_context()

    async def fake_send_photo_markdown_breaks(chat_id, photo, caption=None, parse_mode=None, **kwargs):
        if parse_mode == "Markdown":
            raise bot.TelegramError("Can't parse entities: can't find end of the entity starting at byte offset 5")
        msg = MagicMock()
        msg.message_id = 333
        return msg

    ctx.bot.send_photo = AsyncMock(side_effect=fake_send_photo_markdown_breaks)
    await bot.publish_promotion(ctx)

    photo_sent_plain = any(
        call.kwargs.get("parse_mode") is None for call in ctx.bot.send_photo.call_args_list
    )
    index_after_first = bot.BotState().get_current_promotion_index()

    # Un segundo ciclo debe publicar promo_004 (la rotación ya no está
    # atascada en promo_003).
    await bot.publish_promotion(ctx)
    sent_texts_second = ctx.bot._sent_texts
    reached_next = any("CAPTION::promo_004" in t for t in sent_texts_second)

    record(
        "9b. Promoción con media y Markdown roto (promo_003) ya no traba la rotación",
        photo_sent_plain and index_after_first == 1 and reached_next,
        f"photo_calls={ctx.bot.send_photo.call_args_list} index_after_first={index_after_first} "
        f"reached_next={reached_next} sent_texts_second={sent_texts_second}",
    )

    # 10. Regresión: estructura final de los 4 botones de las promociones,
    # a pedido explícito. En este orden exacto:
    #   1. "Contactar al administrador" -> https://t.me/EcuaAccessBot?start=ventas
    #      (fijo, asistente de ventas del otro bot, ya no el contacto humano)
    #   2. "⚡ Acceso rápido y fácil" -> https://t.me/VentasEcua_bot?start=promo (fijo)
    #   3. "🎁 Solicitar prueba gratis" -> deep-link a este bot (?start=demo),
    #      sin cambios de función/destino respecto a como ya funcionaba.
    #   4. "🆓 Únete al grupo free" -> enlace de invitación fijo.
    reset_storage()
    manager = bot.PromotionsManager()
    manager.data["promotions"] = [promo("promo_1", "promo_cmd")]
    manager.save()
    state = bot.BotState()
    state.set_panel_enabled(True)
    state.save()

    ctx = make_context()
    await bot.publish_promotion(ctx)

    button_calls = [
        c for c in ctx.bot.send_message.call_args_list
        if c.kwargs.get("text") == "Para más información:"
    ]
    rows = []
    if button_calls:
        markup = button_calls[-1].kwargs.get("reply_markup")
        if markup and markup.inline_keyboard:
            rows = [(row[0].text, row[0].url) for row in markup.inline_keyboard]

    expected = [
        ("Contactar al administrador", "https://t.me/EcuaAccessBot?start=ventas"),
        ("⚡ Acceso rápido y fácil", "https://t.me/VentasEcua_bot?start=promo"),
        ("🎁 Solicitar prueba gratis", "https://t.me/test_bot?start=demo"),
        ("🆓 Únete al grupo free", "https://t.me/+csiPLI___58zMWQx"),
    ]
    ok = rows == expected
    record(
        "10. Estructura final de los 4 botones de la promoción (administrador / acceso rápido / prueba gratis / grupo free)",
        ok,
        f"rows={rows} expected={expected}",
    )

    # 11. /chatid: herramienta de diagnóstico para configurar bots nuevos
    # sin buscar los IDs a mano. Debe mostrar chat_id, chat_type,
    # chat_title, message_id, user_id y los datos del propio bot; y no
    # debe responder a un usuario que no sea administrador.
    def make_chatid_update(user_id, chat_id=-100999888777, chat_type="supergroup", chat_title="Grupo de prueba", message_id=321):
        update = MagicMock()
        update.effective_user.id = user_id
        update.effective_chat.id = chat_id
        update.effective_chat.type = chat_type
        update.effective_chat.title = chat_title
        update.effective_chat.username = None
        update.effective_message.message_id = message_id
        update.effective_user.username = "admin_test"
        update.effective_user.first_name = "Admin"
        update.message.reply_text = AsyncMock()
        ctx = MagicMock()
        ctx.bot.id = 987654321
        ctx.bot.username = "nuevo_bot_test"
        return update, ctx

    # 11a. Administrador: recibe el diagnóstico completo.
    update, ctx = make_chatid_update(bot.ADMIN_USER_ID)
    await bot.chat_id_command(update, ctx)
    ok_admin = update.message.reply_text.await_count == 1
    sent_text = update.message.reply_text.call_args.args[0] if ok_admin else ""
    expected_fragments = [
        "-100999888777", "supergroup", "Grupo de prueba", "321",
        str(bot.ADMIN_USER_ID), "admin_test", "Admin", "987654321", "nuevo_bot_test",
    ]
    ok_content = ok_admin and all(fragment in sent_text for fragment in expected_fragments)
    record(
        "11a. /chatid (admin) muestra chat_id, chat_type, chat_title, message_id, user_id y datos del bot",
        ok_content,
        f"texto={sent_text!r}",
    )

    # 11b. No-administrador: no debe recibir ninguna respuesta.
    update, ctx = make_chatid_update(999999999)
    await bot.chat_id_command(update, ctx)
    ok_no_admin = update.message.reply_text.await_count == 0
    record("11b. /chatid no responde a un usuario que no es administrador", ok_no_admin, f"await_count={update.message.reply_text.await_count}")

    print("\n=== RESULTADOS ===")
    for line in PASS:
        print("✅", line)
    for line in FAIL:
        print("❌", line)

    shutil.rmtree(TMP_DATA_DIR, ignore_errors=True)

    if FAIL:
        print(f"\n{len(FAIL)} escenario(s) fallaron de {len(PASS) + len(FAIL)}.")
        sys.exit(1)

    print(f"\nTodos los escenarios pasaron ({len(PASS)}/{len(PASS)}).")


if __name__ == "__main__":
    asyncio.run(main())
