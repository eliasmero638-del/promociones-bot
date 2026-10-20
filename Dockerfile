FROM python:3.12-slim

# ffmpeg: une audio+video y convierte a MP4. git: sube archivos grandes al repo
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Deno: yt-dlp lo necesita para resolver los videos de YouTube
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app
COPY requirements.txt .
# yt-dlp se actualiza en cada despliegue: YouTube/TikTok cambian seguido
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -U "yt-dlp[default]"

COPY *.py ./

ENV PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]
