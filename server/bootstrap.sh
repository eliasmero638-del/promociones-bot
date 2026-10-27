#!/bin/bash
# Instalación en un servidor Ubuntu nuevo (Contabo, Oracle, etc.):
#   curl -sL https://raw.githubusercontent.com/eliasmero638-del/promociones-bot/clipero/server/bootstrap.sh | bash
set -e
export DEBIAN_FRONTEND=noninteractive
echo "== Instalando el Clipero (5-10 min la primera vez) =="
apt-get update -qq && apt-get install -y -qq git >/dev/null
if [ -d /opt/clipero/.git ]; then cd /opt/clipero && git fetch -q --depth 1 origin clipero && git reset -q --hard origin/clipero
else git clone -q --depth 1 -b clipero https://github.com/eliasmero638-del/promociones-bot /opt/clipero; fi
bash /opt/clipero/server/install.sh
echo
echo "==============================================="
echo " Clipero instalado."
echo " Siguiente paso: escribe   clipero token     y pega el token de tu bot."
echo "==============================================="
