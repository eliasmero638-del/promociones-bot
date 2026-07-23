"""
Handlers de Telegram del sistema de ventas (Fase 7).

Este módulo define su PROPIO ConversationHandler, con sus propios estados
(números enteros locales a este handler - no colisionan con los estados
usados en bot.py para promociones/bienvenida, ya que cada ConversationHandler
mantiene su propia máquina de estados independiente).

Flujo:
  /start venta (deep-link desde el botón del canal)
    -> send_sales_welcome(): "🎁 Iniciar prueba gratis" / "💳 Comprar VIP" / "❓ FAQ"

  🎁 Iniciar prueba gratis:
    -> ventas_demo_callback(): entrega el enlace configurado del grupo de
       prueba (SALES_DEMO_GROUP_LINK).
    -> handle_trial_group_new_member() [MessageHandler sobre NEW_CHAT_MEMBERS,
       registrado en un "group" de manejo distinto al de bot.py para no
       interferir con el sistema de bienvenida]: detecta cualquier ingreso
       al grupo de prueba (SALES_TRIAL_GROUP_ID) y programa su expulsión
       automática exactamente 1 minuto después.
    -> _kick_trial_member() [job de JobQueue]: expulsa (ban + unban) al
       usuario del grupo de prueba. Esto SOLO aplica al grupo identificado
       por SALES_TRIAL_GROUP_ID - nunca al grupo VIP ni a ningún otro.

  💳 Comprar acceso VIP:
    -> ventas_vip_callback(): muestra el MENÚ de métodos de pago (sin
       datos financieros todavía).
    -> ventas_method_detail_callback(): al elegir un método, muestra
       ÚNICAMENTE los datos de ESE método.
    -> ventas_paid_entry() [entra a la conversación]: el método ya viaja en
       el callback_data ("ventas_paid_<method>"), así que solo pide el
       nombre + inicial del apellido del titular.
    -> ventas_receive_payer_name(): guarda la solicitud con el método ya
       elegido, notifica al admin, fin.

  Admin (mensaje privado recibido):
    sale_approve_callback() / sale_reject_callback(): resuelven la
    solicitud y notifican al comprador.

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

from .config import SalesConfigManager, TrialKicksStore
from .storage import SalesRequestsManager
from . import keyboards

logger = logging.getLogger("bot")

# Estado propio de este ConversationHandler (independiente de los de bot.py).
# El método de pago ya no es un estado: se elige ANTES de entrar a la
# conversación (en el menú de VIP), y viaja en el callback_data de
# "✅ Ya realicé el pago" - así que solo hace falta un estado: el nombre.
(VENTAS_PAYER_NAME,) = range(1)

# Cuánto puede permanecer un usuario en el grupo de prueba antes de ser
# expulsado automáticamente. Fijo en 1 minuto, tal como se pidió.
TRIAL_DURATION_SECONDS = 60

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
    start() cuando detecta el payload de deep-link ?start=venta, y también
    desde el botón "👑 Quiero ser VIP" del nuevo mensaje de /start. Se usa
    update.effective_message (en vez de update.message) para que funcione
    en ambos casos: un comando tiene update.message poblado, pero un botón
    presionado solo trae update.callback_query - effective_message resuelve
    a la que corresponda en cada caso, sin cambiar el comportamiento
    existente para /start venta."""
    await update.effective_message.reply_text(WELCOME_TEXT, reply_markup=keyboards.welcome_keyboard())


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
    """Entrega el enlace configurado del grupo de prueba. El seguimiento de
    quién debe ser expulsado y cuándo ocurre por completo en
    handle_trial_group_new_member()."""
    query = update.callback_query
    await query.answer()
    config = SalesConfigManager()
    admin_id = _get_admin_user_id()
    text = (
        "📂 ¡Perfecto! Aquí tienes el acceso a nuestro grupo de demostración.\n\n"
        "Podrás permanecer 1 minuto; pasado ese tiempo, el bot te retirará automáticamente."
    )
    if not config.get_demo_group_link():
        text = "El enlace de demostración aún no está configurado. Contacta al administrador."
    await _safe_edit_message(query, text, reply_markup=keyboards.demo_keyboard(config, admin_id))


async def handle_trial_group_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta cualquier ingreso al grupo de prueba (SALES_TRIAL_GROUP_ID) y
    programa su expulsión automática 1 minuto después.

    Aislamiento estricto: si SALES_TRIAL_GROUP_ID no está configurada, o si
    el chat donde ocurrió el ingreso no coincide EXACTAMENTE con ese ID,
    la función no hace nada - nunca actúa sobre el grupo VIP, el grupo
    principal de promociones, ni ningún otro chat donde el bot esté
    presente."""
    message = update.message
    if message is None or message.new_chat_members is None:
        return

    config = SalesConfigManager()
    trial_group_id = config.get_trial_group_id()

    logger.info(
        f"[ventas][trial_debug] NEW_CHAT_MEMBERS event received. "
        f"message.chat_id={message.chat_id} configured_trial_group_id={trial_group_id}"
    )

    if not trial_group_id:
        logger.warning(
            "[ventas][trial_debug] trial_group_id no está configurado (None); "
            "se ignora el evento. La expulsión automática no puede activarse sin este valor."
        )
        return

    if message.chat_id != trial_group_id:
        logger.info(
            f"[ventas][trial_debug] Ingreso ignorado: este chat ({message.chat_id}) "
            f"no coincide con el grupo de prueba configurado ({trial_group_id})."
        )
        return

    logger.info(
        f"[ventas][trial_debug] chat_id coincide con el grupo de prueba. "
        f"Procesando {len(message.new_chat_members)} nuevo(s) miembro(s)."
    )

    for member in message.new_chat_members:
        if member.is_bot:
            logger.info(f"[ventas][trial_debug] Ignorando ingreso de bot: {member.id}")
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
            logger.info(
                f"[ventas][trial_debug] Job de expulsión programado correctamente para "
                f"user_id={member.id} en {TRIAL_DURATION_SECONDS}s (job name=trial_kick_{trial_group_id}_{member.id})."
            )
        else:
            logger.error("[ventas] No job_queue available; cannot schedule automatic trial removal.")


async def _kick_trial_member(context: ContextTypes.DEFAULT_TYPE):
    """JobQueue callback: expulsa (ban + unban) a un usuario del grupo de
    prueba cuando se cumple su minuto. unban con only_if_banned=True hace
    que sea una expulsión, no un baneo permanente - la persona podría
    volver a entrar con el enlace en el futuro si el admin lo permite."""
    data = context.job.data
    chat_id, user_id = data["chat_id"], data["user_id"]

    logger.info(f"[ventas][trial_debug] Job de expulsión disparado para user_id={user_id} en chat_id={chat_id}.")

    ban_ok = False
    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        ban_ok = True
        logger.info(f"[ventas][trial_debug] ban_chat_member OK para user_id={user_id} en chat_id={chat_id}.")
    except TelegramError as e:
        logger.error(
            f"[ventas][trial_debug] ban_chat_member FALLÓ para user_id={user_id} en chat_id={chat_id}: {e}"
        )

    if ban_ok:
        try:
            await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
            logger.info(
                f"[ventas][trial_debug] unban_chat_member OK para user_id={user_id} en chat_id={chat_id}."
            )
            logger.info(f"[ventas] Removed user {user_id} from the trial group {chat_id} after the trial period ended.")
        except TelegramError as e:
            logger.error(
                f"[ventas][trial_debug] unban_chat_member FALLÓ para user_id={user_id} en chat_id={chat_id}: {e}"
            )

    # Se limpia el registro persistido en ambos casos (éxito o error) -
    # si falló porque ya no está en el grupo, reintentar por siempre
    # en cada reinicio no tendría sentido.
    TrialKicksStore().remove_pending_kick(chat_id, user_id)


async def _reschedule_pending_trial_kicks(context: ContextTypes.DEFAULT_TYPE):
    """Se ejecuta UNA SOLA VEZ, poco después de que el bot arranca (ver
    register_ventas_handlers). Recupera cualquier expulsión del grupo de
    prueba que haya quedado pendiente de un reinicio anterior (redeploy de
    Railway, crash, etc. durante la ventana de 1 minuto): si ya se cumplió
    la hora, expulsa de inmediato; si no, reprograma el tiempo restante en
    JobQueue. Así la expulsión automática sobrevive a un reinicio del bot."""
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


# --- "💳 Comprar acceso VIP" -> menú de métodos de pago ---

async def ventas_vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la pantalla de selección de grupo (nuevo paso previo). Los
    métodos de pago ya no se muestran aquí directamente - eso ocurre
    recién en ventas_buy_group_callback(), después de elegir un grupo."""
    query = update.callback_query
    await query.answer()
    await _safe_edit_message(
        query, "¿Qué grupo deseas adquirir?", reply_markup=keyboards.vip_group_selection_keyboard()
    )


async def ventas_group_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el detalle de UN grupo específico (nombre, beneficios,
    precio - el mismo precio ya configurado, sin uno distinto por grupo)."""
    query = update.callback_query
    await query.answer()

    group_key = query.data[len("ventas_group_"):]
    if group_key not in keyboards.GROUP_LABELS:
        return

    config = SalesConfigManager()
    label = keyboards.GROUP_LABELS[group_key]
    text = (
        f"{label}\n\n"
        "✅ Acceso inmediato.\n"
        "✅ Contenido actualizado diariamente.\n"
        "✅ Acceso exclusivo para miembros VIP.\n\n"
        f"💰 Precio: {config.get_vip_price()}\n\n"
        "Presiona \"Comprar ahora\" para continuar."
    )
    await _safe_edit_message(query, text, reply_markup=keyboards.group_detail_keyboard(group_key))


async def ventas_buy_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda el grupo elegido (se usará al guardar la solicitud de pago y,
    más adelante, al aprobarla) y recién aquí muestra el menú de métodos
    de pago - EXACTAMENTE el mismo texto/teclado que ya existía."""
    query = update.callback_query
    await query.answer()

    group_key = query.data[len("ventas_buy_"):]
    if group_key not in keyboards.GROUP_LABELS:
        return

    context.user_data["ventas_selected_group"] = group_key

    config = SalesConfigManager()
    admin_id = _get_admin_user_id()
    text = f"💳 *Acceso VIP* — {config.get_vip_price()}\n\nElige tu método de pago preferido:"
    await _safe_edit_message(
        query, text, reply_markup=keyboards.vip_menu_keyboard(admin_id), parse_mode="Markdown"
    )


_METHOD_DETAIL_GETTERS = {
    "bank_guayaquil": lambda c: c.get_bank_guayaquil_details(),
    "bank_pichincha": lambda c: c.get_bank_pichincha_details(),
    "paypal": lambda c: c.get_paypal_details(),
}


async def ventas_method_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Al elegir un método de pago específico, muestra ÚNICAMENTE la
    información de ESE método (nunca los otros)."""
    query = update.callback_query
    await query.answer()

    method_key = query.data[len("ventas_method_"):]
    if method_key not in keyboards.PAYMENT_METHOD_LABELS:
        return

    config = SalesConfigManager()
    admin_id = _get_admin_user_id()
    label = keyboards.PAYMENT_METHOD_LABELS[method_key]
    details = _METHOD_DETAIL_GETTERS[method_key](config)

    if details:
        text = f"{label}\n\n{details}"
    else:
        logger.warning(f"[ventas] Method '{method_key}' selected but has no configured details.")
        text = f"{label}\n\nEste método aún no está configurado. Contacta al administrador."

    await _safe_edit_message(
        query, text, reply_markup=keyboards.method_detail_keyboard(method_key, admin_id), parse_mode="Markdown"
    )


# --- "❓ Preguntas frecuentes" ---

async def ventas_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    config = SalesConfigManager()
    await _safe_edit_message(query, config.get_faq_text(), reply_markup=keyboards.faq_keyboard())


# --- "💰 Quiero vender contenido" ---

async def ventas_sell_content_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "¿Quieres vender tu contenido o grupo?\n\n"
        "El administrador revisará tu solicitud.\n\n"
        "Presiona el botón de abajo para hablar directamente con el administrador."
    )
    await _safe_edit_message(query, text, reply_markup=keyboards.sell_content_keyboard())


# --- "✅ Ya realicé el pago" -> pedir SOLO el titular (el método ya se conoce) ---

async def ventas_paid_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point de la conversación: el método de pago viaja en el
    callback_data (ventas_paid_<method_key>), así que solo hace falta
    pedir el nombre del titular del pago.

    Antes de iniciar, verifica que el usuario no tenga ya una solicitud
    "pending" en curso - así se evita que un doble tap (o que el usuario
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
            "⏳ Ya tienes una solicitud de pago en revisión.\n\n"
            "Un administrador la confirmará pronto. Te avisaremos aquí mismo apenas se resuelva."
        )
        return ConversationHandler.END

    context.user_data["ventas_payment_method_key"] = method_key
    context.user_data.pop("ventas_payer_name", None)
    await query.edit_message_text(
        "✍️ Por favor, envía el nombre y la inicial del apellido del titular del pago.\n\n"
        "Ejemplo: Ricardo M."
    )
    return VENTAS_PAYER_NAME


async def ventas_receive_payer_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre del titular, guarda la solicitud (el método ya se
    conoce desde ventas_paid_entry) y notifica al administrador."""
    payer_name = update.message.text.strip()
    method_key = context.user_data.pop("ventas_payment_method_key", None)

    if not method_key or method_key not in keyboards.PAYMENT_METHOD_LABELS:
        # Estado inesperado (p. ej. el proceso se reinició a mitad de camino).
        await update.message.reply_text("❌ Ocurrió un problema, por favor comienza de nuevo con /start.")
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
        "group_key": context.user_data.pop("ventas_selected_group", None),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "admin_message_id": None,
    }
    request_id = manager.add(request)

    if not request_id:
        logger.error(f"[ventas] Failed to save payment request for user {user.id}.")
        await update.message.reply_text(
            "❌ Ocurrió un error al registrar tu información. Por favor contacta al administrador directamente."
        )
        return ConversationHandler.END

    await update.message.reply_text(
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
    group_key = request.get("group_key")
    group_line = f"Grupo: {keyboards.GROUP_LABELS[group_key]}\n" if group_key in keyboards.GROUP_LABELS else ""
    text = (
        "🛒 *Nueva solicitud de pago VIP*\n\n"
        f"Usuario: {request['user_first_name']} ({username_part})\n"
        f"{group_line}"
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


async def _create_vip_invite_link(context: ContextTypes.DEFAULT_TYPE, vip_group_id: int) -> str:
    """Intenta crear un enlace de invitación dinámico con member_limit=1
    para el grupo VIP. Devuelve el enlace generado, o None si falla.
    
    Validaciones:
    - Verifica que vip_group_id sea un número válido
    - Detecta errores de permisos y los registra claramente
    - Nunca levanta excepciones (log + fallback silencioso)
    """
    if not vip_group_id:
        logger.error("[ventas] Cannot create VIP invite link: vip_group_id is not configured.")
        return None

    try:
        link_obj = await context.bot.create_chat_invite_link(
            chat_id=vip_group_id,
            member_limit=1,
        )
        generated_link = link_obj.invite_link
        logger.info(
            f"[ventas] Successfully created dynamic VIP invite link with member_limit=1: {generated_link}"
        )
        return generated_link
    except TelegramError as e:
        error_msg = str(e)
        if "not enough rights" in error_msg or "CHAT_ADMIN_REQUIRED" in error_msg:
            logger.error(
                f"[ventas] Bot does not have permission to create invite links in VIP group {vip_group_id}. "
                f"Error: {e}. Falling back to configured link."
            )
        else:
            logger.error(
                f"[ventas] Failed to create VIP invite link for group {vip_group_id}: {e}. "
                f"Falling back to configured link."
            )
        return None


# --- Aprobar / Rechazar (acciones del admin, fuera de la conversación) ---

async def sale_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aprueba un pago y entrega el acceso VIP al usuario mediante:
    1. Intento de crear un enlace dinámico con member_limit=1
    2. Si falla, usar el enlace configurado como respaldo
    3. Enviar SOLO un botón inline con el enlace, nunca mostrar la URL
    """
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
    user_id = request["user_id"]
    group_key = request.get("group_key")

    logger.info(
        f"[ventas][approve_debug] request_id={request_id} group_key={group_key!r} "
        f"(request completa: {request})"
    )

    # Identifica qué grupo compró el usuario y usa el ID/enlace de ESE
    # grupo. Si la solicitud no tiene group_key (creada antes de este
    # cambio), se mantiene el comportamiento anterior exactamente igual,
    # usando el grupo VIP único configurado - así ninguna solicitud ya en
    # curso se ve afectada.
    if group_key == "portoviejo":
        vip_group_id = config.get_portoviejo_group_id()
        configured_link = config.get_portoviejo_group_link()
    elif group_key == "ecuatorianas":
        vip_group_id = config.get_ecuatorianas_group_id()
        configured_link = config.get_ecuatorianas_group_link()
    else:
        vip_group_id = config.get_vip_group_id()
        configured_link = config.get_vip_group_link()
        logger.warning(
            f"[ventas][approve_debug] group_key={group_key!r} no es 'portoviejo' ni 'ecuatorianas' "
            f"(solicitud probablemente creada antes de tener grupos); usando el respaldo genérico "
            f"vip_group_id={vip_group_id!r} vip_group_link={configured_link!r}."
        )

    logger.info(
        f"[ventas][approve_debug] vip_group_id={vip_group_id!r} configured_link={configured_link!r}"
    )

    # Intenta crear enlace dinámico; si falla, usa el configurado
    vip_link = None
    if vip_group_id:
        vip_link = await _create_vip_invite_link(context, vip_group_id)
        logger.info(f"[ventas][approve_debug] Enlace dinámico creado: {vip_link!r}")

    # Si la creación dinámica falló (o no está configurado), usar fallback
    if not vip_link:
        vip_link = configured_link
        if vip_link:
            logger.info(f"[ventas] Using fallback configured VIP link for user {user_id}.")
        else:
            logger.warning(
                f"[ventas] No VIP link available (neither dynamic creation nor fallback configured) "
                f"for user {user_id}."
            )

    # Notificar al usuario
    try:
        if vip_link:
            # Enviar SOLO el botón con el enlace (no mostrar URL como texto)
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ Tu pago fue aprobado.\n\n"
                    "Tu acceso está listo.\n\n"
                    "Presiona el botón para ingresar al grupo."
                ),
                reply_markup=keyboards.vip_access_keyboard(vip_link, _get_admin_user_id()),
            )
            logger.info(f"[ventas] Sent VIP access button to user {user_id}.")
        else:
            # Fallback: si no hay enlace de ningún tipo, mensaje genérico
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Tu pago fue aprobado. El administrador te contactará pronto con el acceso al grupo VIP.",
            )
            logger.warning(f"[ventas] Sent generic approval message to user {user_id} (no VIP link available).")
    except TelegramError as e:
        logger.error(f"[ventas] Could not notify user {user_id} of approval: {e}")

    # Confirmar en el mensaje al admin
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
    context.user_data.pop("ventas_payment_method_key", None)
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
    de pago), completamente independiente del ConversationHandler de
    bot.py. El método de pago ya no es un estado propio: se elige antes de
    entrar aquí, así que solo hay un estado (el nombre del titular)."""
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
    """Punto único de integración con bot.py: registra todos los handlers
    del módulo de ventas en la Application. Los CallbackQueryHandler deben
    llamarse ANTES del catch-all de bot.py (button_callback sin patrón),
    para que los callback_data de ventas no queden atrapados ahí."""
    application.add_handler(build_ventas_conversation_handler())
    application.add_handler(CallbackQueryHandler(ventas_demo_callback, pattern="^ventas_demo$"))
    application.add_handler(CallbackQueryHandler(ventas_vip_callback, pattern="^ventas_vip$"))
    application.add_handler(
        CallbackQueryHandler(ventas_group_detail_callback, pattern="^ventas_group_(portoviejo|ecuatorianas)$")
    )
    application.add_handler(
        CallbackQueryHandler(ventas_buy_group_callback, pattern="^ventas_buy_(portoviejo|ecuatorianas)$")
    )
    application.add_handler(
        CallbackQueryHandler(ventas_method_detail_callback, pattern="^ventas_method_(bank_guayaquil|bank_pichincha|paypal)$")
    )
    application.add_handler(CallbackQueryHandler(ventas_faq_callback, pattern="^ventas_faq$"))
    application.add_handler(CallbackQueryHandler(ventas_sell_content_callback, pattern="^ventas_sell_content$"))
    application.add_handler(CallbackQueryHandler(ventas_back_to_welcome_callback, pattern="^ventas_back_to_welcome$"))
    application.add_handler(CallbackQueryHandler(sale_approve_callback, pattern="^sale_approve_.+$"))
    application.add_handler(CallbackQueryHandler(sale_reject_callback, pattern="^sale_reject_.+$"))
    # Detecta ingresos al grupo de prueba para expulsar automáticamente al
    # cumplirse 1 minuto. Se registra en group=1 (distinto del group=0 por
    # defecto que usa bot.py para su propio detector de NEW_CHAT_MEMBERS,
    # el de la bienvenida). python-telegram-bot solo invoca al primer
    # handler que matchea un filtro DENTRO de un mismo group; si este
    # handler compartiera el group con el de bot.py, cualquiera que se
    # registrara primero "consumiría" el evento y el otro dejaría de
    # funcionar. Con groups distintos, ambos evalúan cada ingreso de forma
    # independiente y cada uno decide por su cuenta (por chat_id) si le
    # corresponde actuar. No requiere ningún cambio en bot.py.
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_trial_group_new_member), group=1
    )

    # Recupera, al arrancar, cualquier expulsión del grupo de prueba que
    # haya quedado pendiente de un reinicio anterior. Se programa aquí
    # (usando application.job_queue directamente, ya disponible desde que
    # se llamó a Application.builder()...build() en bot.py) en vez de en
    # post_init() de bot.py, precisamente para no tener que tocar bot.py.
    if application.job_queue:
        application.job_queue.run_once(_reschedule_pending_trial_kicks, when=1)
    else:
        logger.error("[ventas] No job_queue available at startup; cannot reconcile pending trial kicks.")

    logger.info("[ventas] All sales-system handlers registered.")
