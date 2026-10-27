#!/data/data/com.termux/files/usr/bin/bash
# Graba el en vivo de La Casa 593 desde el teléfono y lo sube al servidor.
S=173.249.44.95; P=443; D=$HOME/clipero; C=$D/cookies.txt
CANAL=https://www.youtube.com/@LaCasa593EnVivo/streams
SSH="ssh -p $P -o BatchMode=yes -o ServerAliveInterval=30 -o ConnectTimeout=20"
YT="yt-dlp --cookies $C --no-warnings --js-runtimes node"
log() { echo "$(date +%H:%M:%S) $*"; }
mkdir -p $D/rec $D/chat

subir() {
  while true; do
    ls -1 $D/rec/*.ts 2>/dev/null | sort | head -n -1 | xargs -r -n1 basename > $D/listos.txt
    if [ -s $D/listos.txt ]; then
      rsync -a --remove-source-files -e "$SSH" --files-from=$D/listos.txt $D/rec/ root@$S:/var/lib/clipero/rec/ \
        && log "subidos $(wc -l < $D/listos.txt) pedazos" || log "error subiendo"
    fi
    rsync -a -e "$SSH" $D/chat/ root@$S:/var/lib/clipero/chat/ 2>/dev/null
    G=false; pgrep -f segment_time >/dev/null && G=true
    printf '{"video":"%s","titulo":"%s","grabando":%s,"hora":%s}\n' "$(cat $D/vid.txt 2>/dev/null)" \
      "$(cat $D/tit.txt 2>/dev/null | tr -d '"\\')" "$G" "$(date +%s)" > $D/estado.json
    rsync -e "$SSH" $D/estado.json root@$S:/var/lib/clipero/remoto.json 2>/dev/null
    find $D/chat -mtime +1 -delete 2>/dev/null
    sleep 20
  done
}
subir &

while true; do
  L=$($YT --flat-playlist --playlist-end 6 --print "%(id)s|%(live_status)s|%(title)s" "$CANAL" 2>>$D/yt.log | grep '|is_live|' | head -1)
  VID=${L%%|*}; TIT=${L##*|}
  if [ -z "$VID" ]; then log "no hay en vivo ahora, reviso en 2 min"; sleep 120; continue; fi
  echo "$VID" > $D/vid.txt; echo "$TIT" > $D/tit.txt
  log "grabando $VID $TIT"
  $YT --skip-download --write-subs --sub-langs live_chat -o "$D/chat/$VID" "https://www.youtube.com/watch?v=$VID" >/dev/null 2>>$D/yt.log &
  CH=$!
  $YT -f "best[height<=480]/best[height<=720]/best" --hls-use-mpegts -o - "https://www.youtube.com/watch?v=$VID" 2>>$D/yt.log \
    | TZ=UTC ffmpeg -v error -i pipe:0 -map 0:v:0? -map 0:a:0? -c copy -f segment -segment_time 120 \
      -segment_format mpegts -reset_timestamps 1 -strftime 1 "$D/rec/%Y%m%d_%H%M%S.ts"
  kill $CH 2>/dev/null
  log "el en vivo se cortó o terminó; busco de nuevo"
  tail -n 2 $D/yt.log
  sleep 15
done
