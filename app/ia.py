"""Cerebro del Clipero: Gemini mira fotos del clip, escucha el audio y decide si vale la pena."""
import base64, json, os, re, subprocess, tempfile
import requests
import config as C

MODELOS = ['gemini-2.5-flash', 'gemini-2.0-flash']

PROMPT = """Eres el editor de una página de Facebook de clips de realities ("{marca}") que vive de las vistas.
Estás viendo un pedazo de {seg} segundos del reality "{reality}" (Ecuador), transmitido en vivo.

Participantes adultos de la casa (nombre: apodos): {participantes}
Comentarios del chat en vivo en ese momento: {chat}

Te doy {nfotos} fotos del clip en orden y su audio. Tareas:
1. Transcribe lo que se dice, con tiempos en segundos desde el inicio del audio, en frases cortas (máx 7 palabras).
2. Di qué participantes intervienen (usa los nombres de la lista; si no estás seguro, no inventes).
3. Califica de 0 a 100 qué tanto engancharía a la audiencia en redes. Puntúa ALTO: peleas, insultos, discusiones,
   chisme, traiciones, estrategias para nominar, coqueteo, doble sentido, propuestas picantes, burlas, patanadas,
   momentos ridículos o muy graciosos, llanto, confesiones, besos, escándalos. Puntúa BAJO: silencio, comer,
   caminar, cantar, conversaciones aburridas, pantalla en negro o publicidad.
4. Escribe un título gancho en MAYÚSCULAS (máx 6 palabras) y un subtítulo (máx 8 palabras) que digan quién y qué pasó,
   estilo "JORGITO SE BURLA DE BRILLIT" / "y ella no se quedó callada". Llamativo pero fiel a lo que pasó.
5. Escribe un texto para publicar en Facebook (1-2 frases, con 2-3 emojis y hashtags).
6. Marca "explicito": true si hay desnudos o actos sexuales visibles.
Reglas: si en el clip aparece un niño o niña, nunca le des un ángulo picante ni sexual al título o texto.

Responde SOLO con este JSON:
{{"interes": 0-100, "categoria": "pelea|chisme|picante|burla|gracioso|romance|llanto|nominacion|otro",
 "personajes": ["..."], "titulo": "...", "subtitulo": "...", "descripcion": "qué pasó en una frase",
 "texto_post": "...", "explicito": false,
 "subtitulos": [{{"t0": 0.0, "t1": 2.1, "texto": "..."}}]}}"""


def activa():
    return bool(C.get().get('gemini_key'))


def _fotos(clip, n=4):
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
    chat = ' | '.join(chat_textos[-40:])[:2500] or '(sin chat)'
    fotos = _fotos(clip)
    prompt = PROMPT.format(marca=cfg['marca'], reality=cfg['reality'], seg=int(seg), participantes=parts_txt,
                           chat=chat, nfotos=len(fotos))
    parts = [{'text': prompt}]
    parts += [{'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(f).decode()}} for f in fotos]
    aud = _audio(clip)
    if aud:
        parts.append({'inline_data': {'mime_type': 'audio/mp3', 'data': base64.b64encode(aud).decode()}})
    body = {'contents': [{'parts': parts}],
            'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.4}}
    ultimo = None
    for m in MODELOS:
        try:
            r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                              params={'key': cfg['gemini_key']}, json=body, timeout=120)
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
    r = requests.post('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent',
                      params={'key': key}, json={'contents': [{'parts': [{'text': 'Responde solo: OK'}]}]}, timeout=60)
    return r.status_code, r.text[:300]
