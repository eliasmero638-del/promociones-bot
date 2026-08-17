"""
Handlers del sistema NUEVO de venta multi-grupo (5 grupos, selección
múltiple, precios por combo, comprobante con reenvío a todos los admins,
aprobación manual o automática a los 5 minutos).

Completamente independiente de ventas/handlers.py (el sistema viejo de 2
grupos, sin comprobante, sin aprobación automática) - no se importa nada
de ahí y no se modifica ese archivo. Todo el callback_data de este módulo
usa el prefijo "ms_" en exclusiva.

Flujo:
  /start (sin deep-link, ver bot.py::start) -> send_multisale_welcome():
  menú de 5 grupos con selección múltiple
    -> ms_toggle_group(): marca/desmarca un grupo (✅/⬜), reescribe el
       mismo mensaje.
    -> ms_recent_payments()/ms_recent_back(): pantalla de comprobantes de
       muestra, conserva la selección.
    -> ms_continue(): calcula el precio automáticamente y muestra la
       oferta.
    -> ms_offer_continue(): fija (snapshot) los grupos seleccionados en
       context.user_data["ms_locked_groups"] y muestra la confirmación.
    -> ms_confirm_pay(): muestra los métodos de pago.
    -> ms_method_selected() [entry point de la conversación]: si el
       usuario ya vio ese método antes (PaymentDataSeenStore, permanente),
       muestra el aviso y termina; si no, muestra los datos, los marca
       como vistos, programa su borrado según el método (interbancario =
       5 min, el resto = 20 min - ver get_payment_data_lifetime_seconds())
       con recuperación tras reinicio vía PendingPaymentDataDeletionsStore,
       y pasa al estado MS_WAITING_RECEIPT.
    -> ms_receive_receipt(): guarda la venta, reenvía el comprobante a
       TODOS los administradores (con botones Aprobar/Rechazar), borra el
       comprobante del chat del cliente, programa la aprobación
       automática a los 5 minutos (con recuperación tras reinicio vía
       PendingAutoApprovalsStore).

  Admin:
    ms_approve_callback() / ms_reject_callback(): resuelven la venta,
    cancelan el timer automático, actualizan el mensaje de TODOS los
    administradores notificados, y entregan (o no) los enlaces exactos.
    _ms_auto_approve_job(): igual que la aprobación manual, pero disparado
    por JobQueue si nadie actuó en 5 minutos.

  /agregar_pago_reciente, /ver_pagos_recientes, /quitar_pago_reciente:
    gestión de las imágenes de muestra mostradas en "💳 Pagos de clientes
    recientes" (solo administradores).
"""

import logging
import time
from datetime import datetime

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from . import multisale_keyboards as kb
from .multisale_config import (
    GROUP_KEYS,
    PAYMENT_METHOD_KEYS,
    MultiSaleConfigManager,
    PaymentDataSeenStore,
    RecentPaymentsStore,
    get_individual_total,
    get_offer_price,
)
from .multisale_storage import (
    MultiSaleRequestsManager,
    PendingAutoApprovalsStore,
    PendingPaymentDataDeletionsStore,
)

logger = logging.getLogger("bot")

# Estado propio de este ConversationHandler (independiente de los de bot.py
# y de ventas/handlers.py - cada ConversationHandler mantiene su propia
# máquina de estados, sin colisión posible entre ellas).
(MS_WAITING_RECEIPT,) = range(1)

# Tiempo que quedan visibles los datos de pago antes de auto-borrarse, por
# método: "Pago interbancario" queda en 5 minutos, el resto (Pichincha,
# Guayaquil, PayPal) en 20. get_payment_data_lifetime_seconds() resuelve
# cuál aplica en cada caso.
PAYMENT_DATA_LIFETIME_SECONDS_DEFAULT = 1200  # 20 minutos
PAYMENT_DATA_LIFETIME_SECONDS_BY_METHOD = {
    "interbancario": 300,  # 5 minutos
}
AUTO_APPROVAL_SECONDS = 300  # 5 minutos


def get_payment_data_lifetime_seconds(method_key: str) -> int:
    return PAYMENT_DATA_LIFETIME_SECONDS_BY_METHOD.get(method_key, PAYMENT_DATA_LIFETIME_SECONDS_DEFAULT)
# Cuánto puede esperar un comprador, tras ver los datos de pago, antes de
# que la conversación se cierre por inactividad. Más largo que el resto
# del proyecto a propósito: acá se espera a que la persona complete una
# transferencia bancaria real, no solo que escriba texto.
MS_CONVERSATION_TIMEOUT_SECONDS = 1800  # 30 minutos


def _get_admin_user_id():
    from bot import ADMIN_USER_ID
    return ADMIN_USER_ID


def _get_admin_user_ids():
    from bot import ADMIN_USER_IDS
    return ADMIN_USER_IDS


async def _safe_edit_message(query, text, reply_markup=None):
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except TelegramError as e:
        logger.warning(f"[multisale] Could not edit message: {e}")


def _pluralize_grupo(count: int) -> str:
    return "grupo" if count == 1 else "grupos"


# --- Textos ---

def _menu_text(config: MultiSaleConfigManager) -> str:
    lines = [
        "🔥 BIENVENIDO/A",
        "",
        "Tenemos 5 grupos exclusivos, cada uno con un tipo de contenido diferente:",
        "",
    ]
    for key in GROUP_KEYS:
        lines.append(config.get_group_label(key))
        lines.append(config.get_group_description(key))
        lines.append("")
    lines.append("👇 Selecciona los grupos que te interesan:")
    lines.append("Puedes seleccionar uno, varios o los cinco.")
    return "\n".join(lines)


def _offer_text(config: MultiSaleConfigManager, selected_keys) -> str:
    count = len(selected_keys)
    individual_total = get_individual_total(count)
    offer_price = get_offer_price(count)
    savings = round(individual_total - offer_price, 2)
    lines = [
        "🔥 OFERTA ESPECIAL",
        "",
        f"Has seleccionado {count} {_pluralize_grupo(count)}:",
        "",
    ]
    for key in selected_keys:
        lines.append(config.get_group_label(key))
    lines.append("")
    lines.append(f"Precio individual: ${individual_total:.2f}")
    lines.append("")
    lines.append(f"🔥 Oferta: ${offer_price:.2f}")
    lines.append(f"💰 Ahorras ${savings:.2f}")
    return "\n".join(lines)


def _confirm_text(config: MultiSaleConfigManager, selected_keys, price: float) -> str:
    lines = ["🛒 CONFIRMA TU SELECCIÓN", ""]
    for key in selected_keys:
        lines.append(config.get_group_label(key))
    lines.append("")
    lines.append(f"💵 Total: ${price:.2f}")
    lines.append("")
    lines.append("¿Deseas continuar con el pago?")
    return "\n".join(lines)


def _payment_data_text(config: MultiSaleConfigManager, method_key: str, price: float) -> str:
    label = config.get_payment_method_label(method_key)
    details = config.get_payment_method_details(method_key)
    minutes = get_payment_data_lifetime_seconds(method_key) // 60
    return (
        f"{label.upper()}\n\n"
        f"{details}\n\n"
        f"💵 Valor a pagar: ${price:.2f}\n\n"
        f"⏱️ Estos datos estarán disponibles durante {minutes} minutos.\n\n"
        "Una vez realizado el pago, envía tu comprobante."
    )


ALREADY_SEEN_TEXT = (
    "⚠️ Los datos de pago ya fueron mostrados.\n\n"
    "Para solicitar nuevamente los datos de pago debes comunicarte con el administrador."
)

RECEIPT_RECEIVED_TEXT = (
    "⏳ PAGO EN PROCESO\n\n"
    "Hemos recibido tu comprobante correctamente.\n\n"
    "Tu pago está siendo procesado.\n\n"
    "⚠️ Importante: el envío de comprobantes falsos, alterados o utilizados para intentar "
    "obtener acceso sin realizar el pago correspondiente provocará el bloqueo de la cuenta "
    "y la pérdida de todos los accesos."
)

APPROVED_MANUAL_TEXT = (
    "✅ PAGO APROBADO POR EL ADMINISTRADOR\n\n"
    "Tu comprobante ha sido revisado y tu pago fue aprobado correctamente.\n\n"
    "🎉 Tu acceso está listo."
)

APPROVED_AUTO_TEXT = (
    "🤖 PAGO APROBADO AUTOMÁTICAMENTE\n\n"
    "Han transcurrido 5 minutos sin recibir una acción del administrador.\n\n"
    "El sistema ha aprobado automáticamente tu solicitud y tus accesos están listos.\n\n"
    "⚠️ Importante: todos los comprobantes pueden ser revisados posteriormente. El envío "
    "de comprobantes falsos, alterados o utilizados para intentar obtener acceso sin "
    "realizar el pago correspondiente provocará el bloqueo de la cuenta y la pérdida de "
    "todos los accesos."
)

REJECTED_TEXT = (
    "❌ PAGO NO APROBADO\n\n"
    "No hemos podido validar el comprobante enviado.\n\n"
    "Para solucionar cualquier inconveniente, comunícate con el administrador."
)

SECURITY_TEXT = (
    "⚠️ Importante:\n\n"
    "Estos accesos son personales y están destinados únicamente para tu cuenta de Telegram.\n\n"
    "No compartas los enlaces con otras personas.\n\n"
    "El uso indebido o los intentos de acceder desde otras cuentas pueden ocasionar la "
    "pérdida del acceso."
)


def _access_delivery_text() -> str:
    return "Estos son los grupos que seleccionaste:"


def _admin_notification_text(request: dict, config: MultiSaleConfigManager) -> str:
    username_part = f"@{request['user_username']}" if request.get("user_username") else f"id {request['user_id']}"
    lines = [
        "🔔 NUEVO COMPROBANTE DE PAGO",
        "",
        f"👤 Usuario: {request['user_first_name']} ({username_part})",
        f"🆔 Telegram ID: {request['user_id']}",
        "",
        "🛒 Grupos seleccionados:",
    ]
    for key in request["groups"]:
        lines.append(f"• {config.get_group_label(key)}")
    lines.append("")
    lines.append(f"💰 Total: ${request['price']:.2f}")
    lines.append(f"💳 Método: {request['payment_method_label']}")
    lines.append("")
    lines.append("⏱️ Aprobación automática en: 05:00")
    return "\n".join(lines)


# --- Menú principal ---

def _selected_set(context: ContextTypes.DEFAULT_TYPE) -> set:
    return context.user_data.setdefault("ms_selected", set())


async def send_multisale_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú principal del sistema nuevo - llamado desde bot.py::start()
    cuando no hay deep-link. Envía un mensaje NUEVO (no edita), igual que
    send_sales_welcome() del sistema viejo."""
    config = MultiSaleConfigManager()
    admin_id = _get_admin_user_id()
    selected = _selected_set(context)
    await update.effective_message.reply_text(
        _menu_text(config), reply_markup=kb.menu_keyboard(config, selected, admin_id)
    )


async def ms_toggle_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    group_key = query.data[len("ms_toggle_"):]
    if group_key not in GROUP_KEYS:
        await query.answer()
        return

    config = MultiSaleConfigManager()
    selected = _selected_set(context)
    if group_key in selected:
        selected.discard(group_key)
        now_selected = False
    else:
        selected.add(group_key)
        now_selected = True

    # Toast de confirmación en cada toque (antes era silencioso): así el
    # comprador ve de inmediato si quedó marcado o desmarcado, en vez de
    # depender únicamente de que el mensaje se vuelva a dibujar - reduce
    # el riesgo de un doble-toque accidental por duda ("¿sí funcionó?").
    label = config.get_group_label(group_key)
    mark = "✅ Agregado" if now_selected else "⬜ Quitado"
    await query.answer(f"{mark}: {label}")

    logger.info(
        f"[multisale] user={update.effective_user.id} toggled '{group_key}' "
        f"-> {'seleccionado' if now_selected else 'deseleccionado'}. "
        f"Selección actual: {sorted(selected)}"
    )

    admin_id = _get_admin_user_id()
    await _safe_edit_message(query, _menu_text(config), reply_markup=kb.menu_keyboard(config, selected, admin_id))


async def ms_recent_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"💳 Pagos de clientes recientes": edita el mensaje actual con el
    encabezado, envía cada imagen de muestra como mensaje nuevo, y termina
    con el botón de volver. Conserva ms_selected sin tocarlo."""
    query = update.callback_query
    await query.answer()

    admin_id = _get_admin_user_id()
    payments = RecentPaymentsStore().get_all()

    header = "💳 PAGOS DE CLIENTES RECIENTES\n\nAquí puedes ver comprobantes de pagos realizados recientemente por clientes que ya ingresaron a nuestros grupos."
    if not payments:
        header += "\n\n(Todavía no hay comprobantes de muestra cargados.)"

    await _safe_edit_message(query, header)

    chat_id = query.message.chat_id
    for payment in payments:
        try:
            if payment.get("file_type") == "document":
                await context.bot.send_document(chat_id=chat_id, document=payment["file_id"])
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=payment["file_id"])
        except TelegramError as e:
            logger.warning(f"[multisale] Could not send recent-payment sample {payment.get('file_id')}: {e}")

    await context.bot.send_message(
        chat_id=chat_id, text="👇", reply_markup=kb.recent_payments_keyboard(admin_id)
    )


async def ms_recent_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vuelve a la selección de grupos, conservando ms_selected. Envía un
    mensaje NUEVO (la pantalla anterior fue una secuencia de varios
    mensajes, no uno solo editable)."""
    query = update.callback_query
    await query.answer()

    config = MultiSaleConfigManager()
    admin_id = _get_admin_user_id()
    selected = _selected_set(context)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=_menu_text(config),
        reply_markup=kb.menu_keyboard(config, selected, admin_id),
    )


async def ms_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"✅ Continuar": calcula el precio automáticamente y muestra la
    oferta."""
    query = update.callback_query
    selected = _selected_set(context)
    if not selected:
        logger.info(f"[multisale] user={update.effective_user.id} presionó Continuar sin ningún grupo seleccionado.")
        await query.answer("Selecciona al menos un grupo antes de continuar.", show_alert=True)
        return
    await query.answer()

    config = MultiSaleConfigManager()
    admin_id = _get_admin_user_id()
    ordered_selection = [key for key in GROUP_KEYS if key in selected]
    logger.info(f"[multisale] user={update.effective_user.id} continúa con selección: {ordered_selection}")
    await _safe_edit_message(query, _offer_text(config, ordered_selection), reply_markup=kb.offer_keyboard(admin_id))


async def ms_offer_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"🔄 Cambiar selección" (desde la oferta): vuelve al menú, mismo
    mensaje, conservando la selección actual."""
    query = update.callback_query
    await query.answer()
    config = MultiSaleConfigManager()
    admin_id = _get_admin_user_id()
    selected = _selected_set(context)
    await _safe_edit_message(query, _menu_text(config), reply_markup=kb.menu_keyboard(config, selected, admin_id))


async def ms_offer_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"💳 Continuar con la compra": fija (snapshot) la selección actual en
    ms_locked_groups - a partir de acá, cambiar el menú de selección ya no
    afecta a esta compra en curso."""
    query = update.callback_query
    await query.answer()

    selected = _selected_set(context)
    ordered_selection = [key for key in GROUP_KEYS if key in selected]
    if not ordered_selection:
        await query.answer("Selecciona al menos un grupo antes de continuar.", show_alert=True)
        return

    context.user_data["ms_locked_groups"] = ordered_selection
    price = get_offer_price(len(ordered_selection))
    context.user_data["ms_locked_price"] = price

    config = MultiSaleConfigManager()
    admin_id = _get_admin_user_id()
    await _safe_edit_message(
        query, _confirm_text(config, ordered_selection, price), reply_markup=kb.confirm_keyboard(admin_id)
    )


async def ms_confirm_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"🔄 Cambiar selección" (desde la confirmación): vuelve al menú,
    desbloqueando ms_locked_groups (todavía no se pagó nada)."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("ms_locked_groups", None)
    context.user_data.pop("ms_locked_price", None)
    config = MultiSaleConfigManager()
    admin_id = _get_admin_user_id()
    selected = _selected_set(context)
    await _safe_edit_message(query, _menu_text(config), reply_markup=kb.menu_keyboard(config, selected, admin_id))


async def ms_confirm_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"💳 Quiero realizar el pago": muestra los métodos de pago."""
    query = update.callback_query
    await query.answer()
    config = MultiSaleConfigManager()
    admin_id = _get_admin_user_id()
    await _safe_edit_message(query, "💳 MÉTODOS DE PAGO", reply_markup=kb.payment_methods_keyboard(config, admin_id))


async def ms_methods_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"🔙 Volver" desde métodos de pago, y también "🔙 Volver a métodos de
    pago" desde la pantalla de datos de pago: ambos regresan a la
    confirmación de la compra ya fijada (ms_locked_groups)."""
    query = update.callback_query
    await query.answer()

    locked_groups = context.user_data.get("ms_locked_groups")
    config = MultiSaleConfigManager()
    admin_id = _get_admin_user_id()

    if not locked_groups:
        # Estado inesperado (p. ej. reinicio a mitad de camino) - vuelve al
        # menú principal en vez de romper.
        selected = _selected_set(context)
        await _safe_edit_message(query, _menu_text(config), reply_markup=kb.menu_keyboard(config, selected, admin_id))
        return

    price = context.user_data.get("ms_locked_price", get_offer_price(len(locked_groups)))
    await _safe_edit_message(
        query, _confirm_text(config, locked_groups, price), reply_markup=kb.confirm_keyboard(admin_id)
    )


async def ms_send_receipt_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botón informativo "📤 Enviar comprobante": el comprobante se recibe
    con solo enviarlo directo al chat (no hace falta ningún paso extra) -
    este botón solo recuerda eso, sin cambiar de pantalla."""
    query = update.callback_query
    await query.answer(
        "Envía tu comprobante como foto o documento directamente en este chat.", show_alert=True
    )


# --- Métodos de pago / datos de pago ---

async def ms_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point de la conversación. Si el usuario ya vio este método
    antes (para siempre, ver PaymentDataSeenStore), muestra el aviso y
    termina sin re-mostrar los datos. Si no, los muestra, los marca como
    vistos, programa su borrado (persistente) con la duración según el
    método - ver get_payment_data_lifetime_seconds() - y pasa a esperar
    el comprobante."""
    query = update.callback_query
    await query.answer()

    method_key = query.data[len("ms_method_"):]
    if method_key not in PAYMENT_METHOD_KEYS:
        return ConversationHandler.END

    locked_groups = context.user_data.get("ms_locked_groups")
    if not locked_groups:
        await _safe_edit_message(
            query,
            "❌ Tu selección expiró o no es válida. Por favor comienza de nuevo con /start.",
        )
        return ConversationHandler.END

    user_id = update.effective_user.id
    seen_store = PaymentDataSeenStore()
    admin_id = _get_admin_user_id()

    if seen_store.has_seen(user_id, method_key):
        logger.info(f"[multisale] User {user_id} tried to re-view payment data for '{method_key}'; already seen.")
        await _safe_edit_message(query, ALREADY_SEEN_TEXT, reply_markup=kb.payment_already_seen_keyboard(admin_id))
        return ConversationHandler.END

    config = MultiSaleConfigManager()
    price = context.user_data.get("ms_locked_price", get_offer_price(len(locked_groups)))

    await _safe_edit_message(
        query, _payment_data_text(config, method_key, price), reply_markup=kb.payment_data_keyboard(admin_id)
    )
    seen_store.mark_seen(user_id, method_key)
    context.user_data["ms_payment_method"] = method_key

    # Programa el auto-borrado del mensaje de datos de pago, con
    # recuperación persistente por si el bot se reinicia antes de que se
    # cumpla el plazo. Duración según el método (interbancario = 5 min,
    # el resto = 20 min - ver get_payment_data_lifetime_seconds()).
    lifetime_seconds = get_payment_data_lifetime_seconds(method_key)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    delete_at = time.time() + lifetime_seconds
    PendingPaymentDataDeletionsStore().add_pending(chat_id, message_id, delete_at)
    if context.job_queue:
        context.job_queue.run_once(
            _ms_delete_payment_data_job,
            when=lifetime_seconds,
            data={"chat_id": chat_id, "message_id": message_id},
            name=f"ms_delete_paydata_{chat_id}_{message_id}",
        )
    else:
        logger.error("[multisale] No job_queue available; cannot schedule payment-data auto-delete.")

    return MS_WAITING_RECEIPT


async def _ms_delete_payment_data_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id, message_id = data["chat_id"], data["message_id"]
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"[multisale] Deleted payment-data message {message_id} in chat {chat_id} after 5 minutes.")
    except TelegramError as e:
        logger.warning(f"[multisale] Could not delete payment-data message {message_id} in chat {chat_id}: {e}")
    PendingPaymentDataDeletionsStore().remove_pending(chat_id, message_id)


# --- Comprobante ---

async def ms_receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el comprobante (foto o documento), crea la venta, la reenvía
    a TODOS los administradores, borra el comprobante del chat del
    cliente, y programa la aprobación automática a los 5 minutos."""
    message = update.message
    locked_groups = context.user_data.get("ms_locked_groups")
    method_key = context.user_data.get("ms_payment_method")

    if not locked_groups or not method_key:
        await message.reply_text("❌ Ocurrió un problema con tu compra. Por favor comienza de nuevo con /start.")
        return ConversationHandler.END

    if message.photo:
        receipt_file_id = message.photo[-1].file_id
        receipt_file_type = "photo"
    elif message.document:
        receipt_file_id = message.document.file_id
        receipt_file_type = "document"
    else:
        return MS_WAITING_RECEIPT

    config = MultiSaleConfigManager()
    user = update.effective_user
    price = context.user_data.get("ms_locked_price", get_offer_price(len(locked_groups)))
    method_label = config.get_payment_method_label(method_key)

    request = {
        "user_id": user.id,
        "user_first_name": user.first_name or "",
        "user_username": user.username,
        "groups": locked_groups,
        "group_count": len(locked_groups),
        "price": price,
        "payment_method_key": method_key,
        "payment_method_label": method_label,
        "receipt_file_id": receipt_file_id,
        "receipt_file_type": receipt_file_type,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
        "resolved_by": None,
        "reason": None,
        "admin_message_ids": {},
    }

    manager = MultiSaleRequestsManager()
    request_id = manager.add(request)
    if not request_id:
        logger.error(f"[multisale] Failed to save sale for user {user.id}.")
        await message.reply_text("❌ Ocurrió un error al registrar tu compra. Por favor contacta al administrador directamente.")
        return ConversationHandler.END

    # Reenvía el comprobante a todos los admins ANTES de borrar el
    # original (copy_message necesita que el mensaje origen siga
    # existiendo). copy_message evita la etiqueta "Reenviado de" y permite
    # adjuntar nuestro propio caption + botones.
    admin_text = _admin_notification_text(request, config)
    admin_message_ids = {}
    for admin_id in _get_admin_user_ids():
        try:
            copied = await context.bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat_id,
                message_id=message.message_id,
                caption=admin_text,
                reply_markup=kb.admin_approval_keyboard(request_id),
            )
            admin_message_ids[str(admin_id)] = copied.message_id
            logger.info(f"[multisale] Notified admin {admin_id} about new sale {request_id}.")
        except TelegramError as e:
            logger.error(f"[multisale] Failed to notify admin {admin_id} about sale {request_id}: {e}")

    # Relee el registro recién guardado (en vez de reusar el dict local
    # `request`, que nunca recibió el "id" asignado por add() - add()
    # trabaja sobre su propia copia interna) para no sobrescribir la venta
    # con una versión que le falte el id.
    stored = manager.get_by_id(request_id)
    if stored:
        stored["admin_message_ids"] = admin_message_ids
        manager.update(request_id, stored)
        request = stored

    # Borra el comprobante del chat del cliente INMEDIATAMENTE (nunca del
    # chat de los administradores, que ya recibieron su propia copia).
    try:
        await message.delete()
    except TelegramError as e:
        logger.warning(f"[multisale] Could not delete receipt message from buyer chat: {e}")

    await context.bot.send_message(
        chat_id=user.id, text=RECEIPT_RECEIVED_TEXT, reply_markup=kb.admin_only_keyboard(_get_admin_user_id())
    )

    # Aprobación automática a los 5 minutos, con recuperación persistente.
    approve_at = time.time() + AUTO_APPROVAL_SECONDS
    PendingAutoApprovalsStore().add_pending(request_id, approve_at)
    if context.job_queue:
        context.job_queue.run_once(
            _ms_auto_approve_job,
            when=AUTO_APPROVAL_SECONDS,
            data={"request_id": request_id},
            name=f"ms_auto_approve_{request_id}",
        )
    else:
        logger.error("[multisale] No job_queue available; cannot schedule auto-approval.")

    for key in ("ms_selected", "ms_locked_groups", "ms_locked_price", "ms_payment_method"):
        context.user_data.pop(key, None)

    return ConversationHandler.END


async def ms_conversation_timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Si el comprador no envía el comprobante dentro de
    MS_CONVERSATION_TIMEOUT_SECONDS. No cancela la venta (todavía no existe
    ninguna) ni borra ms_locked_groups/ms_payment_method a propósito - así,
    si vuelve más tarde y aún no se le borraron los datos de pago (el
    plazo depende del método, ver get_payment_data_lifetime_seconds()),
    su compra en curso sigue siendo
    válida para recibir el comprobante; el timeout solo libera el estado
    de conversación de PTB."""
    try:
        if update.callback_query:
            await update.callback_query.answer()
        elif update.message:
            await update.message.reply_text(
                "⏱️ Se agotó el tiempo de espera. Si aún deseas comprar, pulsa /start de nuevo."
            )
    except TelegramError as e:
        logger.warning(f"[multisale] Could not notify user of conversation timeout: {e}")


# --- Aprobar / Rechazar (fuera de la conversación, acciones del admin) ---

async def _update_all_admin_messages(context: ContextTypes.DEFAULT_TYPE, request: dict, status_line: str):
    """Edita el caption del comprobante en el chat de CADA administrador
    notificado (no solo del primero) para reflejar la resolución y quitar
    los botones Aprobar/Rechazar, evitando que un segundo admin vuelva a
    procesar la misma venta."""
    config = MultiSaleConfigManager()
    base_text = _admin_notification_text(request, config)
    # La línea "⏱️ Aprobación automática en: 05:00" ya no aplica una vez
    # resuelta la venta.
    base_text = base_text.replace("\n\n⏱️ Aprobación automática en: 05:00", "")
    final_text = f"{base_text}\n\n{status_line}"

    for admin_id_str, message_id in request.get("admin_message_ids", {}).items():
        try:
            await context.bot.edit_message_caption(
                chat_id=int(admin_id_str), message_id=message_id, caption=final_text, reply_markup=None
            )
        except TelegramError as e:
            logger.warning(f"[multisale] Could not update admin {admin_id_str} message for sale {request['id']}: {e}")


async def _deliver_access(context: ContextTypes.DEFAULT_TYPE, request: dict, approved_text: str):
    """Envía al comprador: mensaje de aprobación, botones URL de acceso
    (solo a los grupos comprados) y el aviso de seguridad - en ese orden,
    como 3 mensajes separados."""
    config = MultiSaleConfigManager()
    user_id = request["user_id"]
    try:
        await context.bot.send_message(chat_id=user_id, text=approved_text)
        await context.bot.send_message(
            chat_id=user_id,
            text=_access_delivery_text(),
            reply_markup=kb.access_keyboard(config, request["groups"]),
        )
        await context.bot.send_message(chat_id=user_id, text=SECURITY_TEXT)
    except TelegramError as e:
        logger.error(f"[multisale] Could not deliver access to user {user_id} for sale {request['id']}: {e}")


def _cancel_auto_approval_job(context: ContextTypes.DEFAULT_TYPE, request_id: str):
    if context.job_queue:
        for job in context.job_queue.get_jobs_by_name(f"ms_auto_approve_{request_id}"):
            job.schedule_removal()
    PendingAutoApprovalsStore().remove_pending(request_id)


async def ms_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in _get_admin_user_ids():
        await query.answer("❌ No tienes permiso.", show_alert=True)
        return

    request_id = query.data[len("ms_approve_"):]
    manager = MultiSaleRequestsManager()
    request = manager.get_by_id(request_id)

    if not request:
        await query.answer("❌ Esta venta ya no existe.", show_alert=True)
        return

    if request.get("status") != "pending":
        await query.answer(f"ℹ️ Esta venta ya fue resuelta ({request.get('status')}).", show_alert=True)
        return

    request["status"] = "approved"
    request["resolved_at"] = datetime.now().isoformat()
    request["resolved_by"] = "ADMINISTRADOR"
    request["reason"] = "Aprobación manual"
    manager.update(request_id, request)
    logger.info(f"[multisale] Sale {request_id} approved by admin {query.from_user.id}.")

    _cancel_auto_approval_job(context, request_id)
    await _update_all_admin_messages(context, request, "✅ APROBADO por administrador.")
    await _deliver_access(context, request, APPROVED_MANUAL_TEXT)


async def ms_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in _get_admin_user_ids():
        await query.answer("❌ No tienes permiso.", show_alert=True)
        return

    request_id = query.data[len("ms_reject_"):]
    manager = MultiSaleRequestsManager()
    request = manager.get_by_id(request_id)

    if not request:
        await query.answer("❌ Esta venta ya no existe.", show_alert=True)
        return

    if request.get("status") != "pending":
        await query.answer(f"ℹ️ Esta venta ya fue resuelta ({request.get('status')}).", show_alert=True)
        return

    request["status"] = "rejected"
    request["resolved_at"] = datetime.now().isoformat()
    request["resolved_by"] = "ADMINISTRADOR"
    request["reason"] = "Rechazo manual"
    manager.update(request_id, request)
    logger.info(f"[multisale] Sale {request_id} rejected by admin {query.from_user.id}.")

    _cancel_auto_approval_job(context, request_id)
    await _update_all_admin_messages(context, request, "❌ RECHAZADO por administrador.")

    try:
        await context.bot.send_message(
            chat_id=request["user_id"], text=REJECTED_TEXT, reply_markup=kb.admin_only_keyboard(_get_admin_user_id())
        )
    except TelegramError as e:
        logger.error(f"[multisale] Could not notify user {request['user_id']} of rejection: {e}")


async def _ms_auto_approve_job(context: ContextTypes.DEFAULT_TYPE):
    """JobQueue callback: si nadie aprobó/rechazó en 5 minutos, aprueba
    automáticamente. Verifica el estado antes de actuar (si un admin ya
    resolvió la venta en el mismo instante, no hace nada más)."""
    request_id = context.job.data["request_id"]
    manager = MultiSaleRequestsManager()
    request = manager.get_by_id(request_id)

    PendingAutoApprovalsStore().remove_pending(request_id)

    if not request or request.get("status") != "pending":
        logger.info(f"[multisale] Auto-approval job fired for {request_id} but it's no longer pending; skipping.")
        return

    request["status"] = "approved"
    request["resolved_at"] = datetime.now().isoformat()
    request["resolved_by"] = "BOT"
    request["reason"] = "5 minutos sin acción del administrador"
    manager.update(request_id, request)
    logger.info(f"[multisale] Sale {request_id} auto-approved by bot (5 min timeout).")

    await _update_all_admin_messages(context, request, "🤖 APROBADO automáticamente (sin acción en 5 minutos).")
    await _deliver_access(context, request, APPROVED_AUTO_TEXT)


async def _reschedule_pending_ms_actions(context: ContextTypes.DEFAULT_TYPE):
    """Se ejecuta UNA SOLA VEZ, poco después de que el bot arranca (ver
    register_multisale_handlers). Recupera aprobaciones automáticas y
    borrados de datos de pago que hayan quedado pendientes de un reinicio
    anterior (redeploy de Railway, crash, etc.), igual patrón que
    ventas/handlers.py::_reschedule_pending_trial_kicks."""
    if not context.job_queue:
        logger.error("[multisale] No job_queue available at startup; cannot reconcile pending timers.")
        return

    now = time.time()

    pending_approvals = PendingAutoApprovalsStore().get_all_pending()
    if pending_approvals:
        logger.info(f"[multisale] Reconciling {len(pending_approvals)} pending auto-approval(s) after startup.")
    for item in pending_approvals:
        request_id = item.get("request_id")
        approve_at = item.get("approve_at", now)
        remaining = max(0, approve_at - now)
        context.job_queue.run_once(
            _ms_auto_approve_job, when=remaining, data={"request_id": request_id}, name=f"ms_auto_approve_{request_id}"
        )
        logger.info(f"[multisale] Rescheduled auto-approval for sale {request_id} (in {remaining:.0f}s).")

    pending_deletions = PendingPaymentDataDeletionsStore().get_all_pending()
    if pending_deletions:
        logger.info(f"[multisale] Reconciling {len(pending_deletions)} pending payment-data deletion(s) after startup.")
    for item in pending_deletions:
        chat_id = item.get("chat_id")
        message_id = item.get("message_id")
        delete_at = item.get("delete_at", now)
        remaining = max(0, delete_at - now)
        context.job_queue.run_once(
            _ms_delete_payment_data_job,
            when=remaining,
            data={"chat_id": chat_id, "message_id": message_id},
            name=f"ms_delete_paydata_{chat_id}_{message_id}",
        )
        logger.info(f"[multisale] Rescheduled payment-data deletion for chat {chat_id} (in {remaining:.0f}s).")


# --- Comandos admin: pagos de clientes recientes ---

async def ms_agregar_pago_reciente_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in _get_admin_user_ids():
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return
    context.user_data["ms_awaiting_recent_payment"] = True
    await update.message.reply_text(
        "📎 Envía ahora la foto o el documento que quieres agregar como comprobante de muestra."
    )


async def ms_ver_pagos_recientes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in _get_admin_user_ids():
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return

    payments = RecentPaymentsStore().get_all()
    if not payments:
        await update.message.reply_text("No hay comprobantes de muestra cargados todavía.")
        return

    lines = ["📋 Comprobantes de muestra guardados:\n"]
    for i, payment in enumerate(payments, 1):
        tipo = "documento" if payment.get("file_type") == "document" else "foto"
        lines.append(f"{i}. {tipo}, agregado {payment.get('added_at', 'N/A')}")
    lines.append("\nUsa /quitar_pago_reciente <número> para eliminar uno.")
    await update.message.reply_text("\n".join(lines))


async def ms_quitar_pago_reciente_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in _get_admin_user_ids():
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Uso: /quitar_pago_reciente <número>\n(consulta los números con /ver_pagos_recientes)")
        return

    index = int(context.args[0]) - 1
    if RecentPaymentsStore().remove_at(index):
        await update.message.reply_text("✅ Comprobante de muestra eliminado.")
    else:
        await update.message.reply_text("❌ No existe un comprobante con ese número.")


async def ms_admin_receive_recent_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MessageHandler registrado en su propio group (independiente del
    group=0 que usa la conversación de compra) para poder evaluar CADA
    foto/documento sin interferir con ms_receive_receipt: si el
    remitente no es admin, o no ejecutó /agregar_pago_reciente
    justo antes, no hace nada."""
    if not context.user_data.get("ms_awaiting_recent_payment"):
        return
    if update.effective_user.id not in _get_admin_user_ids():
        return

    message = update.message
    if message.photo:
        file_id, file_type = message.photo[-1].file_id, "photo"
    elif message.document:
        file_id, file_type = message.document.file_id, "document"
    else:
        return

    context.user_data["ms_awaiting_recent_payment"] = False
    if RecentPaymentsStore().add(file_id, file_type, update.effective_user.id):
        await message.reply_text("✅ Comprobante de muestra agregado correctamente.")
    else:
        await message.reply_text("❌ No se pudo guardar el comprobante de muestra.")


# --- Registro ---

def build_multisale_conversation_handler():
    method_pattern = "^ms_method_(" + "|".join(PAYMENT_METHOD_KEYS) + ")$"
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(ms_method_selected, pattern=method_pattern)],
        states={
            MS_WAITING_RECEIPT: [MessageHandler(filters.PHOTO | filters.Document.ALL, ms_receive_receipt)],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, ms_conversation_timeout_handler),
                CallbackQueryHandler(ms_conversation_timeout_handler),
            ],
        },
        fallbacks=[],
        name="multisale_conversation",
        persistent=False,
        conversation_timeout=MS_CONVERSATION_TIMEOUT_SECONDS,
    )


def register_multisale_handlers(application):
    """Punto único de integración con bot.py, mismo patrón que
    ventas/handlers.py::register_ventas_handlers. Debe registrarse ANTES
    del catch-all CallbackQueryHandler(button_callback) de bot.py."""
    application.add_handler(build_multisale_conversation_handler())

    application.add_handler(
        CallbackQueryHandler(ms_toggle_group, pattern="^ms_toggle_(" + "|".join(GROUP_KEYS) + ")$")
    )
    application.add_handler(CallbackQueryHandler(ms_recent_payments, pattern="^ms_recent$"))
    application.add_handler(CallbackQueryHandler(ms_recent_back, pattern="^ms_recent_back$"))
    application.add_handler(CallbackQueryHandler(ms_continue, pattern="^ms_continue$"))
    application.add_handler(CallbackQueryHandler(ms_offer_continue, pattern="^ms_offer_continue$"))
    application.add_handler(CallbackQueryHandler(ms_offer_change, pattern="^ms_offer_change$"))
    application.add_handler(CallbackQueryHandler(ms_confirm_pay, pattern="^ms_confirm_pay$"))
    application.add_handler(CallbackQueryHandler(ms_confirm_change, pattern="^ms_confirm_change$"))
    application.add_handler(CallbackQueryHandler(ms_methods_back, pattern="^ms_methods_back$"))
    application.add_handler(CallbackQueryHandler(ms_send_receipt_hint, pattern="^ms_send_receipt_hint$"))
    application.add_handler(CallbackQueryHandler(ms_approve_callback, pattern="^ms_approve_.+$"))
    application.add_handler(CallbackQueryHandler(ms_reject_callback, pattern="^ms_reject_.+$"))

    application.add_handler(CommandHandler("agregar_pago_reciente", ms_agregar_pago_reciente_command))
    application.add_handler(CommandHandler("ver_pagos_recientes", ms_ver_pagos_recientes_command))
    application.add_handler(CommandHandler("quitar_pago_reciente", ms_quitar_pago_reciente_command))

    # group=3: distinto de group=0 (bot.py + esta misma conversación),
    # group=1/2 (grupos de prueba de ventas/handlers.py) - así esta foto se
    # evalúa de forma independiente sin interferir con ms_receive_receipt
    # ni con nada más, exactamente el mismo motivo ya documentado en
    # ventas/handlers.py para sus propios handlers de NEW_CHAT_MEMBERS.
    application.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.ALL, ms_admin_receive_recent_payment_photo), group=3
    )

    if application.job_queue:
        application.job_queue.run_once(_reschedule_pending_ms_actions, when=1)
    else:
        logger.error("[multisale] No job_queue available at startup; cannot reconcile pending timers.")

    logger.info("[multisale] All multi-sale handlers registered.")
