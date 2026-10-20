"""Enviar y recibir archivos grandes por Telegram (hasta 2 GB).

La API normal de bots solo deja enviar 50 MB y descargar 20 MB. Conectándose
como el mismo bot por MTProto (Telethon) el límite sube a 2 GB. Para eso hacen
falta TELEGRAM_API_ID y TELEGRAM_API_HASH, que se sacan en my.telegram.org.
"""

import logging
import os
import shutil
import time

from telethon import TelegramClient
from telethon.sessions import StringSession

log = logging.getLogger(__name__)

LIMITE_MB = 2000


class EnvioGrande:
    def __init__(self, api_id: int, api_hash: str, bot_token: str):
        self._datos = (api_id, api_hash, bot_token)
        self.cliente = None

    async def iniciar(self):
        api_id, api_hash, bot_token = self._datos
        cliente = TelegramClient(StringSession(), api_id, api_hash, receive_updates=False)
        await cliente.start(bot_token=bot_token)
        self.cliente = cliente
        log.info("Envío de archivos grandes (hasta %d MB) activado", LIMITE_MB)

    @property
    def activo(self):
        return self.cliente is not None

    async def enviar(self, chat_id: int, ruta: str, nombre: str, texto: str, aviso=None):
        """Manda el archivo como documento (sin compresión) con el nombre dado."""
        destino = os.path.join(os.path.dirname(ruta), nombre)
        if destino != ruta:
            shutil.move(ruta, destino)
        progreso = _Progreso(aviso, nombre)
        try:
            await self.cliente.send_file(chat_id, destino, caption=texto, force_document=True,
                                         progress_callback=progreso)
        finally:
            if destino != ruta and os.path.exists(destino):
                shutil.move(destino, ruta)

    async def descargar(self, chat_id: int, mensaje_id: int, ruta: str, aviso=None):
        """Descarga un archivo que el usuario mandó al bot (sin el límite de 20 MB)."""
        mensaje = await self.cliente.get_messages(chat_id, ids=mensaje_id)
        if not mensaje or not mensaje.media:
            raise RuntimeError("No encontré el archivo en el mensaje.")
        await self.cliente.download_media(mensaje, file=ruta,
                                          progress_callback=_Progreso(aviso, "archivo", "📥 Recibiendo"))
        return ruta


class _Progreso:
    """Actualiza el mensaje de aviso cada ~10 segundos con el porcentaje."""

    def __init__(self, aviso, nombre, accion="📤 Enviándote"):
        self.aviso, self.nombre, self.accion = aviso, nombre, accion
        self.ultimo = 0

    async def __call__(self, hecho, total):
        if not self.aviso or not total or time.monotonic() - self.ultimo < 10:
            return
        self.ultimo = time.monotonic()
        try:
            await self.aviso.edit_text(f"{self.accion} {self.nombre}… {hecho * 100 // total}% "
                                       f"({hecho / 1048576:.0f} de {total / 1048576:.0f} MB)")
        except Exception:
            pass
