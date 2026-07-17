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

logger = logging.getLogger("bot")

# Deep-link payload que el botón del canal debe usar:
# https://t.me/<tu_bot>?start=venta
SALES_DEEP_LINK_PAYLOAD = "venta"

UPSTASH_SALES_CONFIG_KEY = "ventas_bot:config"
SALES_CONFIG_LOCAL_FILENAME = "ventas_config.json"


def _default_config() -> dict:
    return {
        "vip_price": "Consultar precio",
        "bank_guayaquil_details": "",
        "bank_pichincha_details": "",
        "paypal_details": "",
        "demo_group_link": "",
        "vip_group_link": "",
        "faq_text": "Aún no se ha configurado el texto de preguntas frecuentes.",
    }


def _resolve_local_path() -> str:
    """Resuelve dónde vive el archivo local de respaldo, respetando
    DATA_DIR de bot.py si está definida (mismo criterio que
    promotions.json/bot_state.json/welcome_config.json)."""
    try:
        from bot import DATA_DIR  # import diferido, ver docstring del módulo
    except Exception:
        DATA_DIR = ""
    if DATA_DIR:
        os.makedirs(DATA_DIR, exist_ok=True)
        return os.path.join(DATA_DIR, SALES_CONFIG_LOCAL_FILENAME)
    return SALES_CONFIG_LOCAL_FILENAME


class SalesConfigManager:
    """Administra la configuración del sistema de ventas."""

    def __init__(self):
        self.file_path = _resolve_local_path()
        try:
            from bot import USE_UPSTASH
            self.use_upstash = USE_UPSTASH
        except Exception:
            self.use_upstash = False
        self.data = self._load()

    def _merge_with_defaults(self, data: dict) -> dict:
        merged = _default_config()
        merged.update(data)
        return merged

    def _load(self) -> dict:
        if self.use_upstash:
            return self._load_from_upstash()
        return self._load_from_file()

    def _load_from_upstash(self) -> dict:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[ventas.config] Could not import Upstash client from bot: {e}")
            return _default_config()

        result = _upstash_command("GET", UPSTASH_SALES_CONFIG_KEY)
        if result is None:
            logger.error("[ventas.config] Upstash request failed; using default sales config for this session.")
            return _default_config()

        raw = result.get("result")
        if raw is None:
            logger.info("[ventas.config] No sales config stored yet in Upstash; using defaults.")
            return _default_config()

        try:
            return self._merge_with_defaults(json.loads(raw))
        except Exception as e:
            logger.error(f"[ventas.config] Failed to parse JSON from Upstash: {e}")
            return _default_config()

    def _load_from_file(self) -> dict:
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return self._merge_with_defaults(json.load(f))
            except Exception as e:
                logger.warning(f"[ventas.config] Failed to load local sales config file: {e}")
        return _default_config()

    def save(self) -> bool:
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[ventas.config] Could not import Upstash client from bot: {e}")
            return False

        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[ventas.config] Could not serialize sales config: {e}")
            return False

        result = _upstash_command("SET", UPSTASH_SALES_CONFIG_KEY, payload)
        if result is not None and result.get("result") == "OK":
            logger.info("[ventas.config] Sales config saved to Upstash Redis.")
            return True

        logger.error(f"[ventas.config] Upstash SET did not confirm success: {result}")
        return False

    def _save_to_file(self) -> bool:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            logger.info("[ventas.config] Sales config saved to local file.")
            return True
        except Exception as e:
            logger.error(f"[ventas.config] Failed to save local sales config file: {e}")
            return False

    # --- Getters/setters ---
    def get_vip_price(self) -> str:
        return self.data.get("vip_price", "")

    def set_vip_price(self, value: str):
        self.data["vip_price"] = value

    def get_bank_guayaquil_details(self) -> str:
        return self.data.get("bank_guayaquil_details", "")

    def set_bank_guayaquil_details(self, value: str):
        self.data["bank_guayaquil_details"] = value

    def get_bank_pichincha_details(self) -> str:
        return self.data.get("bank_pichincha_details", "")

    def set_bank_pichincha_details(self, value: str):
        self.data["bank_pichincha_details"] = value

    def get_paypal_details(self) -> str:
        return self.data.get("paypal_details", "")

    def set_paypal_details(self, value: str):
        self.data["paypal_details"] = value

    def get_demo_group_link(self) -> str:
        return self.data.get("demo_group_link", "")

    def set_demo_group_link(self, value: str):
        self.data["demo_group_link"] = value

    def get_vip_group_link(self) -> str:
        return self.data.get("vip_group_link", "")

    def set_vip_group_link(self, value: str):
        self.data["vip_group_link"] = value

    def get_faq_text(self) -> str:
        return self.data.get("faq_text", "")

    def set_faq_text(self, value: str):
        self.data["faq_text"] = value
