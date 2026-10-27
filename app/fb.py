"""Publicación en la página de Facebook (Graph API oficial de Meta)."""
import os, subprocess, time
import requests
import config as C

API = 'https://graph.facebook.com'


def _v():
    return C.get().get('fb_version', 'v23.0')


def pagina(clave=None):
    """(id, token, nombre) de la página. clave=None → la de realities; 'ridmer' → Ridmer TV."""
    c = C.get()
    if clave:
        for pid, d in (c.get('fb_paginas') or {}).items():
            if clave.lower() in d['nombre'].lower():
                return pid, d['token'], d['nombre']
        return None, None, None
    return c.get('fb_page_id'), c.get('fb_page_token'), c.get('fb_page_nombre', '')


def activo(clave=None):
    pid, tok, _ = pagina(clave)
    return bool(pid and tok)


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
        elegida = pags[0]
    todas = {p['id']: {'nombre': p['name'], 'token': p['access_token']} for p in pags}
    C.save(fb_page_id=elegida['id'], fb_page_token=elegida['access_token'], fb_page_nombre=elegida['name'],
           fb_paginas=todas)
    return True, 'Conectado a: ' + ', '.join(p['name'] for p in pags)


def _dur(path):
    try:
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                    capture_output=True, text=True).stdout.strip())
    except Exception:
        return 0.0


def _reel(path, texto, pid, tok):
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


def _video(path, texto, titulo, pid, tok):
    with open(path, 'rb') as f:
        r = requests.post(f'https://graph-video.facebook.com/{_v()}/{pid}/videos',
                          data={'description': texto, 'title': titulo[:100], 'access_token': tok},
                          files={'source': ('clip.mp4', f, 'video/mp4')}, timeout=900).json()
    if 'id' not in r:
        raise RuntimeError(r.get('error', {}).get('message', str(r)))
    return r['id']


def publicar(path, texto, titulo='', clave=None):
    """Reel si dura hasta 90 s (límite de Facebook para reels por API); video normal si es más largo.
    Devuelve (ok, id_o_error)."""
    pid, tok, _ = pagina(clave)
    if not (pid and tok):
        return False, 'Esa página de Facebook no está conectada'
    try:
        if _dur(path) <= 90:
            return True, _reel(path, texto, pid, tok)
        return True, _video(path, texto, titulo, pid, tok)
    except Exception as e:
        return False, str(e)[:300]
