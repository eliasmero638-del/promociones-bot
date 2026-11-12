"""Configuración del Clipero. Lo secreto (token, cookies) vive solo en DATA/secrets, nunca en GitHub."""
import json, os, threading, time

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
    'ia_minimo': 85,                     # con IA: interés mínimo para mandarte el clip
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
    # 9-nov: al dueño le encantó Algenib con este tono (voz 1). Si Gemini lee la instrucción, se recorta sola.
    'estilo_voz_ridmer': 'Narra como un documental de misterio, en tono de suspenso, voz baja y pausada: "{texto}"',
    'ridmer_activo': False,              # fábrica automática apagada (los videos los edita Claude)
    'ridmer_horas_shorts': [8, 12, 16, 20],
    'ridmer_hora_largo': 18,
    'ridmer_espera_min': 20,             # minutos antes de publicar solo en Ridmer TV
    'ridmer_auto': True,
    'ridmer_max_extra': 2,               # noticias urgentes extra por día
    'ridmer_urgencia': 90,
    'reporte_horas': 0,                  # sin reporte periódico (solo /diag cuando lo pidas)
    'ridmer_fb_dia': 3,
    'radar_hora': 2,           # voz de Gemini elegida para Ridmer                     # tema secreto de la app ntfy
    'fb_page_token': '',
    'clip_max': 900,                     # sin tope real: dura lo que dure el momento
    'historias': True,                  # 12-nov: lo que se publica en Ridmer TV también va a sus historias
    'historias_paginas': ['ridmer'],
    'memes': True,                      # 10-nov: versión MEME de los mejores momentos (franja negra + frase)
    'meme_minimo': 70,                   # potencial mínimo de meme (0-100)
    'memes_auto': False,
    'fotos': True,                       # 11-nov: fotos con chisme (Facebook también paga las fotos)
    'fotos_auto': False,                 # False = solo muestras; True = entran a la cola automática                 # False = solo muestras al Telegram; True = entran a la cola automática
    'claude_limite': '12:45',            # 10-nov: si a esta hora Claude no entregó, el servidor arma el respaldo
    'desde_hora': '14:00',               # 10-nov (pedido del dueño, permanente): ningún video sale antes de las 14:00
    'desde_hora_dia': {},                # excepciones por fecha, ej. {'2026-12-24': '10:00'}
    'paquete_hora': '14:00',             # Shorts y largo de YouTube llegan todos juntos a esta hora
    'shorts_extra': 2,
    'ridmer_shorts_propios': 0,          # 9-nov: solo 2 Shorts al día (fb1s y fb2s, de las historias de fb1 y fb2)
    'ridmer_largo_cada': 2,              # 9-nov: video largo día por medio
    'largo_cada_dias': 1,                # video largo de YouTube todos los días                   # Shorts con historia propia además de los 3 de Facebook
    'separacion_pub_min': 60,            # mínimo entre publicaciones en Facebook
    'pub_noche': [0, 7],                 # de 0:00 a 7:00 no se publica (se guarda para la mañana)
    'repetido_min': 30,                  # misma persona dentro de 30 min de grabación = misma conversación
    'sin_nombre_minimo': 90,             # sin nombre seguro solo pasa si el momento es muy fuerte (título neutral)
    'certeza_minima': 70,
    'horas': [],                         # [] = todo el día; ej. [[18, 24], [0, 2]] solo esas horas
    'segmento_seg': 120,
    'guardar_horas': 3,                  # cuánto tiempo guardar lo grabado
    'whisper_modelo': 'small',
    'exparticipantes': {
        'Rey Ezequiel': ['rey', 'ezequiel'],
        'Santiago Castro': ['santiago', 'castro'],
        'Verónica Saltos': ['verónica', 'veronica', 'vero'],
        'Jorgito "El Guayaco"': ['jorgito', 'guayaco', 'jorge'],
        'Abigail Lalama': ['abigail', 'abigaíl', 'abi', 'lalama'],
    },
    'invitados': {                     # visitas (se agregan con /invitado y se quitan con /fuera)
        'Aarón "El Chiche"': ['aarón', 'aaron', 'chiche'],
    },
    'lugar': 'LA CASA',
    'pais': 'Ecuador',
    # La Mansión VIP 2 (HotSpanish Vlogs, México). Se usa sola cuando el teléfono está grabando su en vivo.
    'perfil_mansion': {
        'claves': ['mansion', 'hotspanish', 'vip 2'],
        'reality': 'LA MANSIÓN VIP 2',
        'lugar': 'LA MANSIÓN',
        'pais': 'México',
        'exparticipantes': {},
        'invitados': {},
        'participantes': {             # los 16 que entraron en el estreno (8-nov-2026, Excélsior / Diario del Yaqui)
            'Karely Ruiz': ['karely', 'karelly', 'kareli'],
            'Itatí López': ['itatí', 'itati'],
            'Tony Aguirre': ['tony', 'toni', 'aguirre'],
            'João Ferreira': ['joão', 'joao', 'ferreira'],
            'Edwin Mendoza': ['edwin', 'mendoza'],
            'Paolita Suárez': ['paolita', 'paola', 'suárez', 'suarez'],
            'Doña Alegría': ['doña alegría', 'alegría', 'alegria', 'leticia', 'guajardo'],
            'Cintia Cossio': ['cintia', 'cinthia', 'cossio'],
            'Rod Contreras': ['rod', 'contreras'],
            'Bellakath': ['bellakath', 'bellakat', 'bella kath', 'kath'],
            'Dani Flow': ['dani flow', 'dani', 'flow'],
            'Odette Orlena': ['odette', 'orlena', 'orleana'],
            'Abel Robles': ['abel', 'robles'],
            'Jlexis': ['jlexis', 'jlexispr', 'j lexis'],
            'Jorjais': ['jorjais', 'jorja'],
            'La Cukis': ['cukis', 'la cukis'],
        },
    },
    'participantes': {
        'Josselin "La Sabrosura" Jiménez': ['sabrosura', 'josselin', 'josselyn', 'joselin', 'joselyn'],
        'Bryan "La Firgense"': ['bryan', 'brayan', 'firgense', 'frigersen', 'frigerse'],
        'Brillit Torres': ['brillit', 'brilit', 'brigitte'],
        'Dominik Kaviedes': ['dominik', 'dominic', 'kaviedes', 'caviedes'],
        'Martha Quiñónez': ['martha', 'marta', 'quiñónez', 'quiñonez'],
    },
}

_lock = threading.Lock()
_cfg = None
_propio = {}            # solo lo que se guardó a propósito (no los valores por defecto)

VERSION_CFG = 6
# claves que versiones viejas guardaban sin querer: se borran para que mande el valor por defecto
MIGRAR = {2: ['clip_min', 'clip_max', 'ventana_antes', 'ventana_despues', 'antes_seg', 'despues_seg',
              'umbral_ia', 'max_por_hora', 'separacion_min', 'segmento_seg', 'guardar_horas', 'whisper_modelo',
              'auto_espera_min', 'auto_minimo', 'max_publicaciones_dia', 'participantes', 'canal', 'reality',
              'marca', 'modo', 'web_url', 'web_puerto', 'umbral'],
          5: ['participantes', 'exparticipantes']}       # lista actual según lacasa593.com (1-nov-2026)
FORZAR = {2: {'ia_minimo': 80}, 3: {'ia_minimo': 85}, 4: {'ridmer_urgencia': 90}, 5: {'certeza_minima': 75}, 6: {'certeza_minima': 70}}


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
    if perfil() == 'mansion':
        v = dict(_cfg)
        v.update(_mansion())
        return v
    return _cfg


# ------------------------------------------------ qué reality se está grabando ahora (según el título del en vivo)
PERFIL_CLAVES = ('reality', 'lugar', 'pais', 'participantes', 'exparticipantes', 'invitados')
_perfil_cache = [0, 'casa593']


def _norm(t):
    import unicodedata
    return ''.join(ch for ch in unicodedata.normalize('NFD', str(t).lower()) if unicodedata.category(ch) != 'Mn')


def _mansion():
    m = dict(DEFAULTS['perfil_mansion'])
    m.update((_cfg or {}).get('perfil_mansion') or {})
    return {k: m[k] for k in PERFIL_CLAVES if k in m}


def perfil():
    """'mansion' si el teléfono está grabando La Mansión VIP 2; si no, 'casa593'."""
    forzado = (_cfg or {}).get('perfil_forzado')
    if forzado in ('mansion', 'casa593'):
        return forzado
    if time.time() - _perfil_cache[0] < 20:
        return _perfil_cache[1]
    p = 'casa593'
    try:
        if time.time() - os.path.getmtime(os.path.join(DATA, 'srv_mansion.json')) < 90:   # la graba el servidor
            _perfil_cache[:] = [time.time(), 'mansion']
            return 'mansion'
    except Exception:
        pass
    try:
        d = json.load(open(os.path.join(DATA, 'remoto.json'), encoding='utf-8'))
        txt = _norm(' '.join(str(d.get(k) or '') for k in ('titulo', 'canal')))
        claves = ((_cfg or {}).get('perfil_mansion') or {}).get('claves') or DEFAULTS['perfil_mansion']['claves']
        if any(_norm(k) in txt for k in claves):
            p = 'mansion'
    except Exception:
        pass
    _perfil_cache[:] = [time.time(), p]
    return p


def save(**kw):
    get()
    with _lock:
        if perfil() == 'mansion' and any(k in PERFIL_CLAVES for k in kw):
            pm = dict(_cfg.get('perfil_mansion') or {})
            for k in list(kw):
                if k in PERFIL_CLAVES:
                    pm[k] = kw.pop(k)
            kw['perfil_mansion'] = pm
        _cfg.update(kw)
        _propio.update(kw)
        _escribir()
