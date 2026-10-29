"""Producción Ridmer con Claude como editor.
2:00  radar.preparar_dia()  → encargos (tema + texto fuente + fotos candidatas numeradas)
5:30  Claude (tarea programada) lee los encargos y escribe el PLAN de edición en la rama `planes` de GitHub
luego el servidor baja el plan, hace la voz (Algenib), arma Facebook / Short / largo con las decisiones de Claude
y los entrega a su hora: Facebook se avisa 20 min antes y se publica solo; YouTube se avisa para subir a mano."""
import json, os, re, secrets, shutil, threading, time
import requests
import config as C, montaje, editor, fb, tg, ntfy, radar
import fabrica as F

PLANES_URL = 'https://raw.githubusercontent.com/eliasmero638-del/promociones-bot/planes/planes/{fecha}.json'
HECHOS = os.path.join(F.DIR, 'planes_hechos.json')
ESTADO = os.path.join(F.DIR, 'produccion_estado.json')
_lock = threading.Lock()


def log(*a):
    print(time.strftime('%H:%M:%S'), '[produccion]', *a, flush=True)


def _epoch(fecha, hora):
    try:
        return time.mktime(time.strptime(f'{fecha} {hora}', '%Y-%m-%d %H:%M'))
    except Exception:
        return time.time()


# ---------------------------------------------------------------- escenas del plan → imágenes
def _escena_img(esc, carpeta_enc, carpeta, i, usados=None):
    t = (esc or {}).get('tipo', 'foto')
    foto = None
    usados = usados if usados is not None else set()
    if esc and esc.get('img'):
        p = os.path.join(carpeta_enc, f"c{int(esc['img']):02d}.jpg")
        foto = p if os.path.exists(p) else None
    if esc and not foto and esc.get('url'):          # foto exacta elegida por Claude (p. ej. Wikimedia)
        foto = F._bajar(esc['url'], carpeta, f'u_{i:02d}', usados)
    if esc and not foto and esc.get('buscar'):       # o búsqueda en Wikimedia Commons
        for q in ([esc['buscar']] if isinstance(esc['buscar'], str) else esc['buscar']):
            foto = F._commons(q, carpeta, f'b_{i:02d}', usados)
            if foto:
                break
    out = os.path.join(carpeta, f'esc_{i:02d}.jpg')
    try:
        if t == 'ficha':
            return montaje.escena_ficha(esc.get('nombre', ''), esc.get('sub', ''), foto, out)
        if t == 'fecha':
            return montaje.escena_fecha(esc.get('texto', ''), esc.get('sub', ''), out)
        if t == 'cita':
            return montaje.escena_cita(esc.get('texto', ''), esc.get('autor', ''), out)
        if t == 'mapa' and esc.get('lat') is not None:
            sat = F._satelite(esc['lat'], esc['lon'], carpeta, f'sat_{i:02d}', esc.get('km', 2.5))
            if sat:
                return montaje.escena_mapa(sat, esc.get('lugar', ''), out)
    except Exception as e:
        log('escena', t, e)
    return foto


def _parte_wav(texto, carpeta, k):
    """Una parte de la narración → wav limpio (sin silencio al inicio ni al final) + 0.35 s de pausa."""
    mp3 = os.path.join(carpeta, f'voz_{k:02d}.mp3')
    ok, r = F.voz.gemini(texto, mp3, estilo='')
    if not ok:
        log('voz gemini falló, uso Microsoft:', r)
        ok, r = F.voz.edge(texto, mp3)
        if not ok:
            raise RuntimeError('no se pudo hacer la voz: ' + str(r))
    wav = os.path.join(carpeta, f'voz_{k:02d}.wav')
    lim = 'silenceremove=start_periods=1:start_threshold=-45dB'
    montaje.sh(['ffmpeg', '-y', '-v', 'error', '-i', mp3, '-af', f'{lim},areverse,{lim},areverse,apad=pad_dur=0.35',
                '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', wav])
    return wav


def _narrar(segs, carpeta, g):
    """El gancho se narra aparte: así sabemos al milisegundo dónde termina y la intro nunca corta una palabra."""
    textos = [s['texto'].strip() for s in segs]
    bloques, actual = [' '.join(textos[:g])], ''
    for t in textos[g:]:
        if actual and len(actual) + len(t) > 900:
            bloques.append(actual); actual = ''
        actual = (actual + ' ' + t).strip()
    if actual:
        bloques.append(actual)
    partes = []
    for k, b in enumerate(bloques):
        partes.append(_parte_wav(b, carpeta, k))
        time.sleep(4)
    lista = os.path.join(carpeta, 'voz.txt')
    with open(lista, 'w') as f:
        for p in partes:
            f.write(f"file '{os.path.abspath(p)}'\n")
    wav = os.path.join(carpeta, 'voz.wav')
    montaje.sh(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-c:a', 'pcm_s16le', wav])
    return wav, montaje.dur(partes[0])


def _tiempos(segs, palabras, hook_fin, g):
    """Inicio de cada segmento, siempre en una pausa de la voz (nunca a mitad de palabra)."""
    nw = len(palabras)
    n = [len(s['texto'].split()) for s in segs]
    pal_hook = [k for k, w in enumerate(palabras) if w[0] < hook_fin]
    nh = len(pal_hook)
    tot_h, tot_r = sum(n[:g]) or 1, sum(n[g:]) or 1
    acum, prev = 0, 0
    segs[0]['t0'] = 0.0
    for i in range(1, len(segs)):
        acum += n[i - 1]
        if i == g:
            segs[i]['t0'] = hook_fin; prev = nh; continue
        if i < g:
            est = int(round(acum * nh / tot_h)); lo, hi = 1, max(1, nh - 1)
        else:
            est = nh + int(round((acum - sum(n[:g])) * (nw - nh) / tot_r)); lo, hi = nh + 1, nw - 1
        mejor, puntos = None, -1
        for j in range(max(lo, prev + 1, est - 5), min(hi, est + 5) + 1):
            hueco = palabras[j][0] - palabras[j - 1][1]
            p = hueco + (0.6 if re.search(r'[.?!…]$', palabras[j - 1][2]) else 0) - abs(j - est) * 0.03
            if p > puntos:
                mejor, puntos = j, p
        if mejor is None:
            segs[i]['t0'] = segs[i - 1]['t0'] + 0.8; continue
        prev = mejor
        segs[i]['t0'] = max(palabras[mejor - 1][1] + 0.02, palabras[mejor][0] - 0.25)
    for i in range(1, len(segs)):
        segs[i]['t0'] = max(segs[i]['t0'], segs[i - 1]['t0'] + 0.8)
    return segs


def _cortar_audio(wav, rangos, salida):
    partes = ''.join(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,"
                     f"afade=t=out:st={max(0, b - a - 0.05):.3f}:d=0.05[a{k}];" for k, (a, b) in enumerate(rangos))
    fc = partes + ''.join(f'[a{k}]' for k in range(len(rangos))) + f'concat=n={len(rangos)}:v=0:a=1[o]'
    montaje.sh(['ffmpeg', '-y', '-v', 'error', '-i', wav, '-filter_complex', fc, '-map', '[o]', '-ar', '48000', salida])


# ---------------------------------------------------------------- armar un video del plan
def producir(fecha, v):
    eid = v['eid']
    carpeta_enc = os.path.join(radar.DIR, fecha, eid)
    jid = f'{fecha.replace("-", "")}_{eid}'
    carpeta = os.path.join(F.DIR, jid)
    os.makedirs(carpeta, exist_ok=True)
    segs = [dict(s) for s in v['segmentos'] if str(s.get('texto', '')).strip()]
    reales, usados = [], set()
    for i, s in enumerate(segs):
        s['img'] = _escena_img(s.get('escena'), carpeta_enc, carpeta, i, usados)
        if s['img'] and (s.get('escena') or {}).get('tipo', 'foto') == 'foto':
            reales.append(s['img'])
    for i, s in enumerate(segs):            # escenas sin imagen: repetir una foto real cercana
        if not s['img']:
            s['img'] = reales[min(i, len(reales) - 1)] if reales else montaje.tarjeta(v.get('titulo_video', 'Ridmer'),
                                                                                       os.path.join(carpeta, 'tj.jpg'))
    g = max(1, min(int(v.get('gancho', 1)), len(segs) - 1))
    wav, hook = _narrar(segs, carpeta, g)                # voz Algenib (sin acelerar)
    palabras = editor.transcribir(wav)
    if not palabras:
        todas = ' '.join(s['texto'] for s in segs).split()
        d = montaje.dur(wav)
        palabras = [(k * d / len(todas), (k + 1) * d / len(todas), w) for k, w in enumerate(todas)]
    segs = _tiempos(segs, palabras, hook, g)
    D = montaje.dur(wav)
    escenas = [{'t0': s['t0'], 'img': s['img'], 'rotulo': s.get('rotulo', '')} for s in segs]
    titulo = v.get('titulo_video') or v.get('titulo_youtube', '')
    salidas = []
    if v['tipo'] == 'largo':
        out = os.path.join(carpeta, 'largo.mp4')
        montaje.render(carpeta, wav, palabras, escenas, 'horizontal', titulo, hook, out)
        salidas.append(('largo', out))
    else:
        out = os.path.join(carpeta, 'fb.mp4')
        montaje.render(carpeta, wav, palabras, escenas, 'vertical', titulo, hook, out)
        salidas.append(('fb', out))
        idx = [k for k, s in enumerate(segs) if s.get('short')]
        if idx:
            idx = sorted(set(list(range(g)) + idx))
            rangos, pal_s, esc_s, t = [], [], [], 0.0
            for k in idx:
                a = segs[k]['t0']
                b = segs[k + 1]['t0'] if k + 1 < len(segs) else D
                rangos.append((a, b))
                esc_s.append({'t0': t, 'img': segs[k]['img'], 'rotulo': segs[k].get('rotulo', '')})
                pal_s += [(x - a + t, y - a + t, w) for x, y, w in palabras if a <= x < b]
                t += b - a
            wav_s = os.path.join(carpeta, 'voz_short.wav')
            _cortar_audio(wav, rangos, wav_s)
            maximo = 58.8 - montaje.dur(montaje.INTRO) - 0.6
            if t > maximo:                                   # Short siempre < 60 s
                f_ = t / maximo
                rap = os.path.join(carpeta, 'voz_short_r.wav')
                montaje.sh(['ffmpeg', '-y', '-v', 'error', '-i', wav_s, '-af', f'atempo={min(f_, 1.4):.3f}', rap])
                os.replace(rap, wav_s)
                pal_s = [(x / f_, y / f_, w) for x, y, w in pal_s]
                esc_s = [dict(e, t0=e['t0'] / f_) for e in esc_s]
            hook_s = esc_s[g]['t0'] if len(esc_s) > g else 4.0
            out_s = os.path.join(carpeta, 'short.mp4')
            montaje.render(carpeta, wav_s, pal_s, esc_s, 'vertical', titulo, hook_s, out_s)
            if montaje.dur(out_s) > 59.5:
                tmp = os.path.join(carpeta, 'short_c.mp4')
                montaje.sh(['ffmpeg', '-y', '-v', 'error', '-i', out_s, '-t', '59.4', '-c:v', 'libx264', '-preset',
                            'veryfast', '-crf', '22', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', tmp])
                os.replace(tmp, out_s)
            salidas.append(('short', out_s))
    mini = os.path.join(carpeta, 'miniatura.jpg')
    mi = (v.get('miniatura') or {})
    foto_m = os.path.join(carpeta_enc, f"c{int(mi.get('img', 0) or 0):02d}.jpg")
    if not os.path.exists(foto_m) and mi.get('seg') is not None and 0 <= int(mi['seg']) < len(segs):
        foto_m = segs[int(mi['seg'])]['img']
    montaje.miniatura(foto_m if os.path.exists(foto_m) else (reales[0] if reales else segs[0]['img']),
                      mi.get('texto') or titulo, mini)
    for f_ in os.listdir(carpeta):
        if f_.startswith(('voz_', 'cuerpo_', 'mezcla', 'esc_', 'e_')) and f_.endswith(('.mp3', '.wav', '.txt')):
            os.remove(os.path.join(carpeta, f_))
    # programar entregas
    desc = v.get('descripcion_youtube', '')
    if v.get('fuente'):
        desc += '\n\nFuente: ' + v['fuente']
    for tipo, path in salidas:
        sub = os.path.join(F.DIR, f'{jid}_{tipo}')
        os.makedirs(sub, exist_ok=True)
        shutil.move(path, os.path.join(sub, os.path.basename(path)))
        shutil.copy(mini, os.path.join(sub, 'miniatura.jpg'))
        hora = {'fb': v.get('hora_fb', '12:30'), 'short': v.get('hora_short', '13:00'),
                'largo': v.get('hora_youtube', '18:00')}[tipo]
        if hora == 'ya':                     # prueba: avisar ahora (Facebook se publica a los 20 min)
            cuando = time.time() + (20 * 60 if tipo == 'fb' else 60)
        else:
            cuando = _epoch(fecha, hora)
        meta = {'id': f'{jid}_{tipo}', 'formato': 'short' if tipo != 'largo' else 'largo', 'motivo': 'claude',
                'entrega': tipo, 'titulo': titulo, 'titulo_youtube': v.get('titulo_youtube', titulo),
                'descripcion_youtube': desc, 'etiquetas': v.get('etiquetas', []),
                'texto_facebook': v.get('texto_facebook', ''), 'guion': ' '.join(s['texto'] for s in segs),
                'archivos': {'video': os.path.basename(path), 'miniatura': 'miniatura.jpg'},
                'token': secrets.token_urlsafe(16), 'estado': 'programado', 'hora': hora,
                'aviso_en': cuando - (20 * 60 if tipo == 'fb' else 0), 'publicar_en': cuando,
                'duracion': int(montaje.dur(os.path.join(sub, os.path.basename(path))))}
        F._guardar(os.path.join(sub, 'meta.json'), meta)
    shutil.rmtree(carpeta, ignore_errors=True)
    h = F._leer(F.HIST, [])
    h.append({'fecha': time.strftime('%Y-%m-%d %H:%M'), 'titulo': v.get('articulo', '') + ' · ' + titulo, 'formato': v['tipo']})
    F._guardar(F.HIST, h[-400:])
    log('listo', jid, [t for t, _ in salidas])


# ---------------------------------------------------------------- entregas a su hora
def _avisar_youtube(meta):
    link = f"{C.get().get('web_url', 'http://173.249.44.95')}/r/{meta['token']}"
    largo = meta['entrega'] == 'largo'
    du = meta.get('duracion', 0)
    cap = (f"📺 <b>YOUTUBE · {'VIDEO LARGO' if largo else 'SHORT'}</b> · ⏱️ {du // 60}:{du % 60:02d}\n"
           f"⏰ Es buena hora: <b>súbelo ahora</b>.\n\n<b>{meta['titulo_youtube']}</b>\n\n"
           f"👉 Video en calidad completa, miniatura y textos: {link}")
    texto = (f"📝 <b>Título:</b>\n{meta['titulo_youtube']}\n\n<b>Descripción:</b>\n{meta['descripcion_youtube']}\n\n"
             f"<b>Etiquetas:</b>\n{', '.join(meta.get('etiquetas', []))}")
    v = os.path.join(F.DIR, meta['id'], meta['archivos']['video'])
    for c in C.get()['chat_ids']:
        if os.path.getsize(v) < 48 * 1024 * 1024:
            with open(v, 'rb') as f:
                tg._api('sendVideo', files={'video': f}, chat_id=c, caption=cap[:1000], parse_mode='HTML',
                        supports_streaming='true')
        else:
            tg._api('sendMessage', chat_id=c, text=cap + '\n(El archivo pesa más de 50 MB: descárgalo del link)',
                    parse_mode='HTML')
        if largo:
            with open(os.path.join(F.DIR, meta['id'], 'miniatura.jpg'), 'rb') as f:
                tg._api('sendPhoto', files={'photo': f}, chat_id=c, caption='🖼️ Miniatura')
        tg._api('sendMessage', chat_id=c, text=texto[:4000], parse_mode='HTML')
    if ntfy.activo():
        ntfy.enviar(f"📺 YouTube · {'largo' if largo else 'Short'} para subir", meta['titulo_youtube'], link)


def entregas():
    ahora = time.time()
    for jid in sorted(os.listdir(F.DIR)):
        m = F.leer_meta(jid) if os.path.isdir(os.path.join(F.DIR, jid)) else None
        if not m or m.get('estado') != 'programado' or ahora < m.get('aviso_en', 0):
            continue
        if ahora - m.get('publicar_en', ahora) > 6 * 3600:       # muy atrasado: no publicar viejo
            m['estado'] = 'vencido'; F._guardar(os.path.join(F.DIR, jid, 'meta.json'), m); continue
        if m['entrega'] == 'fb':
            m['estado'] = 'pendiente'
            m['creado'] = ahora           # el publicador automático lo sube a los 20 min si no respondes
            m['destino'] = 'Facebook Ridmer TV (se publica solo)'
            F._guardar(os.path.join(F.DIR, jid, 'meta.json'), m)
            F.avisar(m)
        else:
            m['estado'] = 'avisado_youtube'
            F._guardar(os.path.join(F.DIR, jid, 'meta.json'), m)
            _avisar_youtube(m)


# ---------------------------------------------------------------- bucle
def _bajar_plan(fecha):
    try:
        r = requests.get(PLANES_URL.format(fecha=fecha), params={'t': int(time.time())}, timeout=30)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def bucle():
    while True:
        try:
            est = F._leer(ESTADO, {})
            hoy = time.strftime('%Y-%m-%d')
            hora = time.localtime().tm_hour
            if C.get().get('produccion_activa', True):
                if hora >= C.get().get('radar_hora', 2) and est.get('radar') != hoy:
                    est['radar'] = hoy; F._guardar(ESTADO, est)
                    try:
                        radar.preparar_dia(hoy)
                    except Exception as e:
                        log('radar falló', e)
                plan = _bajar_plan(hoy)
                if plan:
                    hechos = F._leer(HECHOS, [])
                    for v in plan.get('videos', []):
                        clave = f"{hoy}:{v.get('eid')}"
                        if clave in hechos or v.get('omitir'):
                            continue
                        hechos.append(clave); F._guardar(HECHOS, hechos)
                        with _lock:
                            try:
                                producir(hoy, v)
                            except Exception as e:
                                log('error produciendo', clave, e)
                                for c in C.get()['chat_ids']:
                                    tg._api('sendMessage', chat_id=c,
                                            text=f"⚠️ Ridmer: no pude armar el video {v.get('eid')}: {str(e)[:300]}")
        except Exception as e:
            log('error bucle', e)
        time.sleep(120)


def bucle_entregas():
    while True:
        try:
            entregas()
        except Exception as e:
            log('error entregas', e)
        time.sleep(60)


def iniciar():
    threading.Thread(target=bucle, daemon=True).start()
    threading.Thread(target=bucle_entregas, daemon=True).start()
