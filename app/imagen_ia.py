"""Ilustraciones con IA usando la misma clave de Gemini (escena tipo 'ia' del plan): el plan trae la descripción de la
escena y el estilo; aquí se pide la imagen y se guarda como jpg. Si falla, se devuelve None (el editor usa otra cosa)."""
import base64, io, re, time
import requests
import config as C

API = 'https://generativelanguage.googleapis.com/v1beta/models'
RESPALDO = ['gemini-2.5-flash-image', 'gemini-2.5-flash-image-preview', 'gemini-2.0-flash-preview-image-generation']
_mod = None


def modelos(key):
    global _mod
    if _mod:
        return _mod
    lista = []
    try:
        r = requests.get(API, params={'key': key, 'pageSize': 300}, timeout=30).json()
        lista = [m['name'].split('/')[-1] for m in r.get('models', [])
                 if 'image' in m['name'] and 'generateContent' in m.get('supportedGenerationMethods', [])]
    except Exception:
        pass
    _mod = [m for m in RESPALDO if m in lista] + [m for m in lista if m not in RESPALDO] or RESPALDO
    return _mod


def generar(descripcion, salida_jpg, formato='9:16'):
    """Devuelve (ok, modelo_o_error)."""
    from PIL import Image
    key = C.get().get('gemini_key')
    if not key:
        return False, 'sin clave de Gemini'
    ult = ''
    for m in modelos(key)[:3]:
        for intento in range(3):
            try:
                cuerpo = {'contents': [{'parts': [{'text': descripcion}]}],
                          'generationConfig': {'responseModalities': ['TEXT', 'IMAGE'],
                                               'imageConfig': {'aspectRatio': formato}}}
                r = requests.post(f'{API}/{m}:generateContent', params={'key': key}, json=cuerpo, timeout=300)
                if r.status_code == 400 and 'imageConfig' in r.text:          # modelos viejos sin imageConfig
                    cuerpo['generationConfig'].pop('imageConfig')
                    r = requests.post(f'{API}/{m}:generateContent', params={'key': key}, json=cuerpo, timeout=300)
                if r.status_code == 429:
                    ult = f'{m}: límite'; time.sleep(25 * (intento + 1)); continue
                if r.status_code != 200:
                    ult = f'{m}: {r.status_code} {r.text[:200]}'; break
                for p in r.json()['candidates'][0]['content']['parts']:
                    if 'inlineData' in p:
                        im = Image.open(io.BytesIO(base64.b64decode(p['inlineData']['data']))).convert('RGB')
                        im.save(salida_jpg, quality=92)
                        return True, m
                ult = f'{m}: sin imagen'; break
            except Exception as e:
                ult = f'{m}: {e}'; break
    return False, ult
