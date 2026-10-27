"""Publicación en la página de Facebook (Graph API oficial de Meta)."""
import os, subprocess, time
import requests
import config as C

API = 'https://graph.facebook.com'


def _v():
    return C.get().get('fb_version', 'v23.0')


def activo():
    c = C.get()
    return bool(c.get('fb_page_token') and c.get('fb_page_id'))


def conectar(user_token, nombre_pagina=''):
    """Con un token de usuario (de larga duración) busca la página y guarda su token, que no caduca.
    Devuelve (ok, mensaje)."""
    r = requests.get(f'{API}/{_v()}/me/accounts', params={'access_token': user_token, 'fields': 'id,name,access_token,tasks',
                                                          'limit': 100}, timeout=40).json()
    if 'error' in r:
        return False, 'Facebook dijo: ' + r['error'].get('message', str(r['error']))
    pags = r.get('data', [])
    if not pags:
        return False, 'Ese token no tiene ninguna página. ¿Marcaste los permisos y elegiste la página al generar el token?'
    elegida = None
    nb = nombre_pagina.lower().strip()
    for p in pags:
        if nb and nb in p['name'].lower():
            elegida = p
    if not elegida:
        for p in pags:
            if 'realit' in p['name'].lower():
                elegida = p
    if not elegida:
        return False, 'No encontré la página. Páginas que veo: ' + ', '.join(p['name'] for p in pags)
    C.save(fb_page_id=elegida['id'], fb_page_token=elegida['access_token'], fb_page_nombre=elegida['name'])
    return True, f"Conectado a la página: {elegida['name']}"


def _dur(path):
    try:
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                    capture_output=True, text=True).stdout.strip())
    except Exception:
        return 0.0


def _reel(path, texto):
    c = C.get(); pid, tok = c['fb_page_id'], c['fb_page_token']
    r = requests.post(f'{API}/{_v()}/{pid}/video_reels', data={'upload_phase': 'start', 'access_token': tok}, timeout=60).json()
    if 'video_id' not in r:
        raise RuntimeError(r.get('error', {}).get('message', str(r)))
    vid, url = r['video_id'], r['upload_url']
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        u = requests.post(url, headers={'Authorization': f'OAuth {tok}', 'offset': '0', 'file_size': str(size)},
                          data=f, timeout=600).json()
    if not u.get('success'):
        raise RuntimeError(f'subida: {u}')
    fin = requests.post(f'{API}/{_v()}/{pid}/video_reels', data={
        'upload_phase': 'finish', 'video_id': vid, 'video_state': 'PUBLISHED', 'description': texto,
        'access_token': tok}, timeout=120).json()
    if not fin.get('success'):
        raise RuntimeError(fin.get('error', {}).get('message', str(fin)))
    return vid


def _video(path, texto, titulo):
    c = C.get(); pid, tok = c['fb_page_id'], c['fb_page_token']
    with open(path, 'rb') as f:
        r = requests.post(f'https://graph-video.facebook.com/{_v()}/{pid}/videos',
                          data={'description': texto, 'title': titulo[:100], 'access_token': tok},
                          files={'source': ('clip.mp4', f, 'video/mp4')}, timeout=900).json()
    if 'id' not in r:
        raise RuntimeError(r.get('error', {}).get('message', str(r)))
    return r['id']


def publicar(path, texto, titulo=''):
    """Reel si dura hasta 90 s (límite de Facebook para reels por API); video normal si es más largo.
    Devuelve (ok, id_o_error)."""
    if not activo():
        return False, 'Facebook no está conectado'
    try:
        if _dur(path) <= 90:
            return True, _reel(path, texto)
        return True, _video(path, texto, titulo)
    except Exception as e:
        return False, str(e)[:300]
