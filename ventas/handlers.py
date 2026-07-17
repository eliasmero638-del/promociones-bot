"""
Handlers de Telegram del sistema de ventas (Fase 7).

Este módulo define su PROPIO ConversationHandler, con sus propios estados
(números enteros locales a este handler - no colisionan con los estados
usados en bot.py para promociones/bienvenida, ya que cada ConversationHandler
mantiene su propia máquina de estados independiente).

Flujo:
  /start venta (deep-link desde el botón del canal)
    -> send_sales_welcome(): "🎁 Iniciar prueba gratis" / "💳 Comprar VIP" / "❓ FAQ"
       -> ventas_demo_callback(): enlace al grupo de demostración
       -> ventas_vip_callback(): precio + datos bancarios + PayPal + "✅ Ya pagué"
          -> ventas_paid_entry() [entra a la conversación]: pide nombre del titular
             -> ventas_receive_payer_name(): pide método de pago (botones)
                -> ventas_receive_payment_method(): guarda la solicitud, notifica al admin, fin

  Admin (mensaje privado recibido):
    sale_approve_callback() / sale_reject_callback(): resuelven la solicitud
    y notifican al comprador.

NOTA (primera versión de producción, sin panel de configuración todavía):
la configuración del módulo (precio, bancos, PayPal, enlaces, FAQ) se
edita directamente en ventas/config.py (los valores por defecto en
_default_config()) o cargando un valor a Upstash manualmente. El menú
"🛍️ Configurar Ventas" desde el panel se agregará en una fase posterior,
una vez validado el flujo completo de venta en producción.

Todo lo que este módulo necesita de bot.py (ADMIN_USER_ID) se importa de
forma diferida dentro de las funciones - ver docstring de ventas/config.py.
"""

import logging
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

from .config import SalesConfigManager
from .storage import SalesRequestsManager
from . import keyboards

logger = logging.getLogger("bot")

# Estados propios de este ConversationHandler (independientes de los de bot.py).
VENTAS_PAYER_NAME, VENTAS_PAYMENT_METHOD = range(2)

WELCOME_TEXT = (
    "👋 ¡Bienvenido!\n\n"
    "Antes de adquirir el acceso VIP, puedes probar una demostración "
    "gratuita para comprobar la calidad del contenido."
)


def _get_admin_user_id():
    from bot import ADMIN_USER_ID
    return ADMIN_USER_ID


# --- Bienvenida del embudo de ventas (entrada vía deep-link /start venta) ---

async def send_sales_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú de bienvenida de ventas. Llamado desde bot.py's
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


# --- "🎁 Iniciar prueba gratis" ---

async def ventas_demo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    config = SalesConfigManager()
    text = "📂 ¡Perfecto! Aquí tienes el acceso a nuestro grupo de demostración."
    if not config.get_demo_group_link():
        text = "El enlace de demostración aún no está configurado. Contacta al administrador."
    await _safe_edit_message(query, text, reply_markup=keyboards.demo_keyboard(config))


# --- "💳 Comprar acceso VIP" ---

async def ventas_vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    config = SalesConfigManager()

    lines = [f"💳 *Acceso VIP* — {config.get_vip_price()}", ""]
    if config.get_bank_guayaquil_details():
        lines.append(f"🏦 *Banco Guayaquil*\n{config.get_bank_guayaquil_details()}")
        lines.append("")
    if config.get_bank_pichincha_details():
        lines.append(f"🏦 *Banco Pichincha*\n{config.get_bank_pichincha_details()}")
        lines.append("")
    if config.get_paypal_details():
        lines.append(f"💳 *PayPal*\n{config.get_paypal_details()}")
        lines.append("")
    lines.append("Cuando hayas realizado el pago, pulsa el botón de abajo.")

    await _safe_edit_message(
        query, "\n".join(lines), reply_markup=keyboards.vip_purchase_keyboard(), parse_mode="Markdown"
    )


# --- "❓ Preguntas frecuentes" ---

async def ventas_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    config = SalesConfigManager()
    await _safe_edit_message(query, config.get_faq_text(), reply_markup=keyboards.welcome_keyboard())


# --- "✅ Ya realicé el pago" -> pedir titular + método ---

async def ventas_paid_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point de la conversación: pide el nombre del titular del pago.

    Antes de iniciar, verifica que el usuario no tenga ya una solicitud
    "pending" en curso - así se evita que un doble tap (o que el usuario
    repita el proceso mientras espera respuesta) genere una segunda
    solicitud duplicada y, con ella, un segundo aviso duplicado al admin
    por el mismo pago.
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    manager = SalesRequestsManager()
    already_pending = any(
        req.get("user_id") == user_id and req.get("status") == "pending"
        for req in manager.get_all()
    )
    if already_pending:
        logger.info(f"[ventas] User {user_id} tried to submit a new payment while one is still pending; blocked.")
        await query.edit_message_text(
            "⏳ Ya tienes una solicitud de pago en revisión.\n\n"
            "Un administrador la confirmará pronto. Te avisaremos aquí mismo apenas se resuelva."
        )
        return ConversationHandler.END

    context.user_data.pop("ventas_payer_name", None)
    await query.edit_message_text(
        "✍️ Por favor, envía el nombre y la inicial del apellido del titular del pago.\n\n"
        "Ejemplo: Ricardo M."
    )
    return VENTAS_PAYER_NAME


async def ventas_receive_payer_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre del titular y pide el método de pago (por botones)."""
    payer_name = update.message.text.strip()
    context.user_data["ventas_payer_name"] = payer_name
    logger.info(f"[ventas] Payer name received from user {update.effective_user.id}: {payer_name!r}")
    await update.message.reply_text(
        "¿Qué método de pago utilizaste?", reply_markup=keyboards.payment_method_keyboard()
    )
    return VENTAS_PAYMENT_METHOD


async def ventas_receive_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el método de pago (botón), guarda la solicitud y notifica al admin."""
    query = update.callback_query
    await query.answer()

    method_key = query.data[len("ventas_method_"):]
    method_label = keyboards.PAYMENT_METHOD_LABELS.get(method_key, method_key)

    payer_name = context.user_data.pop("ventas_payer_name", None)
    if not payer_name:
        # Estado inesperado (p. ej. el proceso se reinició a mitad de camino).
        await query.edit_message_text("❌ Ocurrió un problema, por favor comienza de nuevo con /start.")
        return ConversationHandler.END

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
        await query.edit_message_text(
            "❌ Ocurrió un error al registrar tu información. Por favor contacta al administrador directamente."
        )
        return ConversationHandler.END

    await query.edit_message_text(
        "✅ ¡Gracias! Recibimos tu información:\n\n"
        f"{payer_name}\n{method_label}.\n\n"
        "Un administrador revisará tu pago pronto y te notificaremos aquí mismo."
    )

    await _notify_admin_new_sale_request(context, request_id, request)
    return ConversationHandler.END


async def _notify_admin_new_sale_request(context: ContextTypes.DEFAULT_TYPE, request_id: str, request: dict):
    """Envía al admin los datos de la solicitud con botones Aprobar/Rechazar."""
    admin_id = _get_admin_user_id()
    username_part = f"@{request['user_username']}" if request.get("user_username") else f"id {request['user_id']}"
    text = (
        "🛒 *Nueva solicitud de pago VIP*\n\n"
        f"Usuario: {request['user_first_name']} ({username_part})\n"
        f"Titular del pago: {request['payer_name']}\n"
        f"Método: {request['payment_method']}"
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


# --- Aprobar / Rechazar (acciones del admin, fuera de la conversación) ---

async def sale_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != _get_admin_user_id():
        await query.answer("❌ No tienes permiso.", show_alert=True)
        return

    request_id = query.data[len("sale_approve_"):]
    manager = SalesRequestsManager()
    request = manager.get_by_id(request_id)

    if not request:
        await query.edit_message_text("❌ Esta solicitud ya no existe.")
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
                text=f"✅ ¡Tu pago fue aprobado! Este es tu acceso al grupo VIP:\n{vip_link}",
            )
        else:
            await context.bot.send_message(
                chat_id=request["user_id"],
                text="✅ Tu pago fue aprobado. El administrador te contactará pronto con el acceso al grupo VIP.",
            )
    except TelegramError as e:
        logger.error(f"[ventas] Could not notify user {request['user_id']} of approval: {e}")

    await query.edit_message_text(
        f"✅ Aprobado — {request['payer_name']} ({request['payment_method']}). Se notificó al usuario."
    )


async def sale_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != _get_admin_user_id():
        await query.answer("❌ No tienes permiso.", show_alert=True)
        return

    request_id = query.data[len("sale_reject_"):]
    manager = SalesRequestsManager()
    request = manager.get_by_id(request_id)

    if not request:
        await query.edit_message_text("❌ Esta solicitud ya no existe.")
        return

    request["status"] = "rejected"
    request["resolved_at"] = datetime.now().isoformat()
    manager.update(request_id, request)
    logger.info(f"[ventas] Payment request {request_id} rejected by admin.")

    try:
        await context.bot.send_message(
            chat_id=request["user_id"],
            text="❌ No pudimos verificar tu pago. Por favor contacta al administrador para resolverlo.",
        )
    except TelegramError as e:
        logger.error(f"[ventas] Could not notify user {request['user_id']} of rejection: {e}")

    await query.edit_message_text(
        f"❌ Rechazado — {request['payer_name']} ({request['payment_method']}). Se notificó al usuario."
    )


# Quality audit fix: how long (seconds) a buyer can be inactive mid-way
# through "Ya realicé el pago" (name -> method) before it auto-cancels.
# Without this, abandoning the flow left them stuck: entry_points are
# bypassed while a conversation is already active for that user, so
# tapping "✅ Ya realicé el pago" again would silently do nothing.
VENTAS_CONVERSATION_TIMEOUT_SECONDS = 300  # 5 minutes


async def ventas_conversation_timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when the payment conversation times out. Clears any partial
    state and lets the buyer know they can start over."""
    context.user_data.pop("ventas_payer_name", None)
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "⏱️ Se agotó el tiempo de espera. Si deseas continuar, pulsa /start de nuevo."
            )
        elif update.message:
            await update.message.reply_text(
                "⏱️ Se agotó el tiempo de espera. Si deseas continuar, pulsa /start de nuevo."
            )
    except TelegramError as e:
        logger.warning(f"[ventas] Could not notify user of conversation timeout: {e}")


def build_ventas_conversation_handler():
    """Construye el ConversationHandler del módulo de ventas (solo el flujo
    de pago en esta primera versión), completamente independiente del
    ConversationHandler de bot.py."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ventas_paid_entry, pattern="^ventas_paid$"),
        ],
        states={
            VENTAS_PAYER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ventas_receive_payer_name)],
            VENTAS_PAYMENT_METHOD: [CallbackQueryHandler(ventas_receive_payment_method, pattern="^ventas_method_.+$")],
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
    """Punto único de integración con bot.py: registra todos los handlers
    del módulo de ventas en la Application. Debe llamarse ANTES del
    CallbackQueryHandler "catch-all" de bot.py (button_callback sin
    patrón), para que los callback_data de ventas no queden atrapados ahí."""
    application.add_handler(build_ventas_conversation_handler())
    application.add_handler(CallbackQueryHandler(ventas_demo_callback, pattern="^ventas_demo$"))
    application.add_handler(CallbackQueryHandler(ventas_vip_callback, pattern="^ventas_vip$"))
    application.add_handler(CallbackQueryHandler(ventas_faq_callback, pattern="^ventas_faq$"))
    application.add_handler(CallbackQueryHandler(ventas_back_to_welcome_callback, pattern="^ventas_back_to_welcome$"))
    application.add_handler(CallbackQueryHandler(sale_approve_callback, pattern="^sale_approve_.+$"))
    application.add_handler(CallbackQueryHandler(sale_reject_callback, pattern="^sale_reject_.+$"))
    logger.info("[ventas] All sales-system handlers registered (payment flow only; panel config deferred).")
