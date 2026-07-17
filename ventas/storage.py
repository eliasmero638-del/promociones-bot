"""
Almacena las solicitudes de pago ("quiero acceso VIP, ya pagué") enviadas
por los usuarios: titular del pago, método usado, estado (pending/approved/
rejected), y el message_id del aviso enviado al admin (para poder editar
ese mensaje después de aprobar/rechazar).

Mismo patrón dual Upstash/archivo local que el resto del proyecto. Ver el
docstring de ventas/config.py sobre por qué las importaciones desde bot.py
son diferidas.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("bot")

UPSTASH_SALES_REQUESTS_KEY = "ventas_bot:payment_requests"
SALES_REQUESTS_LOCAL_FILENAME = "ventas_payment_requests.json"


def _resolve_local_path() -> str:
    try:
        from bot import DATA_DIR
    except Exception:
        DATA_DIR = ""
    if DATA_DIR:
        os.makedirs(DATA_DIR, exist_ok=True)
        return os.path.join(DATA_DIR, SALES_REQUESTS_LOCAL_FILENAME)
    return SALES_REQUESTS_LOCAL_FILENAME


class SalesRequestsManager:
    """Administra la lista de solicitudes de pago ("payment requests")."""

    def __init__(self):
        self.file_path = _resolve_local_path()
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
            logger.error(f"[ventas.storage] Could not import Upstash client from bot: {e}")
            return {"requests": []}

        result = _upstash_command("GET", UPSTASH_SALES_REQUESTS_KEY)
        if result is None:
            logger.error("[ventas.storage] Upstash request failed; starting with an empty list for this session.")
            return {"requests": []}

        raw = result.get("result")
        if raw is None:
            logger.info("[ventas.storage] No payment requests stored yet in Upstash; starting empty.")
            return {"requests": []}

        try:
            data = json.loads(raw)
            logger.info(f"[ventas.storage] Loaded {len(data.get('requests', []))} payment requests from Upstash.")
            return data
        except Exception as e:
            logger.error(f"[ventas.storage] Failed to parse JSON from Upstash: {e}")
            return {"requests": []}

    def _load_from_file(self) -> dict:
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[ventas.storage] Failed to load local payment requests file: {e}")
        return {"requests": []}

    def save(self) -> bool:
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        try:
            from bot import _upstash_command
        except Exception as e:
            logger.error(f"[ventas.storage] Could not import Upstash client from bot: {e}")
            return False

        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[ventas.storage] Could not serialize payment requests: {e}")
            return False

        result = _upstash_command("SET", UPSTASH_SALES_REQUESTS_KEY, payload)
        if result is not None and result.get("result") == "OK":
            logger.info(f"[ventas.storage] Saved {len(self.data.get('requests', []))} payment requests to Upstash.")
            return True

        logger.error(f"[ventas.storage] Upstash SET did not confirm success: {result}")
        return False

    def _save_to_file(self) -> bool:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            logger.info("[ventas.storage] Payment requests saved to local file.")
            return True
        except Exception as e:
            logger.error(f"[ventas.storage] Failed to save local payment requests file: {e}")
            return False

    def get_all(self) -> List[Dict]:
        return self.data.get("requests", [])

    def get_by_id(self, request_id: str) -> Optional[Dict]:
        for req in self.get_all():
            if req.get("id") == request_id:
                return req
        return None

    def _next_id(self) -> str:
        """Mismo criterio anti-colisión que _next_promotion_id() en bot.py:
        se basa en el sufijo numérico más alto en uso, no en la longitud de
        la lista, para no repetir un ID si alguna solicitud fue removida."""
        highest = 0
        for req in self.get_all():
            req_id = str(req.get("id", ""))
            if req_id.startswith("sale_"):
                suffix = req_id[len("sale_"):]
                if suffix.isdigit():
                    highest = max(highest, int(suffix))
        return f"sale_{str(highest + 1).zfill(3)}"

    def add(self, request: Dict) -> Optional[str]:
        """Agrega una nueva solicitud de pago. Devuelve el ID asignado si
        se guardó correctamente, o None si falló."""
        request_id = self._next_id()
        request = dict(request)
        request["id"] = request_id
        self.data.setdefault("requests", []).append(request)

        logger.info(f"[ventas.storage] Adding payment request {request_id}: {request}")
        if self.save():
            return request_id

        logger.error(f"[ventas.storage] Failed to save new payment request {request_id}.")
        return None

    def update(self, request_id: str, request: Dict) -> bool:
        for i, req in enumerate(self.data.get("requests", [])):
            if req.get("id") == request_id:
                self.data["requests"][i] = request
                return self.save()
        return False
