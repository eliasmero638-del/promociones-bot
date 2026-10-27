"""Clipero: graba el reality, detecta los momentos fuertes, los edita y te los manda por Telegram."""
import json, os, queue, subprocess, threading, time
import config as C, recorder, analyzer, editor, tg

VERSION = 'v1'
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
    return [(p, recorder.pedazo_inicio(p), dur(p)) for p in recorder.pedazos()[-6:]]


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
                for s, sc, d in analyzer.mejores(puntos, cfg['umbral'], cfg['separacion_min'] * 60):
                    centro = t0 + s
                    ahora = time.time()
                    recientes = [h for h, _ in historial if ahora - h < 3600]
                    if len(recientes) >= cfg['max_por_hora']:
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
            fin = centro + C.get()['despues_seg']
            for _ in range(80):
                ps = info_pedazos()
                if ps and ps[-1][1] + ps[-1][2] >= fin:
                    break
                time.sleep(15)
            chat = [t for _, t in recorder.chat_mensajes(centro - 40, centro + 40)]
            info = editor.hacer_clip(info_pedazos(), centro, chat)
            if not info:
                if job['manual']:
                    tg.texto('⚠️ No pude armar ese clip (¿todavía no hay grabación de ese momento?).')
                continue
            stats['clips'] += 1
            cid = os.path.basename(os.path.dirname(info['ruta']))
            frase = info['texto'][:220].strip()
            nombres = ', '.join(info['nombres']) or '—'
            cap = (f"{'🎬 Clip pedido' if job['manual'] else '🔥 Momento fuerte'} "
                   f"<b>({job['puntaje']}/100)</b> · {info['hora']}\n"
                   f"<b>{info['titulo']}</b> · {info['subtitulo']}\n"
                   f"👥 {nombres}\n"
                   + (f"🗣️ “{frase}…”\n" if frase else '') +
                   f"\n📝 Texto sugerido:\n{info['titulo'].capitalize()} 😱🔥 #{C.get()['reality'].replace(' ', '')} #Reality")
            tg.video(info['ruta'], cap, cid)
            log('clip enviado', cid, job['puntaje'])
        except Exception as e:
            log('error en clip', e)


def comandos(tipo, chat, dato, raw):
    cfg = C.get()
    if tipo == 'boton':
        accion, _, cid = dato.partition(':')
        with open(decisiones_file, 'a') as f:
            f.write(json.dumps({'clip': cid, 'decision': accion, 'hora': time.time()}) + '\n')
        tg.editar_caption(raw, '✅ Guardado' if accion == 'ok' else '❌ Descartado')
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
                 f"⏸️ Automático: {'pausado' if cfg['pausado'] else 'activo'} · umbral {cfg['umbral']}\n"
                 f"🧩 Pedazos analizados: {stats['pedazos']} (último {stats['ult_pedazo'] or '—'}, "
                 f"pico {stats['ult_puntaje'] if stats['ult_puntaje'] is not None else '—'})\n"
                 f"🎬 Clips enviados: {stats['clips']}\n"
                 + (f"⚠️ {e['error']}" if e.get('error') else ''), chat)
    elif cmd == '/clip':
        cola.put({'centro': time.time() - C.get()['despues_seg'] - 10, 'puntaje': 0, 'detalle': {}, 'manual': True})
        tg.texto('🎬 Ok, armando clip del último minuto. Te llega en unos minutos.', chat)
    elif cmd == '/pausa':
        C.save(pausado=True); tg.texto('⏸️ Clips automáticos en pausa (sigo grabando). /seguir para reanudar.', chat)
    elif cmd == '/seguir':
        C.save(pausado=False); tg.texto('▶️ Clips automáticos activados.', chat)
    elif cmd == '/umbral':
        try:
            v = max(30, min(98, int(dato.split()[1])))
            C.save(umbral=v); tg.texto(f'🎚️ Umbral en {v}.', chat)
        except Exception:
            tg.texto('Usa así: /umbral 70', chat)
    elif cmd == '/start':
        tg.texto('Ya estás registrado. /estado para ver cómo va.', chat)


def main():
    log('Clipero', VERSION, 'iniciando')
    with open(os.path.join(C.DATA, 'estado.json'), 'w') as f:
        json.dump({'vivo': True, 'version': VERSION, 'inicio': time.time()}, f)
    recorder.iniciar()
    threading.Thread(target=analizar_bucle, daemon=True).start()
    threading.Thread(target=trabajador, daemon=True).start()
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
