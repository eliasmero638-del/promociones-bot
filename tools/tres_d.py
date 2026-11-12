"""Escenas 3D (personas realistas Rocketbox + three.js) renderizadas en Chromium sin pantalla.  (12-nov, aprobado por el dueño)

  python3 tools/tres_d.py preparar                                  → baja los modelos (rama `tres_d` del repo, ~1 min, una vez)
  python3 tools/tres_d.py foto ESCENA.js salida.jpg SEG [W H textos DURACION]   → un cuadro para revisar con Read
  (DURACION = lo que durará la escena en el video, para que los cortes caigan igual)
  python3 tools/tres_d.py grabar ESCENA.js salida.mp4 SEGUNDOS [W H] [todo|cabecera|nada]   → video sin audio (24 fps)
  (textos: todo = cabecera + frase de abajo · cabecera = solo fecha/lugar arriba (debajo de la voz) · nada)

ESCENA.js es un módulo que exporta `async function montar(ctx)` y devuelve `frame(t)` (ver docs/ejemplos/3d_*.js).
ctx = {THREE, M (motor.js), G (gente.js), K (kit.js), W, H, renderer, scene, cam, texto, textos, dur}.
frame(t) mueve todo y llama a ctx.renderer.render(escena, ctx.cam). En tools/editar.py se usa con
"dibujo": {"N": {"tres_d": "esc_x.js"}} (ruta junto a cambios.json) y la escena dura lo que dura ese segmento."""
import http.server, json, os, shutil, socketserver, subprocess, sys, tempfile, threading

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(AQUI, '..', 'app', 'tres_d'))
CACHE = os.environ.get('RIDMER_3D', os.path.expanduser('~/.cache/ridmer3d'))
REPO = 'https://github.com/eliasmero638-del/promociones-bot'
FPS = 24

NODE = r"""
const { chromium } = require('playwright');
(async () => {
  const [url, modo, a1, a2, a3, RW, RH] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: +RW, height: +RH } });
  p.on('console', m => { const t = m.text(); if (/ERROR|ERR /.test(t)) console.log(t); });
  p.on('pageerror', e => console.log('ERROR página:', e.message));
  await p.goto(url); await p.waitForFunction('window.listo', null, { timeout: 240000 });
  const fallo = await p.evaluate('window.fallo'); if (fallo) { console.log('ERROR', fallo); process.exit(2); }
  const el = await p.$('#cuadro');
  if (modo === 'foto') { await p.evaluate(t => window.frame(t), +a2); await el.screenshot({ path: a1, quality: 92 }); }
  else { const n = Math.round(+a2 * +a3);
    for (let i = 0; i < n; i++) { await p.evaluate(t => window.frame(t), i / +a3);
      await el.screenshot({ path: `${a1}/${String(i).padStart(5, '0')}.jpg`, quality: 90 }); } }
  await b.close();
})().catch(e => { console.log('ERROR', e.stack || e); process.exit(3); });
"""


def preparar():
    if os.path.exists(os.path.join(CACHE, 'rb', 'indice.json')):
        print('modelos 3D ya están en', CACHE); return
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    shutil.rmtree(CACHE, ignore_errors=True)
    subprocess.run(['git', 'clone', '-q', '--depth', '1', '-b', 'tres_d', REPO, CACHE], check=True)
    print('modelos 3D listos en', CACHE, '·', len(json.load(open(os.path.join(CACHE, 'rb', 'indice.json')))), 'personas')


class _Silencio(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _servir(escena):
    """Carpeta temporal con el kit, los modelos y la escena; servidor web local. Devuelve (dir, puerto, servidor)."""
    preparar()
    d = tempfile.mkdtemp(prefix='t3d_')
    for f in os.listdir(KIT):
        os.symlink(os.path.join(KIT, f), os.path.join(d, f))
    for f in ('tj', 'rb'):
        os.symlink(os.path.join(CACHE, f), os.path.join(d, f))
    shutil.copy(escena, os.path.join(d, 'escena_hoy.js'))
    h = lambda *a, **k: _Silencio(*a, directory=d, **k)  # noqa: E731
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), h); srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return d, srv.server_address[1], srv


def _tam(W, H):
    k = min(1.0, 1280 / max(W, H))           # se dibuja a 1280 de lado y se agranda (más rápido)
    return int(W * k) // 2 * 2, int(H * k) // 2 * 2


def _correr(escena, modo, a1, a2, W, H, textos='todo', dur=None):
    d, puerto, srv = _servir(escena)
    RW, RH = _tam(W, H)
    js = os.path.join(d, '_r.js'); open(js, 'w').write(NODE)
    url = f'http://127.0.0.1:{puerto}/pagina.html?escena=escena_hoy.js&W={RW}&H={RH}&textos={textos}&dur={dur or a2}'
    try:
        r = subprocess.run(['node', js, url, modo, a1, str(a2), str(FPS), str(RW), str(RH)], capture_output=True, text=True,
                           cwd=AQUI, timeout=3600)
        if r.returncode != 0 or 'ERROR' in r.stdout:
            raise RuntimeError('escena 3D falló: ' + (r.stdout + r.stderr)[-1500:])
    finally:
        srv.shutdown(); shutil.rmtree(d, ignore_errors=True)
    return RW, RH


def foto(escena, salida, seg, W=1080, H=1920, textos='todo', dur=None):
    _correr(escena, 'foto', os.path.abspath(salida), float(seg), W, H, textos, dur=float(dur) if dur else float(seg) + 1)
    print(salida)


def grabar(escena, salida, segundos, W=1080, H=1920, textos='todo'):
    tmp = tempfile.mkdtemp(prefix='t3dc_')
    try:
        _correr(escena, 'video', tmp, float(segundos), W, H, textos)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, '%05d.jpg'),
                        '-vf', f'scale={W}:{H}:flags=lanczos,format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast',
                        '-crf', '18', '-r', str(FPS), '-movflags', '+faststart', salida], check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(salida)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'preparar':
        preparar()
    elif a and a[0] in ('foto', 'grabar') and len(a) >= 4:
        W, H = (int(a[4]), int(a[5])) if len(a) >= 6 else (1080, 1920)
        textos = a[6] if len(a) >= 7 else 'todo'
        if a[0] == 'foto':
            foto(a[1], a[2], a[3], W, H, textos, a[7] if len(a) >= 8 else None)
        else:
            grabar(a[1], a[2], a[3], W, H, textos)
    else:
        print(__doc__)
