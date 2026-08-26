#!/usr/bin/env python3
"""
Verificación end-to-end del sistema NUEVO de venta multi-grupo
(ventas/multisale_*.py): ejecuta las funciones REALES de
multisale_handlers.py (no una reimplementación) contra datos aislados
(DATA_DIR temporal - nunca toca ningún archivo/backend real).

Corre como script plano (no requiere pytest):
    python3 test_multisale.py

Cubre los escenarios pedidos en la especificación:
  1-5.  Selección de 1 a 5 grupos: precio automático correcto.
  6.    Cambiar la selección antes de pagar.
  7.    Pagos recientes: agregar/ver/quitar, conserva la selección.
  8-10. Datos de pago vistos una vez por (usuario, método); otro método
        nunca visto sigue disponible.
  11.   Borrado de datos de pago (job real, sin esperar 20 min).
  12-14. Comprobante: se crea la venta, se reenvía a TODOS los admins, se
         borra del chat del cliente, NO se borra del chat de los admins.
  15-16. Aprobación / rechazo manual.
  17-18. Aprobación automática tras 5 minutos (job real).
  19.   Reconciliación tras "reinicio" (recrea los stores desde disco).
  20-21. Se entregan EXACTAMENTE los grupos comprados, siempre por botón URL.
  23.   Dos administradores no pueden procesar la misma venta dos veces.
  24.   Los deep-links ?start=venta y ?start=demo no cambian de comportamiento.
"""
import asyncio
import os
import shutil
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

TMP_DATA_DIR = tempfile.mkdtemp(prefix="multisale_test_")
os.environ["BOT_TOKEN"] = "dummy:token"
os.environ["GROUP_ID"] = "-100123456789"
os.environ["DATA_DIR"] = TMP_DATA_DIR
os.environ.pop("UPSTASH_REDIS_REST_URL", None)
os.environ.pop("UPSTASH_REDIS_REST_TOKEN", None)

sys.path.insert(0, REPO_ROOT)
import bot  # noqa: E402
from ventas import multisale_handlers as h  # noqa: E402
from ventas import multisale_keyboards as kb  # noqa: E402
from ventas.multisale_config import (  # noqa: E402
    GROUP_KEYS,
    MultiSaleConfigManager,
    RecentPaymentsStore,
    get_individual_total,
    get_offer_price,
)
from ventas.multisale_storage import (  # noqa: E402
    MultiSaleRequestsManager,
    PendingAutoApprovalsStore,
    PendingPaymentDataDeletionsStore,
)

PASS = []
FAIL = []


def record(name, ok, detail=""):
    (PASS if ok else FAIL).append(f"{name}: {'OK' if ok else 'FALLÓ'}" + (f" ({detail})" if detail else ""))


def reset_storage():
    for fname in os.listdir(TMP_DATA_DIR):
        os.remove(os.path.join(TMP_DATA_DIR, fname))


def make_context(user_data=None):
    ctx = MagicMock()
    ctx.user_data = user_data if user_data is not None else {}
    sent = []
    copied_to_admins = {}

    async def fake_send_message(chat_id, text, **kwargs):
        sent.append({"chat_id": chat_id, "text": text, "kwargs": kwargs})
        msg = MagicMock()
        msg.message_id = 1000 + len(sent)
        return msg

    async def fake_copy_message(chat_id, from_chat_id, message_id, **kwargs):
        mid = 5000 + len(copied_to_admins)
        copied_to_admins[chat_id] = {"message_id": mid, "caption": kwargs.get("caption"), "reply_markup": kwargs.get("reply_markup")}
        result = MagicMock()
        result.message_id = mid
        return result

    ctx.bot = MagicMock()
    ctx.bot.send_message = AsyncMock(side_effect=fake_send_message)
    ctx.bot.send_photo = AsyncMock()
    ctx.bot.send_document = AsyncMock()
    ctx.bot.copy_message = AsyncMock(side_effect=fake_copy_message)
    ctx.bot.delete_message = AsyncMock()
    ctx.bot.edit_message_caption = AsyncMock()
    ctx.bot._sent = sent
    ctx.bot._copied_to_admins = copied_to_admins

    ctx.job_queue = MagicMock()
    scheduled_jobs = []

    def fake_run_once(callback, when, data=None, name=None):
        job = MagicMock()
        job.name = name
        job.callback = callback
        job.data = data
        job.when = when
        scheduled_jobs.append(job)
        return job

    def fake_get_jobs_by_name(name):
        return [j for j in scheduled_jobs if j.name == name]

    ctx.job_queue.run_once = MagicMock(side_effect=fake_run_once)
    ctx.job_queue.get_jobs_by_name = MagicMock(side_effect=fake_get_jobs_by_name)
    ctx.job_queue._scheduled_jobs = scheduled_jobs

    return ctx


def make_query(data, user_id, chat_id=555, message_id=1):
    query = MagicMock()
    query.data = data
    query.from_user.id = user_id
    query.answer = AsyncMock()
    edited = []

    async def fake_edit(text, **kwargs):
        edited.append({"text": text, "kwargs": kwargs})

    query.edit_message_text = AsyncMock(side_effect=fake_edit)
    query.message.chat_id = chat_id
    query.message.message_id = message_id
    query._edited = edited

    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = user_id
    return update, query


def make_receipt_update(user_id, chat_id, message_id, username="comprador1", first_name="Compradora"):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.effective_user.first_name = first_name

    message = MagicMock()
    message.chat_id = chat_id
    message.message_id = message_id
    photo_size = MagicMock()
    photo_size.file_id = f"FILEID_{message_id}"
    message.photo = [photo_size]
    message.document = None
    message.delete = AsyncMock()
    update.message = message
    return update


async def main():
    admin_id = bot.ADMIN_USER_ID
    buyer_id = 999111222

    # --- 1-5. Precio automático para 1..5 grupos ---
    expected = {1: 6.99, 2: 9.99, 3: 12.99, 4: 16.99, 5: 19.99}
    ok = all(get_offer_price(n) == expected[n] for n in range(1, 6))
    record("1-5. Tabla de precios 1..5 grupos", ok, str([get_offer_price(n) for n in range(1, 6)]))

    ok_individual = get_individual_total(3) == 20.97 and round(get_individual_total(3) - get_offer_price(3), 2) == 7.98
    record("Precio individual y ahorro (ejemplo de 3 grupos)", ok_individual, f"individual={get_individual_total(3)} ahorro={round(get_individual_total(3) - get_offer_price(3), 2)}")

    # --- Universitarias EC (6to grupo, a pedido explícito): precio propio
    # de $8 SOLO cuando se compra ella sola; cualquier combo de 2+ grupos
    # (la incluya o no) sigue usando la MISMA PRICE_TABLE de siempre, sin
    # cambios, y "los 6 grupos" cuesta igual que "los 5" costaba antes. ---
    ok_solo = get_offer_price(1, ["universitarias"]) == 8.00 and get_individual_total(1, ["universitarias"]) == 8.00
    record("Universitarias EC sola: $8 (precio propio, no el genérico de 1 grupo)", ok_solo, str(get_offer_price(1, ["universitarias"])))

    ok_otro_solo_sin_cambios = get_offer_price(1, ["azules"]) == 6.99
    record("Otro grupo solo sigue en $6.99 (sin cambios)", ok_otro_solo_sin_cambios, str(get_offer_price(1, ["azules"])))

    combo = ["portoviejo", "universitarias"]
    ok_combo_sin_cambios = get_offer_price(2, combo) == 9.99
    record("Combo de 2 grupos con Universitarias EC sigue en $9.99 (sin override)", ok_combo_sin_cambios, str(get_offer_price(2, combo)))

    ok_seis = get_offer_price(6, GROUP_KEYS) == 19.99
    record("Seleccionar los 6 grupos cuesta $19.99 (mismo tope que 5 antes)", ok_seis, str(get_offer_price(6, GROUP_KEYS)))

    # --- 6. Toggle de selección (elegir, deseleccionar, cambiar) ---
    reset_storage()
    user_data = {}
    ctx = make_context(user_data)
    update, query = make_query("ms_toggle_portoviejo", buyer_id)
    await h.ms_toggle_group(update, ctx)
    update, query = make_query("ms_toggle_manta", buyer_id)
    await h.ms_toggle_group(update, ctx)
    update, query = make_query("ms_toggle_portoviejo", buyer_id)  # deselecciona portoviejo
    await h.ms_toggle_group(update, ctx)
    ok = user_data.get("ms_selected") == {"manta"}
    record("6. Cambiar selección (toggle on/off)", ok, str(user_data.get("ms_selected")))

    # --- Flujo completo: selección -> oferta -> confirmación -> métodos ---
    reset_storage()
    user_data = {"ms_selected": {"portoviejo", "manta", "ecuatorianas"}}
    ctx = make_context(user_data)
    update, query = make_query("ms_continue", buyer_id)
    await h.ms_continue(update, ctx)
    ok = "OFERTA ESPECIAL" in query._edited[-1]["text"] and "$12.99" in query._edited[-1]["text"]
    record("Pantalla de oferta (3 grupos)", ok, query._edited[-1]["text"][:60])

    update, query = make_query("ms_offer_continue", buyer_id)
    await h.ms_offer_continue(update, ctx)
    ok = user_data.get("ms_locked_groups") == ["portoviejo", "manta", "ecuatorianas"] and user_data.get("ms_locked_price") == 12.99
    record("Confirmación fija (snapshot) la selección", ok, str(user_data.get("ms_locked_groups")))

    update, query = make_query("ms_confirm_pay", buyer_id)
    await h.ms_confirm_pay(update, ctx)
    ok = "MÉTODOS DE PAGO" in query._edited[-1]["text"]
    record("Pantalla de métodos de pago", ok)

    # --- 8-10. Datos de pago vistos una sola vez por (usuario, método) ---
    reset_storage()
    user_data = {"ms_locked_groups": ["portoviejo"], "ms_locked_price": 6.99}
    ctx = make_context(user_data)
    update, query = make_query("ms_method_bank_pichincha", buyer_id, message_id=42)
    state = await h.ms_method_selected(update, ctx)
    ok = state == h.MS_WAITING_RECEIPT and "BANCO PICHINCHA" in query._edited[-1]["text"].upper()
    record("8. Primera vez que ve Banco Pichincha: se muestran los datos", ok, query._edited[-1]["text"][:50])

    ok_scheduled = any(j.name == "ms_delete_paydata_555_42" for j in ctx.job_queue._scheduled_jobs)
    record("Se programa el auto-borrado de los datos de pago (20 min)", ok_scheduled)

    pichincha_job = next(j for j in ctx.job_queue._scheduled_jobs if j.name == "ms_delete_paydata_555_42")
    ok_20min = pichincha_job.when == 1200 and "20 minutos" in query._edited[-1]["text"]
    record(
        "Banco Pichincha: datos de pago duran 20 minutos",
        ok_20min,
        f"when={pichincha_job.when}",
    )

    # Pago interbancario: mismo mecanismo, pero 5 minutos en vez de 20.
    update, query = make_query("ms_method_interbancario", buyer_id, message_id=45)
    state_interbancario = await h.ms_method_selected(update, ctx)
    interbancario_job = next(j for j in ctx.job_queue._scheduled_jobs if j.name == "ms_delete_paydata_555_45")
    ok_5min = (
        state_interbancario == h.MS_WAITING_RECEIPT
        and interbancario_job.when == 300
        and "5 minutos" in query._edited[-1]["text"]
    )
    record(
        "Pago interbancario: datos de pago duran 5 minutos (el resto sigue en 20)",
        ok_5min,
        f"when={interbancario_job.when} texto={query._edited[-1]['text'][-60:]!r}",
    )

    # Excepción a pedido explícito: interbancario muestra la cédula del
    # titular, así que se queda en el límite viejo de 1 sola vista (el
    # resto de métodos sí permite 2, ver más abajo).
    update, query = make_query("ms_method_interbancario", buyer_id, message_id=47)
    state_interbancario2 = await h.ms_method_selected(update, ctx)
    ok = state_interbancario2 == bot.ConversationHandler.END and "ya fueron mostrados" in query._edited[-1]["text"]
    record("Interbancario: segunda vez YA bloqueado (límite de 1, por la cédula)", ok, query._edited[-1]["text"][:50])

    # A pedido explícito: los datos se pueden ver hasta 2 veces por
    # (usuario, método) - pensado para reintentos legítimos (ej. se cortó
    # el internet) - y solo se bloquean a partir de la 3ra vez.
    update, query = make_query("ms_method_bank_pichincha", buyer_id, message_id=43)
    state2 = await h.ms_method_selected(update, ctx)
    ok = state2 == h.MS_WAITING_RECEIPT and "BANCO PICHINCHA" in query._edited[-1]["text"].upper()
    record("9a. Segunda vez que pide Banco Pichincha: SÍ se muestran los datos otra vez", ok, query._edited[-1]["text"][:50])

    update, query = make_query("ms_method_bank_pichincha", buyer_id, message_id=46)
    state2b = await h.ms_method_selected(update, ctx)
    ok = state2b == bot.ConversationHandler.END and "ya fueron mostrados" in query._edited[-1]["text"]
    record("9b. Tercera vez que pide Banco Pichincha: recién ahí bloqueado", ok, query._edited[-1]["text"][:50])

    update, query = make_query("ms_method_paypal", buyer_id, message_id=44)
    state3 = await h.ms_method_selected(update, ctx)
    ok = state3 == h.MS_WAITING_RECEIPT and "PAYPAL" in query._edited[-1]["text"].upper()
    record("10. Un método nunca visto (PayPal) sigue disponible", ok, query._edited[-1]["text"][:50])

    # El administrador está exento del límite: puede ver los datos las
    # veces que quiera, para comprobar que todo funciona.
    for i in range(3):
        update, query = make_query("ms_method_bank_pichincha", admin_id, message_id=50 + i)
        state_admin = await h.ms_method_selected(update, ctx)
        ok_admin_i = state_admin == h.MS_WAITING_RECEIPT and "BANCO PICHINCHA" in query._edited[-1]["text"].upper()
        record(f"El administrador nunca queda bloqueado (intento {i + 1})", ok_admin_i, query._edited[-1]["text"][:50])

    # --- 11. Borrado de datos de pago (ejecuta el job real) ---
    job = next(j for j in ctx.job_queue._scheduled_jobs if j.name == "ms_delete_paydata_555_42")
    job_ctx = MagicMock()
    job_ctx.bot = ctx.bot
    job_ctx.job = job
    await job.callback(job_ctx)
    ok = ctx.bot.delete_message.call_args_list[-1].kwargs == {"chat_id": 555, "message_id": 42}
    record("11. El job de borrado de datos de pago borra el mensaje correcto", ok)

    # --- 12-14. Comprobante: crea la venta, reenvía a todos los admins, borra del cliente ---
    reset_storage()
    user_data = {"ms_locked_groups": ["portoviejo", "vipec"], "ms_locked_price": 9.99, "ms_payment_method": "bank_pichincha"}
    ctx = make_context(user_data)
    receipt_update = make_receipt_update(buyer_id, chat_id=buyer_id, message_id=77)
    state = await h.ms_receive_receipt(receipt_update, ctx)
    ok_end = state == bot.ConversationHandler.END
    record("12. ms_receive_receipt termina la conversación", ok_end)

    manager = MultiSaleRequestsManager()
    all_sales = manager.get_all()
    ok_created = len(all_sales) == 1 and all_sales[0]["groups"] == ["portoviejo", "vipec"] and all_sales[0]["price"] == 9.99
    record("12. La venta se creó con los grupos y precio correctos", ok_created, str(all_sales[0] if all_sales else None)[:120])
    sale_id = all_sales[0]["id"] if all_sales else None

    ok_deleted = receipt_update.message.delete.called
    record("13. El comprobante se borra del chat del cliente", ok_deleted)

    admin_ids_notified = set(ctx.bot._copied_to_admins.keys())
    ok_all_admins = admin_ids_notified == set(bot.ADMIN_USER_IDS)
    record("14. El comprobante se reenvía a TODOS los administradores", ok_all_admins, str(admin_ids_notified))

    ok_not_deleted_from_admin = ctx.bot.delete_message.call_count == 0 or all(
        c.kwargs.get("chat_id") not in bot.ADMIN_USER_IDS for c in ctx.bot.delete_message.call_args_list
    )
    record("El comprobante NO se borra del chat de los administradores", ok_not_deleted_from_admin)

    stored_sale = MultiSaleRequestsManager().get_by_id(sale_id)
    ok_msg_ids = set(int(k) for k in stored_sale.get("admin_message_ids", {}).keys()) == set(bot.ADMIN_USER_IDS)
    record("Se guardó el message_id de CADA administrador notificado", ok_msg_ids, str(stored_sale.get("admin_message_ids")))

    ok_auto_scheduled = any(j.name == f"ms_auto_approve_{sale_id}" for j in ctx.job_queue._scheduled_jobs)
    record("Se programó la aprobación automática (5 min)", ok_auto_scheduled)

    # --- 15. Aprobación manual: entrega EXACTAMENTE los grupos comprados ---
    update, query = make_query(f"ms_approve_{sale_id}", admin_id)
    await h.ms_approve_callback(update, ctx)
    stored_sale = MultiSaleRequestsManager().get_by_id(sale_id)
    ok_approved = stored_sale["status"] == "approved" and stored_sale["resolved_by"] == "ADMINISTRADOR"
    record("15. Aprobación manual actualiza el estado correctamente", ok_approved, str(stored_sale.get("status")))

    access_kb = next(
        (m for m in ctx.bot._sent if m["chat_id"] == buyer_id and m["text"] == h._access_delivery_text()), None
    )
    delivered_urls = []
    if access_kb:
        for row in access_kb["kwargs"]["reply_markup"].inline_keyboard:
            for btn in row:
                delivered_urls.append(btn.url)
    config = MultiSaleConfigManager()
    expected_urls = {config.get_group_link("portoviejo"), config.get_group_link("vipec")}
    ok_exact = set(delivered_urls) == expected_urls
    record("20-21. Se entregan EXACTAMENTE los 2 grupos comprados, como botones URL", ok_exact, str(delivered_urls))

    # --- 23. Dos administradores no pueden procesar la misma venta dos veces ---
    other_admin = (bot.ADMIN_USER_IDS - {admin_id}).pop() if len(bot.ADMIN_USER_IDS) > 1 else admin_id
    update, query = make_query(f"ms_reject_{sale_id}", other_admin)
    await h.ms_reject_callback(update, ctx)
    stored_sale = MultiSaleRequestsManager().get_by_id(sale_id)
    ok_still_approved = stored_sale["status"] == "approved"
    record("23. Un segundo admin no puede volver a resolver una venta ya aprobada", ok_still_approved, str(stored_sale.get("status")))

    ok_alert = query.answer.call_args is not None and "ya fue resuelta" in str(query.answer.call_args)
    record("Se le avisa al segundo admin que ya fue resuelta", ok_alert)

    # --- 16. Rechazo manual: no entrega ningún enlace ---
    reset_storage()
    user_data = {"ms_locked_groups": ["azules"], "ms_locked_price": 6.99, "ms_payment_method": "paypal"}
    ctx = make_context(user_data)
    receipt_update = make_receipt_update(buyer_id, chat_id=buyer_id, message_id=88)
    await h.ms_receive_receipt(receipt_update, ctx)
    manager = MultiSaleRequestsManager()
    sale_id_2 = manager.get_all()[0]["id"]

    update, query = make_query(f"ms_reject_{sale_id_2}", admin_id)
    await h.ms_reject_callback(update, ctx)
    stored_sale = MultiSaleRequestsManager().get_by_id(sale_id_2)
    ok_rejected = stored_sale["status"] == "rejected"
    record("16. Rechazo manual actualiza el estado", ok_rejected)

    reject_msgs = [m for m in ctx.bot._sent if m["chat_id"] == buyer_id and "NO APROBADO" in m["text"]]
    all_group_links = {config.get_group_link(k) for k in GROUP_KEYS}
    no_group_links = all(
        not any(getattr(btn, "url", None) in all_group_links for row in m["kwargs"].get("reply_markup").inline_keyboard for btn in row)
        for m in reject_msgs
        if m["kwargs"].get("reply_markup")
    ) if reject_msgs else False
    record("16. El rechazo no entrega ningún botón de enlace de grupo", bool(reject_msgs) and no_group_links)

    # Cancelar de nuevo (rechazado) no debe volver a hacer nada.
    update, query = make_query(f"ms_approve_{sale_id_2}", admin_id)
    await h.ms_approve_callback(update, ctx)
    stored_sale = MultiSaleRequestsManager().get_by_id(sale_id_2)
    ok_still_rejected = stored_sale["status"] == "rejected"
    record("Si ya fue rechazada, no se puede aprobar después", ok_still_rejected)

    # --- 17-18. Aprobación automática tras 5 minutos ---
    reset_storage()
    user_data = {"ms_locked_groups": ["ecuatorianas", "vipec", "azules"], "ms_locked_price": 12.99, "ms_payment_method": "interbancario"}
    ctx = make_context(user_data)
    receipt_update = make_receipt_update(buyer_id, chat_id=buyer_id, message_id=99)
    await h.ms_receive_receipt(receipt_update, ctx)
    manager = MultiSaleRequestsManager()
    sale_id_3 = manager.get_all()[0]["id"]

    auto_job = next(j for j in ctx.job_queue._scheduled_jobs if j.name == f"ms_auto_approve_{sale_id_3}")
    job_ctx = MagicMock()
    job_ctx.bot = ctx.bot
    job_ctx.job = auto_job
    await auto_job.callback(job_ctx)

    stored_sale = MultiSaleRequestsManager().get_by_id(sale_id_3)
    ok_auto = stored_sale["status"] == "approved" and stored_sale["resolved_by"] == "BOT" and "5 minutos" in stored_sale["reason"]
    record("17-18. Aprobación automática tras 5 min (sin acción del admin)", ok_auto, str(stored_sale.get("resolved_by")))

    auto_access_msgs = [m for m in ctx.bot._sent if m["chat_id"] == buyer_id and m["text"] == h._access_delivery_text()]
    auto_urls = set()
    for m in auto_access_msgs:
        for row in m["kwargs"]["reply_markup"].inline_keyboard:
            for btn in row:
                if getattr(btn, "url", None):
                    auto_urls.add(btn.url)
    expected_auto_urls = {config.get_group_link(k) for k in ["ecuatorianas", "vipec", "azules"]}
    record("20-21. Aprobación automática entrega exactamente los 3 grupos", auto_urls == expected_auto_urls, str(auto_urls))

    # Si el job dispara sobre una venta YA resuelta manualmente, no debe hacer nada raro.
    update, query = make_query(f"ms_approve_{sale_id_3}", admin_id)
    await h.ms_approve_callback(update, ctx)
    ok_noop = query.answer.call_args is not None and "ya fue resuelta" in str(query.answer.call_args)
    record("Tras la aprobación automática, un admin ya no puede volver a procesarla", ok_noop)

    # --- 19. Reconciliación tras "reinicio" (recrear los stores desde disco) ---
    reset_storage()
    PendingAutoApprovalsStore().add_pending("venta_99999", __import__("time").time() + 120)
    PendingPaymentDataDeletionsStore().add_pending(555, 42, __import__("time").time() + 60)
    ctx = make_context()
    job_ctx = MagicMock()
    job_ctx.job_queue = ctx.job_queue
    await h._reschedule_pending_ms_actions(job_ctx)
    scheduled_names = {j.name for j in ctx.job_queue._scheduled_jobs}
    ok_reconciled = "ms_auto_approve_venta_99999" in scheduled_names and "ms_delete_paydata_555_42" in scheduled_names
    record("19. Tras un 'reinicio', los timers pendientes se reprograman", ok_reconciled, str(scheduled_names))

    # --- 7. Pagos recientes: agregar VARIAS seguidas / ver / quitar ---
    # Regresión: bug real reportado en producción - enviar 5 fotos
    # seguidas tras /agregar_pago_reciente solo guardaba la primera,
    # porque ms_awaiting_recent_payment se apagaba después de la
    # primera foto. Este escenario ejercita el flujo real completo
    # (comando -> 5 fotos -> /listo_pagos_recientes), no solo el store.
    reset_storage()
    admin_user_data = {}
    admin_ctx = make_context(admin_user_data)

    def make_admin_message_update(text=None, photo=False):
        update = MagicMock()
        update.effective_user.id = admin_id
        message = MagicMock()
        replies = []

        async def fake_reply(t, **kwargs):
            replies.append(t)

        message.reply_text = AsyncMock(side_effect=fake_reply)
        if photo:
            photo_size = MagicMock()
            photo_size.file_id = f"FILEID_{len(replies)}_{id(message)}"
            message.photo = [photo_size]
            message.document = None
        message.args = None
        update.message = message
        update._replies = replies
        return update

    cmd_update = make_admin_message_update()
    cmd_update.message.text = "/agregar_pago_reciente"
    await h.ms_agregar_pago_reciente_command(cmd_update, admin_ctx)
    ok_started = admin_user_data.get("ms_awaiting_recent_payment") is True
    record("/agregar_pago_reciente activa la espera de fotos", ok_started)

    for _ in range(5):
        photo_update = make_admin_message_update(photo=True)
        await h.ms_admin_receive_recent_payment_photo(photo_update, admin_ctx)

    ok_5_saved = len(RecentPaymentsStore().get_all()) == 5
    record(
        "7. Enviar 5 fotos seguidas guarda las 5 (no solo la primera)",
        ok_5_saved,
        f"guardadas={len(RecentPaymentsStore().get_all())}",
    )

    listo_update = make_admin_message_update()
    await h.ms_listo_pagos_recientes_command(listo_update, admin_ctx)
    ok_stopped = admin_user_data.get("ms_awaiting_recent_payment") is None
    ok_confirmed = any("Se agregaron 5" in r for r in listo_update._replies)
    record("/listo_pagos_recientes apaga la espera y confirma el total", ok_stopped and ok_confirmed, listo_update._replies)

    # Tras /listo, una foto adicional NO debe guardarse (ya no está esperando).
    stray_photo_update = make_admin_message_update(photo=True)
    await h.ms_admin_receive_recent_payment_photo(stray_photo_update, admin_ctx)
    ok_no_stray = len(RecentPaymentsStore().get_all()) == 5
    record("Una foto después de /listo ya no se agrega", ok_no_stray)

    ok_removed = RecentPaymentsStore().remove_at(0) and len(RecentPaymentsStore().get_all()) == 4
    record("/quitar_pago_reciente elimina el correcto", ok_removed)

    # --- 24. Los deep-links ?start=venta y ?start=demo no cambian ---
    import inspect
    start_src = inspect.getsource(bot.start)
    ok_deep_links = (
        "SALES_DEEP_LINK_PAYLOAD" in start_src
        and "send_sales_welcome" in start_src
        and "SALES_DEMO_DEEP_LINK_PAYLOAD" in start_src
        and "send_demo_directly" in start_src
        and "send_multisale_welcome" in start_src
    )
    record("24. bot.start() sigue usando send_sales_welcome/send_demo_directly para los deep-links", ok_deep_links)

    # --- Regresión: ningún botón usa el esquema "tg://user?id=" ---
    # Telegram lo rechaza con "Button_user_invalid" (confirmado en
    # producción: rompía CADA /start, porque este botón vive en la
    # primera pantalla). Los mocks de este test no golpean la API real de
    # Telegram, así que no hubieran detectado esto directamente - pero sí
    # podemos verificar que ningún botón construido por este módulo use
    # ese esquema de URL nunca más.
    admin_kb = kb.admin_button(admin_id)
    ok_admin_button = not (admin_kb.url or "").startswith("tg://user")
    record("El botón de administrador no usa tg://user?id= (Button_user_invalid)", ok_admin_button, admin_kb.url)

    already_seen_kb = kb.payment_already_seen_keyboard(admin_id)
    all_urls_ok = all(
        not (btn.url or "").startswith("tg://user")
        for row in already_seen_kb.inline_keyboard
        for btn in row
        if btn.url
    )
    record("payment_already_seen_keyboard tampoco usa tg://user?id=", all_urls_ok)

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
