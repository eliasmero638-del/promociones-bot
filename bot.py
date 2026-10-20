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
GITHUB_TOKEN = _env("GITHUB_TOKEN")
GITHUB_REPO = _env("GITHUB_REPO")
ALLOWED_USER_ID = int(_env("ALLOWED_USER_ID"))
YTDLP_COOKIES = _env("YTDLP_COOKIES", obligatoria=False) or None

store = GitHubStore(GITHUB_TOKEN, GITHUB_REPO)
estado = {"proyecto": PROYECTO_POR_DEFECTO}
candado = asyncio.Lock()


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
async def guardar(ruta_local: str, etiqueta: str) -> tuple[str, str]:
    """Numera y sube el archivo. Devuelve (nombre, 'repo'|'release')."""
    proyecto = estado["proyecto"]
    async with candado:
        numero = await asyncio.to_thread(store.siguiente_numero, proyecto)
        nombre = nombre_final(numero, etiqueta, ruta_local)
        donde = await asyncio.to_thread(store.subir_archivo, proyecto, ruta_local, nombre)
    return nombre, donde


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
        "• /lista — ver los archivos del proyecto\n\n"
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


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    texto += f"\n🗂 Repositorio: {GITHUB_REPO}"
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
        await responder(aviso, f"⬆️ Subiendo a GitHub ({mb(os.path.getsize(res.ruta))})…")
        nombre, donde = await guardar(res.ruta, etiqueta or res.titulo)
        await responder(aviso, texto_ok(nombre, donde, res.ruta))
    except downloader.BloqueoError as e:
        await responder(aviso, f"{e}\n\nEnlace: {url}")
    except downloader.DescargaError as e:
        await responder(aviso, f"❌ No pude descargar: {e}\n\nEnlace: {url}")
    except GitHubError as e:
        await responder(aviso, f"❌ Se descargó pero falló la subida a GitHub: {e}")
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
        try:
            archivo = await adjunto.get_file()
        except BadRequest as e:
            if "too big" in str(e).lower():
                await responder(aviso, "❌ Telegram no deja a los bots bajar archivos de más "
                                       "de 20 MB. Súbelo a Google Drive y mándame el enlace.")
                return
            raise
        ruta = os.path.join(carpeta, "archivo" + (ext or ".bin"))
        await archivo.download_to_drive(ruta)
        res = await asyncio.to_thread(downloader.normalizar,
                                      downloader.Resultado(ruta, etiqueta))
        await responder(aviso, f"⬆️ Subiendo a GitHub ({mb(os.path.getsize(res.ruta))})…")
        nombre, donde = await guardar(res.ruta, etiqueta)
        await responder(aviso, texto_ok(nombre, donde, res.ruta))
    except GitHubError as e:
        await responder(aviso, f"❌ Falló la subida a GitHub: {e}")
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


# ====================================================================== arranque
async def al_iniciar(app: Application):
    try:
        await asyncio.to_thread(store.check)
        guardado = await asyncio.to_thread(store.leer_estado)
        if guardado.get("proyecto"):
            estado["proyecto"] = guardado["proyecto"]
        aviso = f"🤖 Bot en línea. 📁 Proyecto actual: {estado['proyecto']}"
    except GitHubError as e:
        log.error("Problema con GitHub: %s", e)
        aviso = f"🤖 Bot en línea, pero ⚠️ hay un problema con GitHub:\n{e}"
    log.info(aviso)
    try:
        await app.bot.send_message(ALLOWED_USER_ID, aviso)
    except Exception as e:
        log.warning("No pude escribirte por Telegram (¿ya le diste /start al bot?): %s", e)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(al_iniciar).build()
    yo = filters.User(user_id=ALLOWED_USER_ID)

    app.add_handler(CommandHandler(["start", "ayuda", "help"], cmd_start, filters=yo))
    app.add_handler(CommandHandler("proyecto", cmd_proyecto, filters=yo))
    app.add_handler(CommandHandler("estado", cmd_estado, filters=yo))
    app.add_handler(CommandHandler("lista", cmd_lista, filters=yo))
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
