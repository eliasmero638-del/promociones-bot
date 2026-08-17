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

# Las 5 claves internas posibles, en orden fijo. Son solo identificadores
# internos (callback_data, nombres de variable de entorno) - el nombre que
# ve el cliente es siempre config.get_group_label(key), configurable por
# variable de entorno, nunca esta clave.
_ALL_GROUP_KEYS = ["portoviejo", "manta", "ecuatorianas", "vipec", "azules"]


def _active_group_keys() -> List[str]:
    """Qué claves de _ALL_GROUP_KEYS están activas en esta instalación,
    configurable via MULTISALE_ACTIVE_GROUPS (subconjunto separado por
    coma, ej. "portoviejo" para vender un solo grupo, o
    "portoviejo,manta" para vender 2 de los 5). Si no está definida, se
    usan las 5 - comportamiento histórico sin cambios. El resto de la UI
    (menú, textos, selección múltiple, tabla de precios) se ajusta solo a
    la cantidad de grupos activos, sin tocar código."""
    raw = os.getenv("MULTISALE_ACTIVE_GROUPS", "").strip()
    if not raw:
        return list(_ALL_GROUP_KEYS)
    requested = [k.strip() for k in raw.split(",") if k.strip()]
    active = [k for k in requested if k in _ALL_GROUP_KEYS]
    if not active:
        logger.error(
            f"[multisale.config] MULTISALE_ACTIVE_GROUPS='{raw}' no contiene ninguna clave válida "
            f"(de {_ALL_GROUP_KEYS}); se usan las 5 por defecto."
        )
        return list(_ALL_GROUP_KEYS)
    return active


# Orden fijo de los grupos REALMENTE activos en esta instalación - se usa
# en todos los listados/resúmenes/menús para que el orden mostrado sea
# siempre el mismo, sin depender del orden de iteración de un dict.
GROUP_KEYS = _active_group_keys()

# Orden fijo de los 4 métodos de pago.
PAYMENT_METHOD_KEYS = ["interbancario", "bank_pichincha", "bank_guayaquil", "paypal"]

def _env_float(name: str, default: float) -> float:
    """Lee una variable de entorno numérica (precio); si no está definida
    o no es un número válido, devuelve `default`."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.error(f"[multisale.config] {name}='{raw}' no es un número válido; se usa el valor por defecto.")
        return default


# Tabla de precios por cantidad de grupos seleccionados. El precio "de
# lista" (para el cálculo de "precio individual" en la pantalla de oferta)
# es siempre PRICE_TABLE[1] * cantidad - nunca una combinación escrita a
# mano. Cada precio es configurable via MULTISALE_PRICE_<n> (ej.
# MULTISALE_PRICE_1=6.99) para que una instalación nueva pueda tener su
# propia tabla de precios sin tocar el código.
PRICE_TABLE = {
    1: _env_float("MULTISALE_PRICE_1", 6.99),
    2: _env_float("MULTISALE_PRICE_2", 9.99),
    3: _env_float("MULTISALE_PRICE_3", 12.99),
    4: _env_float("MULTISALE_PRICE_4", 16.99),
    5: _env_float("MULTISALE_PRICE_5", 19.99),
}


def get_offer_price(count: int) -> float:
    """Precio de oferta para `count` grupos (1-5)."""
    return PRICE_TABLE.get(count, PRICE_TABLE[len(GROUP_KEYS)])


def get_individual_total(count: int) -> float:
    """Precio "de lista" con el que se compara la oferta: precio de 1 grupo
    multiplicado por la cantidad seleccionada."""
    return round(PRICE_TABLE[1] * count, 2)


def _env(name: str, default: str) -> str:
    """Lee una variable de entorno de texto; si no está definida (o está
    vacía), devuelve `default`. Ver el mismo helper en ventas/config.py -
    permite que cada grupo/método de pago sea propio de cada instalación."""
    value = os.getenv(name)
    return value if value else default


# Valores por defecto de esta instalación (los de la cuenta que ya está en
# producción). Una instalación nueva los sobreescribe por completo
# definiendo las variables de entorno MULTISALE_GROUP_<key>_LABEL /
# _DESCRIPTION / _LINK y MULTISALE_PAYMENT_<key>_LABEL / _DETAILS - no hace
# falta tocar este archivo.
_GROUP_DEFAULTS = {
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
}

_PAYMENT_METHOD_DEFAULTS = {
    "interbancario": {
        "label": "🏦 Pago interbancario",
        "details": (
            "Banco: Banco Pichincha\n"
            "Tipo de cuenta: Ahorros\n"
            "Número de cuenta: [lo configuraré]\n"
            "Titular: Ricardo Elías Mero Mieles\n"
            "Cédula: 1315531515"
        ),
    },
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
}


def _default_config() -> dict:
    return {
        "groups": {
            key: {
                "label": _env(f"MULTISALE_GROUP_{key.upper()}_LABEL", defaults["label"]),
                "description": _env(f"MULTISALE_GROUP_{key.upper()}_DESCRIPTION", defaults["description"]),
                "link": _env(f"MULTISALE_GROUP_{key.upper()}_LINK", defaults["link"]),
            }
            for key, defaults in _GROUP_DEFAULTS.items()
        },
        "payment_methods": {
            key: {
                "label": _env(f"MULTISALE_PAYMENT_{key.upper()}_LABEL", defaults["label"]),
                "details": _env(f"MULTISALE_PAYMENT_{key.upper()}_DETAILS", defaults["details"]),
            }
            for key, defaults in _PAYMENT_METHOD_DEFAULTS.items()
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


# Máximo de veces que un cliente (no-admin) puede ver los datos de un
# mismo método de pago, a pedido explícito - pensado para reintentos
# legítimos (ej. se cortó internet a mitad del pago). "Pago interbancario"
# es la excepción: muestra la cédula del titular, así que se queda en 1
# sola vez por motivos de privacidad; el resto de métodos permite 2. El
# administrador nunca cuenta contra este límite en ningún método (ver
# ms_method_selected en multisale_handlers.py, que lo exime por completo).
MAX_PAYMENT_DATA_VIEWS_DEFAULT = 2
MAX_PAYMENT_DATA_VIEWS_BY_METHOD = {
    "interbancario": 1,  # muestra la cédula del titular
}


def get_max_payment_data_views(method_key: str) -> int:
    return MAX_PAYMENT_DATA_VIEWS_BY_METHOD.get(method_key, MAX_PAYMENT_DATA_VIEWS_DEFAULT)


class PaymentDataSeenStore:
    """Registra, de forma PERMANENTE, cuántas veces (user_id, método_de_pago)
    ya vio los datos bancarios de ese método - hasta get_max_payment_data_views()
    veces (2, salvo "Pago interbancario" que es 1 por mostrar la cédula del
    titular), luego queda bloqueado para siempre. Independiente por método:
    haber visto Banco Pichincha no bloquea ver PayPal. Nunca se resetea
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
        data = self._load_from_upstash() if self.use_upstash else self._load_from_file()
        # Compatibilidad con el formato viejo (lista de claves "vistas una
        # única vez"): cada entrada se migra a count=1, para no resetear a
        # 0 vistas a quienes ya habían visto los datos bajo el límite
        # anterior (de 1 vez).
        seen = data.get("seen")
        if isinstance(seen, list):
            data["seen"] = {key: 1 for key in seen}
        elif not isinstance(seen, dict):
            data["seen"] = {}
        return data

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

    def get_view_count(self, user_id: int, method_key: str) -> int:
        return self.data.get("seen", {}).get(self._key(user_id, method_key), 0)

    def has_reached_limit(self, user_id: int, method_key: str) -> bool:
        return self.get_view_count(user_id, method_key) >= get_max_payment_data_views(method_key)

    def mark_seen(self, user_id: int, method_key: str) -> None:
        seen = self.data.setdefault("seen", {})
        key = self._key(user_id, method_key)
        seen[key] = seen.get(key, 0) + 1
        self._save()
