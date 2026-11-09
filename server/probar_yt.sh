#!/bin/bash
# Prueba si el SERVIDOR puede grabar un en vivo de YouTube (sin el teléfono). Uso: bash /opt/clipero/server/probar_yt.sh
D=/var/lib/clipero; Y="$D/venv/bin/python -m yt_dlp --no-warnings --cookies $D/secrets/cookies.txt"
echo "== 1) ¿La Mansión está en vivo? =="
L=$($Y --flat-playlist --playlist-end 6 --print "%(id)s %(live_status)s %(title)s" https://www.youtube.com/@hotspanishvlogs/streams 2>&1 | head -6)
echo "$L"
VID=$(echo "$L" | grep ' is_live ' | head -1 | cut -d' ' -f1)
if [ -z "$VID" ]; then
  echo "(La Mansión aún no está en vivo; pruebo con otro en vivo de YouTube que siempre está prendido)"
  VID=$($Y --flat-playlist --playlist-end 6 --print "%(id)s %(live_status)s" https://www.youtube.com/@LofiGirl/streams 2>/dev/null | grep ' is_live' | head -1 | cut -d' ' -f1)
fi
echo "== 2) Intento grabar 15 segundos de $VID =="
rm -f /tmp/prueba_yt.ts
timeout 120 $Y -f "best[height<=720]/best" --hls-use-mpegts -o - "https://www.youtube.com/watch?v=$VID" 2>/tmp/prueba_yt.log | timeout 25 ffmpeg -v error -i pipe:0 -t 15 -c copy -y /tmp/prueba_yt.ts 2>/dev/null
T=$(stat -c %s /tmp/prueba_yt.ts 2>/dev/null || echo 0)
if [ "$T" -gt 300000 ]; then echo "✅ EL SERVIDOR SÍ PUEDE GRABAR ($((T / 1024)) KB). Esta noche graba La Mansión solo."
else echo "❌ YouTube NO deja grabar al servidor. Motivo:"; tail -n 3 /tmp/prueba_yt.log; fi
