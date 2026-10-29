"""Herramienta de Claude para editar a mano un video Ridmer con el material que preparó el servidor.

  python3 tools/editar.py MATERIAL_EID_DIR PLAN.json EID SALIDA_DIR [CAMBIOS.json]

CAMBIOS.json (todo opcional) = decisiones de Claude tras revisar:
  {"img": {"3": "c07.jpg"},            # cambiar la imagen del segmento 3 (cNN.jpg o esc_NN.jpg del material)
   "rotulo": {"5": "17 VÍCTIMAS"},      # cartel rojo (vacío "" para quitarlo)
   "short": [0, 1, 4, 5, 8],            # segmentos del Short
   "t0": {"6": 31.2},                   # mover un corte de escena (segundos de la voz)
   "mov": {"4": "golpe"},               # movimiento: in, out, izq, der, golpe (impacto + temblor), mapa
   "trans": {"4": "fadewhite"},         # transición al ENTRAR a la escena siguiente: fade, fadewhite, fadeblack, dissolve
   "sfx": {"5": "impacto"},             # efecto al entrar: impacto, whoosh, golpe, riser, "" (ninguno)
   "latido": {"9": true},               # latido de corazón debajo de la escena (tensión)
   "titulo_video": "...", "miniatura": {"img": "c04.jpg", "texto": "ERA ÉL"}}
Deja en SALIDA_DIR: fb.mp4 + short.mp4 (o largo.mp4), miniatura.jpg y revision_*.jpg (cuadros cada 2 s para revisar).
"""
import json, os, re, subprocess, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'app'))
os.environ.setdefault('CLIPERO_DATA', os.path.join(os.path.abspath(sys.argv[4] if len(sys.argv) > 4 else '.'), '_datos'))
import produccion as P, montaje  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def silencios(wav, db=-35, d=0.14):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', wav, '-af', f'silencedetect=noise={db}dB:d={d}', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r)]
    fin = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r)]
    return list(zip(ini, fin))


def alinear(wav, segs, hook, g):
    """Sin whisper: corta cada segmento en la pausa real de la voz más cercana y reparte las palabras dentro."""
    D = montaje.dur(wav)
    sil = [(a, b) for a, b in silencios(wav) if b - a >= 0.14]
    def habla(a, b):                      # tiempo con voz entre a y b
        return (b - a) - sum(max(0, min(y, b) - max(x, a)) for x, y in sil)
    partes = [(0, g, 0.0, hook), (g, len(segs), hook, D)]
    for i0, i1, a, b in partes:
        segs[i0]['t0'] = a
        n = i1 - i0
        if n < 2:
            continue
        pal = [len(segs[k]['texto'].split()) + 0.6 * len(re.findall(r'[,.;:…]', segs[k]['texto'])) for k in range(i0, i1)]
        cands = [(x, y) for x, y in sil if a + 0.8 < y < b - 0.5 and y - x >= 0.2]
        fin_habla = max([x for x, y in sil if y >= b - 0.05] + [b])
        cortes = [y for x, y in cands]
        m = len(cortes)
        if m < n - 1:
            continue
        rate = (fin_habla - a) / sum(pal)
        INF = float('inf')
        # dp[j][c] = costo mínimo poniendo el corte j (0..n-2) en el candidato c
        dp = [[INF] * m for _ in range(n - 1)]
        de = [[-1] * m for _ in range(n - 1)]
        def costo(t_ini, t_fin, k, pausa=0.0):
            esperado = pal[k] * rate
            return ((t_fin - t_ini - esperado) / max(esperado, 0.5)) ** 2 - 0.15 * min(pausa, 0.8)
        pausa = {y: y - x for x, y in cands}
        for c in range(m):
            dp[0][c] = costo(a, cortes[c], 0, pausa[cortes[c]])
        for j in range(1, n - 1):
            for c in range(j, m):
                for c0 in range(j - 1, c):
                    v = dp[j - 1][c0] + costo(cortes[c0], cortes[c], j, pausa[cortes[c]])
                    if v < dp[j][c]:
                        dp[j][c], de[j][c] = v, c0
        mejor, cm = INF, -1
        for c in range(n - 2, m):
            v = dp[n - 2][c] + costo(cortes[c], fin_habla, n - 1)
            if v < mejor:
                mejor, cm = v, c
        elegidos = []
        for j in range(n - 2, -1, -1):
            elegidos.append(cortes[cm]); cm = de[j][cm]
        for k, t in zip(range(i0 + 1, i1), reversed(elegidos)):
            segs[k]['t0'] = t - 0.15
    palabras = []
    for k, s in enumerate(segs):
        a = s['t0']
        b = segs[k + 1]['t0'] if k + 1 < len(segs) else D
        fin_voz = max([x for x, y in sil if a < x < b] + [a + 0.5]) if any(a < x < b and y >= b - 0.25 for x, y in sil) else b
        ws = s['texto'].split()
        pesos = [len(w) + (6 if re.search(r'[.?!…:]$', w) else 3 if w.endswith(',') else 1) for w in ws]
        tot = sum(pesos) or 1
        t = a + 0.05
        for w, pz in zip(ws, pesos):
            dd = (fin_voz - a - 0.05) * pz / tot
            palabras.append((t, t + dd * 0.92, w))
            t += dd
    return segs, palabras


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
    v = dict(v, **{k: cambios[k] for k in ('titulo_video', 'miniatura') if k in cambios}, pro=True)
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
        for k in ('mov', 'trans', 'sfx', 'latido'):
            if str(i) in cambios.get(k, {}):
                s[k] = cambios[k][str(i)]
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
    duraciones = {round(p[1] - p[0], 2) for p in palabras}
    if len(duraciones) <= 2 or cambios.get('alinear'):        # el servidor no tuvo whisper: alinear con las pausas
        print('alineando con las pausas de la voz')
        fijos = {int(k): float(x) for k, x in cambios.get('t0', {}).items()}
        segs, palabras = alinear(wav, segs, info['hook_fin'], g)
        for k, x in fijos.items():
            segs[k]['t0'] = x
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
        mov, tr, sfx = montaje._auto(dict(s, tipo=(s.get('escena') or {}).get('tipo', 'foto')), i)
        print(f"  {i:2d} t0={s['t0']:6.2f} {'S' if s.get('short') else ' '} {os.path.basename(s['img'])[:12]:12s} "
              f"{mov:5s} {tr:9s} {sfx or '-':7s} {s['texto'][:50]}")


if __name__ == '__main__':
    main()
