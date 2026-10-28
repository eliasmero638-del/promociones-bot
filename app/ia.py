"""Cerebro del Clipero: Gemini mira fotos del clip, escucha el audio y decide si vale la pena."""
import base64, json, os, re, subprocess, tempfile, time
import requests
import config as C

MODELOS_RESPALDO = ['gemini-flash-latest', 'gemini-2.5-flash', 'gemini-2.0-flash']
_cache = {}
_agotado = {}       # modelo -> hora hasta la que no se usa (cuota gratis acabada)


def _disponibles(key):
    ahora = time.time()
    return [m for m in modelos(key) if _agotado.get(m, 0) < ahora]


def _marcar(m, r):
    if r.status_code == 429:
        _agotado[m] = time.time() + 3600


def modelos(key):
    """Modelos 'flash' disponibles para esta clave, del más nuevo al más viejo."""
    if key in _cache:
        return _cache[key]
    lista = []
    try:
        r = requests.get('https://generativelanguage.googleapis.com/v1beta/models', params={'key': key, 'pageSize': 200}, timeout=30)
        for m in r.json().get('models', []):
            n = m['name'].split('/')[-1]
            if 'generateContent' in m.get('supportedGenerationMethods', []) and 'flash' in n and not any(
                    x in n for x in ('image', 'tts', 'audio', 'live', 'thinking', 'exp', 'preview')):
                lista.append(n)
    except Exception:
        pass
    def ver(n):
        return [int(x) for x in re.findall(r'\d+', n)][:2] or [0]
    lista = sorted(set(lista), key=ver, reverse=True)
    normales = [m for m in lista if 'lite' not in m][:3]
    lite = [m for m in lista if 'lite' in m][:2]
    _cache[key] = normales + [m for m in MODELOS_RESPALDO if m not in normales][:1] + lite
    return _cache[key]

PROMPT = """Eres el editor de una página de Facebook de clips de realities ("{marca}") que vive de las vistas.
Estás viendo un pedazo de {seg} segundos del reality "{reality}" (Ecuador), transmitido en vivo.

Participantes que SIGUEN en la casa (nombre: apodos): {participantes}
Exparticipantes que YA SALIERON (ya no aparecen en cámara, pero pueden ser mencionados): {exparticipantes}
Distingue bien QUIÉN APARECE/HABLA de QUIÉN ES MENCIONADO:
- Quien aparece en cámara o habla solo puede ser alguien que sigue en la casa. Nunca le pongas el nombre de un
  exparticipante a quien está hablando.
- Si hablan DE alguien (aunque ya haya salido), puedes nombrarlo como tema: "KAVIEDES HABLA DE REY EZEQUIEL".
- No confundas a las personas: si no estás 100% seguro de quién está hablando, no le pongas nombre.
Comentarios del chat en vivo en ese momento: {chat}

{aprendizaje}
Te doy {nfotos} fotos del clip en orden y su audio. Tareas:
1. Transcribe lo que se dice, con tiempos en segundos desde el inicio del audio, en frases cortas (máx 7 palabras).
2. Di qué participantes intervienen SOLO si estás 100% seguro de quién es (porque lo nombran claramente en el audio
   por su nombre o apodo, o el chat lo confirma). Si tienes la mínima duda, NO lo pongas en "personajes" y en el
   título, subtítulo, descripción y texto NO uses su nombre: di "una participante", "un compañero", "uno de los chicos".
   Es mucho peor poner un nombre equivocado que no poner ninguno.
3. CLASIFICA el momento (no solo peleas importan; el volumen bajo NUNCA es motivo de descarte, y los gritos NO
   prueban que haya polémica). Categorías:
   - "polemica": discusión real, acusaciones, desacuerdo fuerte, respuesta fuerte, tensión entre participantes.
   - "conversacion_importante": aunque hablen bajo: confesión, decisión, explicación seria, secreto, algo que cambia la situación.
   - "tristeza": llanto, duelo, nostalgia, arrepentimiento, decepción, rechazo, soledad, reconciliación, relato doloroso.
   - "historia_personal": experiencia difícil, superación, familia, pérdidas, dificultades, con un arco que conecte.
   - "picante": coqueteo, insinuaciones, celos, tensión romántica, conversación sobre relaciones o sexo, confesiones íntimas
     (sin inventar ni exagerar: si solo se insinúa, no lo presentes como hecho).
   - "revelacion": información inesperada, contradicción, secreto revelado, giro en una relación o situación.
   - "humor": sorpresa o momento gracioso genuino, con valor por sí mismo (no confundir ruido con interés).
   - "normal": charla cotidiana, rutina, repeticiones, comentarios sin emoción ni giro → se descarta.
   Para cada momento responde con hechos: ¿qué ocurre concretamente?, ¿qué frase o acción lo demuestra ("evidencia",
   copia EXACTA del audio)?, ¿se entiende el contexto antes y después?, ¿tiene inicio, desarrollo y cierre natural?
   Si no puedes explicar con evidencia por qué es interesante, decision = "descartar". Nunca etiquetes una charla común
   como polémica para tener más clips. Si hay gritos pero no se entiende qué pasó, decision = "descartar" (incierto).
   Califica "interes" de 0 a 100 SEGÚN SU CATEGORÍA (una historia triste no necesita pelea; una conversación picante
   puede ser en voz baja; una revelación puede no tener emoción visible). Sé exigente: la rutina queda entre 10 y 55.
   90-100: momento que cualquiera en Facebook se detendría a ver y compartiría (pelea real, confesión impactante,
           llanto serio, revelación fuerte, picante claro, burla o humillación fuerte, giro inesperado).
   75-89: claro y con valor (discusión, conversación íntima conmovedora, coqueteo atrevido, chisme fuerte con evidencia).
   50-74: tiene algo pero flojo o sin nada nuevo.  0-49: rutina, silencio, publicidad, pantalla negra.
4. Escribe un título gancho en MAYÚSCULAS (máx 6 palabras) y un subtítulo (máx 8 palabras) que digan qué pasó
   (y quién, solo si estás 100% seguro del nombre),
   estilo "JORGITO SE BURLA DE BRILLIT" / "y ella no se quedó callada". Llamativo pero fiel a lo que pasó.
5. Escribe un texto para publicar en Facebook (1-2 frases, con 2-3 emojis y hashtags).
6. Marca "explicito": true si hay desnudos o actos sexuales visibles.
7. Decide dónde EMPIEZA y TERMINA el momento completo ("inicio" y "fin", en segundos desde el inicio del audio).
   "inicio" = el segundo donde empieza ESE tema (la primera frase sobre él), NO antes: no incluyas conversación previa de
   otro tema ni relleno. En "primera_frase" copia EXACTAMENTE las primeras 5-8 palabras con las que arranca el tema. Termina cuando el momento de verdad se
   cierre: la respuesta, la reacción, la conclusión o el remate. NUNCA lo cortes a la mitad de lo que está pasando.
   Mínimo {cmin} segundos y SIN máximo fijo: dura lo que dure el momento hasta su cierre natural (incluye la respuesta
   o reacción final). Si el momento sigue al final del audio y no termina, pon "sigue": true.
Reglas: si en el clip aparece un niño o niña, nunca le des un ángulo picante ni sexual al título o texto.

Responde SOLO con este JSON:
{{"decision": "clip|descartar", "motivo_descarte": "", "interes": 0-100,
 "categoria": "polemica|conversacion_importante|tristeza|historia_personal|picante|revelacion|humor|normal",
 "categoria_secundaria": "", "explicacion": "qué ocurre concretamente y por qué interesa",
 "contexto_claro": true, "certeza": 0-100, "intensidad": 0-100, "novedad": 0-100, "sigue": false,
 "personajes": ["..."], "titulo": "...", "subtitulo": "...", "descripcion": "qué pasó en una frase",
 "texto_post": "...", "explicito": false, "inicio": 0.0, "fin": 0.0, "evidencia": "frase exacta", "primera_frase": "primeras palabras exactas del tema",
 "subtitulos": [{{"t0": 0.0, "t1": 2.1, "texto": "..."}}]}}"""


APRENDE = os.path.join(C.DATA, 'aprendizaje.json')


def aprendizaje():
    try:
        d = json.load(open(APRENDE, encoding='utf-8'))
    except Exception:
        return ''
    t = ''
    if d.get('no'):
        t += ('El dueño de la página RECHAZÓ estos clips por aburridos o porque no pasaba lo que decía el título. '
              'NO mandes nada parecido (ponles menos de 50):\n- ' + '\n- '.join(d['no'][-15:]) + '\n')
    if d.get('ok'):
        t += 'Estos SÍ le gustaron (así es lo que busca):\n- ' + '\n- '.join(d['ok'][-10:]) + '\n'
    return t


def aprender(bueno, texto):
    try:
        d = json.load(open(APRENDE, encoding='utf-8'))
    except Exception:
        d = {'ok': [], 'no': []}
    d['ok' if bueno else 'no'].append(texto[:200])
    d['ok'], d['no'] = d['ok'][-30:], d['no'][-30:]
    json.dump(d, open(APRENDE, 'w', encoding='utf-8'), ensure_ascii=False)


def aprender_motivo(titulo, motivo):
    try:
        d = json.load(open(APRENDE, encoding='utf-8'))
    except Exception:
        return
    for i in range(len(d.get('no', [])) - 1, -1, -1):
        if d['no'][i].startswith(titulo[:40]) and '[motivo' not in d['no'][i]:
            d['no'][i] += f' [motivo: {motivo}]'
            break
    json.dump(d, open(APRENDE, 'w', encoding='utf-8'), ensure_ascii=False)


def hay_cuota():
    k = C.get().get('gemini_key')
    return bool(k) and bool(_disponibles(k))


def activa():
    return bool(C.get().get('gemini_key'))


def _fotos(clip, n=8):
    out = []
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', clip],
                               capture_output=True, text=True).stdout.strip() or 60)
    for i in range(n):
        t = dur * (i + 0.5) / n
        r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.1f}', '-i', clip, '-frames:v', '1', '-vf', 'scale=640:-2',
                            '-q:v', '5', '-f', 'image2', '-'], capture_output=True)
        if r.stdout:
            out.append(r.stdout)
    return out


def _audio(clip):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', clip, '-vn', '-ac', '1', '-ar', '16000', '-b:a', '32k', '-f', 'mp3', '-'],
                       capture_output=True)
    return r.stdout


def analizar(clip, chat_textos, seg):
    cfg = C.get()
    parts_txt = '; '.join(f"{k}: {', '.join(v)}" for k, v in cfg['participantes'].items())
    chat = ' | '.join(chat_textos[-80:])[:4000] or '(sin chat)'
    fotos = _fotos(clip)
    ex = cfg.get('exparticipantes') or {}
    ex_txt = '; '.join(f"{k}: {', '.join(v)}" for k, v in ex.items()) or '(ninguno)'
    prompt = PROMPT.format(aprendizaje=aprendizaje(), exparticipantes=ex_txt, marca=cfg['marca'], reality=cfg['reality'], seg=int(seg), participantes=parts_txt,
                           chat=chat, nfotos=len(fotos), cmin=cfg.get('clip_min', 30), cmax=cfg.get('clip_max', 180))
    parts = [{'text': prompt}]
    parts += [{'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(f).decode()}} for f in fotos]
    aud = _audio(clip)
    if aud:
        parts.append({'inline_data': {'mime_type': 'audio/mp3', 'data': base64.b64encode(aud).decode()}})
    body = {'contents': [{'parts': parts}],
            'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.4}}
    ultimo = None
    for m in _disponibles(cfg['gemini_key']):
        try:
            r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                              params={'key': cfg['gemini_key']}, json=body, timeout=300)
            _marcar(m, r)
            if r.status_code != 200:
                ultimo = f'{m}: {r.status_code} {r.text[:200]}'
                continue
            txt = r.json()['candidates'][0]['content']['parts'][0]['text']
            txt = re.sub(r'^```(json)?|```$', '', txt.strip()).strip()
            d = json.loads(txt)
            d['interes'] = int(d.get('interes', 0))
            return d
        except Exception as e:
            ultimo = f'{m}: {e}'
    print('IA error:', ultimo, flush=True)
    return {'error': ultimo}


def probar(key):
    ult = (0, '')
    for m in modelos(key):
      try:
        r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                          params={'key': key}, json={'contents': [{'parts': [{'text': 'Responde solo: OK'}]}]}, timeout=180)
        if r.status_code == 200:
            return 200, m
        ult = (r.status_code, m + ' ' + r.text[:200])
      except Exception as e:
        ult = (0, f'{m}: {e}')
    return ult


def generar(prompt, buscar=False, temperatura=0.7, timeout=240):
    """Texto → JSON con Gemini. buscar=True usa Búsqueda de Google para datos actuales.
    Devuelve (dict, fuentes) o (None, error)."""
    key = C.get().get('gemini_key')
    if not key:
        return None, 'sin clave'
    body = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'temperature': temperatura}}
    if buscar:
        body['tools'] = [{'google_search': {}}]
    else:
        body['generationConfig']['responseMimeType'] = 'application/json'
    ult = None
    for m in _disponibles(key):
        try:
            r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                              params={'key': key}, json=body, timeout=timeout)
            _marcar(m, r)
            if r.status_code != 200:
                ult = f'{m}: {r.status_code} {r.text[:200]}'
                continue
            cand = r.json()['candidates'][0]
            txt = ''.join(p.get('text', '') for p in cand['content']['parts'])
            ini, fin = txt.find('{'), txt.rfind('}')
            if ini < 0:
                ult = f'{m}: sin JSON'
                continue
            d = json.loads(txt[ini:fin + 1])
            fuentes = []
            for ch in (cand.get('groundingMetadata') or {}).get('groundingChunks', []):
                w = ch.get('web') or {}
                if w.get('title') and w['title'] not in fuentes:
                    fuentes.append(w['title'])
            return d, fuentes
        except Exception as e:
            ult = f'{m}: {e}'
    return None, ult


# ---------------------------------------------------------------- Groq (segundo cerebro gratis, solo texto)
_groq_mod = []


def groq_activa():
    return bool(C.get().get('groq_key'))


def groq_modelos(key):
    global _groq_mod
    if _groq_mod:
        return _groq_mod
    pref = ['openai/gpt-oss-120b', 'llama-3.3-70b-versatile', 'moonshotai/kimi-k2-instruct', 'qwen/qwen3-32b',
            'openai/gpt-oss-20b', 'llama-3.1-8b-instant']
    try:
        r = requests.get('https://api.groq.com/openai/v1/models', headers={'Authorization': f'Bearer {key}'},
                         timeout=30).json()
        ids = [m['id'] for m in r.get('data', []) if not any(x in m['id'] for x in ('whisper', 'tts', 'guard', 'vision'))]
    except Exception:
        ids = []
    _groq_mod = [m for m in pref if m in ids] + [m for m in ids if m not in pref and ('70b' in m or '120b' in m)]
    return _groq_mod or pref[:2]


def analizar_groq(palabras, chat_textos, seg):
    """Igual que analizar() pero con la transcripción local (Whisper) y Groq. Sin imágenes."""
    key = C.get().get('groq_key')
    if not key:
        return {'error': 'sin clave de Groq'}
    cfg = C.get()
    lineas, g = [], []
    for a, b, w in palabras:
        g.append((a, w))
        if len(g) >= 8:
            lineas.append(f'[{g[0][0]:.1f}s] ' + ' '.join(x[1] for x in g)); g = []
    if g:
        lineas.append(f'[{g[0][0]:.1f}s] ' + ' '.join(x[1] for x in g))
    parts_txt = '; '.join(f"{k}: {', '.join(v)}" for k, v in cfg['participantes'].items())
    ex = cfg.get('exparticipantes') or {}
    ex_txt = '; '.join(f"{k}: {', '.join(v)}" for k, v in ex.items()) or '(ninguno)'
    prompt = PROMPT.format(aprendizaje=aprendizaje(), exparticipantes=ex_txt, marca=cfg['marca'], reality=cfg['reality'],
                           seg=int(seg), participantes=parts_txt, chat=' | '.join(chat_textos[-80:])[:4000] or '(sin chat)',
                           nfotos=0, cmin=cfg.get('clip_min', 60), cmax=cfg.get('clip_max', 180))
    prompt = prompt.replace('Te doy 0 fotos del clip en orden y su audio.',
                            'No tienes fotos ni audio: te doy la TRANSCRIPCIÓN automática con tiempos (puede tener '
                            'errores; no adivines quién habla si no lo nombran).')
    prompt += '\n\nTRANSCRIPCIÓN:\n' + '\n'.join(lineas)[:12000] + '\n\n(En "subtitulos" devuelve [] — ya los tengo.)'
    ult = ''
    for m in groq_modelos(key):
        try:
            r = requests.post('https://api.groq.com/openai/v1/chat/completions', timeout=120,
                              headers={'Authorization': f'Bearer {key}'},
                              json={'model': m, 'temperature': 0.3, 'response_format': {'type': 'json_object'},
                                    'messages': [{'role': 'user', 'content': prompt}]})
            if r.status_code != 200:
                ult = f'{m}: {r.status_code} {r.text[:150]}'
                continue
            d = json.loads(r.json()['choices'][0]['message']['content'])
            d['interes'] = int(d.get('interes', 0) or 0)
            d['subtitulos'] = [{'t0': a, 't1': b, 'texto': w} for a, b, w in palabras]
            d['_modelo'] = 'groq:' + m
            return d
        except Exception as e:
            ult = f'{m}: {e}'
    return {'error': ult}


def probar_groq(key):
    global _groq_mod
    _groq_mod = []
    for m in groq_modelos(key)[:3]:
        try:
            r = requests.post('https://api.groq.com/openai/v1/chat/completions', timeout=60,
                              headers={'Authorization': f'Bearer {key}'},
                              json={'model': m, 'messages': [{'role': 'user', 'content': 'Responde solo: OK'}]})
            if r.status_code == 200:
                return 200, m
            ult = (r.status_code, r.text[:200])
        except Exception as e:
            ult = (0, str(e))
    return ult


def groq_clasificar(texto, chat=''):
    """Clasificación rápida de texto para el prefiltro. Devuelve (categoria, interes) o (None, 0)."""
    key = C.get().get('groq_key')
    if not key or not texto.strip():
        return None, 0
    p = ('Transcripción automática de un momento de un reality en vivo (puede tener errores). Clasifícalo con '
         'exigencia. Categorías: polemica, conversacion_importante, tristeza, historia_personal, picante, revelacion, '
         'humor, normal (charla de rutina sin emoción ni giro). El volumen no importa; importa lo que se dice. '
         'Responde SOLO JSON {"categoria": "...", "interes": 0-100, "por_que": "..."}.\n\nTEXTO: ' + texto[:6000] +
         ('\n\nCHAT: ' + chat[:1500] if chat else ''))
    for m in groq_modelos(key)[:3]:
        try:
            r = requests.post('https://api.groq.com/openai/v1/chat/completions', timeout=60,
                              headers={'Authorization': f'Bearer {key}'},
                              json={'model': m, 'temperature': 0.2, 'response_format': {'type': 'json_object'},
                                    'messages': [{'role': 'user', 'content': p}]})
            if r.status_code != 200:
                continue
            d = json.loads(r.json()['choices'][0]['message']['content'])
            return str(d.get('categoria', 'normal')), int(d.get('interes', 0) or 0)
        except Exception:
            continue
    return None, 0
