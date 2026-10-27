#!/data/data/com.termux/files/usr/bin/bash
# Instala el grabador del Clipero en Termux (Android). Uso:
#   pkg install -y curl && curl -sL https://raw.githubusercontent.com/eliasmero638-del/promociones-bot/clipero/termux/instalar.sh | bash
set -e
S=173.249.44.95; P=443; D=$HOME/clipero
echo "== 1/4 Instalando herramientas (5-10 min) =="
yes | pkg update -y >/dev/null 2>&1 || true
pkg install -y python ffmpeg openssh rsync nodejs >/dev/null
pip install -q -U yt-dlp
mkdir -p $D/rec $D/chat ~/.ssh ~/.termux/boot
echo "== 2/4 Conectando con tu servidor =="
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -q
if ! ssh -p $P -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 root@$S true 2>/dev/null; then
  echo ">>> Escribe la CONTRASEÑA del servidor (la de root) y presiona Enter. No se ve mientras escribes, es normal."
  cat ~/.ssh/id_ed25519.pub | ssh -p $P -o StrictHostKeyChecking=accept-new root@$S \
    'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys' < /dev/tty
fi
ssh -p $P -o BatchMode=yes root@$S true && echo "Conectado al servidor ✅"
echo "== 3/4 Bajando el grabador y tus cookies =="
curl -sL https://raw.githubusercontent.com/eliasmero638-del/promociones-bot/clipero/termux/grabar.sh -o $D/grabar.sh
chmod +x $D/grabar.sh
scp -q -P $P root@$S:/var/lib/clipero/secrets/cookies.txt $D/cookies.txt && echo "Cookies listas ✅"
cat > ~/.termux/boot/clipero <<'B'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
nohup bash ~/clipero/grabar.sh >> ~/clipero/log.txt 2>&1 &
B
chmod +x ~/.termux/boot/clipero
echo "== 4/4 Arrancando =="
termux-wake-lock || true
pkill -f clipero/grabar.sh 2>/dev/null || true
nohup bash $D/grabar.sh >> $D/log.txt 2>&1 &
sleep 60
echo; tail -n 5 $D/log.txt
echo
echo "================================================"
echo " Grabador funcionando. Deja Termux abierto,"
echo " el teléfono cargando y en WiFi."
echo " Para ver cómo va:   tail ~/clipero/log.txt"
echo "================================================"
