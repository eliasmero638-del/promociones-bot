"""Publicación en la página de Facebook (Graph API oficial de Meta)."""
import html, os, subprocess, tempfile, threading, time
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


def conectar_nueva(user_token):
    """25-nov: cuentas NUEVAS (Ridmer Historias). Se guardan aparte en 'fb_nuevas' para no tocar Ridmer TV ni
    Pasión por los Realities. Busca también el Instagram profesional conectado a cada página."""
    r = requests.get(f'{API}/{_v()}/me/accounts', params={
        'access_token': user_token, 'limit': 100,
        'fields': 'id,name,access_token,instagram_business_account{id,username}'}, timeout=40).json()
    if 'error' in r:
        return False, 'Facebook dijo: ' + r['error'].get('message', str(r['error']))
    pags = r.get('data', [])
    if not pags:
        return False, 'Ese token no tiene ninguna página. Al generar el token, marca los permisos y elige la página nueva.'
    viejas = set((C.get().get('fb_paginas') or {}).keys())
    nuevas = {}
    for p in pags:
        if p['id'] in viejas:
            continue
        ig = p.get('instagram_business_account') or {}
        nuevas[p['id']] = {'nombre': p['name'], 'token': p['access_token'], 'ig_id': ig.get('id', ''),
                           'ig_usuario': ig.get('username', '')}
    if not nuevas:
        return False, 'Solo encontré páginas que ya estaban conectadas. ¿Elegiste la página nueva al dar permisos?'
    C.save(fb_nuevas=nuevas)
    # ¿el token de la página dura para siempre?
    dura = ''
    try:
        pid, d = next(iter(nuevas.items()))
        x = requests.get(f'{API}/{_v()}/debug_token', params={'input_token': d['token'], 'access_token': d['token']},
                         timeout=30).json().get('data', {})
        dura = ' · token permanente ✅' if not x.get('expires_at') else ' · ⚠️ el token VENCE (hay que ampliarlo)'
    except Exception:
        pass
    return True, '\n'.join(f"📘 {d['nombre']} · 📸 Instagram: " + (('@' + d['ig_usuario']) if d['ig_id'] else '❌ no conectado')
                           for d in nuevas.values()) + dura


def nueva():
    """(page_id, token, nombre, ig_id) de la página nueva, o Nones."""
    for pid, d in (C.get().get('fb_nuevas') or {}).items():
        return pid, d['token'], d['nombre'], d.get('ig_id', '')
    return None, None, None, None


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
    """26-nov: subida por partes (reanudable). La subida de un solo golpe fallaba con videos grandes (resumen de 9 min)."""
    U = f'https://graph-video.facebook.com/{_v()}/{pid}/videos'

    def _j(r):
        try:
            return r.json()
        except Exception:
            raise RuntimeError(f'Facebook respondió {r.status_code}: {r.text[:150]}')
    tam = os.path.getsize(path)
    r = _j(requests.post(U, data={'upload_phase': 'start', 'file_size': tam, 'access_token': tok}, timeout=120))
    if 'upload_session_id' not in r:
        raise RuntimeError(r.get('error', {}).get('message', str(r)))
    ses, ini, fin = r['upload_session_id'], int(r['start_offset']), int(r['end_offset'])
    with open(path, 'rb') as f:
        while ini < fin:
            f.seek(ini)
            trozo = f.read(fin - ini)
            for intento in range(4):
                try:
                    r = _j(requests.post(U, data={'upload_phase': 'transfer', 'upload_session_id': ses, 'start_offset': ini,
                                                  'access_token': tok},
                                         files={'video_file_chunk': ('trozo', trozo, 'application/octet-stream')}, timeout=600))
                    if 'start_offset' in r:
                        break
                    raise RuntimeError(r.get('error', {}).get('message', str(r)))
                except Exception:
                    if intento == 3:
                        raise
                    time.sleep(10 * (intento + 1))
            ini, fin = int(r['start_offset']), int(r['end_offset'])
    r = _j(requests.post(U, data={'upload_phase': 'finish', 'upload_session_id': ses, 'access_token': tok,
                                  'description': texto, 'title': titulo[:100]}, timeout=120))
    if not r.get('success'):
        raise RuntimeError(r.get('error', {}).get('message', str(r)))
    return r.get('video_id') or ses


def publicar(path, texto, titulo='', clave=None):
    """Reel si dura hasta 90 s (límite de Facebook para reels por API); video normal si es más largo.
    Devuelve (ok, id_o_error)."""
    pid, tok, _ = pagina(clave)
    if not (pid and tok):
        return False, 'Esa página de Facebook no está conectada'
    try:
        if _dur(path) <= 90:
            res = _reel(path, texto, pid, tok)
        else:
            res = _video(path, texto, titulo, pid, tok)
        _a_historias(clave, path, False)
        return True, res
    except Exception as e:
        return False, str(e)[:300]


def diagnostico():
    """Qué ve Facebook de los últimos videos de cada página: estado, privacidad, derechos de autor, app que publicó."""
    c = C.get()
    out = []
    for pid, d in (c.get('fb_paginas') or {}).items():
        tok = d['token']
        out.append(f"📘 <b>{d['nombre']}</b>")
        try:
            dbg = requests.get(f'{API}/{_v()}/debug_token', params={'input_token': tok, 'access_token': tok}, timeout=30).json()
            dd = dbg.get('data', {})
            out.append(f"  token: válido={dd.get('is_valid')} app={dd.get('application', '?')} permisos={','.join(dd.get('scopes', []))[:160]}")
        except Exception as e:
            out.append(f'  token: error {e}')
        for edge in ('video_reels', 'videos'):
            try:
                r = requests.get(f'{API}/{_v()}/{pid}/{edge}', timeout=40, params={
                    'access_token': tok, 'limit': 6,
                    'fields': 'id,created_time,description,published,privacy,status,permalink_url,application'}).json()
            except Exception as e:
                out.append(f'  {edge}: error {e}'); continue
            if 'error' in r:
                out.append(f"  {edge}: error {html.escape(r['error'].get('message', '')[:200])}"); continue
            out.append(f'  — {edge} —')
            for v in r.get('data', []):
                st = v.get('status') or {}
                pub = (st.get('publishing_phase') or {})
                out.append(f"  • {v.get('created_time', '')[:16]} {html.escape(str(v.get('description', ''))[:35])}\n"
                           f"    publicado={v.get('published')} privacidad={(v.get('privacy') or {}).get('value')} "
                           f"estado={st.get('video_status')} pub={pub.get('status')}/{pub.get('publish_status')} "
                           f"copyright={st.get('copyright_check_status', {}).get('status') if isinstance(st.get('copyright_check_status'), dict) else st.get('copyright_check_status')} "
                           f"app={(v.get('application') or {}).get('name')}")
    return '\n'.join(out) or 'No hay páginas conectadas.'


def publicar_foto(path, texto, clave=None):
    """11-nov: publicación de FOTO con texto (Facebook también paga las fotos con la monetización de contenido)."""
    pid, tok, _ = pagina(clave)
    if not (pid and tok):
        return False, 'Esa página de Facebook no está conectada'
    try:
        with open(path, 'rb') as f:
            r = requests.post(f'{API}/{_v()}/{pid}/photos', data={'message': texto, 'access_token': tok, 'published': 'true'},
                              files={'source': f}, timeout=120).json()
        if 'id' not in r:
            return False, str(r.get('error', r))[:300]
        _a_historias(clave, path, True)
        return True, r.get('post_id') or r['id']
    except Exception as e:
        return False, str(e)[:300]


# ---------- 12-nov: todo lo que se publica en Ridmer TV también va a sus HISTORIAS (pedido del dueño) ----------
HISTORIAS = []          # últimas historias: (hora, página, ok, detalle) para /historias


def _a_historias(clave, path, es_foto):
    """En segundo plano, para no demorar la publicación. Páginas: config 'historias_paginas' (por defecto solo Ridmer TV)."""
    c = C.get()
    if not c.get('historias', True):
        return
    nombre = (clave or 'realities').lower()
    if not any(p.lower() in nombre or nombre in p.lower() for p in c.get('historias_paginas', ['ridmer'])):
        return
    threading.Thread(target=publicar_historia, args=(path, clave, es_foto), daemon=True).start()


def _banda(ancho, alto, texto):
    """PNG transparente con una franja amarilla abajo: 'MIRA EL VIDEO COMPLETO EN LA PÁGINA'."""
    from PIL import Image, ImageDraw, ImageFont
    letra = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'InterDisplay-Black.otf')
    im = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    tam = int(ancho * 0.062)
    f = ImageFont.truetype(letra, tam) if os.path.exists(letra) else ImageFont.load_default()
    lineas = texto.split('\n')
    h = int(len(lineas) * tam * 1.25 + tam)
    y0 = int(alto * 0.80)
    d.rectangle([0, y0, ancho, y0 + h], fill=(255, 214, 0, 240))
    y = y0 + tam // 2
    for l in lineas:
        d.text(((ancho - d.textlength(l, font=f)) / 2, y), l, font=f, fill=(15, 15, 15, 255)); y += int(tam * 1.25)
    p = tempfile.mktemp(suffix='.png'); im.save(p); return p


def publicar_historia(path, clave=None, es_foto=False):
    """12-nov (corregido por el dueño): la historia NO lleva el video completo. Video → los primeros 10 s (el enganche)
    con una franja 'MIRA EL VIDEO COMPLETO EN LA PÁGINA'. Foto → la misma foto con la franja."""
    pid, tok, nombre = pagina(clave)
    ok, det = False, ''
    tmp = []
    try:
        if not (pid and tok):
            raise RuntimeError('página no conectada')
        if es_foto:
            from PIL import Image
            im = Image.open(path).convert('RGB')
            fondo = Image.new('RGB', (1080, 1920), (12, 12, 14))
            im.thumbnail((1080, 1500)); fondo.paste(im, ((1080 - im.width) // 2, (1920 - im.height) // 2 - 120))
            b = _banda(1080, 1920, 'MIRA LA HISTORIA COMPLETA\nEN NUESTRA PÁGINA'); tmp.append(b)
            fondo.paste(Image.open(b), (0, 0), Image.open(b))
            src = tempfile.mktemp(suffix='.jpg'); fondo.save(src, quality=90); tmp.append(src)
            with open(src, 'rb') as f:
                r = requests.post(f'{API}/{_v()}/{pid}/photos', data={'published': 'false', 'access_token': tok},
                                  files={'source': f}, timeout=120).json()
            if 'id' not in r:
                raise RuntimeError(str(r.get('error', r))[:200])
            fin = requests.post(f'{API}/{_v()}/{pid}/photo_stories', data={'photo_id': r['id'], 'access_token': tok},
                                timeout=60).json()
        else:
            b = _banda(720, 1280, 'MIRA EL VIDEO COMPLETO\nEN NUESTRA PÁGINA'); tmp.append(b)
            src = tempfile.mktemp(suffix='.mp4'); tmp.append(src)
            fc = ('[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v];'
                  '[v][1:v]overlay=0:0:enable=gte(t\\,1.5),format=yuv420p[o]')
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-t', '10', '-i', path, '-i', b, '-filter_complex', fc,
                            '-map', '[o]', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-t', '10',
                            '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-b:a', '128k', '-af', 'afade=t=out:st=9:d=1',
                            '-movflags', '+faststart', src], check=True, capture_output=True)
            r = requests.post(f'{API}/{_v()}/{pid}/video_stories', data={'upload_phase': 'start', 'access_token': tok},
                              timeout=60).json()
            if 'video_id' not in r:
                raise RuntimeError(str(r.get('error', r))[:200])
            with open(src, 'rb') as f:
                u = requests.post(r['upload_url'], headers={'Authorization': f'OAuth {tok}', 'offset': '0',
                                                            'file_size': str(os.path.getsize(src))}, data=f, timeout=600).json()
            if not u.get('success'):
                raise RuntimeError(f'subida: {u}'[:200])
            fin = requests.post(f'{API}/{_v()}/{pid}/video_stories', data={'upload_phase': 'finish', 'video_id': r['video_id'],
                                                                         'access_token': tok}, timeout=120).json()
        if not fin.get('success'):
            raise RuntimeError(str(fin.get('error', fin))[:200])
        ok, det = True, fin.get('post_id', '')
    except Exception as e:
        det = str(e)[:200]
    for t in tmp:
        try: os.remove(t)
        except Exception: pass
    HISTORIAS.append((time.strftime('%d/%m %H:%M'), nombre or str(clave), ok, det))
    del HISTORIAS[:-10]
    print('[historia]', nombre, 'ok' if ok else 'FALLÓ', det, flush=True)
    return ok, det
