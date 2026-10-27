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
    'ia_minimo': 80,                     # con IA: interés mínimo para mandarte el clip
    'umbral': 72,                        # puntaje mínimo (0-100) para mandar un clip
    'max_por_hora': 4,
    'separacion_min': 8,                 # minutos mínimos entre clips automáticos
    'antes_seg': 35,                     # segundos antes del pico
    'despues_seg': 25,                   # segundos después del pico
    'ventana_antes': 60,                 # con IA: segundos que mira antes del pico
    'ventana_despues': 150,              # con IA: segundos que mira después (para no cortar el desenlace)
    'clip_min': 60,
    'auto_publicar': True,               # publicar solo en Facebook si no respondes
    'auto_espera_min': 20,               # minutos que espera tu respuesta
    'auto_minimo': 85,                   # interés mínimo para publicar sin preguntarte
    'max_publicaciones_dia': 12,
    'fb_page_id': '',
    'wa_telefono': '',                   # tu WhatsApp, ej. +593991234567
    'wa_apikey': '',                     # clave que te da CallMeBot
    'web_url': 'http://173.249.44.95',   # dirección de la página para ver los clips
    'web_puerto': 80,
    'ntfy_tema': '',
    'voz_narrador': 'Algenib',
    'ridmer_activo': True,               # fábrica de videos Ridmer
    'ridmer_horas_shorts': [8, 12, 16, 20],
    'ridmer_hora_largo': 18,
    'ridmer_espera_min': 20,             # minutos antes de publicar solo en Ridmer TV
    'ridmer_auto': True,
    'ridmer_max_extra': 2,               # noticias urgentes extra por día
    'ridmer_urgencia': 85,           # voz de Gemini elegida para Ridmer                     # tema secreto de la app ntfy
    'fb_page_token': '',
    'clip_max': 180,
    'horas': [],                         # [] = todo el día; ej. [[18, 24], [0, 2]] solo esas horas
    'segmento_seg': 120,
    'guardar_horas': 3,                  # cuánto tiempo guardar lo grabado
    'whisper_modelo': 'small',
    'exparticipantes': {
        'Rey Ezequiel': ['rey', 'ezequiel'],
    },
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
_propio = {}            # solo lo que se guardó a propósito (no los valores por defecto)

VERSION_CFG = 2
# claves que versiones viejas guardaban sin querer: se borran para que mande el valor por defecto
MIGRAR = {2: ['clip_min', 'clip_max', 'ventana_antes', 'ventana_despues', 'antes_seg', 'despues_seg',
              'umbral_ia', 'max_por_hora', 'separacion_min', 'segmento_seg', 'guardar_horas', 'whisper_modelo',
              'auto_espera_min', 'auto_minimo', 'max_publicaciones_dia', 'participantes', 'canal', 'reality',
              'marca', 'modo', 'web_url', 'web_puerto', 'umbral']}
FORZAR = {2: {'ia_minimo': 80}}


def _escribir():
    tmp = CFG_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(_propio, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CFG_FILE)
    os.chmod(CFG_FILE, 0o600)


def get():
    global _cfg, _propio
    with _lock:
        if _cfg is None:
            propio = {}
            if os.path.exists(CFG_FILE):
                try:
                    propio = json.load(open(CFG_FILE, encoding='utf-8'))
                except Exception:
                    propio = {}
            v = propio.get('cfg_version', 1)
            if v < VERSION_CFG:
                for n in range(v + 1, VERSION_CFG + 1):
                    for k in MIGRAR.get(n, []):
                        propio.pop(k, None)
                    propio.update(FORZAR.get(n, {}))
                propio['cfg_version'] = VERSION_CFG
                _propio = propio
                try:
                    _escribir()
                except Exception:
                    pass
            _propio = propio
            c = dict(DEFAULTS)
            c.update(propio)
            _cfg = c
        return _cfg


def save(**kw):
    c = get()
    with _lock:
        c.update(kw)
        _propio.update(kw)
        _escribir()
