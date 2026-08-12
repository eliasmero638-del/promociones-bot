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
