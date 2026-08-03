"""
Construcción de los teclados inline usados por el flujo de ventas.
Funciones puras (reciben datos, devuelven un InlineKeyboardMarkup) para
mantener handlers.py enfocado en la lógica de conversación con Telegram.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import SalesConfigManager

PAYMENT_METHOD_LABELS = {
    "bank_guayaquil": "🏦 Banco Guayaquil",
    "bank_pichincha": "🏦 Banco Pichincha",
    "paypal": "💳 PayPal",
}

# Grupos VIP disponibles para la venta.
GROUP_LABELS = {
    "portoviejo": "🔥 Portoviejo Caliente",
    "ecuatorianas": "🇪🇨 Ecuatorianas Calientes",
}


def welcome_keyboard() -> InlineKeyboardMarkup:
    """Menú principal mostrado directamente en /start. Solo estos 3 botones
    son visibles a pedido explícito; los del menú antiguo (QUIERO SER VIP,
    Iniciar prueba gratis, Preguntas frecuentes) quedan ocultos pero sus
    handlers siguen registrados e intactos (ventas_vip_callback,
    ventas_demo_callback / send_demo_directly vía deep-link ?start=demo,
    ventas_faq_callback) - para volver a mostrarlos en este menú alcanza
    con descomentar sus líneas."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔒 ACCESO EXCLUSIVO A GRUPOS VIP", callback_data="ventas_vip_exclusive")],
            [InlineKeyboardButton("🆓 OBTENER GRUPO FREE", callback_data="ventas_free_group")],
            [InlineKeyboardButton("💰 Quiero vender contenido", callback_data="ventas_sell_content")],
            # [InlineKeyboardButton("🔥 QUIERO SER VIP 🔥", callback_data="ventas_vip")],
            # [InlineKeyboardButton("🎁 Iniciar prueba gratis", callback_data="ventas_demo")],
            # [InlineKeyboardButton("❓ Preguntas frecuentes", callback_data="ventas_faq")],
        ]
    )


def sell_content_keyboard() -> InlineKeyboardMarkup:
    """Pantalla de "💰 Quiero vender contenido": contactar directamente al
    administrador (enlace fijo, no tg://user?id=, a pedido explícito) +
    Volver al menú principal (su único nivel superior)."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👤 Hablar con el administrador", url="https://t.me/el593rm")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="ventas_back_to_welcome")],
        ]
    )


def faq_keyboard() -> InlineKeyboardMarkup:
    """Pantalla de preguntas frecuentes: un único botón para volver al
    menú principal (a diferencia de welcome_keyboard(), que repite las
    3 opciones completas)."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⬅️ Volver", callback_data="ventas_back_to_welcome")],
        ]
    )


def vip_group_selection_keyboard() -> InlineKeyboardMarkup:
    """Pantalla nueva: elegir a qué grupo se quiere comprar acceso, ANTES
    de mostrar los métodos de pago. El "Volver" regresa al menú principal,
    igual que ya hacía el "Volver" del menú de métodos de pago."""
    rows = [
        [InlineKeyboardButton(label, callback_data=f"ventas_group_{key}")]
        for key, label in GROUP_LABELS.items()
    ]
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data="ventas_back_to_welcome")])
    return InlineKeyboardMarkup(rows)


def group_detail_keyboard(group_key: str) -> InlineKeyboardMarkup:
    """Pantalla de detalle de UN grupo específico. "Comprar ahora" recién
    ahí lleva al menú de métodos de pago existente (sin cambios en ese
    menú); "Volver" regresa a la selección de grupo."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Comprar ahora", callback_data=f"ventas_buy_{group_key}")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="ventas_vip")],
        ]
    )


def demo_keyboard(config: SalesConfigManager, admin_user_id: int) -> InlineKeyboardMarkup:
    """Logic fix: el botón de respaldo (cuando no hay enlace de demo
    configurado) antes decía "Contactar al administrador" pero en realidad
    solo volvía al menú - ahora usa un enlace real (tg://user?id=), igual
    que en el resto del flujo."""
    demo_link = config.get_demo_group_link()
    rows = []
    if demo_link:
        rows.append([InlineKeyboardButton("🚪 Entrar a la prueba gratis", url=demo_link)])
    else:
        rows.append([_contact_admin_button(admin_user_id)])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data="ventas_back_to_welcome")])
    return InlineKeyboardMarkup(rows)


def _contact_admin_button(admin_user_id: int) -> InlineKeyboardButton:
    """Botón "Contactar al administrador" mediante tg://user?id=, que abre
    un chat directo sin necesitar un @usuario público configurado. Recibe
    el ID como parámetro (en vez de importarlo aquí desde bot.py) para que
    este archivo siga siendo solo funciones puras, tal como indica el
    docstring del módulo."""
    return InlineKeyboardButton("👤 Contactar al administrador", url=f"tg://user?id={admin_user_id}")


def vip_menu_keyboard(admin_user_id: int, group_key: str) -> InlineKeyboardMarkup:
    """Menú de métodos de pago. Cada método se elige primero; sus datos
    específicos se muestran recién en method_detail_keyboard(). "Volver"
    regresa al nivel inmediatamente anterior: el detalle del grupo elegido
    (no al menú principal)."""
    rows = [
        [InlineKeyboardButton(label, callback_data=f"ventas_method_{key}")]
        for key, label in PAYMENT_METHOD_LABELS.items()
    ]
    rows.append([_contact_admin_button(admin_user_id)])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data=f"ventas_group_{group_key}")])
    return InlineKeyboardMarkup(rows)


def method_detail_keyboard(method_key: str, admin_user_id: int, group_key: str) -> InlineKeyboardMarkup:
    """Botones de la pantalla de detalle de UN método de pago específico.
    "Ya realicé el pago" lleva el método codificado en el callback_data,
    así la conversación de pago ya no necesita volver a preguntarlo.
    "Volver" regresa al menú de métodos de pago (reutiliza
    ventas_buy_group_callback, que ya reconstruye esa pantalla completa)."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Ya realicé el pago", callback_data=f"ventas_paid_{method_key}")],
            [_contact_admin_button(admin_user_id)],
            [InlineKeyboardButton("⬅️ Volver", callback_data=f"ventas_buy_{group_key}")],
        ]
    )


def admin_approval_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Aprobar", callback_data=f"sale_approve_{request_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"sale_reject_{request_id}"),
            ]
        ]
    )


def _contact_admin_el593re_button() -> InlineKeyboardButton:
    """Botón "Contactar al administrador" específico del flujo "🔒 Acceso
    exclusivo a grupos VIP" (pantalla de "prueba ya utilizada" y respaldo
    sin enlace configurado): a pedido explícito, abre directamente
    @El593re (en vez de tg://user?id=ADMIN_USER_ID, como el resto del
    flujo de ventas)."""
    return InlineKeyboardButton("👤 CONTACTAR AL ADMINISTRADOR", url="https://t.me/El593re")


def _buy_exclusive_access_button() -> InlineKeyboardButton:
    """Botón "💎 Comprar acceso exclusivo" de la pantalla principal "🔒
    Acceso exclusivo a grupos VIP": mismo destino que
    _contact_admin_el593re_button() (@El593re), solo cambia el texto."""
    return InlineKeyboardButton("💎 COMPRAR ACCESO EXCLUSIVO", url="https://t.me/El593re")


def vip_exclusive_keyboard() -> InlineKeyboardMarkup:
    """Pantalla "🔒 Acceso exclusivo a grupos VIP": los dos botones pedidos
    + Volver al menú principal (su nivel superior)."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🧪 INICIAR PRUEBA GRATUITA", callback_data="ventas_vip_exclusive_trial")],
            [_buy_exclusive_access_button()],
            [InlineKeyboardButton("⬅️ Volver", callback_data="ventas_back_to_welcome")],
        ]
    )


def vip_exclusive_trial_used_keyboard() -> InlineKeyboardMarkup:
    """Cuando el usuario ya usó su única prueba gratuita: el botón de
    contactar al administrador + Volver a la pantalla de acceso exclusivo
    (de donde se llega a esta pantalla)."""
    return InlineKeyboardMarkup(
        [
            [_contact_admin_el593re_button()],
            [InlineKeyboardButton("⬅️ Volver", callback_data="ventas_vip_exclusive")],
        ]
    )


def vip_exclusive_trial_link_keyboard(trial_link: str) -> InlineKeyboardMarkup:
    """Entrega el enlace del Grupo de Prueba como botón (nunca como texto
    plano, siguiendo la convención ya usada en el resto del proyecto).
    Volver regresa a la pantalla de acceso exclusivo."""
    rows = []
    if trial_link:
        rows.append([InlineKeyboardButton("🚪 Entrar a la prueba gratuita", url=trial_link)])
    else:
        rows.append([_contact_admin_el593re_button()])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data="ventas_vip_exclusive")])
    return InlineKeyboardMarkup(rows)


def free_group_keyboard(free_link: str, admin_user_id: int) -> InlineKeyboardMarkup:
    """Entrega el enlace del grupo Free (independiente del grupo de
    prueba). Volver regresa al menú principal (su nivel superior)."""
    rows = []
    if free_link:
        rows.append([InlineKeyboardButton("🚪 Entrar al grupo Free", url=free_link)])
    else:
        rows.append([_contact_admin_button(admin_user_id)])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data="ventas_back_to_welcome")])
    return InlineKeyboardMarkup(rows)


def vip_access_keyboard(vip_link: str, admin_user_id: int) -> InlineKeyboardMarkup:
    """Teclado para el mensaje de aprobación: "🚪 Unirme al grupo" (el
    enlace, dinámico o fallback, nunca se muestra como texto - solo como
    URL del botón) + "👤 Contactar al administrador", igual que en el
    resto del flujo de ventas."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚪 Unirme al grupo", url=vip_link)],
            [_contact_admin_button(admin_user_id)],
        ]
    )
