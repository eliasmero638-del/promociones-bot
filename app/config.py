"""Configuración del Clipero. Lo secreto (token, cookies) vive solo en DATA/secrets, nunca en GitHub."""
import json, os, threading

DATA = os.environ.get('CLIPERO_DATA', '/var/lib/clipero')
SECRETS = os.path.join(DATA, 'secrets')
REC = os.path.join(DATA, 'rec')          # pedazos grabados del live
CLIPS = os.path.join(DATA, 'clips')      # clips terminados
COOKIES = os.path.join(SECRETS, 'cookies.txt')
CFG_FILE = os.path.join(SECRETS, 'config.json')
for d in (DATA, SECRETS, REC, CLIPS):
    os.makedirs(d, exist_ok=True)

DEFAULTS = {
    'telegram_token': '',
    'chat_ids': [],
    'solo_enviar': False,                # True = bot compartido con otro programa: solo manda, no lee mensajes                      # se llena solo cuando escribes /start al bot
    'canal': 'https://www.youtube.com/@LaCasa593EnVivo/streams',
    'reality': 'LA CASA 593',
    'marca': 'PASIÓN POR LOS REALITIES',
    'modo': 'remoto',                    # 'remoto' = el teléfono graba y sube; 'local' = graba el servidor
    'pausado': False,
    'gemini_key': '',
    'umbral_ia': 50,                     # con IA: puntaje para pasarle el momento a la IA
    'ia_minimo': 75,                     # con IA: interés mínimo para mandarte el clip
    'umbral': 72,                        # puntaje mínimo (0-100) para mandar un clip
    'max_por_hora': 4,
    'separacion_min': 8,                 # minutos mínimos entre clips automáticos
    'antes_seg': 35,                     # segundos antes del pico
    'despues_seg': 25,                   # segundos después del pico
    'ventana_antes': 60,                 # con IA: segundos que mira antes del pico
    'ventana_despues': 150,              # con IA: segundos que mira después (para no cortar el desenlace)
    'clip_min': 30,
    'clip_max': 180,
    'horas': [],                         # [] = todo el día; ej. [[18, 24], [0, 2]] solo esas horas
    'segmento_seg': 120,
    'guardar_horas': 3,                  # cuánto tiempo guardar lo grabado
    'whisper_modelo': 'small',
    'participantes': {
        'Santiago Castro': ['santiago', 'castro'],
        'Josselin "La Sabrosura" Jiménez': ['sabrosura', 'josselin', 'josselyn', 'joselin', 'joselyn'],
        'Verónica Saltos': ['verónica', 'veronica', 'vero'],
        'Jorgito "El Guayaco"': ['jorgito', 'guayaco', 'jorge'],
        'Bryan "La Firgense"': ['bryan', 'brayan', 'firgense', 'frigersen'],
        'Brillit Torres': ['brillit', 'brilit', 'brigitte'],
        'Abigail Lalama': ['abigail', 'abigaíl', 'abi', 'lalama'],
        'Dominik Kaviedes': ['dominik', 'dominic', 'kaviedes', 'caviedes'],
        'Martha Quiñónez': ['martha', 'marta', 'quiñónez', 'quiñonez'],
    },
}

_lock = threading.Lock()
_cfg = None


def get():
    global _cfg
    with _lock:
        if _cfg is None:
            c = dict(DEFAULTS)
            if os.path.exists(CFG_FILE):
                try:
                    c.update(json.load(open(CFG_FILE, encoding='utf-8')))
                except Exception:
                    pass
            _cfg = c
        return _cfg


def save(**kw):
    c = get()
    with _lock:
        c.update(kw)
        tmp = CFG_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(c, f, ensure_ascii=False, indent=1)
        os.replace(tmp, CFG_FILE)
        os.chmod(CFG_FILE, 0o600)
