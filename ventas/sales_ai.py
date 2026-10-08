"""Capa de IA (Claude) opcional: responde cualquier mensaje de texto libre
que un cliente le escriba a este bot FUERA de los botones del menú de
ventas. El único flujo real de compra (grupos, precios, métodos de pago,
aprobación de pagos, entrega de accesos) sigue siendo exactamente el mismo
código fijo de siempre en ventas/handlers.py y ventas/multisale_handlers.py
- esto no lo toca ni lo reemplaza.

La IA nunca decide precios, grupos, disponibilidad, pagos ni accesos: solo
redacta una respuesta corta y amigable, y siempre se acompaña del mismo
teclado del menú principal para que el cliente compre tocando un botón,
nunca por texto.

Si ANTHROPIC_API_KEY no está configurada, o la llamada falla o tarda
demasiado, is_enabled() es False o draft_reply_ai() devuelve None - en ese
caso el fallback simplemente muestra el menú principal sin comentario de
la IA (ver handle_free_text_fallback), nunca se queda en silencio.
"""

import asyncio
import logging
import os
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("bot")

_TIMEOUT_SECONDS = 8
_MODEL = "claude-haiku-4-5"

_client = None


def is_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


_REPLY_SYSTEM = (
    "Eres el asistente conversacional de un bot de Telegram que vende "
    "acceso a grupos VIP, en español ecuatoriano, tono cercano y breve "
    "(máximo 2 frases cortas).\n\n"
    "Reglas estrictas, sin excepción:\n"
    "- NUNCA menciones precios, montos, nombres de grupos, disponibilidad, "
    "descuentos, promociones, estado de pagos ni accesos - no tienes esa "
    "información y no puedes inventarla.\n"
    "- No prometas nada que el sistema no pueda cumplir.\n"
    "- Termina siempre invitando a usar los botones de abajo para ver "
    "grupos o comprar.\n"
    "- Responde solo el texto del mensaje, sin explicaciones ni comillas."
)


async def draft_reply_ai(text: str) -> Optional[str]:
    """Redacta una respuesta corta y segura a un mensaje de texto libre.
    Devuelve None si la IA no está disponible o falla - nunca lanza
    excepción."""
    if not is_enabled() or not text.strip():
        return None
    try:
        client = _get_client()
        response = await asyncio.wait_for(
            client.messages.create(
                model=_MODEL,
                max_tokens=150,
                system=_REPLY_SYSTEM,
                messages=[{"role": "user", "content": text[:500]}],
                extra_body={"temperature": 0.7},
            ),
            timeout=_TIMEOUT_SECONDS,
        )
        reply = response.content[0].text.strip()
        return reply or None
    except Exception:
        logger.exception("[ventas.sales_ai] Fallo la redacción por IA, se sigue sin IA para este mensaje")
        return None


async def handle_free_text_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all para texto libre en privado que ningún otro handler (ni
    las conversaciones de /panel, ventas o multisale) reclamó - es decir,
    nadie estaba esperando ese mensaje. En vez de dejarlo sin respuesta,
    se le pide a la IA una línea corta y segura, y siempre se muestra el
    menú principal de ventas para que compre tocando un botón."""
    message = update.effective_message
    if message is None or not message.text:
        return

    from . import keyboards
    from .handlers import WELCOME_TEXT

    reply = await draft_reply_ai(message.text)
    if reply:
        await message.reply_text(f"{reply}\n\n{WELCOME_TEXT}", reply_markup=keyboards.welcome_keyboard())
    else:
        await message.reply_text(WELCOME_TEXT, reply_markup=keyboards.welcome_keyboard())
