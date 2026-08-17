"""
Construcción de los teclados inline usados por el flujo de ventas.
Funciones puras (reciben datos, devuelven un InlineKeyboardMarkup) para
mantener handlers.py enfocado en la lógica de conversación con Telegram.
"""

import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import SalesConfigManager

# Username de Telegram (sin @) usado como contacto fijo del administrador
# en todo este flujo de ventas. Mismo default histórico de esta
# instalación ("El593re") - configurable via SALES_ADMIN_CONTACT_USERNAME
# (la misma variable que usa bot.py) para que una instalación nueva use su
# propio contacto sin tocar el código.
_ADMIN_CONTACT_USERNAME = os.getenv("SALES_ADMIN_CONTACT_USERNAME", "El593re").strip().lstrip("@")
# Username de Telegram (sin @) usado en la pantalla "Quiero vender
# contenido" (mismo default histórico "el593rm" - normalmente el mismo que
# bot.py::DEFAULT_ADMIN_USERNAME). Configurable via DEFAULT_ADMIN_USERNAME.
_SELL_CONTENT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "el593rm").strip().lstrip("@")

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
            [InlineKeyboardButton("👤 Hablar con el administrador", url=f"https://t.me/{_SELL_CONTENT_ADMIN_USERNAME}")],
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
    """Botón "Contactar al administrador". Fix de producción: url="tg://user?id=..."
    lo rechaza Telegram con "Button_user_invalid" (confirmado en logs de
    Railway - rompía /start en el sistema nuevo; este botón usa el mismo
    esquema, así que tiene el mismo problema latente). Se usa un enlace
    público normal en su lugar, igual que _contact_admin_el593re_button()
    de este mismo archivo (nunca reportado roto). Se mantiene el parámetro
    admin_user_id sin usar para no tener que tocar cada call site."""
    return InlineKeyboardButton("👤 Contactar al administrador", url=f"https://t.me/{_ADMIN_CONTACT_USERNAME}")


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
    return InlineKeyboardButton("👤 CONTACTAR AL ADMINISTRADOR", url=f"https://t.me/{_ADMIN_CONTACT_USERNAME}")


def _buy_exclusive_access_button(bot_username: str = "") -> InlineKeyboardButton:
    """Botón "⚡ Acceso rápido" de la pantalla principal "🔒 Acceso
    exclusivo a grupos VIP": abre este mismo bot (es el bot de ventas).
    `bot_username` se calcula dinámicamente (context.bot.username) en el
    call site en vez de escribirse a mano, así funciona igual sin importar
    con qué @username de Telegram esté corriendo esta instalación. Si por
    algún motivo no está disponible, cae de vuelta al contacto del
    administrador."""
    if bot_username:
        return InlineKeyboardButton("⚡ Acceso rápido", url=f"https://t.me/{bot_username}")
    return _contact_admin_el593re_button()


def vip_exclusive_keyboard(bot_username: str = "") -> InlineKeyboardMarkup:
    """Pantalla "🔒 Acceso exclusivo a grupos VIP": los dos botones pedidos
    + Volver al menú principal (su nivel superior)."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🧪 INICIAR PRUEBA GRATUITA", callback_data="ventas_vip_exclusive_trial")],
            [_buy_exclusive_access_button(bot_username)],
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
        rows.append([InlineKeyboardButton("📂 Entrar al Grupo Free", url=free_link)])
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
