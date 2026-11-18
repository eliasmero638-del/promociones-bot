#!/bin/bash
# 18-nov: clona la voz del dueño con Chatterbox Multilingual (licencia MIT, se puede usar en videos monetizados).
# Corre fuera del servicio (systemd-run) para que un reinicio del Clipero no lo corte.
# Uso: voz_clon.sh AUDIO_DEL_DUEÑO
set -u
APP=/opt/clipero; DATA=/var/lib/clipero; V=$DATA/voz_propia; VENV=/opt/vozclon
mkdir -p $V; LOG=$V/log.txt; exec >>$LOG 2>&1
echo "=== $(date) inicio"
avisa() { $DATA/venv/bin/python $APP/tools/voz_aviso.py "$@"; }
# 1) referencia: 3 trozos limpios de tu audio (sin los silencios del inicio), 24 kHz mono, volumen parejo
ffmpeg -v error -y -i "$1" -ac 1 -ar 24000 -af "silenceremove=start_periods=1:start_threshold=-40dB,loudnorm=I=-18:TP=-2" $V/completo.wav || { avisa error "no pude leer tu audio"; exit 1; }
ffmpeg -v error -y -ss 4 -t 14 -i $V/completo.wav $V/referencia.wav
avisa texto "🎙️ Recibí tu audio. Instalando el programa de clonar voz en el servidor (la primera vez tarda 15–30 min)…"
# 2) instalar (solo la primera vez): Python 3.11 aparte + Chatterbox con PyTorch para CPU
if [ ! -x $VENV/bin/python ] || ! $VENV/bin/python -c "import chatterbox" 2>/dev/null; then
  command -v uv >/dev/null || [ -x /root/.local/bin/uv ] || curl -LsSf https://astral.sh/uv/install.sh | sh
  UV=$(command -v uv || echo /root/.local/bin/uv)
  $UV venv -q --python 3.11 $VENV || { avisa error "no pude crear el entorno de Python"; exit 1; }
  $UV pip install -q --python $VENV/bin/python --index-strategy unsafe-best-match \
      --extra-index-url https://download.pytorch.org/whl/cpu chatterbox-tts || { avisa error "no se pudo instalar Chatterbox"; exit 1; }
fi
echo "=== $(date) instalado"
avisa texto "⚙️ Programa instalado. Ahora hago 5 pruebas con tu voz en distintos tonos (misterio, triste, sorpresa, noticia y alegre). Te las mando una por una (unos 5–10 min cada una)…"
# 3) pruebas con varios tonos (el dueño las escucha antes de usar su voz en los videos)
#    tono: archivo|emoción (exaggeration)|cfg (más bajo = más pausado)
for T in "1_misterio|0.5|0.4|🕵️ MISTERIO / SUSPENSO" "2_triste|0.35|0.35|😢 TRISTE" "3_sorpresa|0.85|0.5|😱 SORPRESA" "4_noticia|0.3|0.5|📰 NOTICIA SERIA" "5_alegre|0.7|0.5|😄 ALEGRE / CURIOSIDAD"; do
  IFS='|' read N EX CF ETQ <<< "$T"
  T0=$(date +%s)
  $VENV/bin/python $APP/tools/voz_gen.py $V/referencia.wav $APP/tools/voz_pruebas/$N.txt $V/$N.wav $EX $CF || { avisa error "falló la prueba $N (mira el log)"; continue; }
  ffmpeg -v error -y -i $V/$N.wav -af "loudnorm=I=-16:TP=-1.5" -c:a libmp3lame -b:a 160k $V/$N.mp3
  avisa audio $V/$N.mp3 "🎧 TU VOZ · $ETQ (tardó $(( ($(date +%s)-T0)/60 )) min)"
done
avisa texto "✅ Esas son las pruebas con tu voz clonada. Dile a Claude cuáles te gustan y cuáles no. Todavía NO se usa en los videos."
echo "=== $(date) fin"
