"""
Handlers de Telegram del sistema de ventas (Fase 7).

Este mÃ³dulo define su PROPIO ConversationHandler, con sus propios estados
(nÃºmeros enteros locales a este handler - no colisionan con los estados
usados en bot.py para promociones/bienvenida, ya que cada ConversationHandler
mantiene su propia mÃ¡quina de estados independiente).

Flujo:
  /start venta (deep-link desde el botÃ³n del canal)
    -> send_sales_welcome(): "ðŸŽ Iniciar prueba gratis" / "ðŸ’³ Comprar VIP" / "â“ FAQ"

  ðŸŽ Iniciar prueba gratis:
    -> ventas_demo_callback(): entrega el enlace configurado del grupo de
       prueba (SALES_DEMO_GROUP_LINK).
    -> handle_trial_group_new_member() [MessageHandler sobre NEW_CHAT_MEMBERS,
       registrado en un "group" de manejo distinto al de bot.py para no
       interferir con el sistema de bienvenida]: detecta cualquier ingreso
       al grupo de prueba (SALES_TRIAL_GROUP_ID) y programa su expulsiÃ³n
       automÃ¡tica exactamente 1 minuto despuÃ©s.
    -> _kick_trial_member() [job de JobQueue]: expulsa (ban + unban) al
       usuario del grupo de prueba. Esto SOLO aplica al grupo identificado
       por SALES_TRIAL_GROUP_ID - nunca al grupo VIP ni a ningÃºn otro.

  ðŸ’³ Comprar acceso VIP:
    -> ventas_vip_callback(): muestra el MENÃš de mÃ©todos de pago (sin
       datos financieros todavÃ­a).
    -> ventas_method_detail_callback(): al elegir un mÃ©todo, muestra
       ÃšNICAMENTE los datos de ESE mÃ©todo.
    -> ventas_paid_entry() [entra a la conversaciÃ³n]: el mÃ©todo ya viaja en
       el callback_data ("ventas_paid_<method>"), asÃ­ que solo pide el
       nombre + inicial del apellido del titular.
    -> ventas_receive_payer_name(): guarda la solicitud con el mÃ©todo ya
       elegido, notifica al admin, fin.

  Admin (mensaje privado recibido):
    sale_approve_callback() / sale_reject_callback(): resuelven la
    solicitud y notifican al comprador.

NOTA (primera versiÃ³n de producciÃ³n, sin panel de configuraciÃ³n todavÃ­a):
la configuraciÃ³n del mÃ³dulo (precio, bancos, PayPal, enlaces, FAQ) se
edita directamente en ventas/config.py (los valores por defecto en
_default_config()) o cargando un valor a Upstash manualmente. El menÃº
"ðŸ›ï¸ Configurar Ventas" desde el panel se agregarÃ¡ en una fase posterior,
una vez validado el flujo completo de venta en producciÃ³n.

Todo lo que este mÃ³dulo necesita de bot.py (ADMIN_USER_ID) se importa de
forma diferida dentro de las funciones - ver docstring de ventas/config.py.
"""

import logging
import time
from datetime import datetime

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import SalesConfigManager, TrialKicksStore, _default_config
from .storage import SalesRequestsManager
from . import keyboards

logger = logging.getLogger("bot")

# Estado propio de este ConversationHandler (independiente de los de bot.py).
# El mÃ©todo de pago ya no es un estado: se elige ANTES de entrar a la
# conversaciÃ³n (en el menÃº de VIP), y viaja en el callback_data de
# "âœ… Ya realicÃ© el pago" - asÃ­ que solo hace falta un estado: el nombre.
(VENTAS_PAYER_NAME,) = range(1)

# CuÃ¡nto puede permanecer un usuario en el grupo de prueba antes de ser
# expulsado automÃ¡ticamente. Fijo en 1 minuto, tal como se pidiÃ³.
TRIAL_DURATION_SECONDS = 60

WELCOME_TEXT = (
    "ðŸ‘‹ Â¡Bienvenido!\n\n"
    "Antes de adquirir el acceso VIP, puedes probar una demostraciÃ³n "
    "gratuita para comprobar la calidad del contenido."
)


def _get_admin_user_id():
    from bot import ADMIN_USER_ID
    return ADMIN_USER_ID


# --- Bienvenida del embudo de ventas (entrada vÃ­a deep-link /start venta) ---

async def send_sales_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menÃº de bienvenida de ventas. Llamado desde bot.py's
    start() cuando detecta el payload de deep-link ?start=venta."""
    logger.info(f"[ventas] Sales welcome shown to user {update.effective_user.id}")
    await update.message.reply_text(WELCOME_TEXT, reply_markup=keyboards.welcome_keyboard())


async def _safe_edit_message(query, text, reply_markup=None, parse_mode=None):
    """Wraps query.edit_message_text with error handling. Quality audit fix:
    these simple callbacks had no protection against a TelegramError (e.g.
    the message is too old to edit, or its content didn't actually change);
    logging and swallowing it here matches the defensive style already
    used elsewhere in the project for Telegram API calls."""
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramError as e:
        logger.warning(f"[ventas] Could not edit message: {e}")


async def ventas_back_to_welcome_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _safe_edit_message(query, WELCOME_TEXT, reply_markup=keyboards.welcome_keyboard())


# --- "ðŸŽ Iniciar prueba gratis" ---

async def ventas_demo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entrega el enlace configurado del grupo de prueba. El seguimiento de
    quiÃ©n debe ser expulsado y cuÃ¡ndo ocurre por completo en
    handle_trial_group_new_member()."""
    query = update.callback_query
    await query.answer()
    config = SalesConfigManager()
    admin_id = _get_admin_user_id()
    text = (
        "ðŸ“‚ Â¡Perfecto! AquÃ­ tienes el acceso a nuestro grupo de demostraciÃ³n.\n\n"
        "PodrÃ¡s permanecer 1 minuto; pasado ese tiempo, el bot te retirarÃ¡ automÃ¡ticamente."
    )
    if not config.get_demo_group_link():
        text = "El enlace de demostraciÃ³n aÃºn no estÃ¡ configurado. Contacta al administrador."
    await _safe_edit_message(query, text, reply_markup=keyboards.demo_keyboard(config, admin_id))


async def handle_trial_group_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta cualquier ingreso al grupo de prueba (SALES_TRIAL_GROUP_ID) y
    programa su expulsiÃ³n automÃ¡tica 1 minuto despuÃ©s.

    Aislamiento estricto: si SALES_TRIAL_GROUP_ID no estÃ¡ configurada, o si
    el chat donde ocurriÃ³ el ingreso no coincide EXACTAMENTE con ese ID,
    la funciÃ³n no hace nada - nunca actÃºa sobre el grupo VIP, el grupo
    principal de promociones, ni ningÃºn otro chat donde el bot estÃ©
    presente."""
    message = update.message
    if message is None or message.new_chat_members is None:
        return

    config = SalesConfigManager()
    trial_group_id = config.get_trial_group_id()
    if not trial_group_id or message.chat_id != trial_group_id:
        return

    for member in message.new_chat_members:
        if member.is_bot:
            continue
        logger.info(
            f"[ventas] User {member.id} joined the trial group ({trial_group_id}); "
            f"will be removed in {TRIAL_DURATION_SECONDS}s."
        )
        # Se registra de forma persistente ANTES de programar el job en
        # memoria, para que si el bot se reinicia durante este minuto,
        # _reschedule_pending_trial_kicks() pueda recuperarlo al arrancar.
        kick_at = time.time() + TRIAL_DURATION_SECONDS
        TrialKicksStore().add_pending_kick(trial_group_id, member.id, kick_at)

        if context.job_queue:
            context.job_queue.run_once(
                _kick_trial_member,
                when=TRIAL_DURATION_SECONDS,
                data={"chat_id": trial_group_id, "user_id": member.id},
                name=f"trial_kick_{trial_group_id}_{member.id}",
            )
        else:
            logger.error("[ventas] No job_queue available; cannot schedule automatic trial removal.")


async def _kick_trial_member(context: ContextTypes.DEFAULT_TYPE):
    """JobQueue callback: expulsa (ban + unban) a un usuario del grupo de
    prueba cuando se cumple su minuto. unban con only_if_banned=True hace
    que sea una expulsiÃ³n, no un baneo permanente - la persona podrÃ­a
    volver a entrar con el enlace en el futuro si el admin lo permite."""
    data = context.job.data
    chat_id, user_id = data["chat_id"], data["user_id"]
    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
        logger.info(f"[ventas] Removed user {user_id} from the trial group {chat_id} after the trial period ended.")
    except TelegramError as e:
        logger.warning(f"[ventas] Could not remove user {user_id} from the trial group (may have already left): {e}")
    finally:
        # Se limpia el registro persistido en ambos casos (Ã©xito o error) -
        # si fallÃ³ porque ya no estÃ¡ en el grupo, reintentar por siempre
        # en cada reinicio no tendrÃ­a sentido.
        TrialKicksStore().remove_pending_kick(chat_id, user_id)


async def _reschedule_pending_trial_kicks(context: ContextTypes.DEFAULT_TYPE):
    """Se ejecuta UNA SOLA VEZ, poco despuÃ©s de que el bot arranca (ver
    register_ventas_handlers). Recupera cualquier expulsiÃ³n del grupo de
    prueba que haya quedado pendiente de un reinicio anterior (redeploy de
    Railway, crash, etc. durante la ventana de 1 minuto): si ya se cumpliÃ³
    la hora, expulsa de inmediato; si no, reprograma el tiempo restante en
    JobQueue. AsÃ­ la expulsiÃ³n automÃ¡tica sobrevive a un reinicio del bot."""
    pending = TrialKicksStore().get_all_pending_kicks()
    if not pending:
        return

    logger.info(f"[ventas] Reconciling {len(pending)} pending trial kick(s) after startup.")
    now = time.time()
    for kick in pending:
        chat_id = kick.get("chat_id")
        user_id = kick.get("user_id")
        kick_at = kick.get("kick_at", now)
        remaining = max(0, kick_at - now)

        if not context.job_queue:
            logger.error("[ventas] No job_queue available; cannot reschedule pending trial kicks.")
            return

        context.job_queue.run_once(
            _kick_trial_member,
            when=remaining,
            data={"chat_id": chat_id, "user_id": user_id},
            name=f"trial_kick_{chat_id}_{user_id}",
        )
        logger.info(
            f"[ventas] Rescheduled pending kick for user {user_id} in chat {chat_id} "
            f"(in {remaining:.0f}s, after bot restart)."
        )


# --- "ðŸ’³ Comprar acceso VIP" -> menÃº de mÃ©todos de pago ---

async def ventas_vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menÃº de mÃ©todos de pago disponibles (sin datos
    financieros todavÃ­a - eso se muestra al elegir uno especÃ­fico)."""
    query = update.callback_query
    await query.answer()
    config = SalesConfigManager()
    admin_id = _get_admin_user_id()

    text = f"ðŸ’³ *Acceso VIP* â€” {config.get_vip_price()}\n\nElige tu mÃ©todo de pago preferido:"
    await _safe_edit_message(
        query, text, reply_markup=keyboards.vip_menu_keyboard(admin_id), parse_mode="Markdown"
    )


_METHOD_DETAIL_GETTERS = {
    "bank_guayaquil": lambda c: c.get_bank_guayaquil_details(),
    "bank_pichincha": lambda c: c.get_bank_pichincha_details(),
    "paypal": lambda c: c.get_paypal_details(),
}


async def ventas_method_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Al elegir un mÃ©todo de pago especÃ­fico, muestra ÃšNICAMENTE la
    informaciÃ³n de ESE mÃ©todo (nunca los otros)."""
    query = update.callback_query
    await query.answer()

    method_key = query.data[len("ventas_method_"):]
    if method_key not in keyboards.PAYMENT_METHOD_LABELS:
        return

    config = SalesConfigManager()
    admin_id = _get_admin_user_id()
    label = keyboards.PAYMENT_METHOD_LABELS[method_key]
    details = _METHOD_DETAIL_GETTERS[method_key](config)

    # === DIAGNOSTICO TEMPORAL - quitar despues de identificar la causa ===
    logger.error(f"[DIAGNOSTICO] method_key={method_key!r}")
    logger.error(f"[DIAGNOSTICO] repr(details)={details!r}")
    logger.error(f"[DIAGNOSTICO] repr(config.data)={config.data!r}")
    logger.error(f"[DIAGNOSTICO] config.use_upstash={config.use_upstash!r}")
    logger.error(f"[DIAGNOSTICO] config.file_path={config.file_path!r}")
    logger.error(f"[DIAGNOSTICO] _default_config()={_default_config()!r}")
    # === FIN DIAGNOSTICO TEMPORAL ===

    if details:
        text = f"{label}\n\n{details}"
    else:
        logger.warning(f"[ventas] Method '{method_key}' selected but has no configured details.")
        text = f"{label}\n\nEste mÃ©todo aÃºn no estÃ¡ configurado. Contacta al administrador."

    await _safe_edit_message(
        query, text, reply_markup=keyboards.method_detail_keyboard(method_key, admin_id), parse_mode="Markdown"
    )


# --- "â“ Preguntas frecuentes" ---

async def ventas_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    config = SalesConfigManager()
    await _safe_edit_message(query, config.get_faq_text(), reply_markup=keyboards.welcome_keyboard())


# --- "âœ… Ya realicÃ© el pago" -> pedir SOLO el titular (el mÃ©todo ya se conoce) ---

async def ventas_paid_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point de la conversaciÃ³n: el mÃ©todo de pago viaja en el
    callback_data (ventas_paid_<method_key>), asÃ­ que solo hace falta
    pedir el nombre del titular del pago.

    Antes de iniciar, verifica que el usuario no tenga ya una solicitud
    "pending" en curso - asÃ­ se evita que un doble tap (o que el usuario
    repita el proceso mientras espera respuesta) genere una segunda
    solicitud duplicada y, con ella, un segundo aviso duplicado al admin
    por el mismo pago.
    """
    query = update.callback_query
    await query.answer()

    method_key = query.data[len("ventas_paid_"):]
    if method_key not in keyboards.PAYMENT_METHOD_LABELS:
        return ConversationHandler.END

    user_id = update.effective_user.id
    manager = SalesRequestsManager()
    already_pending = any(
        req.get("user_id") == user_id and req.get("status") == "pending"
        for req in manager.get_all()
    )
    if already_pending:
        logger.info(f"[ventas] User {user_id} tried to submit a new payment while one is still pending; blocked.")
        await query.edit_message_text(
            "â³ Ya tienes una solicitud de pago en revisiÃ³n.\n\n"
            "Un administrador la confirmarÃ¡ pronto. Te avisaremos aquÃ­ mismo apenas se resuelva."
        )
        return ConversationHandler.END

    context.user_data["ventas_payment_method_key"] = method_key
    context.user_data.pop("ventas_payer_name", None)
    await query.edit_message_text(
        "âœï¸ Por favor, envÃ­a el nombre y la inicial del apellido del titular del pago.\n\n"
        "Ejemplo: Ricardo M."
    )
    return VENTAS_PAYER_NAME


async def ventas_receive_payer_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre del titular, guarda la solicitud (el mÃ©todo ya se
    conoce desde ventas_paid_entry) y notifica al administrador."""
    payer_name = update.message.text.strip()
    method_key = context.user_data.pop("ventas_payment_method_key", None)

    if not method_key or method_key not in keyboards.PAYMENT_METHOD_LABELS:
        # Estado inesperado (p. ej. el proceso se reiniciÃ³ a mitad de camino).
        await update.message.reply_text("âŒ OcurriÃ³ un problema, por favor comienza de nuevo con /start.")
        return ConversationHandler.END

    method_label = keyboards.PAYMENT_METHOD_LABELS[method_key]
    logger.info(f"[ventas] Payer name received from user {update.effective_user.id}: {payer_name!r} ({method_label})")

    user = update.effective_user
    manager = SalesRequestsManager()
    request = {
        "user_id": user.id,
        "user_first_name": user.first_name or "",
        "user_username": user.username,
        "payer_name": payer_name,
        "payment_method": method_label,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "admin_message_id": None,
    }
    request_id = manager.add(request)

    if not request_id:
        logger.error(f"[ventas] Failed to save payment request for user {user.id}.")
        await update.message.reply_text(
            "âŒ OcurriÃ³ un error al registrar tu informaciÃ³n. Por favor contacta al administrador directamente."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "âœ… Â¡Gracias! Recibimos tu informaciÃ³n:\n\n"
        f"{payer_name}\n{method_label}.\n\n"
        "Un administrador revisarÃ¡ tu pago pronto y te notificaremos aquÃ­ mismo."
    )

    await _notify_admin_new_sale_request(context, request_id, request)
    return ConversationHandler.END


async def _notify_admin_new_sale_request(context: ContextTypes.DEFAULT_TYPE, request_id: str, request: dict):
    """EnvÃ­a al admin los datos de la solicitud con botones Aprobar/Rechazar."""
    admin_id = _get_admin_user_id()
    username_part = f"@{request['user_username']}" if request.get("user_username") else f"id {request['user_id']}"
    text = (
        "ðŸ›’ *Nueva solicitud de pago VIP*\n\n"
        f"Usuario: {request['user_first_name']} ({username_part})\n"
        f"Titular del pago: {request['payer_name']}\n"
        f"MÃ©todo: {request['payment_method']}"
    )
    try:
        sent = await context.bot.send_message(
            chat_id=admin_id,
            text=text,
            reply_markup=keyboards.admin_approval_keyboard(request_id),
            parse_mode="Markdown",
        )
        manager = SalesRequestsManager()
        stored = manager.get_by_id(request_id)
        if stored:
            stored["admin_message_id"] = sent.message_id
            manager.update(request_id, stored)
        logger.info(f"[ventas] Notified admin about new payment request {request_id}.")
    except TelegramError as e:
        logger.error(f"[ventas] Failed to notify admin about payment request {request_id}: {e}")


# --- Aprobar / Rechazar (acciones del admin, fuera de la conversaciÃ³n) ---

async def sale_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != _get_admin_user_id():
        await query.answer("âŒ No tienes permiso.", show_alert=True)
        return

    request_id = query.data[len("sale_approve_"):]
    manager = SalesRequestsManager()
    request = manager.get_by_id(request_id)

    if not request:
        await query.edit_message_text("âŒ Esta solicitud ya no existe.")
        return

    request["status"] = "approved"
    request["resolved_at"] = datetime.now().isoformat()
    manager.update(request_id, request)
    logger.info(f"[ventas] Payment request {request_id} approved by admin.")

    config = SalesConfigManager()
    vip_link = config.get_vip_group_link()
    try:
        if vip_link:
            await context.bot.send_message(
                chat_id=request["user_id"],
                text=f"âœ… Â¡Tu pago fue aprobado! Este es tu acceso al grupo VIP:\n{vip_link}",
            )
        else:
            await context.bot.send_message(
                chat_id=request["user_id"],
                text="âœ… Tu pago fue aprobado. El administrador te contactarÃ¡ pronto con el acceso al grupo VIP.",
            )
    except TelegramError as e:
        logger.error(f"[ventas] Could not notify user {request['user_id']} of approval: {e}")

    await query.edit_message_text(
        f"âœ… Aprobado â€” {request['payer_name']} ({request['payment_method']}). Se notificÃ³ al usuario."
    )


async def sale_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != _get_admin_user_id():
        await query.answer("âŒ No tienes permiso.", show_alert=True)
        return

    request_id = query.data[len("sale_reject_"):]
    manager = SalesRequestsManager()
    request = manager.get_by_id(request_id)

    if not request:
        await query.edit_message_text("âŒ Esta solicitud ya no existe.")
        return

    request["status"] = "rejected"
    request["resolved_at"] = datetime.now().isoformat()
    manager.update(request_id, request)
    logger.info(f"[ventas] Payment request {request_id} rejected by admin.")

    try:
        await context.bot.send_message(
            chat_id=request["user_id"],
            text="âŒ No pudimos verificar tu pago. Por favor contacta al administrador para resolverlo.",
        )
    except TelegramError as e:
        logger.error(f"[ventas] Could not notify user {request['user_id']} of rejection: {e}")

    await query.edit_message_text(
        f"âŒ Rechazado â€” {request['payer_name']} ({request['payment_method']}). Se notificÃ³ al usuario."
    )


# Quality audit fix: how long (seconds) a buyer can be inactive mid-way
# through "Ya realicÃ© el pago" (name -> method) before it auto-cancels.
# Without this, abandoning the flow left them stuck: entry_points are
# bypassed while a conversation is already active for that user, so
# tapping "âœ… Ya realicÃ© el pago" again would silently do nothing.
VENTAS_CONVERSATION_TIMEOUT_SECONDS = 300  # 5 minutes


async def ventas_conversation_timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when the payment conversation times out. Clears any partial
    state and lets the buyer know they can start over."""
    context.user_data.pop("ventas_payer_name", None)
    context.user_data.pop("ventas_payment_method_key", None)
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "â±ï¸ Se agotÃ³ el tiempo de espera. Si deseas continuar, pulsa /start de nuevo."
            )
        elif update.message:
            await update.message.reply_text(
                "â±ï¸ Se agotÃ³ el tiempo de espera. Si deseas continuar, pulsa /start de nuevo."
            )
    except TelegramError as e:
        logger.warning(f"[ventas] Could not notify user of conversation timeout: {e}")


def build_ventas_conversation_handler():
    """Construye el ConversationHandler del mÃ³dulo de ventas (solo el flujo
    de pago), completamente independiente del ConversationHandler de
    bot.py. El mÃ©todo de pago ya no es un estado propio: se elige antes de
    entrar aquÃ­, asÃ­ que solo hay un estado (el nombre del titular)."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ventas_paid_entry, pattern="^ventas_paid_(bank_guayaquil|bank_pichincha|paypal)$"),
        ],
        states={
            VENTAS_PAYER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ventas_receive_payer_name)],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, ventas_conversation_timeout_handler),
                CallbackQueryHandler(ventas_conversation_timeout_handler),
            ],
        },
        fallbacks=[],
        name="ventas_conversation",
        persistent=False,
        conversation_timeout=VENTAS_CONVERSATION_TIMEOUT_SECONDS,
    )


def register_ventas_handlers(application):
    """Punto Ãºnico de integraciÃ³n con bot.py: registra todos los handlers
    del mÃ³dulo de ventas en la Application. Los CallbackQueryHandler deben
    llamarse ANTES del catch-all de bot.py (button_callback sin patrÃ³n),
    para que los callback_data de ventas no queden atrapados ahÃ­."""
    application.add_handler(build_ventas_conversation_handler())
    application.add_handler(CallbackQueryHandler(ventas_demo_callback, pattern="^ventas_demo$"))
    application.add_handler(CallbackQueryHandler(ventas_vip_callback, pattern="^ventas_vip$"))
    application.add_handler(
        CallbackQueryHandler(ventas_method_detail_callback, pattern="^ventas_method_(bank_guayaquil|bank_pichincha|paypal)$")
    )
    application.add_handler(CallbackQueryHandler(ventas_faq_callback, pattern="^ventas_faq$"))
    application.add_handler(CallbackQueryHandler(ventas_back_to_welcome_callback, pattern="^ventas_back_to_welcome$"))
    application.add_handler(CallbackQueryHandler(sale_approve_callback, pattern="^sale_approve_.+$"))
    application.add_handler(CallbackQueryHandler(sale_reject_callback, pattern="^sale_reject_.+$"))
    # Detecta ingresos al grupo de prueba para expulsar automÃ¡ticamente al
    # cumplirse 1 minuto. Se registra en group=1 (distinto del group=0 por
    # defecto que usa bot.py para su propio detector de NEW_CHAT_MEMBERS,
    # el de la bienvenida). python-telegram-bot solo invoca al primer
    # handler que matchea un filtro DENTRO de un mismo group; si este
    # handler compartiera el group con el de bot.py, cualquiera que se
    # registrara primero "consumirÃ­a" el evento y el otro dejarÃ­a de
    # funcionar. Con groups distintos, ambos evalÃºan cada ingreso de forma
    # independiente y cada uno decide por su cuenta (por chat_id) si le
    # corresponde actuar. No requiere ningÃºn cambio en bot.py.
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_trial_group_new_member), group=1
    )

    # Recupera, al arrancar, cualquier expulsiÃ³n del grupo de prueba que
    # haya quedado pendiente de un reinicio anterior. Se programa aquÃ­
    # (usando application.job_queue directamente, ya disponible desde que
    # se llamÃ³ a Application.builder()...build() en bot.py) en vez de en
    # post_init() de bot.py, precisamente para no tener que tocar bot.py.
    if application.job_queue:
        application.job_queue.run_once(_reschedule_pending_trial_kicks, when=1)
    else:
        logger.error("[ventas] No job_queue available at startup; cannot reconcile pending trial kicks.")

    logger.info("[ventas] All sales-system handlers registered.")
