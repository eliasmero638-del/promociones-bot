"""Clipero: graba el reality, detecta los momentos fuertes, los edita y te los manda por Telegram."""
import json, os, queue, secrets, subprocess, threading, time
import config as C, recorder, analyzer, editor, tg, ia, fb, wa, web, ntfy
try:
    import fabrica
except Exception as _e:          # si la fábrica falla, el Clipero sigue funcionando
    fabrica = None
    print('fabrica no disponible:', _e, flush=True)

VERSION = 'v32-ultima-hora'
cola = queue.Queue()
historial = []          # (hora, puntaje) de clips enviados, para límites por hora
stats = {'pedazos': 0, 'clips': 0, 'ult_puntaje': None, 'ult_pedazo': None}
decisiones_file = os.path.join(C.DATA, 'decisiones.jsonl')


def log(*a):
    print(time.strftime('%H:%M:%S'), '[main]', *a, flush=True)


def dur(path):
    try:
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                    capture_output=True, text=True).stdout.strip())
    except Exception:
        return 0.0


def info_pedazos():
    return [(p, recorder.pedazo_inicio(p), dur(p)) for p in recorder.pedazos()[-12:]]


def en_horario():
    hs = C.get()['horas']
    if not hs:
        return True
    h = time.localtime().tm_hour
    return any(a <= h < b for a, b in hs)


def analizar_bucle():
    det = analyzer.Detector()
    hechos = set()
    while True:
        try:
            for p in recorder.pedazos():
                if p in hechos:
                    continue
                hechos.add(p)
                t0 = recorder.pedazo_inicio(p)
                vol = analyzer.loudness_por_segundo(p)
                chat = recorder.chat_mensajes(t0 - 5, t0 + len(vol) + 40)
                puntos = det.analizar(vol, chat, t0)
                stats['pedazos'] += 1
                stats['ult_pedazo'] = time.strftime('%H:%M', time.localtime(t0))
                if puntos:
                    stats['ult_puntaje'] = max(s for _, s, _ in puntos)
                cfg = C.get()
                if cfg['pausado'] or not en_horario():
                    continue
                umb = cfg['umbral_ia'] if ia.activa() else cfg['umbral']
                elegidos = analyzer.mejores(puntos, umb, cfg['separacion_min'] * 60)
                # Barrido: momentos tranquilos (charlas en voz baja, confesiones) no suben el volumen,
                # así que cada cierto tiempo la IA revisa igual el mejor momento del pedazo.
                barrer = cfg.get('barrido_cada', 6)
                if ia.activa() and ia.hay_cuota() and not elegidos and puntos and barrer and stats['pedazos'] % barrer == 0:
                    s0, sc0, d0 = max(puntos, key=lambda x: x[1])
                    c0 = t0 + s0
                    if not any(abs(c0 - h) < cfg['separacion_min'] * 60 for h, _ in historial):
                        cola.put({'centro': c0, 'puntaje': sc0, 'detalle': d0, 'manual': False, 'barrido': True})
                for s, sc, d in elegidos:
                    centro = t0 + s
                    ahora = time.time()
                    recientes = [h for h, _ in historial if ahora - h < 3600]
                    if len(recientes) >= cfg['max_por_hora'] * (3 if ia.activa() else 1) or not (ia.hay_cuota() or ia.groq_activa()):
                        break
                    if any(abs(centro - h) < cfg['separacion_min'] * 60 for h, _ in historial):
                        continue
                    historial.append((centro, sc))
                    cola.put({'centro': centro, 'puntaje': sc, 'detalle': d, 'manual': False})
            if len(hechos) > 500:
                hechos = set(list(hechos)[-200:])
        except Exception as e:
            log('error analizando', e)
        time.sleep(15)


def trabajador():
    while True:
        job = cola.get()
        try:
            centro = job['centro']
            # esperar a que el pedazo que contiene el final del clip esté cerrado
            cfg = C.get()
            fin = centro + (cfg['ventana_despues'] if ia.activa() else cfg['despues_seg'])
            for _ in range(80):
                ps = info_pedazos()
                if ps and ps[-1][1] + ps[-1][2] >= fin:
                    break
                time.sleep(15)
            chat = [t for _, t in recorder.chat_mensajes(centro - 40, centro + 40)]
            extra = 0
            while True:
                info = editor.hacer_clip(info_pedazos(), centro, chat, job_filtro=None if job['manual'] else C.get()['ia_minimo'],
                                         solo_ia=not job['manual'], señales=job, extra=extra)
                if not (info and info.get('extender')):
                    break
                # el momento sigue: esperar más grabación y volver a cortar más largo
                extra += 180
                log('el momento sigue, amplío', extra, 's')
                objetivo = centro + C.get()['ventana_despues'] + extra
                for _ in range(40):
                    ps = info_pedazos()
                    if ps and ps[-1][1] + ps[-1][2] >= objetivo:
                        break
                    time.sleep(15)
                chat = [t for _, t in recorder.chat_mensajes(centro - 60, objetivo)]
            if info and info.get('descartado'):
                continue
            if info and not job['manual'] and info.get('duracion', 999) < C.get()['clip_min'] - 5:
                log('clip muy corto, descartado', info.get('duracion'))
                continue
            if not info:
                if job['manual']:
                    tg.texto('⚠️ No pude armar ese clip (¿todavía no hay grabación de ese momento?).')
                continue
            stats['clips'] += 1
            editor.diag['enviados'] += 1
            if job.get('barrido'):
                historial.append((centro, info.get('interes', 0)))
            cid = os.path.basename(os.path.dirname(info['ruta']))
            frase = info['texto'][:220].strip()
            nombres = ', '.join(info['nombres']) or '—'
            pts = info.get('interes') if info.get('ia') else job['puntaje']
            post = info.get('texto_post') or f"{info['titulo'].capitalize()} 😱🔥 #{C.get()['reality'].replace(' ', '')} #Reality"
            cap = ('💗 <b>PASIÓN POR LOS REALITIES</b> · clip del reality\n' +
                   ('⚠️ <b>CONTENIDO EXPLÍCITO — revisar antes de subir</b>\n' if info.get('explicito') else '') +
                   f"{'🎬 Clip pedido' if job['manual'] else '🔥 Momento fuerte'} <b>({pts}/100)</b> · {info['hora']} · ⏱️ {info.get('duracion', 0) // 60}:{info.get('duracion', 0) % 60:02d}\n"
                   f"<b>{info['titulo']}</b>\n{info['subtitulo']}\n"
                   f"👥 {nombres}\n"
                   + (f"📌 {info['descripcion']}\n" if info.get('descripcion') else '')
                   + (f"🗣️ “{frase}…”\n" if frase and not info.get('descripcion') else '') +
                   f"\n📝 Para publicar:\n{post}")
            hay_fb = fb.activo()
            if hay_fb:
                cfg = C.get()
                if info.get('explicito'):
                    cap += '\n\n🔒 Explícito: no se publica solo.'
                elif cfg['auto_publicar'] and (pts or 0) >= cfg['auto_minimo']:
                    cap += f"\n\n⏳ Si no respondes, se publica solo en {cfg['auto_espera_min']} min."
            env = tg.video(info['ruta'], cap, cid, publicar=hay_fb)
            token = secrets.token_urlsafe(16)
            du = int(info.get('duracion', 0))
            guardar_meta(cid, {'ruta': info['ruta'], 'texto_post': post, 'titulo': info['titulo'],
                               'subtitulo': info.get('subtitulo', ''), 'descripcion': info.get('descripcion', ''),
                               'duracion_txt': f'{du // 60}:{du % 60:02d}', 'token': token,
                               'interes': pts or 0, 'explicito': bool(info.get('explicito')), 'manual': job['manual'],
                               'enviado': time.time(), 'estado': 'pendiente', 'mensajes': env})
            cfg = C.get()
            link = f"{cfg.get('web_url', 'http://173.249.44.95')}/c/{token}"
            if ntfy.activo():
                try:
                    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(max(1, du // 3)), '-i', info['ruta'],
                                    '-frames:v', '1', '-vf', 'scale=480:-2', '-q:v', '5',
                                    os.path.join(os.path.dirname(info['ruta']), 'mini.jpg')], timeout=60)
                except Exception:
                    pass
                extra = ''
                if info.get('explicito'):
                    extra = '\n⚠️ Explícito: no se publica solo'
                elif hay_fb and cfg['auto_publicar'] and (pts or 0) >= cfg['auto_minimo']:
                    extra = f"\n⏳ Se publica solo en {cfg['auto_espera_min']} min si no respondes"
                ok_n, r_n = ntfy.enviar(f"💗 REALITIES · {pts or 0}/100 · {info['titulo']}",
                                        f"{info.get('subtitulo', '')} · ⏱️ {du // 60}:{du % 60:02d}{extra}",
                                        link, f"{cfg.get('web_url', 'http://173.249.44.95')}/i/{token}.jpg")
                if not ok_n:
                    log('ntfy falló', r_n)
            if wa.activo():
                aviso = ''
                if hay_fb and not info.get('explicito') and cfg['auto_publicar'] and (pts or 0) >= cfg['auto_minimo']:
                    aviso = f"\n⏳ Se publica solo en {cfg['auto_espera_min']} min si no respondes"
                elif info.get('explicito'):
                    aviso = '\n⚠️ Explícito: no se publica solo'
                ok_wa, r_wa = wa.enviar(f"🔥 *{pts or 0}/100* · ⏱️ {du // 60}:{du % 60:02d}\n"
                                        f"*{info['titulo']}*\n{info.get('subtitulo', '')}{aviso}\n\n"
                                        f"👉 Ver y decidir: {link}")
                if not ok_wa:
                    log('whatsapp falló', r_wa)
            log('clip enviado', cid, job['puntaje'])
        except Exception as e:
            log('error en clip', e)


def meta_path(cid):
    return os.path.join(C.CLIPS, cid, 'meta.json')


def leer_meta(cid):
    try:
        return json.load(open(meta_path(cid)))
    except Exception:
        return None


def guardar_meta(cid, m):
    try:
        with open(meta_path(cid), 'w') as f:
            json.dump(m, f, ensure_ascii=False)
    except Exception as e:
        log('no pude guardar meta', e)


_pub_lock = threading.Lock()


def publicados_hoy():
    hoy = time.strftime('%Y%m%d')
    n = 0
    for d in os.listdir(C.CLIPS):
        m = leer_meta(d)
        if m and m.get('estado') == 'publicado' and time.strftime('%Y%m%d', time.localtime(m.get('publicado', 0))) == hoy:
            n += 1
    return n


def publicar_clip(cid, motivo):
    """Publica un clip en Facebook y avisa en Telegram. motivo: 'tú' o 'auto'."""
    with _pub_lock:
        m = leer_meta(cid)
        if not m or m.get('estado') != 'pendiente':
            return False, 'ya estaba ' + (m or {}).get('estado', 'borrado')
        m['estado'] = 'publicando'; guardar_meta(cid, m)
    ok, res = fb.publicar(m['ruta'], m['texto_post'], m.get('titulo', ''))
    m['estado'] = 'publicado' if ok else 'pendiente'
    if ok:
        m['publicado'] = time.time(); m['fb_id'] = res
    else:
        m['error_fb'] = res; m['auto_fallo'] = True
    guardar_meta(cid, m)
    nota = (f"📤 Publicado en Facebook ({'automático' if motivo == 'auto' else 'por ti'}) "
            f"· {time.strftime('%H:%M')}") if ok else f'⚠️ No se pudo publicar: {res}'
    for chat_id, msg_id, cap in m.get('mensajes', []):
        tg.agregar_nota(chat_id, msg_id, cap, nota)
    log('publicar', cid, ok, res)
    return ok, res


def buscar_token(token):
    for cid in os.listdir(C.CLIPS):
        m = leer_meta(cid)
        if m and m.get('token') == token:
            return cid, m
    return None, None


def no_publicar(cid):
    with _pub_lock:
        m = leer_meta(cid)
        if m:
            ia.aprender(False, f"{m.get('titulo', '')} — {m.get('descripcion', '')}")
        if not m or m.get('estado') != 'pendiente':
            return False, 'ya estaba ' + (m or {}).get('estado', 'borrado')
        m['estado'] = 'descartado'
        guardar_meta(cid, m)
    for chat_id, msg_id, cap in m.get('mensajes', []):
        tg.agregar_nota(chat_id, msg_id, cap, '🚫 No se publica')
    return True, 'ok'


def auto_publicador():
    while True:
        time.sleep(60)
        try:
            cfg = C.get()
            if not (fb.activo() and cfg['auto_publicar']):
                continue
            ahora = time.time()
            for cid in sorted(os.listdir(C.CLIPS)):
                m = leer_meta(cid)
                if not m or m.get('estado') != 'pendiente' or m.get('auto_fallo') or m.get('explicito'):
                    continue
                if m.get('interes', 0) < cfg['auto_minimo'] or ahora - m.get('enviado', ahora) < cfg['auto_espera_min'] * 60:
                    continue
                if ahora - m.get('enviado', ahora) > 6 * 3600:      # muy viejo: ya no
                    continue
                if publicados_hoy() >= cfg['max_publicaciones_dia']:
                    break
                publicar_clip(cid, 'auto')
        except Exception as e:
            log('error auto_publicador', e)


MOTIVOS = {'normal': 'Charla normal, no pasa nada', 'nopol': 'No hay polémica real', 'ctx': 'Fuera de contexto',
           'incomp': 'Historia incompleta / clip cortado', 'emo': 'Emoción mal interpretada',
           'pic': 'Picante exagerado', 'nom': 'Nombre incorrecto', 'tit': 'Título engañoso'}


def texto_diag():
    d = editor.diag
    e = recorder.estado
    ult = stats.get('ult_pedazo') or '—'
    sup = ', '.join(f'{k}: {v}' for k, v in d['supervisor'].most_common(4)) or '—'
    return (f"🩺 <b>Diagnóstico Clipero {VERSION}</b>\n"
            f"📡 Grabación: {'✅ llegando' if e['grabando'] else '❌ NO llega (revisa el teléfono)'} · último pedazo {ult}\n"
            f"🧩 Pedazos analizados: {stats['pedazos']}\n"
            f"🔎 Momentos candidatos: {d['candidatos']} · descartados por el filtro gratis: {d['filtro_descarta']}\n"
            f"🤖 Revisados por IA: {d['a_ia']} · IA sin respuesta: {d['ia_error']} · interés bajo: {d['bajo_interes']}\n"
            f"🛡️ Descartes del supervisor: {sup}\n"
            f"🎬 Clips enviados: {stats['clips']}\n"
            f"IA: Gemini {'✅' if ia.hay_cuota() else '⛔ sin cuota'} · Groq {'✅' if ia.groq_activa() else '❌'}\n\n"
            "Últimos descartes:\n" + ('\n'.join(d['ultimos']) or '—'))


def vigilante():
    """Reporte cada 2 horas (silencioso) y alerta si deja de llegar la grabación."""
    ult_rep, sin_grab_desde, avisado = time.time(), None, False
    while True:
        time.sleep(60)
        try:
            if not recorder.estado['grabando']:
                sin_grab_desde = sin_grab_desde or time.time()
                if time.time() - sin_grab_desde > 15 * 60 and not avisado:
                    avisado = True
                    for c in C.get()['chat_ids']:
                        tg._api('sendMessage', chat_id=c, parse_mode='HTML',
                                text='⚠️ <b>Clipero:</b> hace 15 minutos que NO llega grabación del teléfono. '
                                     'Revisa que el Infinix esté prendido, con internet y con Termux abierto.')
                    if ntfy.activo():
                        ntfy.enviar('⚠️ Clipero: no llega la grabación', 'Revisa el Infinix (Termux, internet, batería).')
            else:
                if avisado:
                    tg.texto('✅ Clipero: la grabación volvió a llegar.')
                sin_grab_desde, avisado = None, False
            if C.get().get('reporte_horas', 2) and time.time() - ult_rep > C.get().get('reporte_horas', 2) * 3600:
                ult_rep = time.time()
                for c in C.get()['chat_ids']:
                    tg._api('sendMessage', chat_id=c, text=texto_diag(), parse_mode='HTML', disable_notification='true')
        except Exception as ex:
            log('vigilante', ex)


def comandos(tipo, chat, dato, raw):
    cfg = C.get()
    if tipo == 'boton' and dato.startswith(('rpub:', 'rno:')) and fabrica:
        accion, _, jid = dato.partition(':')
        if accion == 'rpub':
            tg.texto('📤 Subiendo a Facebook Ridmer TV…', chat)
            ok, res = fabrica.publicar(jid, 'tú')
            if not ok:
                tg.texto(f'⚠️ No se publicó: {res}', chat)
        else:
            fabrica.no_publicar(jid)
        return
    if tipo == 'boton':
        accion, _, cid = dato.partition(':')
        with open(decisiones_file, 'a') as f:
            f.write(json.dumps({'clip': cid, 'decision': accion, 'hora': time.time()}) + '\n')
        m = leer_meta(cid)
        if accion == 'mot':
            cid_, _, k = cid.partition(':')
            mm = leer_meta(cid_)
            if mm:
                ia.aprender_motivo(mm.get('titulo', ''), MOTIVOS.get(k, k))
            tg.editar_caption(raw, f'📝 Motivo guardado: {MOTIVOS.get(k, k)}') if raw.get('message', {}).get('caption') else \
                tg._api('editMessageText', chat_id=chat, message_id=raw['message']['message_id'],
                        text=f'📝 Motivo guardado: {MOTIVOS.get(k, k)}. La IA lo tendrá en cuenta.')
            return
        if m and accion in ('pub', 'no', 'ok'):
            ia.aprender(accion != 'no', f"{m.get('titulo', '')} — {m.get('descripcion', '')}")
        if m and accion == 'no':
            botones = [[{'text': v, 'callback_data': f'mot:{cid}:{k}'}] for k, v in MOTIVOS.items()]
            tg.texto('¿Por qué no sirve? (opcional, así aprende)', chat, botones)
        if accion == 'pub':
            tg.texto('📤 Subiendo a Facebook…', chat)
            ok, res = publicar_clip(cid, 'tú')
            if not ok:
                tg.texto(f'⚠️ No se publicó: {res}', chat)
            return
        if m and m.get('estado') == 'pendiente':
            m['estado'] = 'guardado' if accion == 'ok' else 'descartado'
            guardar_meta(cid, m)
        tg.editar_caption(raw, '✅ Guardado' if accion == 'ok' else ('🚫 No se publica' if fb.activo() else '❌ Descartado'))
        return
    if chat not in cfg['chat_ids']:
        if dato.startswith('/start') and not cfg['chat_ids']:
            C.save(chat_ids=[chat])
            tg.texto('👋 ¡Listo! Desde ahora te mando aquí los clips.\n\nComandos:\n'
                     '/estado – cómo va\n/clip – hacer un clip del último minuto\n'
                     '/pausa y /seguir – parar o reanudar los clips automáticos\n'
                     '/umbral 70 – más alto = menos clips pero más fuertes', chat)
        else:
            tg.texto('Este bot es privado.', chat)
        return
    cmd = dato.split()[0].lower()
    if cmd == '/estado':
        e = recorder.estado
        tg.texto(f"📡 {'Grabando' if e['grabando'] else 'Sin grabar'}: {e.get('titulo') or '—'}\n"
                 f"⏸️ Automático: {'pausado' if cfg['pausado'] else 'activo'} · mínimo {cfg['ia_minimo'] if ia.activa() else cfg['umbral']} · IA {'✅' if ia.hay_cuota() else '⛔ sin cuota'}{' · Groq ✅' if ia.groq_activa() else ''}\n"
                 f"🧩 Pedazos analizados: {stats['pedazos']} (último {stats['ult_pedazo'] or '—'}, "
                 f"pico {stats['ult_puntaje'] if stats['ult_puntaje'] is not None else '—'})\n"
                 f"🎬 Clips enviados: {stats['clips']}\n"
                 f"📘 Facebook: {('✅ ' + cfg.get('fb_page_nombre', '')) if fb.activo() else '❌ sin conectar'}"
                 + (f" · auto {'✅ ' + str(cfg['auto_minimo']) + '+' if cfg['auto_publicar'] else '❌'} · hoy {publicados_hoy()}" if fb.activo() else '')
                 + "\n"
                 + (f"⚠️ {e['error']}" if e.get('error') else ''), chat)
    elif cmd == '/clip':
        if ia.activa():
            cola.put({'centro': time.time() - 30 - C.get()['ventana_despues'], 'puntaje': 0, 'detalle': {}, 'manual': True})
            tg.texto('🎬 Ok, reviso los últimos 3-4 minutos y te armo el momento completo. Te llega en unos minutos.', chat)
        else:
            cola.put({'centro': time.time() - C.get()['despues_seg'] - 10, 'puntaje': 0, 'detalle': {}, 'manual': True})
            tg.texto('🎬 Ok, armando clip del último minuto. Te llega en unos minutos.', chat)
    elif cmd == '/pausa':
        C.save(pausado=True); tg.texto('⏸️ Clips automáticos en pausa (sigo grabando). /seguir para reanudar.', chat)
    elif cmd == '/seguir':
        C.save(pausado=False); tg.texto('▶️ Clips automáticos activados.', chat)
    elif cmd == '/umbral':
        try:
            v = max(30, min(98, int(dato.split()[1])))
            if ia.activa():
                C.save(ia_minimo=v); tg.texto(f'🎚️ Ahora solo te mando clips con interés de {v}/100 o más.', chat)
            else:
                C.save(umbral=v); tg.texto(f'🎚️ Umbral en {v}.', chat)
        except Exception:
            tg.texto('Usa así: /umbral 70', chat)
    elif cmd == '/auto':
        arg = (dato.split() + [''])[1].lower()
        if arg in ('no', 'off', 'apagar'):
            C.save(auto_publicar=False); tg.texto('🛑 Publicación automática apagada. Solo se publica si tocas 📤.', chat)
        elif arg.isdigit():
            v = max(50, min(100, int(arg))); C.save(auto_publicar=True, auto_minimo=v)
            tg.texto(f'🤖 Se publica solo lo que tenga {v}/100 o más, si no respondes en {cfg["auto_espera_min"]} min.', chat)
        else:
            C.save(auto_publicar=True)
            tg.texto(f'🤖 Publicación automática activada: {cfg["auto_minimo"]}/100 o más, tras {cfg["auto_espera_min"]} min '
                     f'sin respuesta, máx {cfg["max_publicaciones_dia"]} al día. Nunca lo explícito.\n'
                     '/auto no – apagarla · /auto 90 – cambiar el mínimo', chat)
    elif cmd in ('/participantes', '/lista'):
        ps = cfg['participantes']
        ex = cfg.get('exparticipantes') or {}
        tg.texto('🏠 Siguen en la casa:\n' + '\n'.join(f'• {n}' for n in ps) +
                 ('\n\n🚪 Ya salieron:\n' + '\n'.join(f'• {n}' for n in ex) if ex else '') +
                 '\n\nSi alguien sale: /salio Nombre\nSi entra alguien: /entro Nombre, apodo1, apodo2', chat)
    elif cmd == '/salio':
        q = editor._norm(dato.partition(' ')[2].strip())
        if not q:
            return tg.texto('Usa así: /salio Kaviedes', chat)
        ps = dict(cfg['participantes'])
        quien = [n for n, al in ps.items() if q in editor._norm(n) or any(q == editor._norm(a) for a in al)]
        if len(quien) != 1:
            return tg.texto('No encontré a uno solo con ese nombre. Mira la lista con /participantes', chat)
        ex = dict(cfg.get('exparticipantes') or {})
        ex[quien[0]] = ps.pop(quien[0])
        C.save(participantes=ps, exparticipantes=ex)
        tg.texto(f'👋 {quien[0]} pasó a exparticipantes: la IA ya no lo pondrá como quien habla, '
                 'pero sí puede nombrarlo si hablan de él.', chat)
    elif cmd == '/entro':
        partes = [x.strip() for x in dato.partition(' ')[2].split(',') if x.strip()]
        if not partes:
            return tg.texto('Usa así: /entro Nombre Apellido, apodo1, apodo2', chat)
        ps = dict(cfg['participantes'])
        ps[partes[0]] = [p.lower() for p in partes[1:]] + [partes[0].split()[0].lower()]
        C.save(participantes=ps)
        tg.texto(f'🆕 {partes[0]} agregado a la lista.', chat)
    elif cmd == '/ridmer' and fabrica:
        f_ = 'largo' if 'largo' in dato.lower() else 'short'
        tema = dato.split(maxsplit=2)[2] if len(dato.split(maxsplit=2)) > 2 else None
        threading.Thread(target=fabrica._cola_segura, args=(f_, {'titulo': tema, 'resumen': '', 'tipo': 'misterio'}
                                                            if tema else None, 'manual'), daemon=True).start()
        tg.texto(f'🎬 Haciendo un {f_} de Ridmer' + (f' sobre: {tema}' if tema else '') + '. Te aviso cuando esté.', chat)
    elif cmd == '/diag':
        tg.texto(texto_diag(), chat)
    elif cmd == '/start':
        tg.texto('Ya estás registrado. /estado para ver cómo va.', chat)


def main():
    log('Clipero', VERSION, 'iniciando')
    with open(os.path.join(C.DATA, 'estado.json'), 'w') as f:
        json.dump({'vivo': True, 'version': VERSION, 'inicio': time.time()}, f)
    recorder.iniciar()
    threading.Thread(target=analizar_bucle, daemon=True).start()
    threading.Thread(target=trabajador, daemon=True).start()
    threading.Thread(target=auto_publicador, daemon=True).start()
    threading.Thread(target=vigilante, daemon=True).start()
    web.iniciar(buscar_token, lambda cid: publicar_clip(cid, 'tú'), no_publicar,
                {'buscar': fabrica.buscar_token, 'publicar': fabrica.publicar, 'no': fabrica.no_publicar}
                if fabrica else None)
    if fabrica:
        fabrica.iniciar()
        try:
            import produccion
            produccion.iniciar()
        except Exception as e:
            log('producción no disponible', e)
    if not C.get().get('solo_enviar'):
        tg.escuchar(comandos)
    if C.get()['chat_ids']:
        tg.texto(f'🟢 Clipero {VERSION} encendido.')
    while True:
        time.sleep(60)
        with open(os.path.join(C.DATA, 'estado.json'), 'w') as f:
            json.dump({'vivo': True, 'version': VERSION, 'hora': time.time(), 'grabando': recorder.estado['grabando'],
                       'clips': stats['clips'], 'pedazos': stats['pedazos']}, f)


if __name__ == '__main__':
    main()
