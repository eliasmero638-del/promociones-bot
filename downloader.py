"""Descarga de archivos desde enlaces.

descargar(url, carpeta) -> Resultado(ruta, titulo)

Lanza DescargaError con un mensaje claro para el usuario si falla, o
BloqueoError si la plataforma bloqueó la descarga (YouTube, TikTok...).
"""

import base64
import glob
import html
import json
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
from dataclasses import dataclass

import requests
import yt_dlp
from PIL import Image

log = logging.getLogger(__name__)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}

EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff",
              ".avif", ".heic", ".svg"}
EXT_VIDEO = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".3gp", ".flv", ".wmv"}
EXT_AUDIO = {".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".wav", ".flac"}

PLATAFORMAS_YTDLP = ("youtube.com", "youtu.be", "tiktok.com", "instagram.com",
                     "facebook.com", "fb.watch", "fb.com", "x.com", "twitter.com",
                     "vimeo.com", "dailymotion.com")

PISTAS_BLOQUEO = (
    "sign in to confirm", "confirm you’re not a bot", "confirm you're not a bot",
    "login required", "log in", "cookies", "rate-limit", "rate limit", "429",
    "403", "ip address is blocked", "your ip", "blocked", "requested content is not available",
    "private video", "use --cookies", "authentication", "not available in your country",
)


class DescargaError(Exception):
    pass


class BloqueoError(DescargaError):
    pass


@dataclass
class Resultado:
    ruta: str
    titulo: str


# ====================================================================== API
def descargar(url: str, carpeta: str, cookies: str | None = None) -> Resultado:
    url = url.strip()
    host = urllib.parse.urlparse(url).netloc.lower()

    if any(p in host for p in PLATAFORMAS_YTDLP):
        try:
            return normalizar(_con_cookies(url, carpeta, cookies))
        except BloqueoError:
            raise
        except DescargaError as error:
            # Publicaciones de Instagram/Facebook que solo son fotos
            es_red_fotos = any(s in host for s in ("instagram", "facebook", "fb."))
            media = _media_de_url(url) if es_red_fotos else None
            if not media:
                raise error
            return normalizar(_directo(media, carpeta))

    if "pexels.com" in host:
        return normalizar(_pexels(url, carpeta))
    if "pixabay.com" in host:
        return normalizar(_pixabay(url, carpeta))
    if "wikipedia.org" in host or "wikimedia.org" in host:
        return normalizar(_wikipedia(url, carpeta))
    if "drive.google.com" in host or "docs.google.com" in host:
        return normalizar(_drive(url, carpeta))

    # Enlace directo o página desconocida
    try:
        return normalizar(_directo(url, carpeta))
    except _NoEsArchivo as pagina:
        # Es una página web: probar yt-dlp y si no, la imagen/video principal
        try:
            return normalizar(_ytdlp(url, carpeta, None))
        except DescargaError:
            media = _media_de_pagina(pagina.html, url)
            if not media:
                raise DescargaError("El enlace es una página web y no encontré "
                                    "ningún video o imagen para descargar.")
            return normalizar(_directo(media, carpeta, titulo=pagina.titulo))


# ====================================================================== yt-dlp
def _con_cookies(url, carpeta, cookies):
    try:
        return _ytdlp(url, carpeta, None)
    except BloqueoError as e:
        if not cookies:
            raise BloqueoError(
                f"🚫 {_plataforma(url)} bloqueó la descarga.\n"
                f"Detalle: {e}\n\n"
                "Solución: configura la variable YTDLP_COOKIES en Railway con tus "
                "cookies (archivo cookies.txt) y vuelve a mandar el enlace. "
                "Mira la guía en el README, sección «Cookies».")
        log.info("Bloqueado sin cookies, reintentando con cookies: %s", e)
    except DescargaError:
        if not cookies:
            raise
    try:
        return _ytdlp(url, carpeta, cookies)
    except BloqueoError as e:
        raise BloqueoError(
            f"🚫 {_plataforma(url)} bloqueó la descarga incluso usando tus cookies.\n"
            f"Detalle: {e}\n\n"
            "Puede que las cookies hayan vencido: expórtalas de nuevo (con la sesión "
            "iniciada) y actualiza YTDLP_COOKIES en Railway.")


def _ytdlp(url, carpeta, cookies):
    opciones = {
        "outtmpl": os.path.join(carpeta, "%(title).80B [%(id)s].%(ext)s"),
        "format": "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "http_headers": {"User-Agent": UA},
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
    }
    cookie_file = None
    if cookies:
        cookie_file = _archivo_cookies(cookies)
        opciones["cookiefile"] = cookie_file
    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        texto = _limpiar(str(e))
        if any(p in texto.lower() for p in PISTAS_BLOQUEO):
            raise BloqueoError(texto)
        raise DescargaError(texto)
    finally:
        if cookie_file:
            os.unlink(cookie_file)

    if info.get("_type") == "playlist" and info.get("entries"):
        info = next(e for e in info["entries"] if e)
    archivos = [f for f in glob.glob(os.path.join(carpeta, "*"))
                if not f.endswith((".part", ".ytdl", ".txt"))]
    if not archivos:
        raise DescargaError("yt-dlp terminó pero no generó ningún archivo.")
    ruta = max(archivos, key=os.path.getsize)
    return Resultado(ruta, info.get("title") or info.get("id") or "video")


def _archivo_cookies(valor: str) -> str:
    texto = valor.strip()
    if "\t" not in texto:
        try:  # Se permite pegar el archivo codificado en base64
            decodificado = base64.b64decode(texto, validate=True).decode("utf-8")
            if "\t" in decodificado:
                texto = decodificado
        except Exception:
            pass
    # Los tabuladores/saltos de línea pueden llegar como "\t" y "\n" literales
    if "\t" not in texto and "\\t" in texto:
        texto = texto.replace("\\n", "\n").replace("\\t", "\t")
    if not texto.startswith("# "):
        texto = "# Netscape HTTP Cookie File\n" + texto
    fd, ruta = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as fh:
        fh.write(texto + "\n")
    return ruta


def _plataforma(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    for nombre, clave in (("YouTube", "youtu"), ("TikTok", "tiktok"),
                          ("Instagram", "instagram"), ("Facebook", "fb"),
                          ("Facebook", "facebook")):
        if clave in host:
            return nombre
    return host


def _limpiar(texto):
    texto = re.sub(r"\x1b\[[0-9;]*m", "", texto)
    return texto.replace("ERROR: ", "").strip()[:400]


# ====================================================================== sitios
def _pexels(url, carpeta):
    m = re.search(r"/(photo|video|foto)s?/(?:[^/]*?-)?(\d+)/?", url)
    if not m:
        m2 = re.search(r"(\d{4,})", url)
        if not m2:
            raise DescargaError("No reconozco este enlace de Pexels.")
        tipo, ident = ("video" if "video" in url else "photo"), m2.group(1)
    else:
        tipo, ident = m.group(1), m.group(2)
    titulo = _titulo_slug(url) or f"pexels_{ident}"
    if tipo == "video":
        for u in (f"https://www.pexels.com/download/video/{ident}/",):
            try:
                return _directo(u, carpeta, titulo=titulo)
            except DescargaError:
                pass
        raise DescargaError("Pexels no me dejó descargar el video. Prueba con el "
                            "enlace directo del botón «Descargar».")
    return _directo(f"https://images.pexels.com/photos/{ident}/pexels-photo-{ident}.jpeg",
                    carpeta, titulo=titulo)


def _pixabay(url, carpeta):
    r = _get(url)
    pagina = r.text
    titulo = _titulo_slug(url) or "pixabay"
    candidatos = []
    # Datos estructurados (JSON-LD)
    for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                             pagina, re.S):
        try:
            datos = json.loads(bloque)
        except Exception:
            continue
        for d in datos if isinstance(datos, list) else [datos]:
            for k in ("contentUrl", "contentURL"):
                if isinstance(d, dict) and d.get(k):
                    candidatos.append(d[k])
    candidatos += re.findall(r'https://cdn\.pixabay\.com/video/[^"\'\s]+?\.mp4', pagina)
    candidatos += re.findall(r'https://cdn\.pixabay\.com/photo/[^"\'\s]+?_1280\.(?:jpg|png)',
                             pagina)
    media = _media_de_pagina(pagina, url)
    if media:
        candidatos.append(media)
    if not candidatos:
        raise DescargaError("No encontré el archivo en la página de Pixabay "
                            "(puede estar bloqueando el acceso).")
    # Prioriza la versión más grande de los videos
    videos = [c for c in candidatos if ".mp4" in c]
    elegido = (sorted(videos, key=lambda v: ("large" in v, "medium" in v))[-1]
               if videos else candidatos[0])
    return _directo(html.unescape(elegido), carpeta, titulo=titulo)


def _wikipedia(url, carpeta):
    p = urllib.parse.urlparse(url)
    if "upload.wikimedia.org" in p.netloc:
        return _directo(url, carpeta)
    ruta = urllib.parse.unquote(p.path)
    fragmento = urllib.parse.unquote(p.fragment)
    api = f"{p.scheme}://{p.netloc}/w/api.php"
    archivo = None
    for texto in (fragmento, ruta):
        m = re.search(r"((?:File|Archivo|Fichier|Datei|Ficheiro|Image|Imagen):[^/?#]+)", texto)
        if m:
            archivo = "File:" + m.group(1).split(":", 1)[1]
            break
    if archivo:
        datos = _get(api, params={"action": "query", "titles": archivo, "prop": "imageinfo",
                                  "iiprop": "url", "format": "json"}).json()
        for pag in datos.get("query", {}).get("pages", {}).values():
            info = pag.get("imageinfo")
            if info:
                return _directo(info[0]["url"], carpeta,
                                titulo=os.path.splitext(archivo[5:])[0])
        raise DescargaError(f"No encontré el archivo {archivo} en Wikipedia.")
    # Artículo: descargar la imagen principal en tamaño original
    articulo = ruta.rsplit("/wiki/", 1)[-1]
    datos = _get(api, params={"action": "query", "titles": articulo, "prop": "pageimages",
                              "piprop": "original", "format": "json",
                              "redirects": 1}).json()
    for pag in datos.get("query", {}).get("pages", {}).values():
        orig = pag.get("original", {}).get("source")
        if orig:
            return _directo(orig, carpeta, titulo=articulo)
    raise DescargaError("Ese artículo de Wikipedia no tiene imagen principal. "
                        "Abre la imagen que quieres y manda ese enlace.")


def _drive(url, carpeta):
    m = (re.search(r"/d/([A-Za-z0-9_-]{10,})", url)
         or re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", url))
    if not m:
        raise DescargaError("No reconozco este enlace de Google Drive "
                            "(las carpetas completas no están soportadas).")
    import gdown
    destino = os.path.join(carpeta, "")
    try:
        salida = gdown.download(id=m.group(1), output=destino, quiet=True)
    except Exception as e:
        salida = None
        log.warning("gdown falló: %s", e)
    if not salida or not os.path.exists(salida):
        raise DescargaError("Google Drive no dejó descargar el archivo. Revisa que "
                            "esté compartido como «Cualquier persona con el enlace».")
    return Resultado(salida, os.path.splitext(os.path.basename(salida))[0])


# ====================================================================== genérico
class _NoEsArchivo(DescargaError):
    def __init__(self, html_, titulo):
        super().__init__("Es una página web")
        self.html = html_
        self.titulo = titulo


def _get(url, **kw):
    try:
        r = requests.get(url, headers=HEADERS, timeout=60, **kw)
    except requests.RequestException as e:
        raise DescargaError(f"No pude conectar: {e}")
    if r.status_code >= 400:
        raise DescargaError(f"El servidor respondió con error {r.status_code}.")
    return r


def _directo(url, carpeta, titulo=None):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=60,
                         allow_redirects=True)
    except requests.RequestException as e:
        raise DescargaError(f"No pude conectar: {e}")
    if r.status_code >= 400:
        raise DescargaError(f"El servidor respondió con error {r.status_code}.")
    tipo = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if tipo in ("text/html", "application/xhtml+xml"):
        texto = r.text[:2_000_000]
        m = re.search(r"<title[^>]*>(.*?)</title>", texto, re.S | re.I)
        raise _NoEsArchivo(texto, html.unescape(m.group(1)).strip() if m else None)

    nombre = _nombre_de_respuesta(r)
    base, ext = os.path.splitext(nombre)
    if not ext or len(ext) > 6:
        ext = mimetypes.guess_extension(tipo) or ".bin"
    ruta = os.path.join(carpeta, f"descarga{ext.lower()}")
    with open(ruta, "wb") as fh:
        for trozo in r.iter_content(1024 * 1024):
            fh.write(trozo)
    if os.path.getsize(ruta) == 0:
        raise DescargaError("El archivo descargado está vacío.")
    return Resultado(ruta, titulo or base or "archivo")


def _nombre_de_respuesta(r):
    cd = r.headers.get("Content-Disposition") or ""
    m = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", cd, re.I) or \
        re.search(r'filename="?([^";]+)"?', cd, re.I)
    if m:
        return urllib.parse.unquote(m.group(1).strip())
    return urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(r.url).path)) or "archivo"


def _media_de_pagina(pagina, url_base):
    for prop in ("og:video:secure_url", "og:video:url", "og:video", "og:image:secure_url",
                 "og:image", "twitter:image"):
        m = (re.search(rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]+content=["\']([^"\']+)',
                       pagina, re.I)
             or re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{prop}["\']',
                          pagina, re.I))
        if m:
            return urllib.parse.urljoin(url_base, html.unescape(m.group(1)))
    return None


def _media_de_url(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        return _media_de_pagina(r.text, url) if r.ok else None
    except requests.RequestException:
        return None


def _titulo_slug(url):
    partes = [p for p in urllib.parse.urlparse(url).path.split("/") if p]
    for p in reversed(partes):
        p = re.sub(r"-?\d+$", "", p)
        if p and p not in ("photo", "photos", "video", "videos", "es", "en", "es-es"):
            return p
    return None


# ====================================================================== formatos
def normalizar(res: Resultado) -> Resultado:
    """Deja los videos en MP4 y las imágenes en JPG/PNG."""
    ruta = res.ruta
    ext = os.path.splitext(ruta)[1].lower()
    tipo = _tipo_real(ruta, ext)

    if tipo == "imagen" and ext not in (".jpg", ".jpeg", ".png"):
        if ext == ".svg":
            return res
        if ext == ".gif" and _es_animado(ruta):
            return Resultado(_a_mp4(ruta), res.titulo)
        return Resultado(_a_jpg_png(ruta), res.titulo)
    if tipo == "imagen" and ext == ".jpeg":
        nueva = ruta[:-5] + ".jpg"
        os.rename(ruta, nueva)
        return Resultado(nueva, res.titulo)
    if tipo == "video" and ext != ".mp4":
        return Resultado(_a_mp4(ruta), res.titulo)
    return res


def _tipo_real(ruta, ext):
    if ext in EXT_IMAGEN:
        return "imagen"
    if ext in EXT_VIDEO:
        return "video"
    if ext in EXT_AUDIO:
        return "audio"
    try:
        with Image.open(ruta) as im:
            im.verify()
        return "imagen"
    except Exception:
        return "otro"


def _es_animado(ruta):
    try:
        with Image.open(ruta) as im:
            return getattr(im, "is_animated", False)
    except Exception:
        return False


def _a_jpg_png(ruta):
    try:
        with Image.open(ruta) as im:
            transparente = im.mode in ("RGBA", "LA", "P") and (
                im.mode != "P" or "transparency" in im.info)
            base = os.path.splitext(ruta)[0]
            if transparente:
                destino = base + ".png"
                im.convert("RGBA").save(destino, "PNG")
            else:
                destino = base + ".jpg"
                im.convert("RGB").save(destino, "JPEG", quality=95)
    except Exception as e:
        log.warning("No pude convertir la imagen %s: %s", ruta, e)
        return ruta
    if destino != ruta:
        os.unlink(ruta)
    return destino


def _a_mp4(ruta):
    destino = os.path.splitext(ruta)[0] + ".conv.mp4"
    # Primero intentar sin recodificar (rápido, sin pérdida); si no, recodificar.
    for args in (["-c", "copy"],
                 ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                  "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                  "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"]):
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ruta, *args,
                            "-movflags", "+faststart", destino],
                           capture_output=True)
        if r.returncode == 0 and os.path.getsize(destino) > 0:
            os.unlink(ruta)
            final = destino.replace(".conv.mp4", ".mp4")
            shutil.move(destino, final)
            return final
    log.warning("ffmpeg no pudo convertir %s: %s", ruta, r.stderr[-300:])
    return ruta
