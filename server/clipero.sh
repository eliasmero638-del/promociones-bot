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
  compartido)
    read -r -p "Pega el token del bot Ridmer Descargas y presiona Enter: " T
    T=$(echo "$T" | tr -d ' \r\n')
    read -r -p "Pega tu chat ID (número) y presiona Enter: " I
    I=$(echo "$I" | tr -dc '0-9-')
    case "$T" in *:*) ;; *) echo "Ese token no parece válido."; exit 1;; esac
    [ -n "$I" ] || { echo "Falta el chat ID."; exit 1; }
    cd /opt/clipero/app && CLIPERO_DATA=$DATA $PY -c "import config; config.save(telegram_token='$T', chat_ids=[int('$I')], solo_enviar=True)"
    systemctl restart clipero
    sleep 5
    curl -s "https://api.telegram.org/bot$T/sendMessage" -d chat_id=$I -d text="🟢 Clipero conectado a este bot (modo solo envío)." | grep -q '"ok":true' \
      && echo "Listo ✅ Revisa tu Telegram: te debió llegar un mensaje." || echo "No pude mandar el mensaje. Revisa el token y el chat ID." ;;
  gemini)
    read -r -p "Pega tu clave de Gemini y presiona Enter: " K
    K=$(echo "$K" | tr -d ' \r\n')
    cd /opt/clipero/app && R=$(CLIPERO_DATA=$DATA $PY -c "import ia,sys; c,t=ia.probar('$K'); print(c)")
    if [ "$R" = "200" ]; then CLIPERO_DATA=$DATA $PY -c "import config; config.save(gemini_key='$K')" && systemctl restart clipero && echo "✅ IA ACTIVADA"; else echo "❌ La clave no funcionó (código $R)"; fi ;;
  estado) systemctl --no-pager status clipero | head -5; cat $DATA/estado.json; echo ;;
  log) journalctl -u clipero -n 60 --no-pager ;;
  reiniciar) systemctl restart clipero; echo "Reiniciado." ;;
  prueba) bash /opt/clipero/server/probar.sh ;;
  *) echo "Usa: clipero token | clipero estado | clipero log | clipero reiniciar | clipero prueba" ;;
esac
