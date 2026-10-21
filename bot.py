"""Bot de Telegram: descarga enlaces o archivos y los sube a un repo de GitHub."""

import asyncio
import logging
import os
import re
import shutil
import tempfile
import unicodedata

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (Application, CommandHandler, ContextTypes, MessageHandler,
                          filters)

import downloader
from envio_grande import LIMITE_MB as LIMITE_GRANDE_MB, EnvioGrande
from github_store import GitHubStore, GitHubError, LIMITE_REPO_MB, tag_de

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                    level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("bot")

PROYECTO_POR_DEFECTO = "general"
URL_RE = re.compile(r"https?://\S+", re.I)


def _env(nombre, obligatoria=True):
    valor = (os.environ.get(nombre) or "").strip()
    if obligatoria and not valor:
        raise SystemExit(f"❌ Falta la variable de entorno {nombre}. "
                         "Agrégala en Railway → tu servicio → Variables.")
    return valor


TELEGRAM_TOKEN = _env("TELEGRAM_TOKEN")
GITHUB_TOKEN = _env("GITHUB_TOKEN", obligatoria=False)
GITHUB_REPO = _env("GITHUB_REPO", obligatoria=False)
GITHUB_BRANCH = _env("GITHUB_BRANCH", obligatoria=False) or None
_id = _env("ALLOWED_USER_ID", obligatoria=False)
ALLOWED_USER_ID = int(_id) if _id.isdigit() else None
YTDLP_COOKIES = _env("YTDLP_COOKIES", obligatoria=False) or None
# Repo PÚBLICO para /redes (enlaces directos para Metricool)
REDES_REPO = _env("REDES_REPO", obligatoria=False) or "eliasmero638-del/promociones-bot"
REDES_BRANCH = _env("REDES_BRANCH", obligatoria=False) or "ridmer-videos"
# Opcionales, de my.telegram.org: permiten enviar/recibir archivos de hasta 2 GB
_api_id = _env("TELEGRAM_API_ID", obligatoria=False)
TELEGRAM_API_HASH = _env("TELEGRAM_API_HASH", obligatoria=False)

FALTAN = [n for n, v in (("ALLOWED_USER_ID", ALLOWED_USER_ID), ("GITHUB_TOKEN", GITHUB_TOKEN),
                         ("GITHUB_REPO", GITHUB_REPO)) if not v]

store = GitHubStore(GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH) if not FALTAN else None
redes = GitHubStore(GITHUB_TOKEN, REDES_REPO, REDES_BRANCH) if not FALTAN else None
grande = (EnvioGrande(int(_api_id), TELEGRAM_API_HASH, TELEGRAM_TOKEN)
          if _api_id.isdigit() and TELEGRAM_API_HASH else None)
estado = {"proyecto": PROYECTO_POR_DEFECTO, "numeros": {}}
candado = asyncio.Lock()


def grande_limite():
    """Lo máximo que el bot puede enviarte por Telegram."""
    return (LIMITE_GRANDE_MB if grande and grande.activo else 50) * 1024 * 1024


# ====================================================================== nombres
def limpiar_nombre(texto: str, maximo: int = 60) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode()
    texto = re.sub(r"[^\w\-]+", "_", texto).strip("_.-")
    texto = re.sub(r"_+", "_", texto)
    return texto[:maximo].rstrip("_.-")


def nombre_final(numero: int, etiqueta: str, ruta: str) -> str:
    ext = os.path.splitext(ruta)[1].lower() or ".bin"
    etiqueta = limpiar_nombre(etiqueta) or "archivo"
    return f"{numero:02d}_{etiqueta}{ext}"


def separar_enlaces(texto: str) -> list[tuple[str, str]]:
    """Devuelve [(etiqueta, url)]. La etiqueta es el texto antes del enlace."""
    resultado = []
    for linea in texto.splitlines():
        pos = 0
        for m in URL_RE.finditer(linea):
            etiqueta = linea[pos:m.start()].strip(" \t-–—:|,;")
            url = m.group(0).rstrip(").,;>]\"'")
            resultado.append((etiqueta, url))
            pos = m.end()
    return resultado


def mb(tam):
    return f"{tam / 1024 / 1024:.1f} MB"


# ====================================================================== guardar
class SubidaError(Exception):
    def __init__(self, nombre, causa):
        super().__init__(str(causa))
        self.nombre = nombre
        self.causa = causa


async def siguiente_numero(proyecto: str) -> int:
    """Número siguiente según GitHub y los archivos que solo se enviaron por Telegram."""
    reservado = estado.setdefault("numeros", {}).get(proyecto, 0)
    try:
        en_github = await asyncio.to_thread(store.siguiente_numero, proyecto)
    except Exception:
        if not reservado:
            raise
        en_github = 0
    numero = max(en_github, reservado + 1)
    estado["numeros"][proyecto] = numero
    return numero


async def guardar_numeros():
    """Recuerda en GitHub los números de los archivos que no están en GitHub."""
    try:
        await asyncio.to_thread(store.guardar_estado, dict(estado))
    except Exception as e:
        log.warning("No pude guardar la numeración en GitHub: %s", e)


async def guardar(ruta_local: str, etiqueta: str) -> tuple[str, str]:
    """Numera y sube el archivo. Devuelve (nombre, 'repo'|'release').

    Si falla lanza SubidaError con el nombre que iba a tener el archivo."""
    proyecto = estado["proyecto"]
    nombre = nombre_final(0, etiqueta, ruta_local).replace("00_", "XX_", 1)
    async with candado:
        try:
            nombre = nombre_final(await siguiente_numero(proyecto), etiqueta, ruta_local)
            donde = await asyncio.to_thread(store.subir_archivo, proyecto, ruta_local, nombre)
        except Exception as e:
            log.exception("Falló la subida de %s a GitHub", nombre)
            raise SubidaError(nombre, e)
    return nombre, donde


async def guardar_redes(aviso, ruta: str, etiqueta: str):
    """Modo /redes: sube a la rama pública y responde con el enlace directo."""
    tam = os.path.getsize(ruta)
    await responder(aviso, f"⬆️ Subiendo a la carpeta pública de redes ({mb(tam)})…")
    ext = os.path.splitext(ruta)[1].lower() or ".bin"
    base = limpiar_nombre(etiqueta) or "video"
    async with candado:
        try:
            existentes = {f["name"] for f in await asyncio.to_thread(redes.listar_carpeta, "")}
            existentes |= {f["name"] for f in await asyncio.to_thread(redes.listar_release,
                                                                       REDES_BRANCH)}
            nombre, n = f"{base}{ext}", 2
            while nombre in existentes:
                nombre, n = f"{base}_{n}{ext}", n + 1
            donde = await asyncio.to_thread(redes.subir_archivo, REDES_BRANCH, ruta, nombre, "")
        except Exception as e:
            log.exception("Falló la subida de %s a redes", base)
            raise SubidaError(f"{base}{ext}", e)
    enlace = redes.url_publica(nombre, donde, REDES_BRANCH)
    await responder(aviso, f"✅ Subido para redes: {nombre}\n\n🔗 Enlace directo para Metricool:\n"
                           f"{enlace}")


async def entregar(update: Update, aviso, ruta: str, etiqueta: str):
    """Sube a GitHub; si pesa más de LIMITE_REPO_MB y está activado el envío
    grande, te lo manda por Telegram en vez de subirlo al Release."""
    if estado.get("modo") == "redes":
        await guardar_redes(aviso, ruta, etiqueta)
        return
    tam = os.path.getsize(ruta)
    if tam >= LIMITE_REPO_MB * 1024 * 1024 and grande and grande.activo:
        async with candado:
            nombre = nombre_final(await siguiente_numero(estado["proyecto"]), etiqueta, ruta)
            await guardar_numeros()
        await responder(aviso, f"📤 Pesa {mb(tam)}, te lo envío por aquí: {nombre}")
        try:
            await grande.enviar(update.effective_chat.id, ruta, nombre,
                                f"📎 {nombre} ({mb(tam)}) — proyecto {estado['proyecto']}", aviso)
            await responder(aviso, f"✅ Descargado y enviado por Telegram: {nombre}\n"
                                   f"(Pesa {mb(tam)}; no se subió a GitHub.)")
            return
        except Exception as e:
            log.exception("No pude enviar %s por Telegram", nombre)
            await update.message.reply_text(f"⚠️ No pude enviártelo por Telegram ({e}). "
                                            "Lo subo al Release de GitHub.")
    await responder(aviso, f"⬆️ Subiendo a GitHub ({mb(tam)})…")
    nombre, donde = await guardar(ruta, etiqueta)
    await responder(aviso, texto_ok(nombre, donde, ruta))


async def plan_b(update: Update, aviso, ruta: str, error: SubidaError):
    """Si GitHub falla, manda el archivo por Telegram para no perderlo."""
    motivo = str(error.causa)[:300] or type(error.causa).__name__
    tam = os.path.getsize(ruta)
    limite = grande_limite()
    if tam > limite:
        await responder(aviso, f"❌ Se descargó pero falló la subida a GitHub: {motivo}\n\n"
                               f"Tampoco te lo puedo mandar por aquí: pesa {mb(tam)} y el límite "
                               f"es {mb(limite)}. Vuelve a mandar el enlace en un rato.")
        return
    await responder(aviso, f"⚠️ Se descargó pero falló la subida a GitHub: {motivo}\n\n"
                           f"📤 Te lo envío aquí para que no se pierda: {error.nombre}")
    await guardar_numeros()
    texto = f"📎 {error.nombre} (no se subió a GitHub)"
    try:
        if grande and grande.activo:
            await grande.enviar(update.effective_chat.id, ruta, error.nombre, texto)
        else:
            with open(ruta, "rb") as fh:
                await update.message.reply_document(
                    fh, filename=error.nombre, caption=texto,
                    read_timeout=600, write_timeout=600, connect_timeout=60)
    except Exception as e:
        log.exception("Tampoco pude enviar %s por Telegram", error.nombre)
        await update.message.reply_text(f"❌ Tampoco pude enviártelo por Telegram: {e}\n"
                                        "Vuelve a mandar el enlace para reintentar.")


def texto_ok(nombre, donde, ruta):
    msg = f"✅ Descargado y subido: {nombre}"
    if donde == "release":
        msg += (f"\n📦 Pesa {mb(os.path.getsize(ruta))} (más de {LIMITE_REPO_MB} MB), "
                f"así que está en el Release «{tag_de(estado['proyecto'])}».")
    return msg


async def responder(aviso, texto):
    try:
        await aviso.edit_text(texto)
    except BadRequest:
        await aviso.reply_text(texto)


# ====================================================================== comandos
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Mándame enlaces (YouTube, TikTok, Instagram, Facebook, Pexels, "
        "Pixabay, Wikipedia, Google Drive o enlaces directos) o fotos/videos/audios, "
        "y los guardo en GitHub.\n\n"
        "• /proyecto NOMBRE — elegir carpeta\n"
        "• /estado — proyecto actual y cuántos archivos tiene\n"
        "• /lista — ver los archivos del proyecto\n"
        "• /redes — subir a la carpeta pública y darte el enlace para Metricool\n\n"
        "Para ponerle nombre: «R1 https://...»\n"
        f"📁 Proyecto actual: {estado['proyecto']}")


async def cmd_proyecto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = limpiar_nombre(" ".join(context.args), maximo=80)
    if not nombre:
        await update.message.reply_text(
            f"📁 Proyecto actual: {estado['proyecto']}\n"
            "Para cambiarlo: /proyecto NOMBRE (ejemplo: /proyecto peter_bergmann)")
        return
    estado["proyecto"] = nombre
    estado["modo"] = None
    try:
        await asyncio.to_thread(store.guardar_estado, dict(estado))
        cantidad = len(await asyncio.to_thread(store.listar_proyecto, nombre))
    except GitHubError as e:
        await update.message.reply_text(f"⚠️ Proyecto cambiado a {nombre}, pero no pude "
                                        f"guardarlo en GitHub: {e}")
        return
    extra = f" (ya tiene {cantidad} archivos)" if cantidad else ""
    await update.message.reply_text(f"📁 Proyecto: {nombre}{extra}\n"
                                    "Todo lo que mandes ahora se guarda ahí.")


async def cmd_redes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estado["modo"] = "redes"
    await guardar_numeros()
    await update.message.reply_text(
        "🌐 Modo redes activado. Lo que mandes ahora se sube a la carpeta PÚBLICA "
        f"({REDES_REPO}, rama {REDES_BRANCH}) y te respondo con el enlace directo para "
        "Metricool.\n\n⚠️ Cualquiera con el enlace podrá verlo.\n"
        f"Para volver al material privado: /proyecto {estado['proyecto']}")


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if estado.get("modo") == "redes":
        await update.message.reply_text(
            f"🌐 Modo redes: lo que mandes va a {REDES_REPO} (rama {REDES_BRANCH}), público.\n"
            f"Para volver al material privado: /proyecto {estado['proyecto']}")
        return
    proyecto = estado["proyecto"]
    try:
        archivos = await asyncio.to_thread(store.listar_proyecto, proyecto)
    except GitHubError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    en_release = sum(1 for a in archivos if a["where"] == "release")
    texto = (f"📁 Proyecto actual: {proyecto}\n"
             f"📄 Archivos: {len(archivos)}")
    if en_release:
        texto += f" ({en_release} en el Release por ser grandes)"
    texto += f"\n🗂 Repositorio: {GITHUB_REPO}" + (f" (rama {GITHUB_BRANCH})" if GITHUB_BRANCH else "")
    texto += "\n🍪 Cookies: " + ("configuradas" if YTDLP_COOKIES else "no configuradas")
    await update.message.reply_text(texto)


async def cmd_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proyecto = estado["proyecto"]
    try:
        archivos = await asyncio.to_thread(store.listar_proyecto, proyecto)
    except GitHubError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    if not archivos:
        await update.message.reply_text(f"📁 {proyecto}: todavía no hay archivos.")
        return
    lineas = [f"📁 {proyecto} — {len(archivos)} archivos:"]
    for a in archivos:
        icono = "📦" if a["where"] == "release" else "•"
        lineas.append(f"{icono} {a['name']} ({mb(a['size'])})")
    texto, trozo = "\n".join(lineas), ""
    for linea in texto.splitlines(keepends=True):
        if len(trozo) + len(linea) > 3900:
            await update.message.reply_text(trozo)
            trozo = ""
        trozo += linea
    if trozo:
        await update.message.reply_text(trozo)


# ====================================================================== mensajes
async def al_recibir_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    enlaces = separar_enlaces(update.message.text or "")
    if not enlaces:
        await update.message.reply_text(
            "No vi ningún enlace. Mándame un enlace (puedes poner un nombre antes, "
            "ej.: «R1 https://...»), o una foto/video/audio.")
        return
    for etiqueta, url in enlaces:
        await procesar_enlace(update, etiqueta, url)


async def procesar_enlace(update: Update, etiqueta: str, url: str):
    aviso = await update.message.reply_text(f"⏳ Descargando… {url[:80]}")
    carpeta = tempfile.mkdtemp(prefix="dl_")
    try:
        res = await asyncio.to_thread(downloader.descargar, url, carpeta, YTDLP_COOKIES)
        await entregar(update, aviso, res.ruta, etiqueta or res.titulo)
    except downloader.BloqueoError as e:
        await responder(aviso, f"{e}\n\nEnlace: {url}")
    except downloader.DescargaError as e:
        await responder(aviso, f"❌ No pude descargar: {e}\n\nEnlace: {url}")
    except SubidaError as e:
        await plan_b(update, aviso, res.ruta, e)
    except Exception as e:
        log.exception("Error procesando %s", url)
        await responder(aviso, f"❌ Error inesperado: {type(e).__name__}: {e}\n\nEnlace: {url}")
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


async def al_recibir_archivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.message
    nombre_original, ext = None, ""
    if m.photo:
        adjunto, ext = m.photo[-1], ".jpg"  # la última es la de mayor resolución
    elif m.video:
        adjunto, nombre_original = m.video, m.video.file_name
        ext = ".mp4"
    elif m.animation:
        adjunto, nombre_original, ext = m.animation, m.animation.file_name, ".mp4"
    elif m.video_note:
        adjunto, ext = m.video_note, ".mp4"
    elif m.audio:
        adjunto, nombre_original, ext = m.audio, m.audio.file_name, ".mp3"
    elif m.voice:
        adjunto, ext = m.voice, ".ogg"
    elif m.document:
        adjunto, nombre_original = m.document, m.document.file_name
    else:
        return
    if nombre_original and os.path.splitext(nombre_original)[1]:
        ext = os.path.splitext(nombre_original)[1].lower()
    etiqueta = (m.caption or "").strip() or (
        os.path.splitext(nombre_original)[0] if nombre_original else "")
    if not etiqueta:
        etiqueta = {".jpg": "foto", ".mp4": "video", ".ogg": "audio"}.get(ext, "archivo")

    aviso = await m.reply_text("⏳ Recibiendo archivo…")
    carpeta = tempfile.mkdtemp(prefix="tg_")
    try:
        ruta = os.path.join(carpeta, "archivo" + (ext or ".bin"))
        try:
            archivo = await adjunto.get_file()
            await archivo.download_to_drive(ruta)
        except BadRequest as e:
            if "too big" not in str(e).lower():
                raise
            if not (grande and grande.activo):
                await responder(aviso, "❌ Telegram no deja a los bots bajar archivos de más "
                                       "de 20 MB. Súbelo a Google Drive y mándame el enlace.")
                return
            await grande.descargar(m.chat_id, m.message_id, ruta, aviso)
        res = await asyncio.to_thread(downloader.normalizar,
                                      downloader.Resultado(ruta, etiqueta))
        if estado.get("modo") == "redes":
            await guardar_redes(aviso, res.ruta, etiqueta)
            return
        await responder(aviso, f"⬆️ Subiendo a GitHub ({mb(os.path.getsize(res.ruta))})…")
        nombre, donde = await guardar(res.ruta, etiqueta)
        await responder(aviso, texto_ok(nombre, donde, res.ruta))
    except SubidaError as e:
        await responder(aviso, f"❌ Falló la subida a GitHub: {e}\n"
                               f"Iba a llamarse {e.nombre}. El archivo sigue en este chat; "
                               "reenvíamelo para reintentar.")
    except Exception as e:
        log.exception("Error con archivo de Telegram")
        await responder(aviso, f"❌ Error: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


async def no_autorizado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    log.warning("Ignorado mensaje de usuario no autorizado: id=%s @%s",
                u.id if u else "?", u.username if u else "?")


async def al_error(update, context: ContextTypes.DEFAULT_TYPE):
    log.error("Error no controlado", exc_info=context.error)


# ====================================================================== configuración
async def modo_configuracion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mientras falten variables, el bot solo explica qué falta (y nada más)."""
    u = update.effective_user
    if not u or not update.effective_message:
        return
    if ALLOWED_USER_ID is None:
        log.warning("Modo configuración: mensaje de id=%s @%s", u.id, u.username)
        await update.effective_message.reply_text(
            f"🔧 El bot aún no está configurado.\n\nTu ID de Telegram es: {u.id}\n\n"
            "Ponlo en Railway en la variable ALLOWED_USER_ID.")
    elif u.id == ALLOWED_USER_ID:
        await update.effective_message.reply_text(
            "🔧 Falta configurar en Railway: " + ", ".join(FALTAN))


# ====================================================================== arranque
async def al_iniciar(app: Application):
    if FALTAN:
        log.warning("Modo configuración. Faltan las variables: %s", ", ".join(FALTAN))
        return
    try:
        await asyncio.to_thread(store.check)
        guardado = await asyncio.to_thread(store.leer_estado)
        if guardado.get("proyecto"):
            estado["proyecto"] = guardado["proyecto"]
        estado["numeros"].update(guardado.get("numeros") or {})
        estado["modo"] = guardado.get("modo")
        aviso = f"🤖 Bot en línea. 📁 Proyecto actual: {estado['proyecto']}"
        if estado["modo"] == "redes":
            aviso += "\n🌐 Modo redes activo (carpeta pública). Para salir: /proyecto NOMBRE"
        try:
            await asyncio.to_thread(redes.check)
        except GitHubError as e:
            aviso += f"\n⚠️ /redes no funcionará: el token no puede escribir en {REDES_REPO} ({e})"
    except GitHubError as e:
        log.error("Problema con GitHub: %s", e)
        aviso = f"🤖 Bot en línea, pero ⚠️ hay un problema con GitHub:\n{e}"
    if grande:
        try:
            await grande.iniciar()
            aviso += f"\n📤 Archivos grandes: te los envío por aquí (hasta {LIMITE_GRANDE_MB} MB)."
        except Exception as e:
            log.exception("No pude activar el envío de archivos grandes")
            aviso += (f"\n⚠️ No pude activar el envío de archivos grandes ({e}). "
                      "Revisa TELEGRAM_API_ID y TELEGRAM_API_HASH.")
    log.info(aviso)
    try:
        await app.bot.send_message(ALLOWED_USER_ID, aviso)
    except Exception as e:
        log.warning("No pude escribirte por Telegram (¿ya le diste /start al bot?): %s", e)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(al_iniciar).build()
    if FALTAN:
        app.add_handler(MessageHandler(filters.ALL, modo_configuracion))
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        return
    yo = filters.User(user_id=ALLOWED_USER_ID)

    app.add_handler(CommandHandler(["start", "ayuda", "help"], cmd_start, filters=yo))
    app.add_handler(CommandHandler("proyecto", cmd_proyecto, filters=yo))
    app.add_handler(CommandHandler("estado", cmd_estado, filters=yo))
    app.add_handler(CommandHandler("lista", cmd_lista, filters=yo))
    app.add_handler(CommandHandler("redes", cmd_redes, filters=yo))
    app.add_handler(MessageHandler(
        yo & (filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE
              | filters.ANIMATION | filters.VIDEO_NOTE | filters.Document.ALL),
        al_recibir_archivo))
    app.add_handler(MessageHandler(yo & filters.TEXT & ~filters.COMMAND, al_recibir_texto))
    app.add_handler(MessageHandler(~yo, no_autorizado))
    app.add_error_handler(al_error)

    log.info("Arrancando bot (repo: %s, usuario permitido: %s)", GITHUB_REPO, ALLOWED_USER_ID)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
