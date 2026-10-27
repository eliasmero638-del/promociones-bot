"""Cerebro del Clipero: Gemini mira fotos del clip, escucha el audio y decide si vale la pena."""
import base64, json, os, re, subprocess, tempfile
import requests
import config as C

MODELOS_RESPALDO = ['gemini-flash-latest', 'gemini-2.5-flash', 'gemini-2.0-flash']
_cache = {}


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
                    x in n for x in ('lite', 'image', 'tts', 'audio', 'live', 'thinking', 'exp', 'preview')):
                lista.append(n)
    except Exception:
        pass
    def ver(n):
        return [int(x) for x in re.findall(r'\d+', n)][:2] or [0]
    lista = sorted(set(lista), key=ver, reverse=True)
    _cache[key] = (lista + [m for m in MODELOS_RESPALDO if m not in lista])[:4]
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

Te doy {nfotos} fotos del clip en orden y su audio. Tareas:
1. Transcribe lo que se dice, con tiempos en segundos desde el inicio del audio, en frases cortas (máx 7 palabras).
2. Di qué participantes intervienen SOLO si estás 100% seguro de quién es (porque lo nombran claramente en el audio
   por su nombre o apodo, o el chat lo confirma). Si tienes la mínima duda, NO lo pongas en "personajes" y en el
   título, subtítulo, descripción y texto NO uses su nombre: di "una participante", "un compañero", "uno de los chicos".
   Es mucho peor poner un nombre equivocado que no poner ninguno.
3. Califica de 0 a 100 qué tanto engancharía a gente en Facebook que NO ve el reality. Califica por LO QUE PASA y
   LO QUE SE DICE, no por el volumen: una conversación a solas en voz baja puede valer 90 si es fuerte.
   Sé exigente: la mayoría de momentos de una casa en vivo son rutina y deben quedar entre 10 y 55. Escala:
   90-100: pelea fuerte, insultos, escándalo, beso o momento picante claro, humillación o burla muy fuerte,
           confesión impactante, secreto revelado, traición descubierta, alguien llorando de verdad por algo serio.
   75-89: discusión clara, burla o patanada evidente, coqueteo atrevido, chisme fuerte sobre otro participante,
          plan secreto para traicionar o nominar a alguien, conversación íntima y conmovedora (familia, pasado,
          sentimientos), alguien que se quiebra, reconciliación, momento MUY gracioso, algo que deje con la boca abierta.
   50-74: conversación común sobre estrategia o nominaciones sin nada nuevo, comentarios sueltos, chisme sin sustancia.
   0-49: silencio, comer, caminar, cantar, charla de rutina, pantalla en negro o publicidad.
   Pregúntate: ¿alguien que va pasando por Facebook se detendría a ver esto y lo comentaría o compartiría?
   Si no estás seguro, ponle menos de 70. Anécdotas, historias del pasado o charlas que no generan reacción en la
   casa ni polémica valen menos de 75, aunque se cuenten con emoción.
4. Escribe un título gancho en MAYÚSCULAS (máx 6 palabras) y un subtítulo (máx 8 palabras) que digan qué pasó
   (y quién, solo si estás 100% seguro del nombre),
   estilo "JORGITO SE BURLA DE BRILLIT" / "y ella no se quedó callada". Llamativo pero fiel a lo que pasó.
5. Escribe un texto para publicar en Facebook (1-2 frases, con 2-3 emojis y hashtags).
6. Marca "explicito": true si hay desnudos o actos sexuales visibles.
7. Decide dónde EMPIEZA y TERMINA el momento completo ("inicio" y "fin", en segundos desde el inicio del audio).
   Empieza un poco antes de que arranque el tema, para que se entienda. Termina cuando el momento de verdad se
   cierre: la respuesta, la reacción, la conclusión o el remate. NUNCA lo cortes a la mitad de lo que está pasando.
   Duración entre {cmin} y {cmax} segundos. Lo normal es entre 90 y 170 segundos: si la conversación sigue sobre el
   mismo tema, inclúyela completa. Si dudas, alárgalo: es mejor que sobre un poco a que falte el final.
   Si todo el audio es el mismo momento, usa todo.
Reglas: si en el clip aparece un niño o niña, nunca le des un ángulo picante ni sexual al título o texto.

Responde SOLO con este JSON:
{{"interes": 0-100, "categoria": "pelea|chisme|picante|burla|gracioso|romance|llanto|nominacion|otro",
 "personajes": ["..."], "titulo": "...", "subtitulo": "...", "descripcion": "qué pasó en una frase",
 "texto_post": "...", "explicito": false, "inicio": 0.0, "fin": 0.0,
 "subtitulos": [{{"t0": 0.0, "t1": 2.1, "texto": "..."}}]}}"""


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
    prompt = PROMPT.format(exparticipantes=ex_txt, marca=cfg['marca'], reality=cfg['reality'], seg=int(seg), participantes=parts_txt,
                           chat=chat, nfotos=len(fotos), cmin=cfg.get('clip_min', 30), cmax=cfg.get('clip_max', 180))
    parts = [{'text': prompt}]
    parts += [{'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(f).decode()}} for f in fotos]
    aud = _audio(clip)
    if aud:
        parts.append({'inline_data': {'mime_type': 'audio/mp3', 'data': base64.b64encode(aud).decode()}})
    body = {'contents': [{'parts': parts}],
            'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.4}}
    ultimo = None
    for m in modelos(cfg['gemini_key']):
        try:
            r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                              params={'key': cfg['gemini_key']}, json=body, timeout=300)
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
    for m in modelos(key):
        try:
            r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                              params={'key': key}, json=body, timeout=timeout)
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
