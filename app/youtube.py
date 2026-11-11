"""Subida automática a YouTube con la API oficial (11-nov, pedido del dueño).
Conexión con "código de dispositivo": el dueño abre google.com/device en el celular y pone un código; no hace falta
ninguna página con https. Las llaves y el permiso se guardan SOLO en el servidor (DATA/secrets), nunca en GitHub.
Mientras Google no apruebe la auditoría del proyecto, YouTube deja los videos subidos por la API en privado."""
import json, os, time
from datetime import datetime, timezone
import requests
import config as C

ALCANCE = 'https://www.googleapis.com/auth/youtube'
_tok = {'access': '', 'vence': 0}


def conectado():
    c = C.get()
    return bool(c.get('yt_client_id') and c.get('yt_client_secret') and c.get('yt_refresh'))


def pedir_codigo():
    """Paso 1: devuelve (codigo_para_el_dueño, url, device_code, intervalo)."""
    c = C.get()
    r = requests.post('https://oauth2.googleapis.com/device/code',
                      data={'client_id': c['yt_client_id'], 'scope': ALCANCE}, timeout=30).json()
    if 'user_code' not in r:
        raise RuntimeError(r.get('error_description') or r.get('error') or str(r))
    return r['user_code'], r.get('verification_url', 'https://www.google.com/device'), r['device_code'], \
        int(r.get('interval', 5)), int(r.get('expires_in', 1800))


def esperar_permiso(device_code, intervalo, vence):
    """Paso 2: espera a que el dueño acepte; guarda el permiso (refresh token)."""
    c = C.get()
    fin = time.time() + vence
    while time.time() < fin:
        time.sleep(intervalo)
        r = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': c['yt_client_id'], 'client_secret': c['yt_client_secret'], 'device_code': device_code,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'}, timeout=30).json()
        if r.get('refresh_token'):
            C.save(yt_refresh=r['refresh_token'])
            _tok.update(access=r['access_token'], vence=time.time() + int(r.get('expires_in', 3600)) - 60)
            return True
        err = r.get('error')
        if err == 'slow_down':
            intervalo += 5
        elif err != 'authorization_pending':
            raise RuntimeError(r.get('error_description') or err or str(r))
    return False


def _acceso():
    if _tok['access'] and time.time() < _tok['vence']:
        return _tok['access']
    c = C.get()
    r = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': c['yt_client_id'], 'client_secret': c['yt_client_secret'], 'refresh_token': c['yt_refresh'],
        'grant_type': 'refresh_token'}, timeout=30).json()
    if 'access_token' not in r:
        raise RuntimeError('permiso de YouTube vencido o quitado: ' + str(r.get('error_description') or r))
    _tok.update(access=r['access_token'], vence=time.time() + int(r.get('expires_in', 3600)) - 60)
    return _tok['access']


def canal():
    h = {'Authorization': 'Bearer ' + _acceso()}
    r = requests.get('https://www.googleapis.com/youtube/v3/channels', params={'part': 'snippet,statistics', 'mine': 'true'},
                     headers=h, timeout=30).json()
    it = (r.get('items') or [{}])[0]
    return it.get('snippet', {}).get('title', '?'), it.get('statistics', {}).get('subscriberCount', '?')


def subir(video, titulo, descripcion, etiquetas, publicar_en=None, miniatura=None, privado=False):
    """Sube el video. publicar_en (epoch) = programado; si ya pasó la hora, público al instante.
    Devuelve el id del video."""
    h = {'Authorization': 'Bearer ' + _acceso()}
    status = {'selfDeclaredMadeForKids': False, 'embeddable': True}
    if privado:
        status['privacyStatus'] = 'private'
    elif publicar_en and publicar_en - time.time() > 900:
        status['privacyStatus'] = 'private'
        status['publishAt'] = datetime.fromtimestamp(publicar_en, timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    else:
        status['privacyStatus'] = 'public'
    cuerpo = {'snippet': {'title': titulo[:100], 'description': descripcion[:4900],
                          'tags': [t[:30] for t in (etiquetas or [])][:25], 'categoryId': '24',
                          'defaultLanguage': 'es', 'defaultAudioLanguage': 'es'},
              'status': status}
    tam = os.path.getsize(video)
    r = requests.post('https://www.googleapis.com/upload/youtube/v3/videos',
                      params={'uploadType': 'resumable', 'part': 'snippet,status'},
                      headers=dict(h, **{'Content-Type': 'application/json; charset=UTF-8',
                                         'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(tam)}),
                      data=json.dumps(cuerpo), timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f'YouTube no aceptó el video ({r.status_code}): {r.text[:300]}')
    url = r.headers['Location']
    with open(video, 'rb') as f:
        r = requests.put(url, data=f, headers=dict(h, **{'Content-Type': 'video/mp4'}), timeout=3600)
    if r.status_code >= 300:
        raise RuntimeError(f'falló la subida ({r.status_code}): {r.text[:300]}')
    vid = r.json()['id']
    if miniatura and os.path.exists(miniatura):
        try:
            with open(miniatura, 'rb') as f:
                requests.post('https://www.googleapis.com/upload/youtube/v3/thumbnails/set', params={'videoId': vid},
                              headers=dict(h, **{'Content-Type': 'image/jpeg'}), data=f, timeout=120)
        except Exception:
            pass
    return vid


def poner_portada(vid, imagen):
    """Cambia la portada de un video ya subido (el dueño la manda por el bot)."""
    from PIL import Image, ImageOps
    tmp = imagen + '_yt.jpg'
    ImageOps.fit(Image.open(imagen).convert('RGB'), (1280, 720)).save(tmp, quality=92)
    h = {'Authorization': 'Bearer ' + _acceso()}
    with open(tmp, 'rb') as f:
        r = requests.post('https://www.googleapis.com/upload/youtube/v3/thumbnails/set', params={'videoId': vid},
                          headers=dict(h, **{'Content-Type': 'image/jpeg'}), data=f, timeout=120)
    if r.status_code >= 300:
        raise RuntimeError(f'YouTube no aceptó la portada ({r.status_code}): {r.text[:300]}')


def canal_id():
    h = {'Authorization': 'Bearer ' + _acceso()}
    r = requests.get('https://www.googleapis.com/youtube/v3/channels', params={'part': 'id', 'mine': 'true'},
                     headers=h, timeout=30).json()
    return (r.get('items') or [{}])[0].get('id', '?')


def estados(ids):
    """{id: {'privacidad': 'public'|'private'|'unlisted', 'publicar_en': iso|None, 'titulo': ...}}"""
    if not ids:
        return {}
    h = {'Authorization': 'Bearer ' + _acceso()}
    r = requests.get('https://www.googleapis.com/youtube/v3/videos', params={'part': 'status,snippet', 'id': ','.join(ids[:50])},
                     headers=h, timeout=30).json()
    return {it['id']: {'privacidad': it['status'].get('privacyStatus'), 'publicar_en': it['status'].get('publishAt'),
                       'titulo': it['snippet'].get('title')} for it in r.get('items', [])}
