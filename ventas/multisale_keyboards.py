"""
Teclados del sistema NUEVO de venta multi-grupo. Funciones puras (reciben
datos, devuelven un InlineKeyboardMarkup), igual que ventas/keyboards.py -
pero completamente separado de ese archivo (no se importa nada de él) para
que ambos sistemas puedan evolucionar de forma independiente.

Todo callback_data de este archivo usa exclusivamente el prefijo "ms_",
para no colisionar con ningún callback_data ya registrado en el resto del
proyecto (ventas_*, sale_*, add_promo, panel*, etc.).
"""

from typing import Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .multisale_config import GROUP_KEYS, PAYMENT_METHOD_KEYS, MultiSaleConfigManager


def admin_button(admin_user_id: int) -> InlineKeyboardButton:
    """Botón "👨‍💼 Hablar con el administrador", presente en todo el flujo.
    Usa tg://user?id= (mismo mecanismo ya usado en el resto del proyecto)
    para abrir un chat directo sin depender de un @usuario público."""
    return InlineKeyboardButton("👨‍💼 Hablar con el administrador", url=f"tg://user?id={admin_user_id}")


def menu_keyboard(config: MultiSaleConfigManager, selected: set, admin_user_id: int) -> InlineKeyboardMarkup:
    """Menú principal: un botón por grupo (✅/⬜ según esté seleccionado),
    + Pagos recientes + Continuar + Administrador."""
    rows = []
    for key in GROUP_KEYS:
        mark = "✅" if key in selected else "⬜"
        label = config.get_group_label(key)
        rows.append([InlineKeyboardButton(f"{mark} {label}", callback_data=f"ms_toggle_{key}")])
    rows.append([InlineKeyboardButton("💳 Pagos de clientes recientes", callback_data="ms_recent")])
    rows.append([InlineKeyboardButton("✅ Continuar", callback_data="ms_continue")])
    rows.append([admin_button(admin_user_id)])
    return InlineKeyboardMarkup(rows)


def recent_payments_keyboard(admin_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔙 Volver a seleccionar grupos", callback_data="ms_recent_back")],
            [admin_button(admin_user_id)],
        ]
    )


def offer_keyboard(admin_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Continuar con la compra", callback_data="ms_offer_continue")],
            [InlineKeyboardButton("🔄 Cambiar selección", callback_data="ms_offer_change")],
            [admin_button(admin_user_id)],
        ]
    )


def confirm_keyboard(admin_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Quiero realizar el pago", callback_data="ms_confirm_pay")],
            [InlineKeyboardButton("🔄 Cambiar selección", callback_data="ms_confirm_change")],
            [admin_button(admin_user_id)],
        ]
    )


def payment_methods_keyboard(config: MultiSaleConfigManager, admin_user_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(config.get_payment_method_label(key), callback_data=f"ms_method_{key}")]
        for key in PAYMENT_METHOD_KEYS
    ]
    rows.append([InlineKeyboardButton("🔙 Volver", callback_data="ms_methods_back")])
    rows.append([admin_button(admin_user_id)])
    return InlineKeyboardMarkup(rows)


def payment_data_keyboard(admin_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📤 Enviar comprobante", callback_data="ms_send_receipt_hint")],
            [InlineKeyboardButton("🔙 Volver a métodos de pago", callback_data="ms_methods_back")],
            [admin_button(admin_user_id)],
        ]
    )


def payment_already_seen_keyboard(admin_user_id: int) -> InlineKeyboardMarkup:
    """Pantalla de "los datos ya fueron mostrados": a pedido explícito,
    ÚNICAMENTE el botón de contactar al administrador."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("👨‍💼 Contactar al administrador", url=f"tg://user?id={admin_user_id}")]])


def admin_approval_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Aprobar pago", callback_data=f"ms_approve_{request_id}"),
                InlineKeyboardButton("❌ Rechazar pago", callback_data=f"ms_reject_{request_id}"),
            ]
        ]
    )


def admin_only_keyboard(admin_user_id: int) -> InlineKeyboardMarkup:
    """Un único botón de contacto al administrador - usado en la pantalla
    de rechazo y en la de "comprobante recibido"."""
    return InlineKeyboardMarkup([[admin_button(admin_user_id)]])


def access_keyboard(config: MultiSaleConfigManager, group_keys: List[str]) -> InlineKeyboardMarkup:
    """Un botón URL por cada grupo comprado - nunca el enlace como texto.
    Solo incluye los grupos de `group_keys` (los realmente comprados en
    ESA venta), en el orden fijo GROUP_KEYS."""
    rows = []
    for key in GROUP_KEYS:
        if key not in group_keys:
            continue
        link = config.get_group_link(key)
        if not link:
            continue
        label = config.get_group_label(key).split(" ", 1)[-1] if " " in config.get_group_label(key) else config.get_group_label(key)
        rows.append([InlineKeyboardButton(f"🔓 Entrar a {label}", url=link)])
    return InlineKeyboardMarkup(rows)
