"""Herramienta de Claude para editar a mano un video Ridmer con el material que preparó el servidor.

  python3 tools/editar.py MATERIAL_EID_DIR PLAN.json EID SALIDA_DIR [CAMBIOS.json]

CAMBIOS.json (todo opcional) = decisiones de Claude tras revisar:
  {"img": {"3": "c07.jpg"},            # cambiar la imagen del segmento 3 (cNN.jpg o esc_NN.jpg del material)
   "rotulo": {"5": "17 VÍCTIMAS"},      # cartel rojo (vacío "" para quitarlo)
   "short": [0, 1, 4, 5, 8],            # segmentos del Short
   "t0": {"6": 31.2},                   # mover un corte de escena (segundos de la voz)
   "titulo_video": "...", "miniatura": {"img": "c04.jpg", "texto": "ERA ÉL"}}
Deja en SALIDA_DIR: fb.mp4 + short.mp4 (o largo.mp4), miniatura.jpg y revision_*.jpg (cuadros cada 2 s para revisar).
"""
import json, os, subprocess, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'app'))
os.environ.setdefault('CLIPERO_DATA', os.path.join(os.path.abspath(sys.argv[4] if len(sys.argv) > 4 else '.'), '_datos'))
import produccion as P, montaje  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def hoja_revision(mp4, salida, cada=2.0):
    d = montaje.dur(mp4)
    tiempos = [t * cada + 0.5 for t in range(int(d // cada) + 1) if t * cada + 0.5 < d]
    cuadros = []
    for k, t in enumerate(tiempos):
        f = salida + f'.{k:03d}.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', mp4, '-frames:v', '1', '-vf', 'scale=-2:320', f])
        if os.path.exists(f):
            cuadros.append((t, f))
    if not cuadros:
        return
    w0, h0 = Image.open(cuadros[0][1]).size
    cols = 10 if w0 < h0 else 6
    filas = (len(cuadros) + cols - 1) // cols
    hoja = Image.new('RGB', (cols * (w0 + 6), filas * (h0 + 30)), (15, 15, 15))
    dr = ImageDraw.Draw(hoja)
    try:
        fnt = ImageFont.truetype(montaje.FUENTE, 22)
    except Exception:
        fnt = None
    for i, (t, f) in enumerate(cuadros):
        x, y = (i % cols) * (w0 + 6), (i // cols) * (h0 + 30)
        hoja.paste(Image.open(f), (x, y + 28))
        dr.text((x + 4, y + 2), f'{int(t // 60)}:{t % 60:04.1f}', fill=(255, 220, 0), font=fnt)
        os.remove(f)
    hoja.save(salida, quality=80)


def main():
    mat, plan_p, eid, out = sys.argv[1:5]
    cambios = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}
    mat, out = os.path.abspath(mat), os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    plan = json.load(open(plan_p))
    v = next(x for x in plan['videos'] if x['eid'] == eid)
    v = dict(v, **{k: cambios[k] for k in ('titulo_video', 'miniatura') if k in cambios})
    info = json.load(open(os.path.join(mat, 'info.json')))
    wav = os.path.join(out, 'voz.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(mat, 'voz.flac'), '-ar', '48000', '-ac', '1', wav], check=True)
    segs = []
    for i, s in enumerate(info['segmentos']):
        s = dict(s)
        img = cambios.get('img', {}).get(str(i)) or s.get('img')
        s['img'] = os.path.join(mat, img) if img and os.path.exists(os.path.join(mat, img)) else None
        if str(i) in cambios.get('rotulo', {}):
            s['rotulo'] = cambios['rotulo'][str(i)]
        if str(i) in cambios.get('t0', {}):
            s['t0'] = float(cambios['t0'][str(i)])
        if 'short' in cambios:
            s['short'] = i in cambios['short']
        segs.append(s)
    reales = [s['img'] for s in segs if s['img']]
    for i, s in enumerate(segs):
        if not s['img']:
            s['img'] = reales[min(i, len(reales) - 1)] if reales else montaje.tarjeta(v.get('titulo_video', 'Ridmer'),
                                                                                       os.path.join(out, 'tj.jpg'))
    palabras = [tuple(p) for p in info['palabras']]
    g = max(1, min(int(v.get('gancho', 1)), len(segs) - 1))
    mi = v.get('miniatura') or {}
    fm = None
    if isinstance(mi.get('img'), str) and os.path.exists(os.path.join(mat, mi['img'])):
        fm = os.path.join(mat, mi['img'])
    elif mi.get('seg') is not None and 0 <= int(mi['seg']) < len(segs):
        fm = segs[int(mi['seg'])]['img']
    salidas, mini = P.armar(out, wav, palabras, segs, g, info['hook_fin'], v, fm or reales[0])
    intro = montaje.dur(montaje.INTRO)
    print('gancho termina en', info['hook_fin'], 's · intro', round(intro, 2), 's')
    for tipo, mp4 in salidas:
        d = montaje.dur(mp4)
        aviso = '  ⚠️ SHORT DE 60 s O MÁS' if tipo == 'short' and d >= 59.5 else ''
        print(f'{tipo}: {mp4}  {int(d // 60)}:{d % 60:04.1f}{aviso}')
        hoja_revision(mp4, os.path.join(out, f'revision_{tipo}.jpg'))
    for f_ in os.listdir(out):
        if f_.startswith(('voz', 'cuerpo_', 'mezcla', 'esc_', 'subs_', 'tj')) and not f_.endswith('.mp4'):
            os.remove(os.path.join(out, f_))
    print('segmentos:')
    for i, s in enumerate(segs):
        print(f"  {i:2d} t0={s['t0']:6.2f} {'S' if s.get('short') else ' '} {os.path.basename(s['img'])[:14]:14s} {s['texto'][:60]}")


if __name__ == '__main__':
    main()
