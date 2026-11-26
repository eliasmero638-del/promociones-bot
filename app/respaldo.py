"""25-nov: RESPALDO de los videos para resubirlos en las cuentas nuevas (pedido del dueño).
- Facebook (Ridmer TV): todos los videos desde que empezó el 3D (13-nov 18:00) se bajan con la API de la página.
- YouTube: Shorts desde el 14-nov y TODOS los videos largos. YouTube bloquea al servidor, así que los baja el teléfono
  (pedidos_video/yt_<id>.txt con "URL todo todo") y los sube a videos_listos/; de ahí se mueven a respaldo/yt/.
- Lo que todavía está en el servidor (últimos 4 días) se copia tal cual, en su calidad original.
Cada video queda con su .json (título, texto, fecha) para programarlo después.
"""
import glob, json, os, re, shutil, threading, time
import requests
import config as C, fb, tg

D = os.path.join(C.DATA, 'respaldo')
INICIO_3D = time.mktime(time.strptime('2026-11-13 18:00', '%Y-%m-%d %H:%M'))
NO_LARGOS = ('irán se prepara',)          # noticia vieja


def log(*a):
    print(time.strftime('%H:%M:%S'), '[respaldo]', *a, flush=True)


def _bajar(url, dst):
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dst + '.part', 'wb') as f:
            for ch in r.iter_content(1 << 20):
                f.write(ch)
    os.replace(dst + '.part', dst)


def facebook():
    pid, tok, _ = fb.pagina('ridmer')
    if not (pid and tok):
        log('Ridmer TV no está conectada'); return 0
    out = os.path.join(D, 'fb'); os.makedirs(out, exist_ok=True)
    url = f'https://graph.facebook.com/v21.0/{pid}/videos'
    params = {'access_token': tok, 'limit': 50, 'fields': 'id,title,description,created_time,length,source,permalink_url'}
    n = 0
    while url:
        r = requests.get(url, params=params, timeout=60).json()
        params = None
        for v in r.get('data', []):
            t = time.mktime(time.strptime(v['created_time'][:19], '%Y-%m-%dT%H:%M:%S')) - time.timezone
            if t < INICIO_3D:
                return n
            base = os.path.join(out, time.strftime('%Y%m%d_%H%M', time.localtime(t)) + '_' + v['id'])
            json.dump({**{k: v.get(k) for k in ('id', 'title', 'description', 'created_time', 'length', 'permalink_url')},
                       'origen': 'facebook Ridmer TV'}, open(base + '.json', 'w'), ensure_ascii=False, indent=1)
            if not os.path.exists(base + '.mp4') and v.get('source'):
                try:
                    _bajar(v['source'], base + '.mp4'); n += 1
                except Exception as e:
                    log('no pude bajar', v['id'], e)
        url = (r.get('paging') or {}).get('next')
    return n


def _videos_youtube():
    import youtube as YT
    h = {'Authorization': 'Bearer ' + YT._acceso()}
    G = lambda u, **p: requests.get('https://www.googleapis.com/youtube/v3/' + u, params=p, headers=h, timeout=30).json()
    ch = (G('channels', part='contentDetails', mine='true').get('items') or [{}])[0]
    up = ch['contentDetails']['relatedPlaylists']['uploads']
    ids, tok = [], None
    while True:
        r = G('playlistItems', part='contentDetails', playlistId=up, maxResults=50, **({'pageToken': tok} if tok else {}))
        ids += [it['contentDetails']['videoId'] for it in r.get('items', [])]
        tok = r.get('nextPageToken')
        if not tok or len(ids) >= 400:
            break
    vids = []
    for i in range(0, len(ids), 50):
        for it in G('videos', part='snippet,contentDetails', id=','.join(ids[i:i + 50])).get('items', []):
            m = re.match(r'P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', it['contentDetails']['duration'])
            seg = sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1))) if m else 0
            t = time.mktime(time.strptime(it['snippet']['publishedAt'][:19], '%Y-%m-%dT%H:%M:%S')) - time.timezone
            vids.append({'id': it['id'], 'titulo': it['snippet']['title'], 'descripcion': it['snippet'].get('description', ''),
                         'tags': it['snippet'].get('tags', []), 'publicado': it['snippet']['publishedAt'], 't': t, 'seg': seg})
    return vids


def youtube():
    out = os.path.join(D, 'yt'); os.makedirs(out, exist_ok=True)
    ped = os.path.join(C.DATA, 'pedidos_video'); lis = os.path.join(C.DATA, 'videos_listos')
    os.makedirs(ped, exist_ok=True); os.makedirs(lis, exist_ok=True)
    elegidos = []
    for v in _videos_youtube():
        largo = v['seg'] > 180
        if largo and not any(x in v['titulo'].lower() for x in NO_LARGOS) and v['t'] > time.time() - 120 * 86400:
            v['tipo'] = 'largo'
        elif not largo and v['t'] >= INICIO_3D:
            v['tipo'] = 'short'
        else:
            continue
        elegidos.append(v)
    pend = 0
    for v in elegidos:
        base = os.path.join(out, f"{v['tipo']}_{v['publicado'][:10]}_{v['id']}")
        json.dump(v, open(base + '.json', 'w'), ensure_ascii=False, indent=1)
        listo = os.path.join(lis, f"yt_{v['id']}.mp4")
        if os.path.exists(base + '.mp4'):
            continue
        if os.path.exists(listo) and time.time() - os.path.getmtime(listo) > 10:
            shutil.move(listo, base + '.mp4')
            try:
                os.remove(os.path.join(ped, f"yt_{v['id']}.txt"))
            except Exception:
                pass
            continue
        if not os.path.exists(os.path.join(lis, f"yt_{v['id']}.falla")):
            open(os.path.join(ped, f"yt_{v['id']}.txt"), 'w').write(f"https://www.youtube.com/watch?v={v['id']} todo todo\n")
            pend += 1
    return len(elegidos), pend


def servidor():
    """Lo que el servidor todavía tiene (últimos 4 días) en su calidad original."""
    import fabrica as F
    out = os.path.join(D, 'servidor'); os.makedirs(out, exist_ok=True)
    n = 0
    for jid in os.listdir(F.DIR):
        m = F._leer(os.path.join(F.DIR, jid, 'meta.json'), None)
        if not m or not (m.get('archivos') or {}).get('video'):
            continue
        src = os.path.join(F.DIR, jid, m['archivos']['video'])
        if os.path.exists(src) and not os.path.exists(os.path.join(out, jid + '.mp4')):
            shutil.copy2(src, os.path.join(out, jid + '.mp4'))
            json.dump(m, open(os.path.join(out, jid + '.json'), 'w'), ensure_ascii=False, indent=1, default=str)
            n += 1
    return n


def resumen_txt():
    c = lambda pat: len(glob.glob(os.path.join(D, pat)))
    return (f"Facebook {c('fb/*.mp4')} · Shorts {c('yt/short_*.mp4')}/{c('yt/short_*.json')} · "
            f"Largos {c('yt/largo_*.mp4')}/{c('yt/largo_*.json')} · del servidor {c('servidor/*.mp4')}")


def bucle():
    marca = os.path.join(D, 'listo_avisado')
    os.makedirs(D, exist_ok=True)
    if os.path.exists(marca):
        return
    try:
        log('servidor', servidor())
        log('facebook', facebook())
    except Exception as e:
        log('error', e)
    while True:
        try:
            total, pend = youtube()
            log('youtube', total, 'pendientes', pend, '|', resumen_txt())
            if pend == 0 and total:
                tg.texto('📦 RESPALDO LISTO para las cuentas nuevas: ' + resumen_txt())
                open(marca, 'w').write(time.strftime('%F %T'))
                return
        except Exception as e:
            log('error youtube', e)
        time.sleep(300)
