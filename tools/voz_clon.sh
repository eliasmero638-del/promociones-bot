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
avisa texto "⚙️ Programa instalado. Ahora estoy haciendo la prueba con tu voz (unos 10–20 min)…"
# 3) prueba con un guion típico de Ridmer
T0=$(date +%s)
$VENV/bin/python $APP/tools/voz_gen.py $V/referencia.wav $APP/tools/voz_prueba.txt $V/prueba.wav || { avisa error "falló al generar la voz (mira el log)"; exit 1; }
T1=$(date +%s)
ffmpeg -v error -y -i $V/prueba.wav -af "loudnorm=I=-16:TP=-1.5" -c:a libmp3lame -b:a 160k $V/prueba_tu_voz.mp3
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $V/prueba.wav | cut -d. -f1)
avisa audio $V/prueba_tu_voz.mp3 "🎧 PRUEBA CON TU VOZ (clonada). Duración ${DUR}s · tardó $(( (T1-T0)/60 )) min en hacerla. ¿Se parece a ti?"
echo "=== $(date) fin ${DUR}s en $((T1-T0))s"
