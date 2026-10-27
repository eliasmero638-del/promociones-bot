#!/bin/bash
APP=/opt/clipero
cd $APP || exit 0
old=$(git rev-parse HEAD)
git fetch -q --depth 1 origin clipero && git reset -q --hard origin/clipero
new=$(git rev-parse HEAD)
if [ "$old" != "$new" ]; then bash $APP/server/install.sh >> /var/lib/clipero/update.log 2>&1; fi
