"""
Configuración del sistema de ventas: precio VIP, datos bancarios, PayPal,
enlaces (grupo demo / grupo VIP) y texto de preguntas frecuentes.

Sigue exactamente el mismo patrón dual (Upstash Redis si está configurado,
si no un archivo JSON local) que ya usan PromotionsManager/BotState/
WelcomeConfigManager en bot.py - así el módulo de ventas hereda las mismas
garantías de persistencia sin inventar un mecanismo nuevo.

Todo lo que este archivo necesita de bot.py (el cliente HTTP de Upstash,
si está activado, y la ruta de archivo respetando DATA_DIR) se importa de
forma DIFERIDA dentro de las funciones, nunca a nivel de módulo, para que
este paquete pueda importarse en cualquier momento sin riesgo de import
circular con bot.py.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("bot")

# Deep-link payload que el botón del canal debe usar:
# https://t.me/<tu_bot>?start=venta
SALES_DEEP_LINK_PAYLOAD = "venta"

# Deep-link payload usado por el botón "🎁 Solicitar prueba gratis" de las
# promociones publicadas: https://t.me/<tu_bot>?start=demo - lleva
# directamente a la pantalla de prueba gratis, sin pasar por el menú de
# 4 opciones (ver send_demo_directly en handlers.py).
SALES_DEMO_DEEP_LINK_PAYLOAD = "demo"

UPSTASH_SALES_CONFIG_KEY = "ventas_bot:config"
SALES_CONFIG_LOCAL_FILENAME = "ventas_config.json"


def _default_trial_group_id() -> Optional[int]:
    """Lee SALES_TRIAL_GROUP_ID (el ID numérico del grupo de prueba). Si no
    está definida o no es un número válido, usa el ID del grupo de prueba
    ya conocido como valor por defecto, para que la expulsión automática
    de 1 minuto funcione sin necesidad de configurar nada en Railway (ver
    handle_trial_group_new_member en handlers.py). Se puede seguir
    sobreescribiendo con la variable de entorno si el grupo cambia."""
    raw = os.getenv("SALES_TRIAL_GROUP_ID", "").strip()
    if not raw:
        return -1003754652912
    try:
        return int(raw)
    except ValueError:
        logger.error(f"[ventas.config] SALES_TRIAL_GROUP_ID='{raw}' no es un ID de chat numérico válido; se ignora.")
        return None


def _default_vip_group_id() -> Optional[int]:
    """Lee SALES_VIP_GROUP_ID (el ID numérico del grupo VIP, por ejemplo
    -1001234567890) como entero. Si no está definida o no es un número
    válido, devuelve None - en ese caso, no se pueden crear enlaces
    dinámicos, pero el sistema sigue usando el enlace configurado como
