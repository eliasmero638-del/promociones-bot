#!/bin/bash
# Baja la última versión y la instala. Si una instalación falla, la vuelve a intentar en la siguiente vuelta
# (antes solo instalaba cuando cambiaba el código, y si fallaba una vez se quedaba en la versión vieja).
APP=/opt/clipero
M=/var/lib/clipero/.instalado
cd $APP || exit 0
git fetch -q --depth 1 origin clipero && git reset -q --hard origin/clipero
new=$(git rev-parse HEAD)
if [ "$(cat $M 2>/dev/null)" != "$new" ]; then
  if bash $APP/server/install.sh >> /var/lib/clipero/update.log 2>&1; then echo "$new" > $M; fi
fi
