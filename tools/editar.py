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
   "corregir": {"Rhythmert": "Ridmer", "Kopki": "Koepcke", "#57": ""},   # subtítulos mal oídos ("#N" = palabra N)
   "musica": "tension",                 # tension | epico | misterio (pistas propias, bajan solas bajo la voz)
   "foto_estilo": "polaroid",           # fotos reales: polaroid que cae con cinta (por defecto) | "plano"
   "estilo_foto": {"9": "duo"}, "dato": {"9": "1 DE 92"}, "pie": {"2": "Juliane, hoy"},   # por segmento
   (una imagen también puede ser v_NN.mp4: fragmento de video real en recuadro, máx. 7 s en movimiento)
Escenas animadas (se piden en el plan; el servidor baja el mapa y aquí se animan):
   {"tipo": "ruta", "a": [lat, lon], "b": [lat, lon], "na": "AUSTIN", "nb": "BAHAMAS", "corte": 0.55,
    "c": [lat, lon], "nc": "PALM BEACH"}       → línea que avanza de A a B (corte < 1 = no llegó) y marca C
   {"tipo": "caida", "lat": .., "lon": .., "km": 2, "lugar": "PALM BEACH"}  → recreación de una caída con impacto
   {"tipo": "contador", "n": 9, "texto": "MUERTOS", "sub": "..."}           → cifra que sube
   {"tipo": "linea_tiempo", "hitos": [["1977", "..."], ["2002", "..."]]}    → línea de tiempo animada
   "titulo_video": "...", "miniatura": {"img": "c04.jpg", "texto": "ERA ÉL"}}
Deja en SALIDA_DIR: fb.mp4 + short.mp4 (o largo.mp4), miniatura.jpg y revision_*.jpg (cuadros cada 2 s para revisar).
"""
import json, os, re, subprocess, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(AQUI, '..', 'app'))
sys.path.insert(0, APP_DIR)
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
    v = dict(v, **{k: cambios[k] for k in ('titulo_video', 'miniatura', 'musica') if k in cambios}, pro=True)
    info = json.load(open(os.path.join(mat, 'info.json')))
    wav = os.path.join(out, 'voz.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(mat, 'voz.flac'), '-ar', '48000', '-ac', '1', wav], check=True)
    segs = []
    tipo_de = {f'esc_{k:02d}.jpg': (x.get('escena') or {}).get('tipo', 'foto') for k, x in enumerate(info['segmentos'])}
    for i, s in enumerate(info['segmentos']):
        s = dict(s)
        img = cambios.get('img', {}).get(str(i)) or s.get('img')
        if str(i) in cambios.get('img', {}):            # la imagen cambiada conserva su tipo (tarjeta/mapa no se recorta)
            t_ = 'tarjeta' if img.startswith('x_') else tipo_de.get(img, 'foto')
            s['escena'] = dict(s.get('escena') or {}, tipo=t_)
        s['img'] = os.path.join(mat, img) if img and os.path.exists(os.path.join(mat, img)) else None
        if str(i) in cambios.get('rotulo', {}):
            s['rotulo'] = cambios['rotulo'][str(i)]
        if str(i) in cambios.get('t0', {}):
            s['t0'] = float(cambios['t0'][str(i)])
        if str(i) in cambios.get('dibujo', {}):          # escena dibujada en vez de la foto
            s['escena'] = dict(cambios['dibujo'][str(i)], tipo='dibujo')
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
    # subtítulos: corrige palabras mal oídas por el transcriptor ("Rhythmert" → "Ridmer"). Clave = palabra sin
    # signos, en minúsculas; valor = texto nuevo ("" la borra y su tiempo pasa a la anterior).
    corr = {re.sub(r'[^\w]', '', k.lower()): x for k, x in (cambios.get('corregir') or {}).items()}
    if corr:
        nuevas = []
        for n_, (a, b, w) in enumerate(palabras):
            k = re.sub(r'[^\w]', '', w.lower())
            if f'{n_}' in corr and (cambios.get('corregir') or {}).get(f'#{n_}') is not None:
                k = f'{n_}'                                      # "#57": por posición (ver palabras en info.json)
            if k in corr:
                fin = w[-1] if w[-1] in '.,;:!?' and not corr[k][-1:] in '.,;:!?' else ''
                if corr[k] == '' and nuevas:
                    nuevas[-1] = (nuevas[-1][0], b, nuevas[-1][2] + fin)
                    continue
                w = corr[k] + fin
            nuevas.append((a, b, w))
        palabras = nuevas
    mi = v.get('miniatura') or {}
    fm = None
    if isinstance(mi.get('img'), str) and os.path.exists(os.path.join(mat, mi['img'])):
        fm = os.path.join(mat, mi['img'])
    elif mi.get('seg') is not None and 0 <= int(mi['seg']) < len(segs):
        fm = segs[int(mi['seg'])]['img']
    # animaciones (ruta, caída, contador, línea de tiempo) y escenas DIBUJADAS (estilo cuentos): a pantalla completa
    import animar, dibujos, terror  # noqa: F401  (terror agrega rio, pueblo, bosque, susto)
    W_, H_ = (1920, 1080) if v['tipo'] == 'largo' else (1080, 1920)
    for k, s in enumerate(segs):
        esc = s.get('escena') or {}
        t = esc.get('tipo')
        if t not in ('ruta', 'caida', 'contador', 'linea_tiempo', 'dibujo'):
            continue
        t1 = segs[k + 1]['t0'] if k + 1 < len(segs) else montaje.dur(wav)
        dd = max(2.5, t1 - s['t0'] + 0.4)
        sal = os.path.join(out, f'anim_{k:02d}.mp4')
        try:
            if t == 'ruta' and s['img'] and not s['img'].endswith('.mp4'):
                animar.ruta(s['img'], esc['centro'], esc['km'], esc['a'], esc['b'], esc.get('na', ''), esc.get('nb', ''),
                            sal, dd, W_, H_, float(esc.get('corte', 1.0)), esc.get('c'), esc.get('nc', ''))
            elif t == 'caida' and s['img'] and not s['img'].endswith('.mp4'):
                animar.caida(s['img'], esc.get('lugar', ''), sal, dd, W_, H_)
            elif t == 'contador':
                animar.contador(int(esc.get('n', 0)), esc.get('texto', ''), esc.get('sub', ''), sal, min(dd, 5), W_, H_)
            elif t == 'dibujo' and esc.get('mp4') and os.path.exists(esc['mp4']):   # reutilizar una animación ya hecha
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-stream_loop', '-1', '-i', esc['mp4'], '-t', f'{dd:.2f}',
                                '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', sal],
                               check=True)
            elif t == 'dibujo' and esc.get('script'):     # dibujo hecho a medida: python3 script salida seg W H
                sc = esc['script'] if os.path.isabs(esc['script']) else os.path.join(os.path.dirname(os.path.abspath(
                    sys.argv[5])) if len(sys.argv) > 5 else mat, esc['script'])
                env_ = dict(os.environ, PYTHONPATH=os.pathsep.join([APP_DIR, os.environ.get('PYTHONPATH', '')]))
                subprocess.run([sys.executable, sc, sal, f'{dd:.2f}', str(W_), str(H_)], check=True, env=env_)  # import plano
            elif t == 'dibujo':
                extra = {k_: x_ for k_, x_ in esc.items() if k_ not in ('tipo', 'nombre', 'img', 'letrero')}
                dibujos.escena(esc['nombre'], sal, dd, W_, H_, letrero=esc.get('letrero', 'RECREACIÓN'), **extra)
            elif t == 'linea_tiempo':
                animar.linea_tiempo([tuple(h) for h in esc.get('hitos', [])], sal, dd, W_, H_)
            else:
                continue
            s['img'] = sal
            print('animación', k, t, round(dd, 1), 's')
        except Exception as e:
            print('animación falló', k, t, e)
    # FOTOS REALES con estilo (regla del dueño, 9-nov): nunca planas a pantalla completa → polaroid que cae con cinta
    # o "duo" (teñida + dato grande). cambios: "foto_estilo": "polaroid" (por defecto) | "plano";
    # "estilo_foto": {"9": "duo"}, "pie": {"2": "Juliane, hoy"}, "dato": {"9": "1 DE 92"}
    import plano as PL
    est_g = cambios.get('foto_estilo', 'polaroid')
    for k, s in enumerate(segs):
        tipo_e = (s.get('escena') or {}).get('tipo', 'foto')
        img_ = s.get('img') or ''
        if tipo_e not in ('foto', None) or not img_.lower().endswith(('.jpg', '.jpeg', '.png')) or not os.path.exists(img_):
            continue
        est = cambios.get('estilo_foto', {}).get(str(k), est_g)
        if est == 'plano':
            continue
        t1 = segs[k + 1]['t0'] if k + 1 < len(segs) else montaje.dur(wav)
        dd = max(2.0, t1 - s['t0'] + 0.4)
        sal = os.path.join(out, f'anim_foto_{k:02d}.mp4')
        try:
            PL.polaroid_anim(img_, sal, dd, W_, H_, pie=cambios.get('pie', {}).get(str(k), ''), estilo=est,
                             dato=cambios.get('dato', {}).get(str(k), ''), semilla=k)
            s['img'] = sal
            print('foto con estilo', k, est, round(dd, 1), 's')
        except Exception as e:
            print('foto con estilo falló', k, e)
    fm = fm or next((r_ for r_ in reales if not r_.endswith('.mp4')), reales[0])
    if fm.endswith('.mp4'):
        cuadro = os.path.join(out, 'mini_fuente.jpg')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '1', '-i', fm, '-frames:v', '1', cuadro])
        fm = cuadro
    salidas, mini = P.armar(out, wav, palabras, segs, g, info['hook_fin'], v, fm)
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
