"""18-nov: avisos de la clonación de voz al Telegram del dueño (lo usa voz_clon.sh)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import config as C, tg
tipo, a = sys.argv[1], sys.argv[2]
for c in C.get()['chat_ids']:
    if tipo == 'audio':
        with open(a, 'rb') as f:
            tg._api('sendAudio', files={'audio': ('prueba_tu_voz.mp3', f)}, chat_id=c, caption=(sys.argv[3] if len(sys.argv) > 3 else '')[:1000])
    else:
        tg._api('sendMessage', chat_id=c, text=('⚠️ Clonar voz: ' + a) if tipo == 'error' else a)
