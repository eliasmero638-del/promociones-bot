"""Editor: corta el momento, transcribe, arma título y lo deja vertical con subtítulos."""
import os, re, subprocess, time, unicodedata
import config as C
import ia

_modelo = None


def log(*a):
    print(time.strftime('%H:%M:%S'), '[editor]', *a, flush=True)


def cortar(pedazos_info, desde, hasta, salida):
    """pedazos_info: [(path, inicio_epoch, dur)]. Corta [desde, hasta] (epoch) uniendo pedazos si hace falta."""
    usar = [(p, t0, d) for p, t0, d in pedazos_info if t0 < hasta and t0 + d > desde]
    if not usar:
        return False
    lista = salida + '.txt'
    with open(lista, 'w') as f:
        for p, _, _ in usar:
            f.write(f"file '{p}'\n")
    ss = max(0.0, desde - usar[0][1])
    r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-ss', f'{ss:.2f}',
                        '-t', f'{hasta - desde:.2f}', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                        '-c:a', 'aac', '-b:a', '160k', salida])
    os.remove(lista)
    return r.returncode == 0 and os.path.exists(salida)


def transcribir(path):
    """Lista de palabras [(inicio, fin, palabra)]. Si whisper no está disponible devuelve []."""
    global _modelo
    try:
        if _modelo is None:
            from faster_whisper import WhisperModel
            _modelo = WhisperModel(C.get()['whisper_modelo'], device='cpu', compute_type='int8',
                                   download_root=os.path.join(C.DATA, 'modelos'))
        segs, _ = _modelo.transcribe(path, language='es', word_timestamps=True, vad_filter=True, beam_size=1)
        return [(w.start, w.end, w.word.strip()) for s in segs for w in (s.words or []) if w.word.strip()]
    except Exception as e:
        log('sin transcripción:', e)
        return []


def _norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


TIPOS = [
    ('pelea', r'callate|cállate|respetame|respeta|no me grites|que te pasa|qué te pasa|mentirosa|mentiroso|hipocrita|'
              r'falsa|falso|pelea|vete|a mi no|a mí no|no me hables|loca|loco|mierda|carajo|verga|puta'),
    ('nominacion', r'nomin|eliminad|elimina|salvad|placa|votacion|votación|expulsad'),
    ('romance', r'beso|te quiero|me gustas|te amo|novio|novia|enamorad|coquete'),
    ('llanto', r'llor|perdon|perdón|lo siento|me duele|extraño a'),
]
TITULOS = {
    'pelea': ['¡SE ARMÓ LA PELEA!', '¡SE PRENDIÓ LA CASA!'],
    'nominacion': ['¡MOMENTO DE NOMINACIÓN!'],
    'romance': ['¿HAY ROMANCE EN LA CASA?'],
    'llanto': ['¡SE QUEBRÓ EN VIVO!'],
    None: ['¡SE PRENDIÓ LA CASA!'],
}


def analizar_texto(palabras, chat_textos):
    texto = ' '.join(w for _, _, w in palabras)
    nt = _norm(texto + ' ' + ' '.join(chat_textos))
    nombres = []
    for nombre, alias in C.get()['participantes'].items():
        cnt = sum(len(re.findall(r'\b' + re.escape(_norm(a)) + r'\b', nt)) for a in alias)
        if cnt:
            nombres.append((cnt, nombre))
    nombres = [n for _, n in sorted(nombres, reverse=True)][:2]
    tipo = None
    mejor = 0
    for t, rx in TIPOS:
        c = len(re.findall(_norm(rx), nt))
        if c > mejor:
            tipo, mejor = t, c
    if len(nombres) == 2 and tipo in ('pelea', None):
        titulo = f'{nombres[0].split()[0].upper()} VS {nombres[1].split()[0].upper()}'
        sub = '¡SE ARMÓ LA PELEA!' if tipo == 'pelea' else '¡SE PRENDIÓ LA CASA!'
    else:
        titulo = TITULOS[tipo][0]
        sub = nombres[0].upper() if nombres else C.get()['reality']
    return {'titulo': titulo, 'subtitulo': sub, 'nombres': nombres, 'tipo': tipo, 'texto': texto}


def _ass_tiempo(t):
    t = max(0, t)
    return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}'


def _esc(s):
    return s.replace('\\', '').replace('{', '(').replace('}', ')').replace('\n', ' ')


def hacer_ass(palabras, info, dur, path):
    marca = C.get()['marca']
    lineas = []
    grupo = []
    for w in palabras:
        if grupo and w[0] - grupo[-1][1] > 1.0:
            lineas.append(grupo); grupo = []
        grupo.append(w)
        if len(grupo) >= 5 or re.search(r'[.?!,]$', w[2]):
            lineas.append(grupo); grupo = []
    if grupo:
        lineas.append(grupo)
    ev = []
    ev.append(f'Dialogue: 1,0:00:00.00,{_ass_tiempo(dur)},Marca,,0,0,0,,{_esc(marca)}')
    ev.append(f'Dialogue: 1,0:00:00.00,{_ass_tiempo(dur)},Titulo,,0,0,0,,{_esc(info["titulo"])}')
    ev.append(f'Dialogue: 1,0:00:00.00,{_ass_tiempo(dur)},Sub,,0,0,0,,{_esc(info["subtitulo"])}')
    for g in lineas:
        a, b = g[0][0], g[-1][1] + 0.15
        ev.append(f'Dialogue: 0,{_ass_tiempo(a)},{_ass_tiempo(b)},Cap,,0,0,0,,{_esc(" ".join(x[2] for x in g)).upper()}')
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Marca,DejaVu Sans,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,1,0,1,0,0,8,20,20,40,1
Style: Titulo,DejaVu Sans,62,&H0000DCFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,8,30,30,105,1
Style: Sub,DejaVu Sans,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,8,30,30,195,1
Style: Cap,DejaVu Sans,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,2,40,40,230,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(head + '\n'.join(ev) + '\n')


def vertical(entrada, ass, salida):
    fc = ('[0:v]split[a][b];[a]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=25:2,'
          'eq=brightness=-0.25[bg];[b]scale=720:-2[fg];[bg][fg]overlay=0:(H-h)/2,'
          'drawbox=x=0:y=0:w=720:h=270:color=black@0.75:t=fill,'
          f"subtitles='{ass}'[v]")
    r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', entrada, '-filter_complex', fc, '-map', '[v]', '-map', '0:a?',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-maxrate', '2.5M', '-bufsize', '5M',
                        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-af', 'loudnorm=I=-14:TP=-1.5',
                        '-movflags', '+faststart', salida], capture_output=True, text=True)
    if r.returncode != 0:
        log('error vertical:', r.stderr[-500:])
    return r.returncode == 0


def recortar(entrada, ss, t, salida):
    r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{ss:.2f}', '-i', entrada, '-t', f'{t:.2f}',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-c:a', 'aac', '-b:a', '160k', salida])
    return r.returncode == 0 and os.path.exists(salida)


FUERTE = (r'callate|cállate|respeta|no me grites|que te pasa|qué te pasa|mentiros|hipocrit|hipócrit|falsa|falso|'
          r'pelea|peleamos|no me hables|loca|loco|mierda|carajo|verga|puta|maldit|estupid|estúpid|idiota|imbecil|'
          r'imbécil|perra|cachudo|sapo|sapa|lárgate|largate|vete a|me vale|asco|odio|traicion|traición|traidor|'
          r'nomin|placa|expuls|elimina|salvad|beso|besa|te quiero|me gustas|te amo|enamorad|coquete|cama|bañ|'
          r'llor|perdón|perdon|lo siento|secreto|confies|confes|mi mamá|mi mama|mi hijo|mi hija|mi familia|'
          r'se burla|burla|ridícul|ridicul|jajaja|grita|gritando|golpe|empuj|amenaz|chisme|dijo que tú|dijo que tu|'
          r'a tus espaldas|hablando de ti|hablan de ti|estrategia|votar|voto')


_local = {}       # transcripción local del último clip (para Groq)


def prefiltro(crudo, chat_textos, señales=None):
    """Filtro gratis en el servidor (Whisper) antes de gastar cuota de Gemini. Devuelve (pasa, motivo)."""
    s_ = señales or {}
    d = s_.get('detalle') or {}
    if s_.get('puntaje', 0) >= C.get().get('pasa_directo', 88) or d.get('chat_fuerte', 0) >= 4 or d.get('chat_z', 0) >= 3:
        return True, 'señal fuerte de volumen/chat'
    palabras = transcribir(crudo)
    _local[crudo] = palabras
    texto = _norm(' '.join(w for _, _, w in palabras))
    if len(texto.split()) < 25:
        return False, 'casi no hablan'
    fuertes = len(re.findall(_norm(FUERTE), texto))
    chat_f = len(re.findall(_norm(FUERTE), _norm(' '.join(chat_textos))))
    nombres = sum(1 for n, al in C.get()['participantes'].items()
                  if any(re.search(r'\b' + re.escape(_norm(a)) + r'\b', texto) for a in al))
    puntos = fuertes * 2 + min(chat_f, 4) + min(nombres, 2)
    minimo = C.get().get('prefiltro_minimo', 6)
    if puntos >= minimo:
        return True, f'prefiltro {puntos}/{minimo} (fuertes {fuertes}, chat {chat_f}, nombres {nombres})'
    if ia.groq_activa():
        cat, inte = ia.groq_clasificar(' '.join(w for _, _, w in palabras), ' | '.join(chat_textos[-40:]))
        if cat:
            return (cat != 'normal' and inte >= C.get().get('prefiltro_groq', 65)), f'Groq: {cat} {inte}'
    return False, f'prefiltro {puntos}/{minimo} (fuertes {fuertes}, chat {chat_f}, nombres {nombres})'


def _evidencia_real(evid, palabras):
    """¿La frase de evidencia aparece de verdad en lo que se dijo? (al menos la mitad de sus palabras importantes)"""
    ev = [w for w in _norm(evid).split() if len(w) >= 4]
    if not ev:
        return False
    dicho = set(w.strip('.,;:!?¡¿"') for w in _norm(' '.join(x[2] for x in palabras)).split())
    return sum(1 for w in ev if w.strip('.,;:!?¡¿"') in dicho) >= max(1, len(ev) // 2)


def _buscar_frase(frase, palabras):
    """Segundo donde aparece la frase en la transcripción local (o None)."""
    ws = [w for w in _norm(frase).split() if len(w) >= 3][:6]
    if len(ws) < 2:
        return None
    tx = [_norm(x[2]).strip('.,;:!?¡¿"') for x in palabras]
    mejor, t = 0, None
    for i in range(len(tx)):
        ventana = set(tx[i:i + 12])
        n = sum(1 for w in ws if w.strip('.,;:!?¡¿"') in ventana)
        if n > mejor:
            mejor, t = n, palabras[i][0]
    return t if mejor >= max(2, len(ws) // 2 + 1) else None


def hacer_clip(pedazos_info, centro, chat_textos, nombre=None, job_filtro=None, solo_ia=False, señales=None, extra=0):
    """Devuelve dict con ruta del clip y datos, o None."""
    cfg = C.get()
    usar_ia = ia.activa()
    if usar_ia:
        desde, hasta = centro - cfg['ventana_antes'], centro + cfg['ventana_despues'] + extra
    else:
        desde, hasta = centro - cfg['antes_seg'], centro + cfg['despues_seg']
    nombre = nombre or time.strftime('%Y%m%d_%H%M%S', time.localtime(centro))
    d = os.path.join(C.CLIPS, nombre); os.makedirs(d, exist_ok=True)
    crudo = os.path.join(d, 'crudo.mp4')
    if not cortar(pedazos_info, desde, hasta, crudo):
        return None
    dur = hasta - desde
    info = None
    if usar_ia and job_filtro is not None and cfg.get('prefiltro', True) and not extra:
        pasa, motivo = prefiltro(crudo, chat_textos, señales)
        log(motivo, '→', 'a Gemini' if pasa else 'descartado sin gastar cuota')
        if not pasa:
            return {'descartado': True}
    if usar_ia:
        r = ia.analizar(crudo, chat_textos, dur) if ia.hay_cuota() else {'error': 'Gemini sin cuota'}
        if 'error' in r and ia.groq_activa():
            loc = _local.pop(crudo, None) or transcribir(crudo)
            if loc:
                r = ia.analizar_groq(loc, chat_textos, dur)
                log('Gemini no disponible → Groq', r.get('_modelo') or r.get('error'))
        local = _local.pop(crudo, None)
        if 'error' not in r and job_filtro is not None:
            # supervisor: reglas obligatorias antes de Telegram
            motivo = ''
            if r.get('decision') == 'descartar':
                motivo = 'IA: ' + str(r.get('motivo_descarte') or 'descartar')
            elif str(r.get('categoria', '')).lower() == 'normal':
                motivo = 'conversación normal'
            elif not str(r.get('explicacion') or '').strip():
                motivo = 'sin explicación concreta'
            elif r.get('contexto_claro') is False:
                motivo = 'contexto no claro'
            elif int(r.get('certeza', 100) or 0) < cfg.get('certeza_minima', 60):
                motivo = f"certeza baja ({r.get('certeza')})"
            elif not str(r.get('evidencia') or '').strip():
                motivo = 'sin evidencia'
            else:
                ref = local or [(0, 0, w) for s_ in r.get('subtitulos') or [] for w in str(s_.get('texto', '')).split()]
                if ref and not _evidencia_real(r['evidencia'], ref):
                    motivo = 'la evidencia no aparece en el audio'
            if motivo:
                log('supervisor descarta:', motivo, '·', r.get('titulo'))
                return {'descartado': True, 'motivo': motivo}
            if r.get('sigue') and extra < cfg.get('extension_max', 360):
                return {'extender': True}
        if 'error' not in r:
            # recorte del momento completo que eligió la IA
            try:
                ini, fin = float(r.get('inicio') or 0), float(r.get('fin') or 0)
            except Exception:
                ini, fin = 0.0, 0.0
            if fin <= ini:
                ini, fin = max(0, cfg['ventana_antes'] - 35), cfg['ventana_antes'] + 40
            # ajustar el inicio a donde de verdad arranca el tema (con la transcripción local)
            if r.get('primera_frase'):
                ref_local = local if local else (transcribir(crudo) if job_filtro is not None else [])
                tf = _buscar_frase(r['primera_frase'], ref_local) if ref_local else None
                if tf is not None and abs(tf - ini) > 3:
                    log('inicio ajustado', round(ini, 1), '→', round(tf, 1))
                    ini = tf
            ini = max(0.0, ini - 1.5)
            fin = min(dur, fin + 4.0)
            if fin - ini < cfg['clip_min']:
                fin = min(dur, ini + cfg['clip_min'])
            if fin - ini > cfg.get('clip_max', 900):
                fin = ini + cfg.get('clip_max', 900)
            palabras = []
            for s_ in r.get('subtitulos') or []:
                ws = str(s_.get('texto', '')).split()
                if not ws:
                    continue
                try:
                    t0, t1 = float(s_.get('t0', 0)), float(s_.get('t1', 0))
                except Exception:
                    continue
                if t1 <= t0:
                    t1 = t0 + 0.4 * len(ws)
                st = (t1 - t0) / len(ws)
                for i, w in enumerate(ws):
                    a_, b_ = t0 + i * st - ini, t0 + (i + 1) * st - ini
                    if b_ > 0 and a_ < fin - ini:
                        palabras.append((max(0.0, a_), b_, w))
            if ini > 0.5 or fin < dur - 0.5:
                rec = os.path.join(d, 'momento.mp4')
                if recortar(crudo, ini, fin - ini, rec):
                    crudo, dur = rec, fin - ini
                else:
                    palabras = [(a_ + ini, b_ + ini, w) for a_, b_, w in palabras]
            # solo nombres que estén en la lista actual de participantes
            nombres_ok = []
            for n in r.get('personajes') or []:
                nn = _norm(str(n))
                for nombre, alias in cfg['participantes'].items():
                    claves = [_norm(nombre)] + [_norm(a_) for a_ in alias]
                    if any(re.search(r'\b' + re.escape(k) + r'\b', nn) for k in claves if len(k) >= 3):
                        if nombre not in nombres_ok:
                            nombres_ok.append(nombre)
                        break
            r['personajes'] = nombres_ok
            # supervisor de nombres: solo los confirmados (habla / con quién, certeza ≥ 90)
            conf = set()
            for campo in ('habla', 'con_quien'):
                for x in r.get(campo) or []:
                    try:
                        if int(x.get('certeza', 0) or 0) >= cfg.get('certeza_nombres', 90):
                            nx = _norm(str(x.get('nombre', '')))
                            for nombre_, al in list(cfg['participantes'].items()) + list((cfg.get('exparticipantes') or {}).items()):
                                if any(k and k in nx for k in [_norm(nombre_)] + [_norm(a_) for a_ in al] if len(k) >= 3):
                                    conf.add(nombre_)
                    except Exception:
                        pass
            texto_tit = _norm(' '.join(str(r.get(k, '')) for k in ('titulo', 'subtitulo', 'texto_post', 'descripcion')))
            dudosos = []
            for nombre_, al in list(cfg['participantes'].items()) + list((cfg.get('exparticipantes') or {}).items()):
                if nombre_ in conf:
                    continue
                if any(re.search(r'\b' + re.escape(k) + r'\b', texto_tit) for k in [_norm(a_) for a_ in al] if len(k) >= 3):
                    dudosos.append(nombre_)
            if dudosos:
                cat = str(r.get('categoria', '')).lower()
                neutros = {'polemica': ('SE ARMA UNA DISCUSIÓN EN LA CASA', 'y nadie se quedó callado'),
                           'tristeza': ('MOMENTO MUY EMOTIVO EN LA CASA', 'no pudo contener lo que siente'),
                           'historia_personal': ('UNA HISTORIA QUE CONMUEVE', 'contó lo que vivió'),
                           'picante': ('SE PONE PICANTE LA CONVERSACIÓN', 'y nadie lo vio venir'),
                           'revelacion': ('SALE A LA LUZ UN SECRETO', 'lo que dijeron cambia todo'),
                           'humor': ('NADIE PUDO PARAR DE REÍR', 'momento épico en la casa'),
                           'conversacion_importante': ('CONVERSACIÓN TENSA EN LA CASA', 'lo que dijeron cambia todo')}
                t_, s_ = neutros.get(cat, ('CONVERSACIÓN TENSA EN LA CASA', 'mira lo que pasó'))
                log('nombres dudosos en el título', dudosos, '→ título neutral')
                r['titulo'], r['subtitulo'] = t_, s_
                r['texto_post'] = f"{t_.capitalize()} 😱 ¿Qué opinas? #{cfg['reality'].replace(' ', '')} #Reality"
                r['descripcion'] = re.sub('|'.join(re.escape(n.split()[0]) for n in dudosos), 'un participante',
                                          str(r.get('descripcion', '')), flags=re.I)
                r['personajes'] = [n for n in r['personajes'] if n in conf]
            if str(r.get('categoria', '')).lower() != 'polemica':
                for k in ('titulo', 'subtitulo', 'texto_post'):
                    r[k] = re.sub(r'(?i)\bpeleas?\b', 'conversación', str(r.get(k, '')))
            if not str(r.get('evidencia') or '').strip():
                r['interes'] = min(int(r.get('interes', 0) or 0), 55)
            info = {'titulo': str(r.get('titulo') or '¡SE PRENDIÓ LA CASA!').upper(),
                    'subtitulo': str(r.get('subtitulo') or C.get()['reality']),
                    'nombres': r.get('personajes') or [], 'tipo': r.get('categoria'),
                    'texto': ' '.join(w for _, _, w in palabras), 'interes': r.get('interes', 0),
                    'descripcion': r.get('descripcion', ''), 'texto_post': r.get('texto_post', ''),
                    'explicito': bool(r.get('explicito')), 'ia': True, 'evidencia': r.get('evidencia', '')}
        else:
            log('IA falló, uso el método básico')
    if info is None and solo_ia:
        return {'descartado': True}
    if info is None and usar_ia:
        # sin respuesta de la IA: me quedo con la ventana corta de siempre
        ss = max(0.0, cfg['ventana_antes'] - cfg['antes_seg'])
        rec = os.path.join(d, 'momento.mp4')
        if recortar(crudo, ss, cfg['antes_seg'] + cfg['despues_seg'], rec):
            crudo, dur = rec, cfg['antes_seg'] + cfg['despues_seg']
    if info is None:
        palabras = transcribir(crudo)
        info = analizar_texto(palabras, chat_textos)
        info['ia'] = False
    if job_filtro is not None and info.get('ia') and info.get('interes', 0) < job_filtro:
        log('IA dice que no interesa:', info.get('interes'), info.get('descripcion'))
        return {'descartado': True, **info}
    ass = os.path.join(d, 'subs.ass')
    hacer_ass(palabras, info, dur, ass)
    final = os.path.join(d, 'clip.mp4')
    if not vertical(crudo, ass, final):
        return None
    # control de calidad: que tenga audio y la duración esperada
    pr = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type:format=duration', '-of', 'json', final],
                        capture_output=True, text=True)
    try:
        jd = __import__('json').loads(pr.stdout)
        tiene_audio = any(x.get('codec_type') == 'audio' for x in jd.get('streams', []))
        d_final = float(jd['format']['duration'])
    except Exception:
        tiene_audio, d_final = False, 0
    if not tiene_audio or d_final < dur - 3:
        log('control de calidad falló: audio', tiene_audio, 'duración', d_final, 'esperada', dur)
        return None
    info['ruta'] = final
    info['duracion'] = int(dur)
    info['hora'] = time.strftime('%H:%M', time.localtime(centro))
    return info
