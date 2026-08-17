"""
Configuración del sistema NUEVO de venta multi-grupo (5 grupos, selección
múltiple, precios por combo). Completamente independiente de ventas/config.py
(el sistema viejo de 2 grupos) - no comparte clases, claves de Upstash, ni
archivos locales con él, para no arriesgar el flujo que ya funciona.

Mismo patrón dual (Upstash Redis si está configurado, si no un archivo JSON
local) que el resto del proyecto. Igual que ventas/config.py, todo lo que
este módulo necesita de bot.py se importa de forma DIFERIDA dentro de las
funciones, nunca a nivel de módulo, para evitar un import circular.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("bot")

UPSTASH_MULTISALE_CONFIG_KEY = "multisale_bot:config"
MULTISALE_CONFIG_LOCAL_FILENAME = "multisale_config.json"

UPSTASH_RECENT_PAYMENTS_KEY = "multisale_bot:recent_payments"
RECENT_PAYMENTS_LOCAL_FILENAME = "multisale_recent_payments.json"

UPSTASH_PAYMENT_DATA_SEEN_KEY = "multisale_bot:payment_data_seen"
PAYMENT_DATA_SEEN_LOCAL_FILENAME = "multisale_payment_data_seen.json"

# Orden fijo de los 5 grupos - se usa en todos los listados/resúmenes para
# que el orden mostrado sea siempre el mismo, sin depender del orden de
# iteración de un dict.
GROUP_KEYS = ["portoviejo", "manta", "ecuatorianas", "vipec", "azules"]

# Orden fijo de los 4 métodos de pago.
PAYMENT_METHOD_KEYS = ["interbancario", "bank_pichincha", "bank_guayaquil", "paypal"]

# Tabla de precios por cantidad de grupos seleccionados. El precio "de
# lista" (para el cálculo de "precio individual" en la pantalla de oferta)
# es siempre PRICE_TABLE[1] * cantidad - nunca una combinación escrita a
# mano.
PRICE_TABLE = {
    1: 6.99,
    2: 9.99,
    3: 12.99,
    4: 16.99,
    5: 19.99,
}


def get_offer_price(count: int) -> float:
    """Precio de oferta para `count` grupos (1-5)."""
    return PRICE_TABLE.get(count, PRICE_TABLE[len(GROUP_KEYS)])


def get_individual_total(count: int) -> float:
    """Precio "de lista" con el que se compara la oferta: precio de 1 grupo
    multiplicado por la cantidad seleccionada."""
    return round(PRICE_TABLE[1] * count, 2)


def _default_config() -> dict:
    return {
        "groups": {
            "portoviejo": {
                "label": "1️⃣ Portoviejo Exclusivo",
                "description": "Contenido relacionado con chicas y material exclusivo de Portoviejo.",
                "link": "https://t.me/+VX6lOT4YfnEwYTE5",
            },
            "manta": {
                "label": "2️⃣ Exclusivas de Manta",
                "description": "Contenido relacionado con chicas de Manta y sus alrededores.",
                "link": "https://t.me/+VEc0aYafQ1VhMTlh",
            },
            "ecuatorianas": {
                "label": "3️⃣ Ecuatorianas VIP",
                "description": "Contenido de diferentes provincias y ciudades del Ecuador.",
                "link": "https://t.me/+-dNUyLEaCU04Nzgx",
            },
            "vipec": {
                "label": "4️⃣ VIP EC",
                "description": "Contenido casero ecuatoriano y material compartido dentro de la comunidad.",
                "link": "https://t.me/+B58R7JG2NgtlMTYx",
            },
            "azules": {
                "label": "5️⃣ Azules EC",
                "description": "Famosas y modelos de Ecuador.",
                "link": "https://t.me/+6TweKM1ROMMyNTNh",
            },
        },
        "payment_methods": {
            "interbancario": {
                "label": "🏦 Pago interbancario",
                # Igual que pidió el admin - se deja como placeholder
                # explícito hasta que configure el número de cuenta real.
                "details": (
                    "Banco: Banco Pichincha\n"
                    "Tipo de cuenta: Ahorros\n"
                    "Número de cuenta: [lo configuraré]\n"
                    "Titular: Ricardo Elías Mero Mieles\n"
                    "Cédula: 1315531515"
                ),
            },
            # Datos reales confirmados por el admin (imagen "DATOS DE PAGO").
            "bank_pichincha": {
                "label": "🏦 Banco Pichincha",
                "details": "Cuenta de ahorro transaccional: 2214437107\nTitular: Ricardo.m",
            },
            "bank_guayaquil": {
                "label": "🏦 Banco Guayaquil",
                "details": "Cuenta de ahorros: 0013991214\nTitular: Ricardo.m",
            },
            "paypal": {
                "label": "💙 PayPal",
                "details": "Ridmerwtf@gmail.com\nTitular: Ricardo.m",
            },
        },
    }


def _resolve_local_path(filename: str) -> str:
    try:
        from bot import DATA_DIR
    except Exception:
        DATA_DIR = ""
    if DATA_DIR:
        os.makedirs(DATA_DIR, exist_ok=True)
        return os.path.join(DATA_DIR, filename)
    return filename


class MultiSaleConfigManager:
    """Administra la configuración de los 5 grupos y los 4 métodos de pago
    del sistema nuevo de ventas."""

    def __init__(self):
        self.file_path = _resolve_local_path(MULTISALE_CONFIG_LOCAL_FILENAME)
        try:
            from bot import USE_UPSTASH
            self.use_upstash = USE_UPSTASH
        except Exception:
            self.use_upstash = False
        self.data = self._load()

    def _merge_with_defaults(self, data: dict) -> dict:
        defaults = _default_config()
        merged = dict(defaults)
        merged.update(data)
        # Merge de un nivel más para "groups"/"payment_methods", para que
        # agregar una clave nueva a los defaults en el futuro no se pierda
        # solo porque ya había datos guardados con las claves viejas.
        merged["groups"] = {**defaults["groups"], **data.get("groups", {})}
        merged["payment_methods"] = {**defaults["payment_methods"], **data.get("payment_methods", {})}
        return merged

    def _load(self) -> dict:
        if self.use_upstash:
            return self._load_from_upstash()
        return self._load_from_file()

    def _load_from_upstash(self) -> dict:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[multisale.config] Could not import Upstash client from bot: {e}")
            return _default_config()

        result = _upstash_command("GET", UPSTASH_MULTISALE_CONFIG_KEY)
        if result is None:
            logger.error("[multisale.config] Upstash request failed; using default config for this session.")
            return _default_config()

        raw = result.get("result")
        if raw is None:
            logger.info("[multisale.config] No config stored yet in Upstash; using defaults.")
            return _default_config()

        try:
            return self._merge_with_defaults(json.loads(raw))
        except Exception as e:
            logger.error(f"[multisale.config] Failed to parse JSON from Upstash: {e}")
            return _default_config()

    def _load_from_file(self) -> dict:
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return self._merge_with_defaults(json.load(f))
            except Exception as e:
                logger.warning(f"[multisale.config] Failed to load local config file: {e}")
        return _default_config()

    def save(self) -> bool:
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[multisale.config] Could not import Upstash client from bot: {e}")
            return False
        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[multisale.config] Could not serialize config: {e}")
            return False
        result = _upstash_command("SET", UPSTASH_MULTISALE_CONFIG_KEY, payload)
        if result is not None and result.get("result") == "OK":
            logger.info("[multisale.config] Config saved to Upstash Redis.")
            return True
        logger.error(f"[multisale.config] Upstash SET did not confirm success: {result}")
        return False

    def _save_to_file(self) -> bool:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            logger.info("[multisale.config] Config saved to local file.")
            return True
        except Exception as e:
            logger.error(f"[multisale.config] Failed to save local config file: {e}")
            return False

    # --- Grupos ---
    def get_group(self, group_key: str) -> Optional[dict]:
        return self.data.get("groups", {}).get(group_key)

    def get_group_label(self, group_key: str) -> str:
        return self.get_group(group_key).get("label", group_key) if self.get_group(group_key) else group_key

    def get_group_description(self, group_key: str) -> str:
        group = self.get_group(group_key)
        return group.get("description", "") if group else ""

    def get_group_link(self, group_key: str) -> str:
        group = self.get_group(group_key)
        return group.get("link", "") if group else ""

    def get_all_groups(self) -> Dict[str, dict]:
        return self.data.get("groups", {})

    # --- Métodos de pago ---
    def get_payment_method(self, method_key: str) -> Optional[dict]:
        return self.data.get("payment_methods", {}).get(method_key)

    def get_payment_method_label(self, method_key: str) -> str:
        method = self.get_payment_method(method_key)
        return method.get("label", method_key) if method else method_key

    def get_payment_method_details(self, method_key: str) -> str:
        method = self.get_payment_method(method_key)
        return method.get("details", "") if method else ""


class RecentPaymentsStore:
    """Guarda los file_id de las imágenes de comprobantes de muestra que el
    admin agrega manualmente (ver /agregar_pago_reciente en
    multisale_handlers.py), mostradas en "💳 Pagos de clientes recientes"."""

    def __init__(self):
        self.file_path = _resolve_local_path(RECENT_PAYMENTS_LOCAL_FILENAME)
        try:
            from bot import USE_UPSTASH
            self.use_upstash = USE_UPSTASH
        except Exception:
            self.use_upstash = False
        self.data = self._load()

    def _load(self) -> dict:
        if self.use_upstash:
            return self._load_from_upstash()
        return self._load_from_file()

    def _load_from_upstash(self) -> dict:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[multisale.config] Could not import Upstash client from bot: {e}")
            return {"payments": []}
        result = _upstash_command("GET", UPSTASH_RECENT_PAYMENTS_KEY)
        if result is None:
            return {"payments": []}
        raw = result.get("result")
        if raw is None:
            return {"payments": []}
        try:
            return json.loads(raw)
        except Exception as e:
            logger.error(f"[multisale.config] Failed to parse recent payments JSON: {e}")
            return {"payments": []}

    def _load_from_file(self) -> dict:
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[multisale.config] Failed to load local recent payments file: {e}")
        return {"payments": []}

    def _save(self) -> bool:
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[multisale.config] Could not import Upstash client from bot: {e}")
            return False
        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[multisale.config] Could not serialize recent payments: {e}")
            return False
        result = _upstash_command("SET", UPSTASH_RECENT_PAYMENTS_KEY, payload)
        return bool(result is not None and result.get("result") == "OK")

    def _save_to_file(self) -> bool:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            return True
        except Exception as e:
            logger.error(f"[multisale.config] Failed to save local recent payments file: {e}")
            return False

    def get_all(self) -> List[dict]:
        return list(self.data.get("payments", []))

    def add(self, file_id: str, file_type: str, added_by: int) -> bool:
        from datetime import datetime
        self.data.setdefault("payments", []).append(
            {
                "file_id": file_id,
                "file_type": file_type,
                "added_by": added_by,
                "added_at": datetime.now().isoformat(),
            }
        )
        return self._save()

    def remove_at(self, index: int) -> bool:
        payments = self.data.get("payments", [])
        if index < 0 or index >= len(payments):
            return False
        payments.pop(index)
        return self._save()


class PaymentDataSeenStore:
    """Registra, de forma PERMANENTE (user_id, método_de_pago) -> ya vio
    los datos bancarios de ese método. Independiente por método: haber
    visto Banco Pichincha no bloquea ver PayPal. Nunca se resetea
    automáticamente - solo un administrador puede volver a mostrar los
    datos manualmente por fuera del bot."""

    def __init__(self):
        self.file_path = _resolve_local_path(PAYMENT_DATA_SEEN_LOCAL_FILENAME)
        try:
            from bot import USE_UPSTASH
            self.use_upstash = USE_UPSTASH
        except Exception:
            self.use_upstash = False
        self.data = self._load()

    def _load(self) -> dict:
        if self.use_upstash:
            return self._load_from_upstash()
        return self._load_from_file()

    def _load_from_upstash(self) -> dict:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[multisale.config] Could not import Upstash client from bot: {e}")
            return {"seen": []}
        result = _upstash_command("GET", UPSTASH_PAYMENT_DATA_SEEN_KEY)
        if result is None:
            return {"seen": []}
        raw = result.get("result")
        if raw is None:
            return {"seen": []}
        try:
            return json.loads(raw)
        except Exception as e:
            logger.error(f"[multisale.config] Failed to parse payment-data-seen JSON: {e}")
            return {"seen": []}

    def _load_from_file(self) -> dict:
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[multisale.config] Failed to load local payment-data-seen file: {e}")
        return {"seen": []}

    def _save(self) -> bool:
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[multisale.config] Could not import Upstash client from bot: {e}")
            return False
        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[multisale.config] Could not serialize payment-data-seen: {e}")
            return False
        result = _upstash_command("SET", UPSTASH_PAYMENT_DATA_SEEN_KEY, payload)
        return bool(result is not None and result.get("result") == "OK")

    def _save_to_file(self) -> bool:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            return True
        except Exception as e:
            logger.error(f"[multisale.config] Failed to save local payment-data-seen file: {e}")
            return False

    @staticmethod
    def _key(user_id: int, method_key: str) -> str:
        return f"{user_id}:{method_key}"

    def has_seen(self, user_id: int, method_key: str) -> bool:
        return self._key(user_id, method_key) in self.data.get("seen", [])

    def mark_seen(self, user_id: int, method_key: str) -> None:
        seen = self.data.setdefault("seen", [])
        key = self._key(user_id, method_key)
        if key not in seen:
            seen.append(key)
            self._save()
