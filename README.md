# descargas-bot

Bot de Telegram que descarga enlaces (YouTube, TikTok, Instagram, Facebook, Pexels,
Pixabay, Wikipedia, Google Drive, enlaces directos) o archivos que le mandas, y los
guarda en un repositorio **privado** de GitHub, numerados en orden de llegada.

## Uso

| Mensaje | Qué hace |
|---|---|
| `/proyecto peter_bergmann` | Todo lo que mandes después va a la carpeta `peter_bergmann/` |
| `https://youtu.be/...` | Descarga y guarda como `01_Titulo_del_video.mp4` |
| `R1 https://...` | Guarda como `02_R1.mp4` (el texto antes del enlace es el nombre) |
| Varias líneas con enlaces | Procesa cada uno en orden |
| Foto / video / audio | Lo guarda (si tiene texto al pie, se usa como nombre) |
| `/lista` | Lista los archivos del proyecto actual |
| `/estado` | Proyecto actual y cuántos archivos tiene |

- Archivos de menos de 90 MB → carpeta del proyecto en el repositorio.
- Archivos más grandes → *asset* del Release con el nombre del proyecto
  (pestaña **Releases** del repositorio).
- El proyecto elegido se guarda en `_estado_bot.json` dentro del repo, así que
  sobrevive a los reinicios.
- Telegram no deja a los bots descargar archivos que le mandas de más de 20 MB;
  para esos, súbelos a Google Drive y manda el enlace.

## Variables de entorno (Railway → servicio → Variables)

| Variable | Ejemplo | Para qué |
|---|---|---|
| `TELEGRAM_TOKEN` | `123456:ABC...` | Token que da @BotFather |
| `GITHUB_TOKEN` | `github_pat_...` | Token con permiso de escritura en el repo de material |
| `GITHUB_REPO` | `usuario/ridmer-material` | Repo donde se guardan los archivos |
| `ALLOWED_USER_ID` | `123456789` | Tu ID de Telegram; el bot ignora a cualquier otra persona |
| `GITHUB_BRANCH` | `material` | *(opcional)* Rama donde guardar; si no existe, el bot la crea vacía |
| `YTDLP_COOKIES` | *(opcional)* | Contenido de `cookies.txt` para cuando YouTube/TikTok bloquean |
| `TELEGRAM_API_ID` | *(opcional)* `12345678` | De my.telegram.org. Con esto y el siguiente, los archivos de más de 90 MB te llegan por Telegram (hasta 2 GB) y puedes mandarle al bot archivos de más de 20 MB |
| `TELEGRAM_API_HASH` | *(opcional)* `0123abcd...` | De my.telegram.org |

## Cookies (si YouTube/TikTok/Instagram bloquean)

Los servidores de Railway a veces son bloqueados por YouTube («Sign in to confirm
you're not a bot»). El bot te avisa cuando pasa. Para solucionarlo:

1. En Chrome, instala la extensión **«Get cookies.txt LOCALLY»**.
2. Entra a youtube.com (o tiktok.com / instagram.com) con tu cuenta iniciada.
   Mejor una cuenta secundaria, no la principal.
3. Pulsa la extensión → **Export** → se descarga un `cookies.txt`.
4. Ábrelo con el Bloc de notas, copia todo el texto.
5. Railway → servicio → **Variables** → **New Variable** → nombre `YTDLP_COOKIES`,
   pega el texto como valor → guardar. Railway reinicia el bot solo.
6. Vuelve a mandar el enlace. El bot primero intenta sin cookies y, si lo
   bloquean, reintenta automáticamente con ellas.

Puedes juntar cookies de varios sitios en un mismo texto (una línea por cookie).
Las cookies vencen con el tiempo; si vuelve a bloquear, repite los pasos.

## Desarrollo

```
pip install -r requirements.txt
TELEGRAM_TOKEN=... GITHUB_TOKEN=... GITHUB_REPO=... ALLOWED_USER_ID=... python bot.py
```

El `Dockerfile` instala ffmpeg (para juntar audio y video y convertir a MP4) y
Deno (yt-dlp lo necesita para YouTube). yt-dlp se actualiza en cada despliegue.
