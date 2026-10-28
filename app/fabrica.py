"""Fábrica Ridmer: busca temas, escribe el guion, pone la voz, arma Short y video largo, y los publica en Ridmer TV."""
import json, os, random, re, secrets, shutil, subprocess, sys, threading, time
import requests
import config as C, ia, voz, montaje, editor, fb, ntfy, tg
import fuentes as wiki

DIR = os.path.join(C.DATA, 'ridmer')
os.makedirs(DIR, exist_ok=True)
HIST = os.path.join(DIR, 'historial.json')
ESTADO = os.path.join(DIR, 'estado.json')
UA = {'User-Agent': 'RidmerVideos/1.0 (https://github.com/eliasmero638-del/promociones-bot)'}
_lock = threading.Lock()


def log(*a):
    print(time.strftime('%H:%M:%S'), '[ridmer]', *a, flush=True)


def _leer(p, defecto):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return defecto


def _guardar(p, d):
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


# ---------------------------------------------------------------- temas
TEMAS = """Eres el productor del canal de YouTube "Ridmer" (170 mil suscriptores, Ecuador): historias REALES de misterio,
casos sin resolver, sobrevivientes, desapariciones, sucesos extraños y documentales cortos de suspenso.
Fecha de hoy: {hoy}. Busca en internet y propón {n} temas para un {formato}.
{extra}
Reglas:
- Solo historias REALES y verificables (con fuentes). Nada inventado ni leyendas presentadas como hechos.
- Que enganchen desde la primera frase: misterio, giro inesperado, algo difícil de creer pero cierto.
- El "titulo" de cada tema debe ser CLICKBAIT: que provoque una curiosidad irresistible (dato impactante, pregunta,
  giro, algo que no se dice completo). Ej: "Las soltaba en el bosque… y luego salía a cazarlas",
  "Encontraron su diario 30 años después y lo que decía heló a todos". Siempre basado en hechos reales.
- Variedad: no repitas estos temas ya hechos: {hechos}
- Con tacto: si hay víctimas, nada morboso ni burlón.
Responde SOLO con JSON:
{{"temas": [{{"titulo": "...", "resumen": "2 frases con los datos clave", "tipo": "misterio|noticia",
  "puntaje": 0-100 (qué tanto engancharía), "por_que": "..."}}]}}"""

URGENTE = """Fecha y hora: {hoy}. Busca en internet noticias de las últimas 12 horas. ¿Pasó algo MUY importante que la
gente en Ecuador y Latinoamérica querría ver ya mismo en video? (terremoto fuerte, tsunami, erupción, catástrofe,
accidente grave, hecho histórico, descubrimiento impactante). Noticias normales de política o farándula NO cuentan.
Ya publicados hoy: {hechos}
Responde SOLO con JSON: {{"hay": true/false, "urgencia": 0-100, "titulo": "...", "resumen": "datos clave confirmados"}}"""


def _hechos(n=60):
    return '; '.join(h['titulo'] for h in _leer(HIST, [])[-n:]) or '(ninguno)'


ULTIMO_ERROR = ''


ELEGIR = """Eres productor del canal de YouTube "Ridmer" (misterio, casos reales, sobrevivientes, sucesos extraños).
Estos son artículos REALES de Wikipedia. Elige el que dé el {formato} más impactante y que enganche más
(misterio, giro, algo difícil de creer pero cierto). Evita temas aburridos, políticos o sin historia.
{lista}
Responde SOLO JSON: {{"elegido": número, "titulo": "título CLICKBAIT verdadero (máx 80 caracteres)",
 "resumen": "2 frases con lo clave", "puntaje": 0-100}}"""


def tema_wikipedia(formato):
    cands = wiki.candidatos(8, excluir=_hechos(400))
    if not cands:
        return None
    lista = '\n'.join(f'{i}. {c["titulo"]}: {c["intro"][:400]}' for i, c in enumerate(cands))
    p = ELEGIR.format(formato='video largo' if formato == 'largo' else 'Short', lista=lista)
    d = ia.groq_json(p) if ia.groq_activa() else None
    if not d and ia.hay_cuota():
        d, _ = ia.generar(p, buscar=False, temperatura=0.8)
    try:
        c = cands[int(d['elegido'])]
        titulo, resumen = d.get('titulo') or c['titulo'], d.get('resumen') or c['intro'][:300]
    except Exception:
        c = cands[0]
        titulo, resumen = c['titulo'], c['intro'][:300]
    return {'titulo': titulo, 'resumen': resumen, 'tipo': 'misterio', 'articulo': c['titulo'], 'url': c['url']}


def buscar_tema(formato):
    if C.get().get('ridmer_fuente', 'wikipedia') == 'wikipedia':
        try:
            t = tema_wikipedia(formato)
            if t:
                log('tema de Wikipedia:', t['articulo'])
                return t
        except Exception as e:
            log('Wikipedia falló:', e)
    hoy = time.strftime('%d/%m/%Y')
    extra = ('Es un video largo de 4 a 5 minutos: elige un caso con suficiente historia y giros.' if formato == 'largo'
             else 'Es un Short de menos de 60 segundos: elige algo que se cuente rápido y sorprenda. '
                  'Si hoy hay una noticia importante y llamativa, puede ser uno de los temas.')
    p = TEMAS.format(hoy=hoy, n=5, formato='video LARGO' if formato == 'largo' else 'SHORT', extra=extra, hechos=_hechos())
    intentos = []
    d, f = ia.generar(p, buscar=True, temperatura=0.9)                 # 1) Gemini con Google
    intentos.append(f'Gemini+Google: {"ok" if d else f}')
    if not d or not d.get('temas'):                                     # 2) Gemini sin búsqueda (casos conocidos)
        d, f = ia.generar(p.replace('Busca en internet y propón', 'Propón (casos REALES bien documentados que conozcas)'),
                          buscar=False, temperatura=0.9)
        intentos.append(f'Gemini: {"ok" if d else f}')
    if (not d or not d.get('temas')) and ia.groq_activa():              # 3) Groq
        d = ia.groq_json(p.replace('Busca en internet y propón', 'Propón (casos REALES bien documentados que conozcas)'))
        intentos.append(f'Groq: {"ok" if d else "falló"}')
    if not d or not d.get('temas'):
        global ULTIMO_ERROR
        ULTIMO_ERROR = 'no encontré tema → ' + ' | '.join(str(x)[:160] for x in intentos)
        log(ULTIMO_ERROR)
        return None
    hechos = _hechos(200).lower()
    temas = [t for t in d['temas'] if t.get('titulo') and t['titulo'].lower()[:40] not in hechos]
    temas.sort(key=lambda t: -int(t.get('puntaje', 0) or 0))
    return temas[0] if temas else None


URG_RSS = """Titulares de Google Noticias de las últimas 12 horas:
{lista}
¿Hay algo MUY importante que la gente en Ecuador y Latinoamérica querría ver ya en video (terremoto fuerte, tsunami,
erupción, catástrofe, accidente grave, hecho histórico)? Política y farándula NO cuentan. Ya publicados: {hechos}
Responde SOLO JSON: {{"hay": true/false, "urgencia": 0-100, "titulo": "...", "resumen": "solo datos que digan los titulares",
 "indices": [números de los titulares usados]}}"""


def revisar_urgente():
    items = wiki.noticias()
    if items:
        lista = '\n'.join(f"{i}. {x['titulo']} ({x['fuente']}, {x['fecha']})" for i, x in enumerate(items))
        p = URG_RSS.format(lista=lista, hechos=_hechos(10))
        d = ia.groq_json(p, 0.2) if ia.groq_activa() else None
        if not d and ia.hay_cuota():
            d, _ = ia.generar(p, buscar=False, temperatura=0.2)
        if d and d.get('hay') and int(d.get('urgencia', 0) or 0) >= C.get().get('ridmer_urgencia', 85) \
                and d.get('titulo', '').lower()[:40] not in _hechos(30).lower():
            usados = [items[i] for i in d.get('indices', []) if isinstance(i, int) and i < len(items)] or items[:5]
            return {'titulo': d['titulo'], 'resumen': d.get('resumen', ''), 'tipo': 'noticia',
                    'urgencia': int(d.get('urgencia', 0)), 'noticias': usados}
        return None
    d, _ = ia.generar(URGENTE.format(hoy=time.strftime('%d/%m/%Y %H:%M'), hechos=_hechos(10)), buscar=True,
                      temperatura=0.2)
    if d and d.get('hay') and int(d.get('urgencia', 0) or 0) >= C.get().get('ridmer_urgencia', 85):
        if d.get('titulo', '').lower()[:40] not in _hechos(30).lower():
            return {'titulo': d['titulo'], 'resumen': d.get('resumen', ''), 'tipo': 'noticia',
                    'urgencia': int(d.get('urgencia', 0))}
    return None


# ---------------------------------------------------------------- guion
GUION = """Eres guionista del canal "Ridmer" (misterio e historias reales, narrador con voz grave y suspenso).
Escribe el guion de un {formato} sobre: "{titulo}" — {resumen}
Busca en internet y usa SOLO datos verificados (nombres, fechas, lugares, cifras). Si algo no está confirmado,
no lo digas o di "según reportes". Nunca inventes.

Estructura:
- Segmento 1 = GANCHO tipo clickbait: 1 o 2 frases con lo más impactante o una pregunta que deje al espectador sin
  poder irse, sin revelar el final (después de él va la intro del canal).
- Luego la historia en orden, con tensión y giros, frases cortas y fáciles de narrar.
- Final: cierre impactante + "Suscríbete a Ridmer para más historias como esta." (una sola vez, corto).
- Español latino neutro, sin emojis, números escritos con letras cuando sea fácil leerlos.
- Largo total del texto: {palabras} palabras (respeta esto).
- Divide el texto en {segmentos} segmentos (1 o 2 frases cada uno). Para cada segmento da una búsqueda de imagen
  REAL para Wikimedia Commons en inglés ("imagen_en", 2-5 palabras concretas: lugar, persona, objeto, año) y en
  español ("imagen_es"). Si el segmento ocurre en un lugar concreto, da "lat" y "lon".
{tono}
Responde SOLO con JSON:
{{"titulo_video": "MÁX 6 PALABRAS EN MAYÚSCULAS, clickbait", "miniatura_texto": "2 a 4 palabras clickbait que den ganas de tocar",
 "titulo_youtube": "título CLICKBAIT irresistible, máx 80 caracteres (curiosidad, giro, dato impactante; puede usar …, ¿?, MAYÚSCULAS en 1-2 palabras clave; nunca falso)", "descripcion_youtube": "3-5 líneas + hashtags",
 "etiquetas": ["...", "..."], "texto_facebook": "1-2 frases clickbait que no revelen el final + 3 hashtags",
 "segmentos": [{{"texto": "...", "imagen_en": "...", "imagen_es": "...", "lat": null, "lon": null}}]}}"""


def escribir_guion(tema, formato):
    corto = formato == 'short'
    tono = ('Es una noticia del día: tono serio e informativo, respetuoso con las víctimas, con los datos útiles '
            'confirmados (dónde, cuándo, magnitud, qué se sabe).' if tema.get('tipo') == 'noticia' else '')
    p = GUION.format(formato='SHORT vertical (menos de 60 segundos)' if corto else 'video largo de YouTube (4 a 5 minutos)',
                     titulo=tema['titulo'], resumen=tema.get('resumen', ''),
                     palabras='entre 95 y 115' if corto else 'entre 620 y 760',
                     segmentos='7 a 9' if corto else '28 a 38', tono=tono)
    fuente_txt, fuentes_urls = '', []
    if not tema.get('articulo') and tema.get('tipo') != 'noticia':
        try:   # pedido manual: buscar el caso en Wikipedia
            c = wiki._get({'action': 'query', 'list': 'search', 'srsearch': tema['titulo'], 'srlimit': 1})
            hit = c.get('query', {}).get('search', [])
            if hit and hit[0].get('size', 0) > 5000:
                tema['articulo'] = hit[0]['title']
        except Exception:
            pass
    if tema.get('articulo'):
        try:
            art = wiki.articulo(tema['articulo'])
            tema['_imagenes'] = art['imagenes']
            fuente_txt, fuentes_urls = art['texto'], [art['url']]
        except Exception as e:
            log('no pude leer Wikipedia:', e)
    elif tema.get('noticias'):
        fuente_txt = '\n'.join(f"- {x['titulo']} ({x['fuente']}, {x['fecha']}): {x['resumen']}" for x in tema['noticias'])
        fuentes_urls = [f"{x['fuente']}: {x['url']}" for x in tema['noticias'][:5]]
    d = None
    if fuente_txt:
        pf = p.replace('Busca en internet y usa SOLO datos verificados',
                       'Usa SOLO los datos del TEXTO FUENTE de abajo') + '\n\nTEXTO FUENTE:\n' + fuente_txt
        d = ia.groq_json(pf, 0.7) if ia.groq_activa() else None
        if (not d or not d.get('segmentos')) and ia.hay_cuota():
            d, _ = ia.generar(pf, buscar=False, temperatura=0.7, timeout=300)
        if d and d.get('segmentos'):
            d['fuentes'] = fuentes_urls
            return d
    d, fuentes = ia.generar(p, buscar=True, temperatura=0.7, timeout=300)
    if not d or not d.get('segmentos'):
        log('guion con búsqueda falló:', fuentes, '→ sin búsqueda')
        d, fuentes = ia.generar(p.replace('Busca en internet y usa SOLO datos verificados',
                                          'Usa SOLO datos que conozcas con seguridad'), buscar=False, temperatura=0.7)
        fuentes = []
    if not d or not d.get('segmentos'):
        raise RuntimeError(f'no se pudo escribir el guion: {fuentes}')
    d['fuentes'] = fuentes if isinstance(fuentes, list) else []
    return d


# ---------------------------------------------------------------- imágenes
def _commons(q, carpeta, nombre, usados):
    if not q:
        return None
    try:
        r = requests.get('https://commons.wikimedia.org/w/api.php', headers=UA, timeout=30, params={
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': 12,
            'gsrsearch': f'{q} filetype:bitmap', 'prop': 'imageinfo', 'iiprop': 'url|size|mime', 'iiurlwidth': 1600}).json()
        pags = sorted((r.get('query') or {}).get('pages', {}).values(), key=lambda p: p.get('index', 99))
        for p in pags:
            ii = (p.get('imageinfo') or [{}])[0]
            t = p.get('title', '').lower()
            if ii.get('mime') not in ('image/jpeg', 'image/png') or ii.get('width', 0) < 700:
                continue
            if any(x in t for x in ('logo', 'icon', 'flag of', 'coat of arms', 'signature', 'diagram')):
                continue
            url = ii.get('thumburl') or ii.get('url')
            if url in usados:
                continue
            img = requests.get(url, headers=UA, timeout=60)
            if img.status_code != 200 or len(img.content) < 15000:
                continue
            path = os.path.join(carpeta, nombre + ('.png' if ii['mime'] == 'image/png' else '.jpg'))
            open(path, 'wb').write(img.content)
            usados.add(url)
            return path
    except Exception as e:
        log('commons', q, e)
    return None


def _satelite(lat, lon, carpeta, nombre, zoom_km=2.5):
    try:
        lat, lon = float(lat), float(lon)
        d = zoom_km / 111.0
        r = requests.get('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export',
                         headers=UA, timeout=60, params={'bbox': f'{lon - d * 1.6},{lat - d},{lon + d * 1.6},{lat + d}',
                                                         'bboxSR': 4326, 'size': '1600,1000', 'format': 'jpg',
                                                         'f': 'image'})
        if r.status_code == 200 and len(r.content) > 20000:
            path = os.path.join(carpeta, nombre + '.jpg')
            open(path, 'wb').write(r.content)
            return path
    except Exception:
        pass
    return None


def _bajar(url, carpeta, nombre, usados):
    try:
        if url in usados:
            return None
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 200 and len(r.content) > 15000:
            path = os.path.join(carpeta, nombre + ('.png' if url.lower().endswith('.png') else '.jpg'))
            open(path, 'wb').write(r.content)
            usados.add(url)
            return path
    except Exception:
        pass
    return None


def buscar_imagenes(segmentos, carpeta, extra=None):
    usados, reales = set(), []
    extra = list(extra or [])
    for i, s in enumerate(segmentos):
        n = f'img_{i:02d}'
        p = (_commons(s.get('imagen_en'), carpeta, n, usados) or _commons(s.get('imagen_es'), carpeta, n, usados))
        while not p and extra:
            p = _bajar(extra.pop(0), carpeta, n, usados)
        if not p and s.get('lat') not in (None, '') and s.get('lon') not in (None, ''):
            p = _satelite(s['lat'], s['lon'], carpeta, n)
        if p:
            reales.append(p)
        elif reales:
            p = random.choice(reales[-4:])
        else:
            p = montaje.tarjeta(s.get('imagen_es') or 'Ridmer', os.path.join(carpeta, n + '.jpg'))
        s['img'] = p
    return segmentos


# ---------------------------------------------------------------- voz
ESTILO_SHORT = ('Narra en español latinoamericano neutro, como narrador de misterio: voz grave, tono de suspenso, '
                'ritmo ágil (es un video corto), con pequeñas pausas dramáticas. Lee exactamente este texto: ')


def narrar(segmentos, carpeta, formato):
    textos = [s['texto'].strip() for s in segmentos]
    bloques, actual = [], ''
    for t in textos:
        if actual and len(actual) + len(t) > 900:
            bloques.append(actual); actual = ''
        actual = (actual + ' ' + t).strip()
    if actual:
        bloques.append(actual)
    partes = []
    for k, b in enumerate(bloques):
        mp3 = os.path.join(carpeta, f'voz_{k:02d}.mp3')
        ok, r = voz.gemini(b, mp3, estilo=ESTILO_SHORT if formato == 'short' else voz.ESTILO)
        if not ok:
            log('voz gemini falló, uso Microsoft:', r)
            ok, r = voz.edge(b, mp3)
            if not ok:
                raise RuntimeError('no se pudo hacer la voz: ' + str(r))
        partes.append(mp3)
        time.sleep(4)
    lista = os.path.join(carpeta, 'voz.txt')
    with open(lista, 'w') as f:
        for p in partes:
            f.write(f"file '{p}'\n")
    wav = os.path.join(carpeta, 'voz.wav')
    montaje.sh(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lista,
                '-af', 'silenceremove=start_periods=1:start_threshold=-45dB,apad=pad_dur=0.3',
                '-ar', '48000', '-ac', '1', wav])
    if formato == 'short':
        maximo = 58.5 - montaje.dur(montaje.INTRO) - 0.6
        d = montaje.dur(wav)
        if d > maximo:
            f_ = min(1.35, d / maximo)
            rapido = os.path.join(carpeta, 'voz_r.wav')
            montaje.sh(['ffmpeg', '-y', '-v', 'error', '-i', wav, '-af', f'atempo={f_:.3f}', rapido])
            os.replace(rapido, wav)
    return wav


def tiempos(segmentos, palabras):
    """Reparte los segmentos sobre las palabras que reconoció whisper."""
    n = [len(s['texto'].split()) for s in segmentos]
    total, nw = sum(n) or 1, len(palabras)
    acum = 0
    for s, k in zip(segmentos, n):
        idx = min(nw - 1, int(round(acum * nw / total))) if nw else 0
        s['t0'] = palabras[idx][0] if nw else 0.0
        acum += k
    segmentos[0]['t0'] = 0.0
    for i in range(1, len(segmentos)):
        segmentos[i]['t0'] = max(segmentos[i]['t0'], segmentos[i - 1]['t0'] + 0.8)
    return segmentos


# ---------------------------------------------------------------- producir
def producir(formato, tema=None, motivo='programado'):
    """formato: 'short' o 'largo'. Devuelve el id del trabajo."""
    with _lock:
        tema = tema or buscar_tema(formato)
        if not tema:
            raise RuntimeError(ULTIMO_ERROR or 'no encontré tema')
        jid = time.strftime('%Y%m%d_%H%M%S') + '_' + formato
        carpeta = os.path.join(DIR, jid)
        os.makedirs(carpeta, exist_ok=True)
        log('produciendo', formato, '·', tema['titulo'])
        g = escribir_guion(tema, formato)
        segs = buscar_imagenes(g['segmentos'], carpeta, tema.get('_imagenes'))
        wav = narrar(segs, carpeta, formato)
        palabras = editor.transcribir(wav)
        if not palabras:
            # sin whisper: reparto parejo
            todas = ' '.join(s['texto'] for s in segs).split()
            d = montaje.dur(wav)
            palabras = [(i * d / len(todas), (i + 1) * d / len(todas), w) for i, w in enumerate(todas)]
        segs = tiempos(segs, palabras)
        hook = segs[1]['t0'] - 0.15 if len(segs) > 1 else 4.0
        titulo = g.get('titulo_video') or tema['titulo']
        archivos = {}
        if formato == 'short':
            out = os.path.join(carpeta, 'short.mp4')
            montaje.render(carpeta, wav, palabras, segs, 'vertical', titulo, hook, out)
            if montaje.dur(out) > 59.5:
                corto = os.path.join(carpeta, 'short_c.mp4')
                montaje.sh(['ffmpeg', '-y', '-v', 'error', '-i', out, '-t', '59.4', '-c:v', 'libx264', '-preset', 'veryfast',
                            '-crf', '22', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', corto])
                os.replace(corto, out)
            archivos['video'] = 'short.mp4'
        else:
            out = os.path.join(carpeta, 'largo.mp4')
            montaje.render(carpeta, wav, palabras, segs, 'horizontal', titulo, hook, out)
            archivos['video'] = 'largo.mp4'
        imgs = [s['img'] for s in segs if not os.path.basename(s['img']).startswith('tarjeta')]
        mini = os.path.join(carpeta, 'miniatura.jpg')
        montaje.miniatura(imgs[min(1, len(imgs) - 1)] if imgs else segs[0]['img'], g.get('miniatura_texto') or titulo, mini)
        archivos['miniatura'] = 'miniatura.jpg'
        desc = (g.get('descripcion_youtube', '') + '\n\nImágenes: Wikimedia Commons (licencias libres).'
                + ('\nFuentes: ' + '\n'.join(g['fuentes'][:6]) if g.get('fuentes') else ''))
        meta = {'id': jid, 'formato': formato, 'motivo': motivo, 'tema': tema, 'titulo': titulo,
                'titulo_youtube': g.get('titulo_youtube', titulo), 'descripcion_youtube': desc,
                'etiquetas': g.get('etiquetas', []), 'texto_facebook': g.get('texto_facebook', ''),
                'guion': ' '.join(s['texto'] for s in segs), 'archivos': archivos, 'token': secrets.token_urlsafe(16),
                'creado': time.time(), 'estado': 'pendiente', 'duracion': int(montaje.dur(out))}
        _guardar(os.path.join(carpeta, 'meta.json'), meta)
        h = _leer(HIST, [])
        h.append({'fecha': time.strftime('%Y-%m-%d %H:%M'), 'titulo': (tema.get('articulo') or '') + ' · ' + tema['titulo'],
                  'formato': formato})
        _guardar(HIST, h[-400:])
        for f_ in os.listdir(carpeta):
            if f_.startswith(('voz_', 'cuerpo_', 'mezcla', 'esc_')):
                os.remove(os.path.join(carpeta, f_))
        avisar(meta)
        log('listo', jid)
        return jid


def leer_meta(jid):
    return _leer(os.path.join(DIR, jid, 'meta.json'), None)


def buscar_token(token):
    for jid in sorted(os.listdir(DIR), reverse=True):
        m = leer_meta(jid) if os.path.isdir(os.path.join(DIR, jid)) else None
        if m and m.get('token') == token:
            return os.path.join(DIR, jid), m
    return None, None


def _nota(meta, texto):
    for chat_id, msg_id, cap in meta.get('mensajes', []):
        tg.agregar_nota(chat_id, msg_id, cap, texto)


def avisar(meta):
    cfg = C.get()
    link = f"{cfg.get('web_url', 'http://173.249.44.95')}/r/{meta['token']}"
    du = meta.get('duracion', 0)
    corto = meta['formato'] == 'short'
    tipo = '🎬 SHORT (vertical)' if corto else '🎞️ VIDEO LARGO (horizontal)'
    destino = ('Para: YouTube Shorts (lo subes tú) + Reel de Facebook en Ridmer TV' if corto else
               'Para: YouTube (lo subes tú) + video en Facebook Ridmer TV')
    espera = cfg.get('ridmer_espera_min', 20)
    auto = fb.activo('ridmer') and cfg.get('ridmer_auto', True)
    extra = (f'⏳ Si no respondes, se publica solo en Facebook Ridmer TV en {espera} min' if auto
             else '⚠️ Ridmer TV no está conectado todavía: no se publica solo')
    if ntfy.activo():
        ntfy.enviar(f"🔴 RIDMER · {tipo.split(' (')[0]} · {meta['titulo']}", f"⏱️ {du // 60}:{du % 60:02d} · {extra}",
                    link, f"{link}/miniatura.jpg")
    cap = (f"🔴 <b>RIDMER TV</b> · {tipo} · ⏱️ {du // 60}:{du % 60:02d}\n{destino}\n\n"
           f"<b>{meta['titulo_youtube']}</b>\n\n{extra}\n"
           f"👉 Video en calidad completa, miniatura, descripción y etiquetas: {link}")
    v = os.path.join(DIR, meta['id'], meta['archivos']['video'])
    if os.path.getsize(v) >= 48 * 1024 * 1024:
        # Telegram no deja mandar más de 50 MB: va una versión liviana para revisar
        prev = os.path.join(DIR, meta['id'], 'vista_previa.mp4')
        montaje.sh(['ffmpeg', '-y', '-v', 'error', '-i', v, '-vf', 'scale=-2:540', '-c:v', 'libx264', '-preset', 'veryfast',
                    '-b:v', '900k', '-maxrate', '1M', '-bufsize', '2M', '-c:a', 'aac', '-b:a', '96k',
                    '-movflags', '+faststart', prev])
        v = prev
        cap += '\n(En Telegram va en calidad baja para revisar; descarga la buena del link)'
    botones = json.dumps({'inline_keyboard': [[
        {'text': '✅ Publicar en Ridmer TV', 'callback_data': f"rpub:{meta['id']}"},
        {'text': '❌ No publicar', 'callback_data': f"rno:{meta['id']}"}]]})
    mensajes = []
    for c in cfg['chat_ids']:
        kw = dict(chat_id=c, caption=cap[:1000], parse_mode='HTML', supports_streaming='true')
        if not cfg.get('solo_enviar'):
            kw['reply_markup'] = botones
        with open(v, 'rb') as f:
            r = tg._api('sendVideo', files={'video': f}, **kw)
        if r and r.get('ok'):
            mensajes.append((c, r['result']['message_id'], r['result'].get('caption', '')))
        else:
            tg._api('sendMessage', chat_id=c, text=cap, parse_mode='HTML')
    meta['mensajes'] = mensajes
    _guardar(os.path.join(DIR, meta['id'], 'meta.json'), meta)


def publicar(jid, motivo='tú'):
    carpeta = os.path.join(DIR, jid)
    m = leer_meta(jid)
    if not m or m.get('estado') != 'pendiente':
        return False, 'ya estaba ' + (m or {}).get('estado', 'borrado')
    m['estado'] = 'publicando'; _guardar(os.path.join(carpeta, 'meta.json'), m)
    ok, res = fb.publicar(os.path.join(carpeta, m['archivos']['video']), m.get('texto_facebook') or m['titulo_youtube'],
                          m['titulo_youtube'], clave='ridmer')
    m['estado'] = 'publicado' if ok else 'pendiente'
    m['fb'] = res
    if not ok:
        m['auto_fallo'] = True
    else:
        m['publicado'] = time.time()
    _guardar(os.path.join(carpeta, 'meta.json'), m)
    _nota(m, (f"📤 Publicado en Facebook Ridmer TV ({'automático' if motivo == 'auto' else 'por ti'}) · "
              f"{time.strftime('%H:%M')}") if ok else f'⚠️ No se pudo publicar en Facebook: {res}')
    log('publicar', jid, ok, res)
    return ok, res


def no_publicar(jid):
    m = leer_meta(jid)
    if not m or m.get('estado') != 'pendiente':
        return False, 'ya estaba ' + (m or {}).get('estado', 'borrado')
    m['estado'] = 'descartado'
    _guardar(os.path.join(DIR, jid, 'meta.json'), m)
    _nota(m, '❌ No se publica en Facebook')
    return True, 'ok'


# ---------------------------------------------------------------- horario
def _cola_segura(formato, tema=None, motivo='programado', intento=1):
    try:
        producir(formato, tema, motivo)
    except Exception as e:
        log('error produciendo', formato, e)
        reintento = intento < 2
        txt = (f"⚠️ Ridmer: no se pudo hacer el {'Short' if formato == 'short' else 'video largo'} "
               f"({time.strftime('%H:%M')}).\nMotivo: {str(e)[:400]}\n"
               + ('🔁 Lo vuelvo a intentar en 1 hora.' if reintento else '⏭️ Sigo con el próximo horario.'))
        if ntfy.activo():
            ntfy.enviar('⚠️ Ridmer: no se pudo hacer un video', txt[:500], prioridad=2)
        for c in C.get()['chat_ids']:
            tg._api('sendMessage', chat_id=c, text=txt, disable_notification='true')
        if reintento:
            def otra_vez():
                time.sleep(3600)
                _cola_segura(formato, tema, motivo, intento + 1)
            threading.Thread(target=otra_vez, daemon=True).start()


PEDIDOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pedidos.json')


def revisar_pedidos():
    """Pedidos que Claude deja en el repositorio (pedidos.json): se hacen una sola vez cada uno."""
    hechos_p = os.path.join(DIR, 'pedidos_hechos.json')
    hechos = _leer(hechos_p, [])
    for p in _leer(PEDIDOS, []):
        if p.get('despues') and time.time() < p['despues']:
            continue
        if p.get('id') and p['id'] not in hechos:
            hechos.append(p['id']); _guardar(hechos_p, hechos)
            tema = {'titulo': p['tema'], 'resumen': p.get('resumen', ''), 'tipo': p.get('tipo', 'misterio')} \
                if p.get('tema') else None
            threading.Thread(target=_cola_segura, args=(p.get('formato', 'short'), tema, 'pedido'), daemon=True).start()


def bucle():
    while True:
        try:
            revisar_pedidos()
        except Exception as e:
            log('error pedidos', e)
        try:
            cfg = C.get()
            if cfg.get('ridmer_activo', True) and cfg.get('gemini_key'):
                est = _leer(ESTADO, {})
                hoy = time.strftime('%Y-%m-%d')
                if est.get('fecha') != hoy:
                    est = {'fecha': hoy, 'hechos': [], 'extra': 0, 'urgente_rev': 0}
                ahora = time.localtime()
                tareas = [(h, 'short') for h in cfg.get('ridmer_horas_shorts', [8, 12, 16, 20])]
                tareas.append((cfg.get('ridmer_hora_largo', 18), 'largo'))
                for h, formato in tareas:
                    clave = f'{formato}{h}'
                    if ahora.tm_hour == h and clave not in est['hechos']:
                        est['hechos'].append(clave); _guardar(ESTADO, est)
                        threading.Thread(target=_cola_segura, args=(formato,), daemon=True).start()
                # noticias urgentes: cada 2 horas entre 7 y 23
                if 7 <= ahora.tm_hour <= 23 and time.time() - est.get('urgente_rev', 0) > 7200 \
                        and est.get('extra', 0) < cfg.get('ridmer_max_extra', 2):
                    est['urgente_rev'] = time.time(); _guardar(ESTADO, est)
                    t = revisar_urgente()
                    if t:
                        est['extra'] = est.get('extra', 0) + 1; _guardar(ESTADO, est)
                        def urg(t=t):
                            _cola_segura('short', t, 'urgente')
                            if t['urgencia'] >= 95:
                                _cola_segura('largo', t, 'urgente')
                        threading.Thread(target=urg, daemon=True).start()
                # publicar solos los que nadie respondió
                if fb.activo('ridmer') and cfg.get('ridmer_auto', True):
                    for jid in sorted(os.listdir(DIR)):
                        m = leer_meta(jid) if os.path.isdir(os.path.join(DIR, jid)) else None
                        if m and m.get('estado') == 'pendiente' and not m.get('auto_fallo') and \
                                time.time() - m.get('creado', 0) > cfg.get('ridmer_espera_min', 20) * 60 and \
                                time.time() - m.get('creado', 0) < 12 * 3600:
                            publicar(jid, 'auto')
                # limpiar trabajos de más de 4 días
                for jid in os.listdir(DIR):
                    p = os.path.join(DIR, jid)
                    if os.path.isdir(p) and time.time() - os.path.getmtime(p) > 4 * 86400:
                        shutil.rmtree(p, ignore_errors=True)
        except Exception as e:
            log('error bucle', e)
        time.sleep(60)


def iniciar():
    threading.Thread(target=bucle, daemon=True).start()


if __name__ == '__main__':
    # uso manual:  python fabrica.py short|largo ["tema opcional"]
    f = sys.argv[1] if len(sys.argv) > 1 else 'short'
    tema = {'titulo': sys.argv[2], 'resumen': '', 'tipo': 'misterio'} if len(sys.argv) > 2 else None
    print('✅ Listo:', producir(f, tema, 'manual'))
