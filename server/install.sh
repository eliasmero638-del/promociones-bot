#!/bin/bash
# Instalador / actualizador del Clipero. Se puede correr muchas veces sin problema.
set -e
APP=/opt/clipero
DATA=/var/lib/clipero
mkdir -p $DATA/clips $DATA/rec $DATA/secrets
chmod 700 $DATA/secrets
export DEBIAN_FRONTEND=noninteractive
if [ ! -f $DATA/.paquetes ]; then
  apt-get update -qq
  apt-get install -y -qq git ffmpeg python3-venv python3-pip fonts-dejavu-core curl unzip >/dev/null
  touch $DATA/.paquetes
fi
if [ ! -d $DATA/venv ]; then python3 -m venv $DATA/venv; fi
$DATA/venv/bin/pip install -q -U pip
$DATA/venv/bin/pip install -q -U -r $APP/app/requirements.txt
# yt-dlp necesita un motor de JavaScript para YouTube
if ! command -v deno >/dev/null; then curl -fsSL https://deno.land/install.sh | sh -s -- -y >/dev/null 2>&1; ln -sf /root/.deno/bin/deno /usr/local/bin/deno; fi
# cookies subidas a /root
[ -s /root/cookies.txt ] && mv /root/cookies.txt $DATA/secrets/cookies.txt && chmod 600 $DATA/secrets/cookies.txt
ln -sf $APP/server/clipero.sh /usr/local/bin/clipero
# Servicio principal
cat > /etc/systemd/system/clipero.service <<UNIT
[Unit]
Description=Clipero
After=network-online.target
[Service]
WorkingDirectory=$APP/app
Environment=CLIPERO_DATA=$DATA
ExecStart=$DATA/venv/bin/python -u $APP/app/main.py
Restart=always
RestartSec=20
[Install]
WantedBy=multi-user.target
UNIT
# Actualizador: cada 5 minutos baja cambios de GitHub
cat > /etc/systemd/system/clipero-update.service <<UNIT
[Unit]
Description=Actualizar Clipero
[Service]
Type=oneshot
ExecStart=/bin/bash $APP/server/update.sh
UNIT
cat > /etc/systemd/system/clipero-update.timer <<UNIT
[Unit]
Description=Actualizar Clipero cada 5 min
[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now clipero-update.timer
systemctl enable clipero.service
systemctl restart clipero.service
echo "Clipero instalado"
