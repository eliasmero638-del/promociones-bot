"""
Almacenamiento del sistema NUEVO de venta multi-grupo: el registro de cada
venta (MultiSaleRequestsManager) y los dos stores de timers persistentes
(PendingAutoApprovalsStore / PendingPaymentDataDeletionsStore), que existen
para que los timers de 5 minutos sobrevivan un redeploy/reinicio de
Railway - mismo patrón que ventas/config.py::TrialKicksStore.

Completamente independiente de ventas/storage.py (SalesRequestsManager, el
sistema viejo) - claves de Upstash y archivos locales propios, sin tocar
nada del sistema viejo.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("bot")

UPSTASH_MULTISALE_REQUESTS_KEY = "multisale_bot:requests"
MULTISALE_REQUESTS_LOCAL_FILENAME = "multisale_requests.json"

UPSTASH_PENDING_AUTO_APPROVALS_KEY = "multisale_bot:pending_auto_approvals"
PENDING_AUTO_APPROVALS_LOCAL_FILENAME = "multisale_pending_auto_approvals.json"

UPSTASH_PENDING_PAYMENT_DATA_DELETIONS_KEY = "multisale_bot:pending_payment_data_deletions"
PENDING_PAYMENT_DATA_DELETIONS_LOCAL_FILENAME = "multisale_pending_payment_data_deletions.json"


def _resolve_local_path(filename: str) -> str:
    try:
        from bot import DATA_DIR
    except Exception:
        DATA_DIR = ""
    if DATA_DIR:
        os.makedirs(DATA_DIR, exist_ok=True)
        return os.path.join(DATA_DIR, filename)
    return filename


class MultiSaleRequestsManager:
    """Administra el registro de ventas del sistema nuevo. A diferencia de
    ventas/storage.py::SalesRequestsManager (que solo guarda UN
    admin_message_id), acá se guarda admin_message_ids: {admin_id:
    message_id} - un mensaje por administrador notificado - para poder
    actualizar el mensaje de TODOS los admins al aprobar/rechazar, no solo
    del primero."""

    def __init__(self):
        self.file_path = _resolve_local_path(MULTISALE_REQUESTS_LOCAL_FILENAME)
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
            logger.error(f"[multisale.storage] Could not import Upstash client from bot: {e}")
            return {"requests": []}

        result = _upstash_command("GET", UPSTASH_MULTISALE_REQUESTS_KEY)
        if result is None:
            logger.error("[multisale.storage] Upstash request failed; starting with an empty list for this session.")
            return {"requests": []}

        raw = result.get("result")
        if raw is None:
            logger.info("[multisale.storage] No sale requests stored yet in Upstash; starting empty.")
            return {"requests": []}

        try:
            data = json.loads(raw)
            logger.info(f"[multisale.storage] Loaded {len(data.get('requests', []))} sale requests from Upstash.")
            return data
        except Exception as e:
            logger.error(f"[multisale.storage] Failed to parse JSON from Upstash: {e}")
            return {"requests": []}

    def _load_from_file(self) -> dict:
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[multisale.storage] Failed to load local sale requests file: {e}")
        return {"requests": []}

    def save(self) -> bool:
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[multisale.storage] Could not import Upstash client from bot: {e}")
            return False
        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[multisale.storage] Could not serialize sale requests: {e}")
            return False
        result = _upstash_command("SET", UPSTASH_MULTISALE_REQUESTS_KEY, payload)
        if result is not None and result.get("result") == "OK":
            logger.info(f"[multisale.storage] Saved {len(self.data.get('requests', []))} sale requests to Upstash.")
            return True
        logger.error(f"[multisale.storage] Upstash SET did not confirm success: {result}")
        return False

    def _save_to_file(self) -> bool:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            logger.info("[multisale.storage] Sale requests saved to local file.")
            return True
        except Exception as e:
            logger.error(f"[multisale.storage] Failed to save local sale requests file: {e}")
            return False

    def get_all(self) -> List[Dict]:
        return self.data.get("requests", [])

    def get_by_id(self, request_id: str) -> Optional[Dict]:
        for req in self.get_all():
            if req.get("id") == request_id:
                return req
        return None

    def _next_id(self) -> str:
        """ID secuencial tipo "venta_00001" (se muestra al admin como
        "Venta #00001"). Basado en el sufijo numérico más alto en uso, no
        en la longitud de la lista, para no repetir un ID si alguna venta
        fuera removida del registro."""
        highest = 0
        for req in self.get_all():
            req_id = str(req.get("id", ""))
            if req_id.startswith("venta_"):
                suffix = req_id[len("venta_"):]
                if suffix.isdigit():
                    highest = max(highest, int(suffix))
        return f"venta_{str(highest + 1).zfill(5)}"

    def add(self, request: Dict) -> Optional[str]:
        """Agrega una nueva venta. Devuelve el ID asignado si se guardó
        correctamente, o None si falló."""
        request_id = self._next_id()
        request = dict(request)
        request["id"] = request_id
        self.data.setdefault("requests", []).append(request)

        logger.info(f"[multisale.storage] Adding sale {request_id}: {request}")
        if self.save():
            return request_id

        logger.error(f"[multisale.storage] Failed to save new sale {request_id}.")
        return None

    def update(self, request_id: str, request: Dict) -> bool:
        for i, req in enumerate(self.data.get("requests", [])):
            if req.get("id") == request_id:
                self.data["requests"][i] = request
                return self.save()
        return False

    @staticmethod
    def display_id(request_id: str) -> str:
        """"venta_00001" -> "Venta #00001", para mostrar al admin."""
        suffix = request_id[len("venta_"):] if request_id.startswith("venta_") else request_id
        return f"Venta #{suffix}"


class PendingAutoApprovalsStore:
    """Registra, de forma persistente, qué ventas tienen una aprobación
    automática pendiente y a qué hora exacta (timestamp Unix) debe
    ocurrir. Mismo motivo que TrialKicksStore en ventas/config.py: el
    JobQueue de python-telegram-bot solo vive en memoria, así que sin esto
    un redeploy de Railway durante la ventana de 5 minutos perdería la
    aprobación automática por completo."""

    def __init__(self):
        self.file_path = _resolve_local_path(PENDING_AUTO_APPROVALS_LOCAL_FILENAME)
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
            logger.error(f"[multisale.storage] Could not import Upstash client from bot: {e}")
            return {"pending": []}
        result = _upstash_command("GET", UPSTASH_PENDING_AUTO_APPROVALS_KEY)
        if result is None:
            return {"pending": []}
        raw = result.get("result")
        if raw is None:
            return {"pending": []}
        try:
            return json.loads(raw)
        except Exception as e:
            logger.error(f"[multisale.storage] Failed to parse pending auto-approvals JSON: {e}")
            return {"pending": []}

    def _load_from_file(self) -> dict:
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[multisale.storage] Failed to load local pending auto-approvals file: {e}")
        return {"pending": []}

    def _save(self) -> bool:
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[multisale.storage] Could not import Upstash client from bot: {e}")
            return False
        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[multisale.storage] Could not serialize pending auto-approvals: {e}")
            return False
        result = _upstash_command("SET", UPSTASH_PENDING_AUTO_APPROVALS_KEY, payload)
        return bool(result is not None and result.get("result") == "OK")

    def _save_to_file(self) -> bool:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            return True
        except Exception as e:
            logger.error(f"[multisale.storage] Failed to save local pending auto-approvals file: {e}")
            return False

    def add_pending(self, request_id: str, approve_at: float) -> None:
        self.data.setdefault("pending", []).append({"request_id": request_id, "approve_at": approve_at})
        self._save()

    def remove_pending(self, request_id: str) -> None:
        pending = self.data.get("pending", [])
        self.data["pending"] = [p for p in pending if p.get("request_id") != request_id]
        self._save()

    def get_all_pending(self) -> list:
        return list(self.data.get("pending", []))


class PendingPaymentDataDeletionsStore:
    """Registra, de forma persistente, qué mensajes de datos de pago
    (bancarios) deben borrarse y cuándo. Mismo motivo/patrón que
    PendingAutoApprovalsStore de arriba: sobrevive un redeploy de Railway
    durante la ventana de 5 minutos."""

    def __init__(self):
        self.file_path = _resolve_local_path(PENDING_PAYMENT_DATA_DELETIONS_LOCAL_FILENAME)
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
            logger.error(f"[multisale.storage] Could not import Upstash client from bot: {e}")
            return {"pending": []}
        result = _upstash_command("GET", UPSTASH_PENDING_PAYMENT_DATA_DELETIONS_KEY)
        if result is None:
            return {"pending": []}
        raw = result.get("result")
        if raw is None:
            return {"pending": []}
        try:
            return json.loads(raw)
        except Exception as e:
            logger.error(f"[multisale.storage] Failed to parse pending payment-data deletions JSON: {e}")
            return {"pending": []}

    def _load_from_file(self) -> dict:
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[multisale.storage] Failed to load local pending payment-data deletions file: {e}")
        return {"pending": []}

    def _save(self) -> bool:
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[multisale.storage] Could not import Upstash client from bot: {e}")
            return False
        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[multisale.storage] Could not serialize pending payment-data deletions: {e}")
            return False
        result = _upstash_command("SET", UPSTASH_PENDING_PAYMENT_DATA_DELETIONS_KEY, payload)
        return bool(result is not None and result.get("result") == "OK")

    def _save_to_file(self) -> bool:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            return True
        except Exception as e:
            logger.error(f"[multisale.storage] Failed to save local pending payment-data deletions file: {e}")
            return False

    def add_pending(self, chat_id: int, message_id: int, delete_at: float) -> None:
        self.data.setdefault("pending", []).append(
            {"chat_id": chat_id, "message_id": message_id, "delete_at": delete_at}
        )
        self._save()

    def remove_pending(self, chat_id: int, message_id: int) -> None:
        pending = self.data.get("pending", [])
        self.data["pending"] = [
            p for p in pending if not (p.get("chat_id") == chat_id and p.get("message_id") == message_id)
        ]
        self._save()

    def get_all_pending(self) -> list:
        return list(self.data.get("pending", []))
