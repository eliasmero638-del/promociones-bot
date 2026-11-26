"""25-nov: RESUMEN DEL DÍA del reality (pedido del dueño).
Todos los días a las 9:00 sale en Facebook (Pasión por los Realities) un video de ~8 min con lo más llamativo de las
últimas 24 h: conversaciones, chismes, lo que hablaron bajito… SIN edición: una portada «RESUMEN DEL DÍA N» y los
trozos del en vivo uno tras otro. No repite lo que ya salió como clip (salvo que sea de lo más fuerte del día).

- registrar(): por cada pedazo analizado guarda su mejor momento y un enlace duro al .ts (así sobrevive a la limpieza
  de 3 h del grabador).
- bucle(): 06:00 arma el video (material de ayer 9:00 a hoy 4:00, sobre todo la noche) (whisper + IA eligen los trozos), 08:30 lo manda por Telegram (/noresumen lo cancela),
  09:00 lo publica.
"""
import glob, json, os, re, shutil, subprocess, threading, time
import base64, requests
import config as C, editor, fb, ia, tg

D = os.path.join(C.DATA, 'resumen')
PED = os.path.join(D, 'ped')
CAND = os.path.join(D, 'candidatos.jsonl')
USADOS = os.path.join(D, 'clips.jsonl')
os.makedirs(PED, exist_ok=True)
_lock = threading.Lock()


def log(*a):
    print(time.strftime('%H:%M:%S'), '[resumen]', *a, flush=True)


def _titulo_vivo():
    try:
        return json.load(open(os.path.join(C.DATA, 'remoto.json'))).get('titulo') or ''
    except Exception:
        return ''


def registrar(path, t0, dur, puntos):
    """Lo llama el analizador por cada pedazo (2 min)."""
    try:
        if not puntos:
            return
        s, sc, det = max(puntos, key=lambda x: x[1])
        h = time.localtime(t0).tm_hour
        noche = h >= 22 or h < 5                     # 25-nov: de noche (cuarto VIP, acostados) se guarda TODO, aunque hablen bajito
        if sc < C.get().get('resumen_min', 45) and not noche:
            return
        dst = os.path.join(PED, os.path.basename(path))
        if not os.path.exists(dst):
            try:
                os.link(path, dst)
            except Exception:
                shutil.copy2(path, dst)
        with _lock, open(CAND, 'a') as f:
            f.write(json.dumps({'t0': t0, 'dur': dur, 'ruta': dst, 'centro': t0 + s, 'puntaje': sc,
                                'reality': C.get().get('reality'), 'vivo': _titulo_vivo()}, ensure_ascii=False) + '\n')
    except Exception as e:
        log('registrar', e)


def marcar_clip(centro):
    """Momentos que ya salieron como clip (para no repetirlos)."""
    try:
        with _lock, open(USADOS, 'a') as f:
            f.write(json.dumps({'centro': centro, 't': time.time()}) + '\n')
    except Exception:
        pass


def _leer(p):
    out = []
    try:
        for l in open(p):
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    except Exception:
        pass
    return out


def limpiar():
    lim = time.time() - 30 * 3600
    for p in glob.glob(os.path.join(PED, '*.ts')):
        if os.path.getmtime(p) < lim:
            os.remove(p)
    with _lock:
        for p in (CAND, USADOS):
            filas = [x for x in _leer(p) if x.get('t0', x.get('t', x.get('centro', 0))) > lim]
            with open(p, 'w') as f:
                f.writelines(json.dumps(x, ensure_ascii=False) + '\n' for x in filas)


def _dia(vivos):
    for v in vivos:
        m = re.search(r'D[IÍ]A\s*(\d+)', v or '', re.I)
        if m:
            return int(m.group(1))
    return None


def armar(desde, hasta, salida):
    """Elige los trozos y arma el video. Devuelve (ruta, info) o (None, motivo)."""
    cfg = C.get()
    cands = [c for c in _leer(CAND) if desde <= c['centro'] <= hasta and os.path.exists(c['ruta'])]
    if len(cands) < 6:
        return None, f'pocos momentos guardados ({len(cands)})'
    usados = [u['centro'] for u in _leer(USADOS)]
    info = sorted({(c['ruta'], c['t0'], c['dur']) for c in cands}, key=lambda x: x[1])
    # 1) preseleccionar: los mejores, separados ≥ 8 min, priorizando lo que NO salió como clip
    for c in cands:
        c['ya_clip'] = any(abs(c['centro'] - u) < 150 for u in usados)
        h = time.localtime(c['centro']).tm_hour
        c['noche'] = h >= 22 or h < 5
    cands.sort(key=lambda c: (c['ya_clip'], -c['puntaje']))
    # 25-nov: lo más importante del día es la noche (cuarto VIP, cuando ya están acostados): 2/3 de los candidatos
    pre = []
    for grupo, cupo, sep in ((lambda c: c['noche'], 22, 240), (lambda c: True, 34, 480)):
        for c in cands:
            if len(pre) >= cupo:
                break
            if grupo(c) and c not in pre and all(abs(c['centro'] - p['centro']) > sep for p in pre):
                pre.append(c)
    # 2) escuchar cada uno (whisper) para que la IA elija lo que de verdad llama la atención
    tmp = os.path.join(D, 'tmp'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    for i, c in enumerate(pre):
        c['id'] = i
        c['a'], c['b'] = c['centro'] - 25, c['centro'] + 35
        f = os.path.join(tmp, f'c{i}.mp4')
        c['texto'] = ''
        if editor.cortar(info, c['a'], c['b'], f):
            c['archivo'] = f
            c['texto'] = ' '.join(w for _, _, w in editor.transcribir(f))[:700]
    pre = [c for c in pre if c.get('archivo')]
    lista = '\n'.join(f"[{c['id']}] ({time.strftime('%H:%M', time.localtime(c['centro']))}{', de noche' if c['noche'] else ''}"
                      f"{', ya salió como clip' if c['ya_clip'] else ''}) {c['texto'] or '(no se entiende lo que dicen)'}"
                      for c in pre)
    prompt = (f"Eres editor de una página de Facebook de chismes del reality «{cfg.get('reality')}» "
              f"(participantes: {', '.join(cfg.get('participantes', {}))}). Estas son transcripciones de momentos del en vivo "
              "del día. Elige los 9 a 11 más PICANTES para un RESUMEN DEL DÍA. Lo MÁS importante (el dueño lo pidió así): "
              "lo que pasa en el CUARTO VIP y de noche cuando ya están ACOSTADOS en la cama — coqueteos, quién duerme con "
              "quién, besos, lo que se dicen bajito en la cama. Si pasó algo entre ellos, se muestra, pero NO elijas "
              "momentos donde se esté teniendo relaciones sexuales o haya desnudos (eso lo castiga Facebook). Después: chismes, lo que hablan a escondidas de otros, "
              "secretos, confesiones, estrategias, discusiones, romances. Evita los momentos aburridos o sin sentido, y los que ya "
              "salieron como clip salvo que sean de lo más fuerte del día. Ordénalos del más fuerte al menos fuerte.\n\n"
              f"{lista}\n\nResponde SOLO JSON: {{\"elegidos\": [ids], \"gancho\": \"frase corta (máx 12 palabras) "
              "sobre lo más fuerte del día, sin inventar nada que no esté en las transcripciones\"}")
    r = None
    try:
        r = ia.groq_json(prompt, temperatura=0.4) if ia.groq_activa() else None
        if not r:
            r, _ = ia.generar(prompt, temperatura=0.4)
    except Exception as e:
        log('IA no respondió', e)
    ids = [int(x) for x in (r or {}).get('elegidos', []) if str(x).isdigit()]
    elegidos = [c for i in ids for c in pre if c['id'] == i][:11] or [c for c in pre if not c['ya_clip']][:10]
    # 25-nov: lo interesante sí, pero nada explícito (desnudos o sexo visible): la IA mira fotos de cada trozo
    reemplazos = [c for c in pre if c not in elegidos]
    revisados = []
    for c in elegidos:
        while c is not None and _explicito(c['archivo']):
            log('trozo explícito, lo cambio', time.strftime('%H:%M', time.localtime(c['centro'])))
            c = reemplazos.pop(0) if reemplazos else None
            while c is not None and any(abs(c['centro'] - r['centro']) < 120 for r in revisados):
                c = reemplazos.pop(0) if reemplazos else None
        if c is not None:
            revisados.append(c)
    elegidos = revisados
    # en el video van en orden de la hora (como pasó), hasta ~8 min
    elegidos = sorted(elegidos, key=lambda c: c['centro'])
    while len(elegidos) > 6 and sum(c['b'] - c['a'] for c in elegidos) > 9 * 60:
        elegidos.remove(min(elegidos, key=lambda c: c['puntaje']))
    dia = _dia([c.get('vivo') for c in elegidos]) or _dia([_titulo_vivo()])
    reality = elegidos[0].get('reality') or cfg.get('reality') or 'EL REALITY'
    # 3) portada (4 s) + trozos tal cual, en 1280x720
    portada = os.path.join(tmp, 'portada.png')
    _portada(portada, f"RESUMEN DEL DÍA {dia}" if dia else 'RESUMEN DEL DÍA', reality)
    partes = [os.path.join(tmp, 'p00.mp4')]
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-t', '4', '-i', portada, '-f', 'lavfi', '-t', '4', '-i',
                    'anullsrc=r=48000:cl=stereo', '-vf', 'scale=1280:720,fps=30,format=yuv420p', '-c:v', 'libx264',
                    '-preset', 'veryfast', '-c:a', 'aac', '-ar', '48000', '-shortest', partes[0]], check=True)
    for k, c in enumerate(elegidos, 1):
        p = os.path.join(tmp, f'p{k:02d}.mp4')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', c['archivo'], '-vf',
                        'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p',
                        '-af', 'loudnorm=I=-16:TP=-1.5,aresample=48000', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                        '-c:a', 'aac', '-ar', '48000', '-ac', '2', p], check=True)
        partes.append(p)
    lst = os.path.join(tmp, 'lista.txt')
    open(lst, 'w').writelines(f"file '{p}'\n" for p in partes)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy',
                    '-movflags', '+faststart', salida], check=True)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', salida],
                               capture_output=True, text=True).stdout or 0)
    return salida, {'dia': dia, 'reality': reality, 'gancho': (r or {}).get('gancho', ''), 'trozos': len(elegidos),
                    'dur': dur, 'portada': portada}


def _explicito(clip):
    """True si se ven desnudos o actos sexuales. Si la IA no responde, por seguridad revisa el dueño a las 8:30."""
    key = C.get().get('gemini_key')
    if not key:
        return False
    fotos = ia._fotos(clip, 6)
    parts = [{'text': 'Estas son 6 fotos de un trozo del en vivo de un reality. Responde SOLO JSON {"explicito": true/false}: '
                      'true únicamente si se ven desnudos (genitales o pechos descubiertos) o un acto sexual visible. '
                      'Besos, abrazos, gente en ropa de dormir o en la cama bajo las sábanas = false.'}]
    parts += [{'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(f).decode()}} for f in fotos]
    body = {'contents': [{'parts': parts}], 'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0}}
    for m in ia._disponibles(key)[:4]:
        try:
            r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                              params={'key': key}, json=body, timeout=120)
            if r.status_code != 200:
                continue
            txt = r.json()['candidates'][0]['content']['parts'][0]['text']
            return bool(json.loads(re.sub(r'^```(json)?|```$', '', txt.strip()).strip()).get('explicito'))
        except Exception:
            continue
    return False


def _portada(path, titulo, reality):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('RGB', (1280, 720), (12, 12, 18)); d = ImageDraw.Draw(im)
    fuentes = glob.glob('/usr/share/fonts/**/*Bold*.ttf', recursive=True) + glob.glob('/usr/share/fonts/**/*.ttf', recursive=True)
    f1 = ImageFont.truetype(fuentes[0], 92) if fuentes else ImageFont.load_default()
    f2 = ImageFont.truetype(fuentes[0], 54) if fuentes else ImageFont.load_default()
    for txt, fnt, y, col in ((titulo, f1, 250, (255, 214, 0)), (reality, f2, 390, (255, 255, 255))):
        w = d.textlength(txt, font=fnt)
        d.text(((1280 - w) / 2, y), txt, font=fnt, fill=col, stroke_width=4, stroke_fill=(0, 0, 0))
    im.save(path)


def _texto_post(inf):
    dia = f" DÍA {inf['dia']}" if inf.get('dia') else ''
    g = (inf.get('gancho') or '').strip()
    return (f"📺 RESUMEN DEL{dia} | {inf['reality']}\n"
            + (f"{g} 😱\n" if g else '')
            + "Lo más fuerte, lo que hablaron a escondidas y lo que nadie vio 👀\n"
            + "#LaMansionVIP #Realities #Chisme")


def bucle():
    """Arma a las 07:20, avisa a las 08:30 y publica a las 09:00."""
    ef = os.path.join(D, 'estado.json')
    try:
        hecho = json.load(open(ef))
    except Exception:
        hecho = {}
    while True:
        try:
            limpiar() if time.localtime().tm_min == 0 else None
            cfg = C.get()
            if cfg.get('resumen_diario', True):
                hoy = time.strftime('%Y-%m-%d'); h = time.localtime(); hm = h.tm_hour * 60 + h.tm_min
                est = hecho.setdefault(hoy, {})
                out = os.path.join(D, f'resumen_{hoy}.mp4')
                if hm >= 6 * 60 and hm < 9 * 60 and (est.get('armado') in (None, 'intentando')):
                    est['armado'] = 'intentando'
                    json.dump(hecho, open(ef, 'w'), ensure_ascii=False, default=str)
                    log('armando el resumen del día')
                    hoy4 = time.mktime(time.strptime(hoy + ' 04:00', '%Y-%m-%d %H:%M'))
                    ruta, inf = armar(hoy4 - 19 * 3600, hoy4, out)       # de ayer 9:00 am a hoy 4:00 am
                    est['armado'] = inf if ruta else {'error': inf}
                    log('resumen', ruta, inf)
                    if not ruta:
                        tg.texto(f'ℹ️ Hoy no armé el RESUMEN DEL DÍA: {inf}.')
                inf = est.get('armado') if isinstance(est.get('armado'), dict) else None
                if inf and 'error' not in inf:
                    if hm >= 8 * 60 + 30 and 'avisado' not in est:
                        est['avisado'] = True
                        prev = os.path.join(D, 'vista.mp4')
                        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', out, '-vf', 'scale=-2:480', '-c:v', 'libx264',
                                        '-preset', 'veryfast', '-b:v', '700k', '-c:a', 'aac', '-b:a', '96k', prev])
                        cap = (f"📺 <b>RESUMEN DEL DÍA</b> ({int(inf['dur'] // 60)} min, {inf['trozos']} momentos)\n"
                               "Se publica solo a las <b>9:00 am</b> en Pasión por los Realities.\n"
                               "Para cancelarlo escribe /noresumen")
                        for c in cfg['chat_ids']:
                            with open(prev, 'rb') as f:
                                r = tg._api('sendVideo', files={'video': f}, chat_id=c, caption=cap, parse_mode='HTML',
                                            supports_streaming='true')
                            if not (r and r.get('ok')):
                                tg._api('sendMessage', chat_id=c, text=cap, parse_mode='HTML')
                    if hm >= 9 * 60 and not est.get('pub_ok') and est.get('pub_intentos', 0) < 4 \
                            and time.time() - est.get('pub_ultimo', 0) > 900 and not est.get('cancelado') \
                            and not os.path.exists(os.path.join(D, f'cancelado_{hoy}')):
                        # 26-nov: reintenta hasta 4 veces (cada 15 min) si Facebook falla
                        est['pub_intentos'] = est.get('pub_intentos', 0) + 1; est['pub_ultimo'] = time.time()
                        json.dump(hecho, open(ef, 'w'), ensure_ascii=False, default=str)
                        titulo = f"RESUMEN DEL DÍA {inf['dia']} | {inf['reality']}" if inf.get('dia') else f"RESUMEN DEL DÍA | {inf['reality']}"
                        ok, rid = fb.publicar(out, _texto_post(inf), titulo)
                        log('publicado' if ok else 'no se pudo publicar', rid)
                        if ok:
                            est['pub_ok'] = True
                            tg.texto('✅ Publiqué el RESUMEN DEL DÍA en Pasión por los Realities.')
                        elif est['pub_intentos'] >= 4:
                            tg.texto(f'⚠️ No pude publicar el RESUMEN DEL DÍA: {str(rid)[:200]}')
            for k in list(hecho):
                if k < time.strftime('%Y-%m-%d', time.localtime(time.time() - 2 * 86400)):
                    hecho.pop(k)
            json.dump(hecho, open(ef, 'w'), ensure_ascii=False, default=str)
        except Exception as e:
            log('error', e)
        time.sleep(60)


def cancelar():
    open(os.path.join(D, f"cancelado_{time.strftime('%Y-%m-%d')}"), 'w').write('1')
