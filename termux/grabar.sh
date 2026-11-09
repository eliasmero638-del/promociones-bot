#!/data/data/com.termux/files/usr/bin/bash
# Graba el en vivo del reality desde el teléfono y lo sube al servidor. Se actualiza solo desde GitHub.
S=173.249.44.95; P=443; D=$HOME/clipero; C=$D/cookies.txt
# Revisa estos canales en orden y graba el primero que esté EN VIVO. La Mansión VIP 2 va primero:
# si se está grabando La Casa 593 y empieza La Mansión, cambia sola.
CANALES="https://www.youtube.com/@hotspanishvlogs/streams https://www.youtube.com/@LaCasa593EnVivo/streams"
PRIMERO=${CANALES%% *}
URL=https://raw.githubusercontent.com/eliasmero638-del/promociones-bot/clipero/termux/grabar.sh
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
    printf '{"video":"%s","titulo":"%s","canal":"%s","grabando":%s,"hora":%s}\n' "$(cat $D/vid.txt 2>/dev/null)" \
      "$(cat $D/tit.txt 2>/dev/null | tr -d '"\\')" "$(cat $D/canal.txt 2>/dev/null)" "$G" "$(date +%s)" > $D/estado.json
    rsync -e "$SSH" $D/estado.json root@$S:/var/lib/clipero/remoto.json 2>/dev/null
    find $D/chat -mtime +1 -delete 2>/dev/null
    sleep 20
  done
}
subir &
SP=$!

# Videos que pide el servidor para la edición de Ridmer (YouTube bloquea al servidor; el teléfono sí puede bajarlos)
videos() {
  mkdir -p $D/vped $D/vlisto $D/vhecho
  while true; do
    rsync -a --delete -e "$SSH" root@$S:/var/lib/clipero/pedidos_video/ $D/vped/ 2>/dev/null
    for f in $D/vped/*.txt; do
      [ -e "$f" ] || continue
      ID=$(basename $f .txt)
      [ -e $D/vhecho/$ID ] && continue
      read U A B < $f
      log "bajando video pedido $ID ($A-$B s)"
      rm -f $D/vlisto/$ID.*
      timeout 900 $YT -q --no-playlist --download-sections "*$A-$B" -f "bv*[height<=720]+ba/b[height<=720]/b" \
        --merge-output-format mp4 -o "$D/vlisto/$ID.%(ext)s" "$U" 2>>$D/yt.log
      F=$(ls $D/vlisto/$ID.* 2>/dev/null | head -1)
      if [ -n "$F" ]; then
        rsync -a -e "$SSH" "$F" root@$S:/var/lib/clipero/videos_listos/$ID.mp4 && log "video $ID subido"
      else
        echo falla > $D/vlisto/$ID.falla
        rsync -a -e "$SSH" $D/vlisto/$ID.falla root@$S:/var/lib/clipero/videos_listos/ 2>/dev/null; log "video $ID falló"
      fi
      touch $D/vhecho/$ID; rm -f $D/vlisto/$ID.*
    done
    find $D/vhecho -mtime +3 -delete 2>/dev/null
    sleep 30
  done
}
videos &
VP=$!

en_vivo() { $YT --flat-playlist --playlist-end 6 --print "%(id)s|%(live_status)s|%(title)s" "$1" 2>>$D/yt.log | grep '|is_live|' | head -1; }

actualizar() {
  N=$(curl -sL "$URL")
  if echo "$N" | grep -q segment_time && [ "$N" != "$(cat $D/grabar.sh 2>/dev/null)" ]; then
    echo "$N" > $D/grabar.sh; log "grabador actualizado, reinicio"
    kill $SP $VP 2>/dev/null; exec bash $D/grabar.sh
  fi
}

while true; do
  actualizar
  L=""
  for CANAL in $CANALES; do
    L=$(en_vivo "$CANAL")
    [ -n "$L" ] && break
  done
  VID=${L%%|*}; TIT=${L##*|}
  if [ -z "$VID" ]; then log "no hay en vivo ahora, reviso en 2 min"; sleep 120; continue; fi
  echo "$VID" > $D/vid.txt; echo "$TIT" > $D/tit.txt; echo "${CANAL##*@}" > $D/canal.txt
  log "grabando $VID $TIT"
  $YT --skip-download --write-subs --sub-langs live_chat -o "$D/chat/$VID" "https://www.youtube.com/watch?v=$VID" >/dev/null 2>>$D/yt.log &
  CH=$!
  U=$($YT -f "bv*[height<=480]+ba/b[height<=480]/bv*+ba/b" -g "https://www.youtube.com/watch?v=$VID" 2>>$D/yt.log)
  V=$(echo "$U" | sed -n 1p); A=$(echo "$U" | sed -n 2p)
  if [ -z "$V" ]; then log "no pude obtener el video, reintento en 1 min"; tail -n 2 $D/yt.log; kill $CH 2>/dev/null; sleep 60; continue; fi
  if [ -n "$A" ]; then IN="-i $V -i $A -map 0:v:0 -map 1:a:0"; else IN="-i $V -map 0:v:0? -map 0:a:0?"; fi
  log "grabando video+audio"
  TZ=UTC ffmpeg -v error -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 $IN -c copy -f segment -segment_time 120 \
    -segment_format mpegts -reset_timestamps 1 -strftime 1 "$D/rec/%Y%m%d_%H%M%S.ts" 2>>$D/ffmpeg.log &
  FF=$!
  n=0
  while kill -0 $FF 2>/dev/null; do
    sleep 20; n=$((n + 1))
    if [ $((n % 15)) -eq 0 ]; then                      # cada 5 min
      if [ "$CANAL" != "$PRIMERO" ] && [ -n "$(en_vivo "$PRIMERO")" ]; then
        log "empezó el en vivo principal, cambio de canal"; kill $FF 2>/dev/null
      fi
      [ $((n % 90)) -eq 0 ] && N=$(curl -sL "$URL") && echo "$N" | grep -q segment_time && [ "$N" != "$(cat $D/grabar.sh)" ] && kill $FF 2>/dev/null
    fi
  done
  wait $FF 2>/dev/null
  kill $CH 2>/dev/null
  log "la grabación se detuvo; vuelvo a conectar"
  tail -n 2 $D/ffmpeg.log
  sleep 15
done
