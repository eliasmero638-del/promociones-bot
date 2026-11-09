#!/bin/bash
# Prueba varias formas de pedirle el en vivo a YouTube desde el servidor.
D=/var/lib/clipero; P="$D/venv/bin/python -m yt_dlp"
$D/venv/bin/pip install -q -U "yt-dlp[default]" >/dev/null 2>&1
echo "yt-dlp $($P --version)"
VID=$($P --no-warnings --flat-playlist --playlist-end 6 --print "%(id)s %(live_status)s" https://www.youtube.com/@hotspanishvlogs/streams 2>/dev/null | grep ' is_live' | head -1 | cut -d' ' -f1)
echo "en vivo: $VID"
for CK in con sin; do
  for CL in default tv web_safari mweb ios android_vr web_embedded tv_simply; do
    A="--no-warnings --extractor-args youtube:player_client=$CL"
    [ "$CK" = con ] && A="$A --cookies $D/secrets/cookies.txt"
    U=$(timeout 60 $P $A -f "best[height<=720]/best" -g "https://www.youtube.com/watch?v=$VID" 2>/tmp/yt2.log | head -1)
    if [ -n "$U" ]; then echo "✅ $CK cookies · $CL"; else echo "❌ $CK cookies · $CL · $(grep -o 'ERROR.\{0,70\}' /tmp/yt2.log | head -1)"; fi
  done
done
