#!/bin/bash
# Prueba rápida en el servidor: instala lo básico y verifica si YouTube deja descargar La Casa 593
# con las cookies de la cuenta secundaria (/var/lib/clipero/secrets/cookies.txt).
set -u
DATA=/var/lib/clipero; mkdir -p $DATA/secrets $DATA/prueba; chmod 700 $DATA/secrets
export DEBIAN_FRONTEND=noninteractive
echo "== Instalando herramientas (2-4 min) =="
apt-get update -qq && apt-get install -y -qq git ffmpeg python3-venv unzip curl >/dev/null
[ -d $DATA/venv ] || python3 -m venv $DATA/venv
$DATA/venv/bin/pip install -q -U pip yt-dlp requests
if ! command -v deno >/dev/null; then curl -fsSL https://deno.land/install.sh | sh -s -- -y >/dev/null 2>&1; ln -sf /root/.deno/bin/deno /usr/local/bin/deno; fi
C=$DATA/secrets/cookies.txt
if [ ! -s "$C" ]; then
  [ -s /root/cookies.txt ] && mv /root/cookies.txt "$C"
fi
if [ ! -s "$C" ]; then echo "FALTA el archivo de cookies. Súbelo como /root/cookies.txt y vuelve a correr esto."; exit 1; fi
chmod 600 "$C"
Y="$DATA/venv/bin/yt-dlp --cookies $C --no-warnings"
echo "== Buscando el en vivo actual de La Casa 593 =="
VID=$($Y --flat-playlist --playlist-end 5 --print "%(id)s %(live_status)s" https://www.youtube.com/@LaCasa593EnVivo/streams 2>/dev/null | awk '$2=="is_live"{print $1; exit}')
[ -z "$VID" ] && VID=$($Y --flat-playlist --playlist-end 1 --print "%(id)s" https://www.youtube.com/@LaCasa593EnVivo/streams 2>/dev/null)
echo "Video: $VID"
echo "== Probando descarga de 30 segundos =="
cd $DATA/prueba && rm -f prueba.*
$Y -f "bv*[height<=720]+ba/b[height<=720]/b" --merge-output-format mp4 --download-sections "*0:00-0:30" \
   -o "prueba.%(ext)s" "https://www.youtube.com/watch?v=$VID" > log.txt 2>&1
if [ -s prueba.mp4 ]; then
  echo "======================================"
  echo " ✅ FUNCIONA: YouTube dejó descargar. ($(du -h prueba.mp4 | cut -f1))"
  echo "======================================"
else
  echo "======================================"
  echo " ❌ NO FUNCIONÓ. Últimas líneas del error:"
  grep -E "ERROR|WARNING" log.txt | tail -4
  echo "======================================"
fi
