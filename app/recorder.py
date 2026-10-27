"""Grabador: busca el en vivo actual del canal, lo graba en pedazos y guarda el chat."""
import calendar, glob, json, os, re, shutil, subprocess, sys, threading, time
import config as C

YTDLP = [sys.executable, '-m', 'yt_dlp']
estado = {'video': None, 'titulo': None, 'grabando': False, 'desde': None, 'error': None}
_procs = []


def log(*a):
    print(time.strftime('%H:%M:%S'), '[grabador]', *a, flush=True)


def ytdlp_base():
    b = YTDLP + ['--no-warnings', '--quiet']
    if os.path.exists(C.COOKIES):
        b += ['--cookies', C.COOKIES]
    return b


def en_vivo_actual():
    """Devuelve (id, titulo) del en vivo activo del canal, o (None, None)."""
    canal = C.get()['canal']
    try:
        out = subprocess.run(ytdlp_base() + ['--flat-playlist', '--playlist-end', '6',
                             '--print', '%(id)s\t%(live_status)s\t%(title)s', canal],
                             capture_output=True, text=True, timeout=120).stdout
    except Exception as e:
        estado['error'] = f'listar canal: {e}'
        return None, None
    for line in out.splitlines():
        p = line.split('\t')
        if len(p) >= 3 and p[1] == 'is_live':
            return p[0], p[2]
    return None, None


def _matar():
    for p in _procs:
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(2)
    for p in _procs:
        try:
            p.kill()
        except Exception:
            pass
    _procs.clear()


def _grabar(vid):
    """Video+audio → pedazos .ts con la hora en el nombre. Chat → chat/VID.live_chat.json"""
    url = f'https://www.youtube.com/watch?v={vid}'
    seg = str(C.get()['segmento_seg'])
    y = subprocess.Popen(ytdlp_base() + ['-f', 'best[height<=720]/best', '--hls-use-mpegts', '-o', '-', url],
                         stdout=subprocess.PIPE, stderr=open(os.path.join(C.DATA, 'ytdlp.log'), 'a'))
    f = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-map', '0:v:0?', '-map', '0:a:0?', '-c', 'copy',
                          '-f', 'segment', '-segment_time', seg, '-segment_format', 'mpegts', '-reset_timestamps', '1',
                          '-strftime', '1', os.path.join(C.REC, '%Y%m%d_%H%M%S.ts')],
                         stdin=y.stdout, stderr=open(os.path.join(C.DATA, 'ffmpeg_rec.log'), 'a'))
    y.stdout.close()
    chat_dir = os.path.join(C.DATA, 'chat'); os.makedirs(chat_dir, exist_ok=True)
    ch = subprocess.Popen(ytdlp_base() + ['--skip-download', '--write-subs', '--sub-langs', 'live_chat',
                                         '-o', os.path.join(chat_dir, vid), url],
                          stdout=subprocess.DEVNULL, stderr=open(os.path.join(C.DATA, 'chat.log'), 'a'))
    _procs.extend([y, f, ch])
    return y, f


def limpiar():
    lim = time.time() - C.get()['guardar_horas'] * 3600
    for p in glob.glob(os.path.join(C.REC, '*.ts')):
        if os.path.getmtime(p) < lim:
            os.remove(p)
    for p in glob.glob(os.path.join(C.CLIPS, '*')):
        if os.path.getmtime(p) < time.time() - 2 * 86400:
            os.remove(p) if os.path.isfile(p) else shutil.rmtree(p, ignore_errors=True)


def bucle():
    """Mantiene grabando el en vivo actual. Cada 5 min revisa si cambió (el canal abre uno nuevo cada ~12 h)."""
    actual, procs, ult_rev = None, None, 0
    while True:
        try:
            limpiar()
            if time.time() - ult_rev > 300 or procs is None or procs[0].poll() is not None:
                ult_rev = time.time()
                vid, tit = en_vivo_actual()
                if vid and (vid != actual or procs is None or procs[0].poll() is not None):
                    _matar()
                    log('grabando', vid, tit)
                    procs = _grabar(vid)
                    actual = vid
                    estado.update(video=vid, titulo=tit, grabando=True, desde=time.time(), error=None)
                elif not vid:
                    if procs is not None:
                        _matar(); procs = None
                    estado.update(grabando=False)
                    if not estado.get('error'):
                        estado['error'] = 'no hay en vivo ahora'
        except Exception as e:
            estado['error'] = str(e)
            log('error', e)
        time.sleep(20)


def bucle_remoto():
    """El teléfono graba y sube pedazos a REC y el chat a chat/. Aquí solo leemos su estado."""
    f = os.path.join(C.DATA, 'remoto.json')
    while True:
        try:
            limpiar()
            d = json.load(open(f)) if os.path.exists(f) else {}
            vivo = d.get('grabando') and time.time() - d.get('hora', 0) < 300
            estado.update(video=d.get('video'), titulo=d.get('titulo'), grabando=bool(vivo),
                          error=None if vivo else 'el teléfono no está enviando grabación')
        except Exception as e:
            estado['error'] = f'remoto: {e}'
        time.sleep(15)


def iniciar():
    fn = bucle_remoto if C.get().get('modo') == 'remoto' else bucle
    threading.Thread(target=fn, daemon=True).start()


def pedazos():
    """Pedazos terminados (todos menos el que se está escribiendo), ordenados."""
    fs = sorted(glob.glob(os.path.join(C.REC, '*.ts')))
    if C.get().get('modo') == 'remoto':
        return [p for p in fs if time.time() - os.path.getmtime(p) > 5]
    return fs[:-1] if estado['grabando'] else fs


def pedazo_inicio(path):
    m = re.search(r'(\d{8}_\d{6})', os.path.basename(path))
    return calendar.timegm(time.strptime(m.group(1), '%Y%m%d_%H%M%S')) if m else os.path.getctime(path)


def chat_mensajes(desde, hasta):
    """Mensajes del chat (hora, texto) entre dos horas (epoch)."""
    out = []
    vid = estado.get('video')
    if not vid:
        return out
    for p in glob.glob(os.path.join(C.DATA, 'chat', vid + '*live_chat*')):
        try:
            with open(p, encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if '"timestampUsec"' not in line:
                        continue
                    for ts, txt in _extraer(line):
                        if desde <= ts <= hasta:
                            out.append((ts, txt))
        except Exception:
            pass
    return out


def _extraer(line):
    try:
        d = json.loads(line)
    except Exception:
        return []
    res = []

    def walk(o):
        if isinstance(o, dict):
            if 'timestampUsec' in o and 'message' in o:
                txt = ''.join(r.get('text', '') or r.get('emoji', {}).get('shortcuts', [''])[0]
                              for r in o['message'].get('runs', []))
                res.append((int(o['timestampUsec']) / 1e6, txt))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return res
