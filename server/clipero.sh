#!/bin/bash
# Comando de ayuda en el servidor:  clipero token | clipero estado | clipero log | clipero reiniciar
DATA=/var/lib/clipero; PY=$DATA/venv/bin/python
case "$1" in
  token)
    read -r -p "Pega el token de tu bot de Telegram y presiona Enter: " T
    T=$(echo "$T" | tr -d ' \r\n')
    case "$T" in *:*) ;; *) echo "Ese token no parece válido."; exit 1;; esac
    cd /opt/clipero/app && CLIPERO_DATA=$DATA $PY -c "import config; config.save(telegram_token='$T')"
    systemctl restart clipero
    echo "Listo. Ahora abre tu bot en Telegram y escríbele /start" ;;
  estado) systemctl --no-pager status clipero | head -5; cat $DATA/estado.json; echo ;;
  log) journalctl -u clipero -n 60 --no-pager ;;
  reiniciar) systemctl restart clipero; echo "Reiniciado." ;;
  prueba) bash /opt/clipero/server/probar.sh ;;
  *) echo "Usa: clipero token | clipero estado | clipero log | clipero reiniciar | clipero prueba" ;;
esac
