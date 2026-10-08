"""Asistente de texto libre para cualquier mensaje que un cliente le
escriba a este bot FUERA de los botones del menú de ventas. El único
flujo real de compra (grupos, precios, métodos de pago, aprobación de
pagos, entrega de accesos) sigue siendo exactamente el mismo código fijo
de siempre en ventas/handlers.py y ventas/multisale_handlers.py - esto no
lo toca ni lo reemplaza, solo reacciona a mensajes que nadie más estaba
esperando.

Mismo diseño de 2 capas que ya usa el bot de bloqueo (handlers/sales_flow.py
+ handlers/sales_ai.py), para no gastar créditos de IA en lo que ya se
puede resolver gratis:

  1. Palabras clave (classify_text, determinista, sin costo): reconoce
     saludo, agradecimiento, "grupo free", "vender contenido", preguntas
     frecuentes, cómo pagar, o que quiere ver los grupos/precios - y
     responde con el mismo contenido real de siempre (texto + botones).
  2. Solo si NINGUNA palabra clave matcheó, y ANTHROPIC_API_KEY está
     configurada: la IA (Claude) intenta primero clasificar el mensaje
     en una de esas mismas etiquetas (classify_intent_ai) - si lo logra,
     se ejecuta exactamente la misma acción fija de arriba. Si tampoco
     logra clasificarlo, la IA redacta una respuesta corta y genérica
     (draft_reply_ai) que NUNCA menciona precios, grupos, pagos ni
     accesos - no tiene esa información y no puede inventarla.
  3. Si la IA no está habilitada, falla, o nada de lo anterior aplicó:
     se muestra el menú principal (send_multisale_welcome) - nunca se
     queda en silencio.
"""

import asyncio
import logging
import os
import random
import unicodedata
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


# =========================
# NORMALIZACIÓN Y CLASIFICACIÓN POR PALABRAS CLAVE (sin IA, gratis)
# =========================

def normalize_phrase(text: str) -> str:
    """minúsculas + sin tildes, para que las listas de frases no tengan
    que repetir cada variante acentuada."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


_GREETING_PHRASES = (
    "hola", "buenas", "hey", "ola", "que tal", "q tal", "buenos dias",
    "buenas tardes", "buenas noches", "saludos", "buen dia",
)
_ACK_PHRASES = ("gracias", "perfecto", "listo", "ok", "entiendo", "excelente", "dale", "de acuerdo")
_FREE_PHRASES = ("grupo free", "grupo gratis", "prueba gratis", "algo gratis", "free", "gratis")
_SELL_PHRASES = (
    "quiero vender", "vender contenido", "vender mi contenido", "soy modelo",
    "tengo contenido", "monetizar", "ganar dinero con mi contenido",
)
_FAQ_PHRASES = ("preguntas frecuentes", "pregunta frecuente", "faq", "duda", "dudas")
_PAYMENT_PHRASES = (
    "como pago", "como puedo pagar", "metodos de pago", "metodo de pago",
    "forma de pago", "formas de pago", "donde pago", "como se paga",
)
_GROUPS_PHRASES = (
    "grupos", "que grupos", "cuales grupos", "lista", "listado", "catalogo",
    "que tienen", "que hay", "contenido", "vip",
)
_PRICE_PHRASES = ("precio", "precios", "cuanto cuesta", "costo", "cuesta", "vale", "cuanto vale", "cuanto sale")

# Orden de chequeo: de más específico a más genérico (igual criterio que
# el bot de bloqueo), para que "gracias, cuanto sale lo free" caiga en
# "free" antes que en el "ack" genérico de "gracias".
_INTENT_TABLE = (
    ("free", _FREE_PHRASES),
    ("sell", _SELL_PHRASES),
    ("faq", _FAQ_PHRASES),
    ("payment", _PAYMENT_PHRASES),
    ("groups", _GROUPS_PHRASES),
    ("groups", _PRICE_PHRASES),
    ("greeting", _GREETING_PHRASES),
    ("ack", _ACK_PHRASES),
)

_KNOWN_INTENTS = ("greeting", "ack", "free", "sell", "faq", "payment", "groups")


def classify_text(normalized_text: str) -> Optional[str]:
    """Clasificación por palabras clave, sin IA. Devuelve una de
    _KNOWN_INTENTS, o None si no reconoce nada."""
    if not normalized_text:
        return None
    for intent, phrases in _INTENT_TABLE:
        for phrase in phrases:
            if phrase in normalized_text:
                return intent
    return None


_GREETING_REPLIES = (
    "¡Hola! ¿Qué tal? Escribí \"grupos\" para ver las opciones 👇",
    "¡Hola! ¿Cómo estás? Decime \"grupos\" si querés ver lo que tenemos.",
    "¡Buenas! Si querés ver los grupos disponibles, escribí \"grupos\".",
)
_ACK_REPLIES = (
    "¡De nada! Cualquier cosa, avisame.",
    "¡Genial! Acá ando si necesitás algo más.",
    "¡Perfecto! Escribí \"grupos\" si querés ver las opciones.",
)


async def _dispatch_intent(intent: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ejecuta la acción determinística asociada a un intent ya
    reconocido - por palabras clave o, si está habilitada, por la capa de
    IA - y devuelve True si lo manejó. Toda la lógica real vive acá; la
    IA (cuando participa) solo elige la etiqueta, nunca redacta ni
    ejecuta la acción por su cuenta."""
    message = update.effective_message

    if intent == "greeting":
        await message.reply_text(random.choice(_GREETING_REPLIES))
        return True

    if intent == "ack":
        await message.reply_text(random.choice(_ACK_REPLIES))
        return True

    if intent == "groups":
        from ventas.multisale_handlers import send_multisale_welcome
        await send_multisale_welcome(update, context)
        return True

    if intent == "free":
        from ventas import keyboards
        from ventas.config import SalesConfigManager
        from bot import ADMIN_USER_ID

        config = SalesConfigManager()
        free_link = config.get_free_group_link()
        if free_link:
            text = (
                "🆓 ¡Aquí tienes el acceso al Grupo Free!\n\n"
                "Disfruta del contenido disponible.\n\n"
                "⚠️ Importante:\n\n"
                "Si no compartiste previamente el grupo, tu solicitud de ingreso no será aceptada por el administrador.\n\n"
                "👇 Pulsa el botón de abajo para ingresar."
            )
        else:
            text = "El enlace del grupo Free aún no está configurado. Contacta al administrador."
        await message.reply_text(text, reply_markup=keyboards.free_group_keyboard(free_link, ADMIN_USER_ID))
        return True

    if intent == "sell":
        from ventas import keyboards

        text = (
            "💰 ¿Quieres vender tu contenido?\n\n"
            "Si deseas vender contenido propio o administras un grupo de Telegram con contenido exclusivo, "
            "ponte en contacto con el administrador.\n\n"
            "Presiona el botón de abajo y con gusto revisaremos tu propuesta."
        )
        await message.reply_text(text, reply_markup=keyboards.sell_content_keyboard())
        return True

    if intent == "faq":
        from ventas import keyboards
        from ventas.config import SalesConfigManager

        config = SalesConfigManager()
        await message.reply_text(config.get_faq_text(), reply_markup=keyboards.faq_keyboard())
        return True

    if intent == "payment":
        from ventas.multisale_handlers import send_multisale_welcome

        await message.reply_text("Para pagar primero elegí los grupos que te interesan 👇")
        await send_multisale_welcome(update, context)
        return True

    return False


# =========================
# CAPA DE IA (Claude) - solo si las palabras clave no reconocieron nada
# =========================

_CLASSIFY_SYSTEM = (
    "Clasificas mensajes de clientes de un bot que vende acceso a grupos "
    "VIP de Telegram. Responde ÚNICAMENTE con una sola palabra de esta "
    "lista, sin explicaciones ni puntuación:\n"
    + ", ".join(_KNOWN_INTENTS) + ", fallback\n\n"
    "greeting: solo saluda.\n"
    "ack: agradece o confirma que entendió, sin pedir nada más.\n"
    "free: quiere el grupo gratis / prueba gratis.\n"
    "sell: quiere vender su propio contenido.\n"
    "faq: pregunta algo general sobre cómo funciona el servicio.\n"
    "payment: pregunta cómo o dónde pagar.\n"
    "groups: quiere ver los grupos disponibles o pregunta precios.\n"
    "fallback: cualquier otra cosa - charla, algo ajeno al negocio, o no "
    "queda claro qué quiere."
)


async def classify_intent_ai(text: str) -> Optional[str]:
    """Devuelve una de _KNOWN_INTENTS, "fallback", o None si la IA no
    está disponible / falló / respondió algo fuera de la lista cerrada.
    Nunca lanza excepción - cualquier falla degrada a None."""
    if not is_enabled() or not text.strip():
        return None
    try:
        client = _get_client()
        response = await asyncio.wait_for(
            client.messages.create(
                model=_MODEL,
                max_tokens=8,
                system=_CLASSIFY_SYSTEM,
                messages=[{"role": "user", "content": text[:500]}],
                extra_body={"temperature": 0},
            ),
            timeout=_TIMEOUT_SECONDS,
        )
        label = response.content[0].text.strip().lower()
        if label in _KNOWN_INTENTS or label == "fallback":
            return label
        return None
    except Exception:
        logger.exception("[ventas.sales_ai] Fallo la clasificación por IA, se sigue sin IA para este mensaje")
        return None


_REPLY_SYSTEM = (
    "Eres el asistente conversacional de un bot de Telegram que vende "
    "acceso a grupos VIP, en español ecuatoriano, tono cercano y breve "
    "(máximo 2 frases cortas). El mensaje del cliente no tiene ninguna "
    "intención comercial clara reconocida por el sistema.\n\n"
    "Reglas estrictas, sin excepción:\n"
    "- NUNCA menciones precios, montos, nombres de grupos, disponibilidad, "
    "descuentos, promociones, estado de pagos ni accesos - no tienes esa "
    "información y no puedes inventarla.\n"
    "- Si el mensaje roza cualquiera de esos temas, no lo respondas "
    "directamente: invita a escribir \"grupos\" para verlo de verdad.\n"
    "- No prometas nada que el sistema no pueda cumplir.\n"
    "- Responde solo el texto del mensaje, sin explicaciones ni comillas."
)


async def draft_reply_ai(text: str) -> Optional[str]:
    """Redacta una respuesta corta de charla genérica, sin datos
    comerciales. Devuelve None si la IA no está disponible o falla -
    nunca lanza excepción."""
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


# =========================
# HANDLER: catch-all de texto libre en privado
# =========================

async def handle_free_text_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all para texto libre en privado que ningún otro handler (ni
    las conversaciones de /panel, ventas o multisale) reclamó - es decir,
    nadie estaba esperando ese mensaje. Orden: 1) palabras clave
    (gratis), 2) IA para clasificar (si está habilitada), 3) IA para
    charla genérica, 4) menú principal como último respaldo - nunca se
    queda en silencio."""
    message = update.effective_message
    if message is None or not message.text:
        return

    normalized = normalize_phrase(message.text)
    intent = classify_text(normalized)
    if intent and await _dispatch_intent(intent, update, context):
        return

    if is_enabled():
        ai_intent = await classify_intent_ai(message.text)
        if ai_intent in _KNOWN_INTENTS:
            if await _dispatch_intent(ai_intent, update, context):
                return
        ai_reply = await draft_reply_ai(message.text)
        if ai_reply:
            await message.reply_text(ai_reply)
            return

    from ventas.multisale_handlers import send_multisale_welcome
    await send_multisale_welcome(update, context)
