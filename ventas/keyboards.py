""" Construcción de los teclados inline usados por el flujo de ventas. Funciones puras (reciben datos, devuelven un InlineKeyboardMarkup) para mantener handlers.py enfocado en la lógica de conversación con Telegram. """

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import SalesConfigManager

PAYMENT_METHOD_LABELS = {
    "bank_guayaquil": "🏦 Banco Guayaquil",
    "bank_pichincha": "🏦 Banco Pichincha",
    "paypal": "💳 PayPal",
}


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎁 Iniciar prueba gratis", callback_data="ventas_demo")],
            [InlineKeyboardButton("💳 Comprar acceso VIP", callback_data="ventas_vip")],
            [InlineKeyboardButton("❓ Preguntas frecuentes", callback_data="ventas_faq")],
        ]
    )


def demo_keyboard(config: SalesConfigManager, admin_user_id: int) -> InlineKeyboardMarkup:
    """Logic fix: el botón de respaldo (cuando no hay enlace de demo configurado) antes decía "Contactar al administrador" pero en realidad solo volvía al menú - ahora usa un enlace real (tg://user?id=), igual que en el resto del flujo."""
    demo_link = config.get_demo_group_link()
    rows = []
    if demo_link:
        rows.append([InlineKeyboardButton("📂 Entrar al grupo de demostración", url=demo_link)])
    else:
        rows.append([_contact_admin_button(admin_user_id)])
    rows.append([InlineKeyboardButton("⬅️ Volver al menú", callback_data="ventas_back_to_welcome")])
    return InlineKeyboardMarkup(rows)


def _contact_admin_button(admin_user_id: int) -> InlineKeyboardButton:
    """Botón "Contactar al administrador" mediante tg://user?id=, que abre un chat directo sin necesitar un @usuario público configurado. Recibe el ID como parámetro (en vez de importarlo aquí desde bot.py) para que este archivo siga siendo solo funciones puras, tal como indica el docstring del módulo."""
    return InlineKeyboardButton("👤 Contactar al administrador", url=f"tg://user?id={admin_user_id}")


def vip_menu_keyboard(admin_user_id: int) -> InlineKeyboardMarkup:
    """Menú de métodos de pago. Cada método se elige primero; sus datos específicos se muestran recién en method_detail_keyboard()."""
    rows = [
        [InlineKeyboardButton(label, callback_data=f"ventas_method_{key}")]
        for key, label in PAYMENT_METHOD_LABELS.items()
    ]
    rows.append([_contact_admin_button(admin_user_id)])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data="ventas_back_to_welcome")])
    return InlineKeyboardMarkup(rows)


def method_detail_keyboard(method_key: str, admin_user_id: int) -> InlineKeyboardMarkup:
    """Botones de la pantalla de detalle de UN método de pago específico. "Ya realicé el pago" lleva el método codificado en el callback_data, así la conversación de pago ya no necesita volver a preguntarlo."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Ya realicé el pago", callback_data=f"ventas_paid_{method_key}")],
            [_contact_admin_button(admin_user_id)],
            [InlineKeyboardButton("⬅️ Volver", callback_data="ventas_vip")],
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
