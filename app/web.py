"""Página web privada para ver cada clip y decidir (Publicar / No publicar) desde el link de WhatsApp."""
import html, json, os, re, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import config as C

_generando = False
_acciones = {}      # 'publicar' / 'no' -> función(cid) -> (ok, msg)
_buscar = None      # función(token) -> (cid, meta) o (None, None)
_ridmer = None      # {'buscar','publicar','no'}

CSS = """
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#120818;color:#f4eef8;
font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}main{max-width:520px;margin:0 auto;padding:16px}
.marca{font-size:13px;letter-spacing:.08em;color:#ff4f8b;font-weight:800}h1{font-size:22px;margin:6px 0 2px;line-height:1.2}
.sub{color:#cdbfd8;margin:0 0 12px}video{display:block;width:100%;aspect-ratio:9/16;max-height:72vh;object-fit:contain;border-radius:14px;background:#000;margin:0 auto}
.pts{display:inline-block;background:#ff2b6e;color:#fff;border-radius:99px;padding:3px 10px;font-weight:700;font-size:14px}
.box{background:#22142c;border-radius:12px;padding:12px;margin:12px 0;white-space:pre-wrap;font-size:15px}
.btns{display:flex;gap:10px;margin:14px 0}button{flex:1;border:0;border-radius:12px;padding:16px;font-size:17px;font-weight:700}
.pub{background:#22c55e;color:#04130a}.no{background:#3a2a46;color:#f4eef8}.aviso{background:#ffb02033;color:#ffd27a}
.estado{font-size:18px;font-weight:700;text-align:center;padding:14px;border-radius:12px;background:#22142c}
.copiar{background:#3a2a46;color:#fff;padding:10px;font-size:14px;margin-top:6px;width:100%}
"""


def _pagina(cid, m, token, msg=''):
    e = html.escape
    est = m.get('estado', 'pendiente')
    if est == 'pendiente':
        acciones = (f'<form method="post" class="btns"><button class="pub" name="a" value="publicar">📤 Publicar</button>'
                    f'<button class="no" name="a" value="no">🚫 No publicar</button></form>')
    else:
        txt = {'publicado': '✅ Ya está publicado en Facebook', 'publicando': '⏳ Publicando…',
               'descartado': '🚫 No se publica', 'guardado': '💾 Guardado sin publicar'}.get(est, est)
        acciones = f'<div class="estado">{txt}</div>'
    explic = '<div class="box aviso">⚠️ Contenido explícito: revisa antes de publicar.</div>' if m.get('explicito') else ''
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>{e(m.get('titulo', 'Clip'))}</title><style>{CSS}</style></head><body><main>
<div class="marca">{e(C.get()['marca'])}</div>
<h1>{e(m.get('titulo', ''))}</h1><p class="sub">{e(m.get('subtitulo', ''))}</p>
<span class="pts">{m.get('interes', 0)}/100 · {e(m.get('duracion_txt', ''))}</span>
{explic}{('<div class="estado">' + e(msg) + '</div>') if msg else ''}
{acciones}
<video src="/v/{token}.mp4" poster="/i/{token}.jpg" controls playsinline preload="none"></video>
<p style="text-align:center;margin:8px 0"><a style="color:#ff8fb3" href="/v/{token}.mp4">▶️ Si no se ve, toca aquí para abrir el video</a></p>
<div class="box" id="t">{e(m.get('texto_post', ''))}</div>
<button class="copiar" onclick="navigator.clipboard.writeText(document.getElementById('t').innerText);this.innerText='✅ Copiado'">📋 Copiar texto</button>
<div class="box">{e(m.get('descripcion', ''))}</div>
</main></body></html>"""


def _pagina_ridmer(m, token, msg=''):
    e = html.escape
    est = m.get('estado', 'pendiente')
    if est == 'pendiente':
        acciones = ('<form method="post" class="btns"><button class="pub" name="a" value="publicar">📤 Publicar en Ridmer TV'
                    '</button><button class="no" name="a" value="no">🚫 No publicar</button></form>')
    else:
        acciones = '<div class="estado">' + {'publicado': '✅ Publicado en Ridmer TV', 'publicando': '⏳ Publicando…',
                                               'descartado': '🚫 No se publica en Facebook'}.get(est, est) + '</div>'
    v = m['archivos']['video']
    horiz = v.startswith('largo')
    du = m.get('duracion', 0)

    def copiar(idx, titulo, texto):
        return (f'<div class="box"><b>{titulo}</b><div id="c{idx}" style="margin-top:6px">{e(texto)}</div>'
                f'<button class="copiar" onclick="navigator.clipboard.writeText(document.getElementById(\'c{idx}\')'
                f'.innerText);this.innerText=\'✅ Copiado\'">📋 Copiar</button></div>')
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>{e(m.get('titulo', 'Ridmer'))}</title><style>{CSS}
.dl{{display:block;text-align:center;background:#e01818;color:#fff;text-decoration:none;font-weight:800;border-radius:12px;padding:14px;margin:10px 0}}
</style></head><body><main>
<div class="marca" style="color:#ff3b3b">RIDMER · {'VIDEO LARGO' if horiz else 'SHORT'}</div>
<h1>{e(m.get('titulo_youtube', ''))}</h1>
<span class="pts" style="background:#e01818">⏱️ {du // 60}:{du % 60:02d}</span>
{('<div class="estado">' + e(msg) + '</div>') if msg else ''}
{acciones}
<video src="/r/{token}/{v}" poster="/r/{token}/miniatura.jpg" controls playsinline preload="none"
 style="aspect-ratio:{'16/9' if horiz else '9/16'}"></video>
<a class="dl" href="/r/{token}/{v}?d=1">⬇️ Descargar video para YouTube</a>
<a class="dl" style="background:#3a2a46" href="/r/{token}/miniatura.jpg?d=1">🖼️ Descargar miniatura</a>
{copiar(1, 'Título para YouTube', m.get('titulo_youtube', ''))}
{copiar(2, 'Descripción', m.get('descripcion_youtube', ''))}
{copiar(3, 'Etiquetas', ', '.join(m.get('etiquetas', [])))}
{copiar(4, 'Texto para Facebook', m.get('texto_facebook', ''))}
<details class="box"><summary>📜 Guion</summary>{e(m.get('guion', ''))}</details>
</main></body></html>"""


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'      # iPhone (Safari) necesita 1.1 para reproducir video por partes

    def log_message(self, *a):
        pass

    def do_HEAD(self):
        self._solo_cabecera = True
        try:
            self.do_GET()
        finally:
            self._solo_cabecera = False

    def _send(self, code, body, ctype='text/html; charset=utf-8'):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if not getattr(self, '_solo_cabecera', False):
            self.wfile.write(b)

    def _clip(self):
        m_ = re.match(r'^/(c|v|i)/([A-Za-z0-9_-]{16,64})(\.mp4|\.jpg)?$', self.path.split('?')[0])
        if not m_:
            return None, None, None, None
        cid, meta = _buscar(m_.group(2))
        return m_.group(1), m_.group(2), cid, meta

    def _muestras(self):
        d = os.path.join(C.DATA, 'muestras')
        if self.path.startswith('/m/'):
            n = os.path.basename(self.path.split('?')[0])
            p_ = os.path.join(d, n)
            if not (n.endswith('.mp3') and os.path.exists(p_)):
                return self._send(404, 'No')
            return self._send(200, open(p_, 'rb').read(), 'audio/mpeg')
        global _generando
        if 'hacer=1' in self.path and not _generando:
            def gen():
                global _generando
                _generando = True
                try:
                    import voz
                    voz.muestras()
                except Exception as e:
                    print('voces error', e, flush=True)
                finally:
                    _generando = False
            threading.Thread(target=gen, daemon=True).start()
            _generando = True
        fs = sorted(os.listdir(d)) if os.path.isdir(d) else []
        filas = ''.join(f'<div class="box"><b>{"🎙️ Gemini" if f.startswith("gemini") else "🪟 Microsoft"} · '
                        f'{html.escape(f.split("_", 1)[1][:-4])}</b><br><audio controls preload="none" '
                        f'style="width:100%;margin-top:8px" src="/m/{html.escape(f)}"></audio></div>' for f in fs)
        return self._send(200, f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" '
                          f'content="width=device-width,initial-scale=1"><title>Voces</title><style>{CSS}</style></head>'
                          f'<body><main><div class="marca">RIDMER</div><h1>Muestras de voces</h1>'
                          + ('<meta http-equiv="refresh" content="20;url=/voces"><div class="estado">⏳ Creando las voces… la página se '
                             'actualiza sola, tarda 2-3 minutos.</div>' if _generando else
                             '<form action="/voces"><input type="hidden" name="hacer" value="1">'
                             '<button class="pub" style="width:100%;margin:10px 0">🎙️ Crear muestras de voces</button></form>')
                          + f'{filas or "<p>Todavía no hay muestras.</p>"}</main></body></html>')

    def _ridmer(self, post=False):
        m_ = re.match(r'^/r/([A-Za-z0-9_-]{16,64})(?:/([a-z_]+\.(?:mp4|jpg)))?$', self.path.split('?')[0])
        if not m_ or not _ridmer:
            return self._send(404, 'No encontrado')
        carpeta, m = _ridmer['buscar'](m_.group(1))
        if not m:
            return self._send(404, 'No encontrado')
        if m_.group(2):
            if m_.group(2) not in m['archivos'].values():
                return self._send(404, 'No')
            p_ = os.path.join(carpeta, m_.group(2))
            nombre = re.sub(r'[^A-Za-z0-9_-]+', '_', m.get('titulo', 'ridmer'))[:50] + '_' + m_.group(2)
            return self._archivo(p_, 'video/mp4' if p_.endswith('.mp4') else 'image/jpeg',
                                 nombre if 'd=1' in self.path else None)
        msg = ''
        if post:
            n = int(self.headers.get('Content-Length', 0) or 0)
            datos = self.rfile.read(min(n, 1000)).decode(errors='ignore')
            if 'a=publicar' in datos:
                ok, res = _ridmer['publicar'](m['id'])
                msg = '✅ Publicado en Ridmer TV' if ok else f'⚠️ No se pudo publicar: {res}'
            elif 'a=no' in datos:
                _ridmer['no'](m['id'])
            carpeta, m = _ridmer['buscar'](m_.group(1))
        return self._send(200, _pagina_ridmer(m, m_.group(1), msg))

    def do_GET(self):
        if self.path.startswith('/r/'):
            return self._ridmer()
        if self.path.startswith('/voces') or self.path.startswith('/m/'):
            return self._muestras()
        tipo, token, cid, m = self._clip()
        if not cid:
            return self._send(404, 'No encontrado')
        if tipo == 'c':
            return self._send(200, _pagina(cid, m, token))
        if tipo == 'i':
            p_ = os.path.join(os.path.dirname(m.get('ruta', '')), 'mini.jpg')
            if not os.path.exists(p_):
                return self._send(404, 'Sin imagen')
            return self._send(200, open(p_, 'rb').read(), 'image/jpeg')
        path = m.get('ruta', '')
        if not os.path.exists(path):
            return self._send(404, 'Video borrado')
        return self._archivo(path, 'video/mp4')

    def _archivo(self, path, ctype, descarga=None):
        size = os.path.getsize(path)
        rng = self.headers.get('Range')
        a, b = 0, size - 1
        if rng:
            mr = re.match(r'bytes=(\d*)-(\d*)', rng.strip())
            if mr and (mr.group(1) or mr.group(2)):
                if mr.group(1):
                    a = int(mr.group(1))
                    if mr.group(2):
                        b = min(int(mr.group(2)), size - 1)
                else:
                    a = max(0, size - int(mr.group(2)))
            else:
                rng = None
            if rng and a >= size:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
        self.send_response(206 if rng else 200)
        self.send_header('Content-Type', ctype)
        if descarga:
            self.send_header('Content-Disposition', f'attachment; filename="{descarga}"')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(b - a + 1))
        if rng:
            self.send_header('Content-Range', f'bytes {a}-{b}/{size}')
        self.end_headers()
        if getattr(self, '_solo_cabecera', False):
            return
        try:
            with open(path, 'rb') as f:
                f.seek(a)
                falta = b - a + 1
                while falta > 0:
                    chunk = f.read(min(256 * 1024, falta))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    falta -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


    def do_POST(self):
        if self.path.startswith('/r/'):
            return self._ridmer(post=True)
        tipo, token, cid, m = self._clip()
        if not cid or tipo != 'c':
            return self._send(404, 'No encontrado')
        n = int(self.headers.get('Content-Length', 0) or 0)
        datos = self.rfile.read(min(n, 1000)).decode(errors='ignore')
        accion = 'publicar' if 'a=publicar' in datos else ('no' if 'a=no' in datos else '')
        msg = ''
        if accion in _acciones:
            ok, res = _acciones[accion](cid)
            if accion == 'publicar':
                msg = '✅ Publicado en Facebook' if ok else f'⚠️ No se pudo publicar: {res}'
        _, m = _buscar(token)
        self._send(200, _pagina(cid, m, token, msg))


class Servidor(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass        # el celular cortó la conexión (normal al adelantar el video)


def iniciar(buscar, publicar, no_publicar, ridmer=None):
    global _buscar, _ridmer
    _buscar = buscar
    _ridmer = ridmer
    _acciones['publicar'] = publicar
    _acciones['no'] = no_publicar
    puerto = int(C.get().get('web_puerto', 80))

    def correr():
        try:
            Servidor(('0.0.0.0', puerto), H).serve_forever()
        except Exception as e:
            print('web error', e, flush=True)
    threading.Thread(target=correr, daemon=True).start()
