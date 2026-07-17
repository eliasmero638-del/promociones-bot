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


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎁 Iniciar prueba gratis", callback_data="ventas_demo")],
            [InlineKeyboardButton("💳 Comprar acceso VIP", callback_data="ventas_vip")],
            [InlineKeyboardButton("❓ Preguntas frecuentes", callback_data="ventas_faq")],
        ]
    )


def demo_keyboard(config: SalesConfigManager) -> InlineKeyboardMarkup:
    demo_link = config.get_demo_group_link()
    rows = []
    if demo_link:
        rows.append([InlineKeyboardButton("📂 Entrar al grupo de demostración", url=demo_link)])
    else:
        # Sin enlace configurado: no se manda un botón roto.
        rows.append([InlineKeyboardButton("👤 Contactar al administrador", callback_data="ventas_back_to_welcome")])
    rows.append([InlineKeyboardButton("⬅️ Volver al menú", callback_data="ventas_back_to_welcome")])
    return InlineKeyboardMarkup(rows)


def vip_purchase_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Ya realicé el pago", callback_data="ventas_paid")],
            [InlineKeyboardButton("⬅️ Volver al menú", callback_data="ventas_back_to_welcome")],
        ]
    )


def payment_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"ventas_method_{key}")] for key, label in PAYMENT_METHOD_LABELS.items()]
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
