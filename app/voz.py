"""Voces para narración: Gemini TTS (gratis con la clave de Gemini) y Microsoft Edge (gratis)."""
import base64, os, re, subprocess, sys, time
import requests
import config as C

GEMINI_VOCES = ['Charon', 'Fenrir', 'Orus', 'Algenib', 'Enceladus', 'Alnilam', 'Kore', 'Gacrux']
ESTILO = ('Narra en español latinoamericano neutro, como narrador de documental de misterio: voz grave, '
          'tono de suspenso, ritmo pausado, con pausas dramáticas. Lee exactamente este texto: ')
RESPALDO = ['gemini-2.5-flash-preview-tts', 'gemini-2.5-pro-preview-tts']
_mod = None


def modelos_tts(key):
    global _mod
    if _mod:
        return _mod
    lista = []
    try:
        r = requests.get('https://generativelanguage.googleapis.com/v1beta/models',
                         params={'key': key, 'pageSize': 200}, timeout=30).json()
        lista = [m['name'].split('/')[-1] for m in r.get('models', []) if 'tts' in m['name']]
    except Exception:
        pass
    def orden(n):
        v = [int(x) for x in re.findall(r'\d+', n)][:2]
        return (('lite' not in n), ('flash' in n), v)
    lista = sorted(set(lista), key=orden, reverse=True)
    _mod = lista + [m for m in RESPALDO if m not in lista]
    return _mod


def _prompt(estilo, texto):
    """El estilo puede traer {texto} para encerrar el texto entre comillas (así Gemini no lee la instrucción en voz alta)."""
    if not estilo:
        return texto
    return estilo.replace('{texto}', texto) if '{texto}' in estilo else estilo + texto


def gemini(texto, salida_mp3, voz=None, estilo=ESTILO, modelo=None):
    voz = voz or C.get().get('voz_narrador', 'Algenib')
    key = C.get().get('gemini_key')
    if not key:
        return False, 'sin clave de Gemini'
    ult = ''
    # 11-nov: con 'modelo' se usa SOLO ese (cambiar de modelo a mitad de una narración cambia la voz)
    for m in ([modelo] if modelo else modelos_tts(key)[:3]):
        for intento in range(3):
            try:
                r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                                  params={'key': key}, timeout=300, json={
                                      'contents': [{'parts': [{'text': _prompt(estilo, texto)}]}],
                                      'generationConfig': {'responseModalities': ['AUDIO'], 'temperature': 0.6, 'speechConfig': {
                                          'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voz}}}}})
                if r.status_code == 429:
                    ult = f'{m}: límite, espero'; time.sleep(20 * (intento + 1)); continue
                if r.status_code != 200:
                    ult = f'{m}: {r.status_code} {r.text[:150]}'; break
                parte = r.json()['candidates'][0]['content']['parts'][0]['inlineData']
                pcm = base64.b64decode(parte['data'])
                tasa = int((re.search(r'rate=(\d+)', parte.get('mimeType', '')) or [0, 24000])[1])
                p = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 's16le', '-ar', str(tasa), '-ac', '1', '-i', '-',
                                    '-b:a', '128k', salida_mp3], input=pcm)
                return p.returncode == 0, m
            except Exception as e:
                ult = f'{m}: {e}'; break
    return False, ult


def _edge1(texto, salida_mp3, voz):
    err = ''
    for intento in range(4):
        p = subprocess.run([sys.executable, '-m', 'edge_tts', '--voice', voz, '--rate=-5%', '--text=' + texto,
                            '--write-media', salida_mp3], capture_output=True, text=True, timeout=300)
        if p.returncode == 0 and os.path.exists(salida_mp3) and os.path.getsize(salida_mp3) > 1000:
            return True, ''
        err = p.stderr[-200:]; time.sleep(3 + 4 * intento)
    return False, err


def edge(texto, salida_mp3, voz='es-EC-LuisNeural'):
    """13-nov: en pedazos cortos (frases) y con reintentos: con textos largos Microsoft a veces no devolvía audio."""
    frases = re.split(r'(?<=[.!?…])\s+', texto.strip())
    trozos, act = [], ''
    for f in frases:
        if act and len(act) + len(f) > 350:
            trozos.append(act); act = ''
        act = (act + ' ' + f).strip()
    if act:
        trozos.append(act)
    if len(trozos) <= 1:
        return _edge1(texto, salida_mp3, voz)
    partes = []
    for i, t in enumerate(trozos):
        pm = salida_mp3 + f'.{i:02d}.mp3'
        ok, err = _edge1(t, pm, voz)
        if not ok:
            return False, err
        partes.append(pm)
    lista = salida_mp3 + '.txt'
    with open(lista, 'w') as f:
        for pm in partes:
            f.write(f"file '{os.path.abspath(pm)}'\n")
    p = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-c:a', 'libmp3lame',
                        '-b:a', '128k', salida_mp3], capture_output=True, text=True)
    for pm in partes + [lista]:
        try: os.remove(pm)
        except Exception: pass
    return p.returncode == 0, p.stderr[-200:]


MUESTRA = ('El catorce de abril, a las tres de la madrugada, alguien tocó la puerta de la casa de los Mendoza. '
           'Nadie abrió. A la mañana siguiente, la puerta estaba abierta... y la familia había desaparecido. '
           'Lo que encontró la policía adentro, todavía no tiene explicación.')


def muestras():
    d = os.path.join(C.DATA, 'muestras'); os.makedirs(d, exist_ok=True)
    hechos = []
    for v in ['es-EC-LuisNeural', 'es-MX-JorgeNeural', 'es-CO-GonzaloNeural']:
        ok, r = edge(MUESTRA, os.path.join(d, f'edge_{v}.mp3'), v)
        print(('✅' if ok else '❌'), 'Microsoft', v, '' if ok else r, flush=True)
        if ok:
            hechos.append(v)
    for v in GEMINI_VOCES:
        ok, r = gemini(MUESTRA, os.path.join(d, f'gemini_{v}.mp3'), v)
        print(('✅' if ok else '❌'), 'Gemini', v, r, flush=True)
        if ok:
            hechos.append(v)
        time.sleep(8)
    return hechos


if __name__ == '__main__':
    muestras()
