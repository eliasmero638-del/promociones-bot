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
  facebook)
    read -r -p "Pega el token de Facebook y presiona Enter: " K
    K=$(echo "$K" | tr -d ' \r\n')
    [ -n "$K" ] || { echo "No pegaste nada."; exit 1; }
    cd /opt/clipero/app && CLIPERO_DATA=$DATA $PY -c "import fb,sys; ok,m=fb.conectar(sys.argv[1]); print(('✅ ' if ok else '❌ ')+m); sys.exit(0 if ok else 1)" "$K" \
      && systemctl restart clipero && echo "Listo. En Telegram escribe /estado para verlo." ;;
  whatsapp)
    read -r -p "Tu número de WhatsApp con +593 (ej. +593991234567): " T
    T=$(echo "$T" | tr -dc '0-9+')
    read -r -p "La apikey que te mandó CallMeBot: " K
    K=$(echo "$K" | tr -d ' \r\n')
    cd /opt/clipero/app && CLIPERO_DATA=$DATA $PY -c "import wa,sys; ok,r=wa.enviar('✅ Avisos de clips activados. Así te van a llegar.', sys.argv[1], sys.argv[2]); print('OK' if ok else 'ERROR '+r); sys.exit(0 if ok else 1)" "$T" "$K" \
      && CLIPERO_DATA=$DATA $PY -c "import config,sys; config.save(wa_telefono=sys.argv[1], wa_apikey=sys.argv[2])" "$T" "$K" \
      && systemctl restart clipero && echo "✅ Listo. Revisa tu WhatsApp: te debió llegar un mensaje." \
      || echo "❌ No llegó. Revisa el número (con +593) y la apikey." ;;
  avisos)
    TEMA=$(CLIPERO_DATA=$DATA $PY -c "import sys; sys.path.insert(0,'/opt/clipero/app'); import config; print(config.get().get('ntfy_tema',''))")
    if [ -z "$TEMA" ]; then TEMA="clips-$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n')"; fi
    cd /opt/clipero/app && CLIPERO_DATA=$DATA $PY -c "import config,sys; config.save(ntfy_tema=sys.argv[1])" "$TEMA" && systemctl restart clipero
    echo ""; echo "En la app ntfy toca + y suscríbete a este tema (cópialo exacto):"; echo ""; echo "   $TEMA"; echo ""
    echo "Cuando estés suscrito escribe:  clipero probaraviso" ;;
  probaraviso)
    cd /opt/clipero/app && CLIPERO_DATA=$DATA $PY -c "import ntfy; ok,r=ntfy.enviar('🔥 90/100 · PRUEBA DEL CLIPERO','Así te van a llegar los avisos de los clips', 'http://173.249.44.95'); print('✅ Enviado, revisa tu celular' if ok else '❌ '+r)" ;;
  voces)
    echo "Haciendo muestras de voces (tarda 2-3 minutos)..."
    cd /opt/clipero/app && CLIPERO_DATA=$DATA $PY voz.py
    echo ""; echo "👉 Escúchalas en el celular: http://173.249.44.95/voces" ;;
  ridmer)
    F=${2:-short}; if [ $# -ge 2 ]; then shift 2; else shift $#; fi; TEMA="$*"
    echo "Haciendo un $F de Ridmer (tarda 5-15 minutos)..."
    cd /opt/clipero/app && CLIPERO_DATA=$DATA nice -n 5 $PY fabrica.py "$F" ${TEMA:+"$TEMA"} ;;
  estado) systemctl --no-pager status clipero | head -5; cat $DATA/estado.json; echo ;;
  log) journalctl -u clipero -n 60 --no-pager ;;
  reiniciar) systemctl restart clipero; echo "Reiniciado." ;;
  prueba) bash /opt/clipero/server/probar.sh ;;
  *) echo "Usa: clipero token | clipero gemini | clipero facebook | clipero whatsapp | clipero avisos | clipero estado | clipero log | clipero reiniciar | clipero prueba" ;;
esac
