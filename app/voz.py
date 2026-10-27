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
        return (('flash' in n), v)
    lista = sorted(set(lista), key=orden, reverse=True)
    _mod = lista + [m for m in RESPALDO if m not in lista]
    return _mod


def gemini(texto, salida_mp3, voz='Charon', estilo=ESTILO):
    key = C.get().get('gemini_key')
    if not key:
        return False, 'sin clave de Gemini'
    ult = ''
    for m in modelos_tts(key)[:3]:
        for intento in range(3):
            try:
                r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                                  params={'key': key}, timeout=300, json={
                                      'contents': [{'parts': [{'text': estilo + texto}]}],
                                      'generationConfig': {'responseModalities': ['AUDIO'], 'speechConfig': {
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


def edge(texto, salida_mp3, voz='es-EC-LuisNeural'):
    p = subprocess.run([sys.executable, '-m', 'edge_tts', '--voice', voz, '--rate', '-5%', '--text', texto,
                        '--write-media', salida_mp3], capture_output=True, text=True, timeout=300)
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
