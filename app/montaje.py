"""Montaje de videos Ridmer: imágenes con movimiento, voz, música, efectos, subtítulos e intro después del gancho."""
import os, re, subprocess, textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

APP = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(APP), 'assets')
INTRO = os.path.join(ASSETS, 'intro_ridmer.mp4')
MUSICA = os.path.join(ASSETS, 'musica_suspenso.mp3')
SFX = os.path.join(ASSETS, 'sfx')
FUENTE = os.path.join(ASSETS, 'InterDisplay-Black.otf')
FORMATOS = {'vertical': (1080, 1920), 'horizontal': (1920, 1080)}


def sh(cmd, timeout=3600):
    if cmd and cmd[0] == 'ffmpeg':
        cmd = ['nice', '-n', '10'] + cmd      # que el Clipero siga rápido mientras se arma el video
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(' '.join(cmd[:6]) + ' … ' + r.stderr[-600:])
    return r


def dur(p):
    try:
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                    capture_output=True, text=True).stdout.strip())
    except Exception:
        return 0.0


def _t(t):
    t = max(0.0, t)
    return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}'


def _esc(s):
    return str(s).replace('\\', '').replace('{', '(').replace('}', ')').replace('\n', ' ')


def tarjeta(texto, salida, formato='horizontal'):
    """Imagen de respaldo (fondo oscuro con texto) cuando no hay foto."""
    W, H = (1600, 1000)
    im = Image.new('RGB', (W, H), (12, 10, 16))
    d = ImageDraw.Draw(im)
    for r in range(600, 0, -6):
        c = int(40 * (1 - r / 600))
        d.ellipse([W / 2 - r * 1.6, H / 2 - r, W / 2 + r * 1.6, H / 2 + r], fill=(20 + c, 8 + c // 3, 14 + c // 2))
    f = ImageFont.truetype(FUENTE, 90)
    lineas = textwrap.wrap(texto.upper(), 18)[:3]
    y = H / 2 - len(lineas) * 55
    for ln in lineas:
        d.text((W / 2, y), ln, font=f, fill=(235, 235, 235), anchor='mm', stroke_width=3, stroke_fill=(0, 0, 0))
        y += 110
    im.save(salida, quality=90)
    return salida


def _escena(img, d, i, W, H, salida):
    """Una escena: fondo desenfocado + imagen con zoom lento (alternando acercar/alejar)."""
    fw, fh = (W, int(H * 0.55)) if H > W else (W, H)
    z = '(1+0.10*t/{d})' if i % 2 == 0 else '(1.10-0.10*t/{d})'
    z = z.format(d=max(d, 0.5))
    fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:3,eq=brightness=-0.33[bg];"
          f"[0:v]scale={fw}:{fh}:force_original_aspect_ratio=decrease[f0];"
          f"[f0]scale=w='trunc(iw*{z}/2)*2':h=-2:eval=frame[fg];"
          f"[bg][fg]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame,fps=30,format=yuv420p[v]")
    sh(['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-t', f'{d:.3f}', '-i', img, '-filter_complex', fc, '-map', '[v]',
        '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-an', salida])


def _ass(palabras, W, H, titulo, path, por_linea=3, rotulos=None):
    """Subtítulos estilo Ridmer: 3 palabras, grandes, la palabra que se dice se pinta en amarillo (karaoke).
    rotulos: [(t0, t1, texto)] carteles de lugar/fecha/nombre sobre la imagen."""
    vertical = H > W
    lineas, g = [], []
    for w in palabras:
        if g and (w[0] - g[-1][1] > 0.5):
            lineas.append(g); g = []
        g.append(w)
        if len(g) >= por_linea or re.search(r'[.?!,;:]$', w[2]):
            lineas.append(g); g = []
    if g:
        lineas.append(g)
    tam, mv = (80, 300) if vertical else (78, 90)
    estilos = (f"Style: Cap,Inter Display Black,{tam},&H0000E5FF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,8,3,2,60,60,{mv},1\n"
               f"Style: Rot,Inter Display Black,{56 if vertical else 50},&H00FFFFFF,&H00FFFFFF,&H001A1AD0,&H001A1AD0,0,0,0,0,100,100,2,0,3,14,0,{8 if vertical else 7},60,60,{430 if vertical else 60},1\n")
    if vertical:
        estilos += ("Style: Tit,Inter Display Black,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,7,0,8,60,60,170,1\n"
                    "Style: Mar,Inter Display Black,40,&H002020E0,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,6,0,1,3,0,8,60,60,95,1\n")
    ev = []
    fin = palabras[-1][1] + 1 if palabras else 1
    if vertical and titulo:
        ev.append(f'Dialogue: 1,0:00:00.00,{_t(fin + 30)},Mar,,0,0,0,,RIDMER')
        ev.append(f'Dialogue: 1,0:00:00.00,{_t(fin + 30)},Tit,,0,0,0,,{_esc(titulo.upper())}')
    for t0, t1, txt in rotulos or []:
        if txt and t1 - t0 > 1.2:
            ev.append(f'Dialogue: 2,{_t(t0 + 0.3)},{_t(min(t1, t0 + 4.5))},Rot,,0,0,0,,{{\\fad(200,200)}}{_esc(txt.upper())}')
    for g in lineas:
        partes = []
        for k, w in enumerate(g):
            fin_w = g[k + 1][0] if k + 1 < len(g) else w[1]
            cs = max(1, int(round((fin_w - w[0]) * 100)))
            partes.append(f'{{\\k{cs}}}{_esc(w[2]).upper()}')
        ev.append(f'Dialogue: 0,{_t(g[0][0])},{_t(g[-1][1] + 0.15)},Cap,,0,0,0,,' + ' '.join(partes))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\n\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
                "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
                "MarginR, MarginV, Encoding\n" + estilos +
                "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" +
                '\n'.join(ev) + '\n')


def _mezcla(voz, D, hook_fin, salida):
    """Voz + música de suspenso bajita + golpe al inicio + subida antes de la intro."""
    ins = ['-i', voz, '-stream_loop', '-1', '-i', MUSICA,
           '-i', os.path.join(SFX, 'golpe_terror.mp3'), '-i', os.path.join(SFX, 'riser2.mp3')]
    r_ini = max(0.0, hook_fin - 4.0)
    fc = (f"[0:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={D:.2f}[v];"
          f"[1:a]atrim=0:{D:.2f},volume=0.13,afade=t=in:d=2,afade=t=out:st={max(0, D - 3):.2f}:d=3[m];"
          f"[2:a]volume=0.45[s1];"
          f"[3:a]volume=0.35,adelay={int(r_ini * 1000)}|{int(r_ini * 1000)}[s2];"
          f"[v][m][s1][s2]amix=inputs=4:normalize=0:duration=first,atrim=0:{D:.2f}[a]")
    sh(['ffmpeg', '-y', '-v', 'error'] + ins + ['-filter_complex', fc, '-map', '[a]', '-ar', '48000', '-ac', '2', salida])


def render(trabajo, voz, palabras, escenas, formato, titulo, hook_fin, salida):
    """escenas: [{'t0','t1','img'}] en segundos de la voz. Intro de Ridmer va después del gancho (hook_fin)."""
    W, H = FORMATOS[formato]
    trabajo, voz, salida = os.path.abspath(trabajo), os.path.abspath(voz), os.path.abspath(salida)
    escenas = [dict(e, img=os.path.abspath(e['img'])) for e in escenas]
    os.makedirs(trabajo, exist_ok=True)
    D = dur(voz) + 0.6
    lista = os.path.join(trabajo, f'esc_{formato}.txt')
    with open(lista, 'w') as f:
        for i, e in enumerate(escenas):
            t1 = D if i == len(escenas) - 1 else escenas[i + 1]['t0']
            d = max(0.6, t1 - e['t0'])
            out = os.path.join(trabajo, f'e_{formato}_{i:03d}.mp4')
            _escena(e['img'], d, i, W, H, out)
            f.write(f"file '{out}'\n")
    cuerpo = os.path.join(trabajo, f'cuerpo_{formato}.mp4')
    sh(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-c', 'copy', cuerpo])
    mezcla = os.path.join(trabajo, 'mezcla.wav')
    _mezcla(voz, D, hook_fin, mezcla)
    ass = os.path.join(trabajo, f'subs_{formato}.ass')
    rot = []
    for i, e in enumerate(escenas):
        t1 = D if i == len(escenas) - 1 else escenas[i + 1]['t0']
        rot.append((e['t0'], t1, e.get('rotulo', '')))
    _ass(palabras, W, H, titulo if formato == 'vertical' else '', ass, rotulos=rot)
    # cuerpo + audio + subtítulos, partido en gancho | intro | resto
    hf = min(max(hook_fin, 1.0), D - 1)
    if formato == 'vertical':
        vi = (f"[2:v]split[i1][i2];[i1]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:3,"
              f"eq=brightness=-0.3[ib];[i2]scale={W}:-2[if];[ib][if]overlay=0:(H-h)/2,fps=30,format=yuv420p,setsar=1[vi]")
    else:
        vi = f"[2:v]scale={W}:{H},fps=30,format=yuv420p,setsar=1[vi]"
    fuentes_dir = os.path.dirname(FUENTE)
    fc = (f"[0:v]subtitles='{ass}':fontsdir='{fuentes_dir}',fps=30,format=yuv420p,setsar=1,split[c1][c2];"
          f"[c1]trim=0:{hf:.3f},setpts=PTS-STARTPTS[va];[c2]trim={hf:.3f},setpts=PTS-STARTPTS[vb];"
          f"[1:a]asplit[x1][x2];[x1]atrim=0:{hf:.3f},asetpts=PTS-STARTPTS[aa];[x2]atrim={hf:.3f},asetpts=PTS-STARTPTS[ab];"
          f"{vi};[2:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[ai];"
          f"[va][aa][vi][ai][vb][ab]concat=n=3:v=1:a=1[v][a0];[a0]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    enc = (['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-maxrate', '8M', '-bufsize', '16M']
           if formato == 'horizontal' else
           ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-maxrate', '5M', '-bufsize', '10M'])
    sh(['ffmpeg', '-y', '-v', 'error', '-i', cuerpo, '-i', mezcla, '-i', INTRO, '-filter_complex', fc,
        '-map', '[v]', '-map', '[a]'] + enc + ['-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                                               '-movflags', '+faststart', salida])
    for f_ in os.listdir(trabajo):
        if f_.startswith(f'e_{formato}_'):
            os.remove(os.path.join(trabajo, f_))
    return salida


def miniatura(img, texto, salida):
    """Miniatura 1280x720 estilo Ridmer: foto + texto grande blanco/rojo."""
    W, H = 1280, 720
    base = ImageOps.fit(Image.open(img).convert('RGB'), (W, H), Image.LANCZOS)
    sombra = Image.new('L', (W, H), 0)
    ds = ImageDraw.Draw(sombra)
    for x in range(W):
        ds.line([(x, 0), (x, H)], fill=int(215 * max(0.0, 1 - x / (W * 0.78)) ** 0.8))
    base = Image.composite(Image.new('RGB', (W, H), (0, 0, 0)), base, sombra)
    d = ImageDraw.Draw(base)
    palabras = texto.upper().split()
    lineas = textwrap.wrap(' '.join(palabras), 11)[:3]
    tam = 118 if len(lineas) <= 2 else 100
    f = ImageFont.truetype(FUENTE, tam)
    y = H / 2 - (len(lineas) * (tam + 10)) / 2
    for k, ln in enumerate(lineas):
        col = (232, 24, 24) if k == len(lineas) - 1 else (255, 255, 255)
        d.text((48, y), ln, font=f, fill=col, stroke_width=8, stroke_fill=(0, 0, 0))
        y += tam + 10
    d.text((48, 40), 'RIDMER', font=ImageFont.truetype(FUENTE, 44), fill=(232, 24, 24), stroke_width=3,
           stroke_fill=(0, 0, 0))
    base.save(salida, quality=92)
    return salida


# ---------------------------------------------------------------- escenas diseñadas (estilo Ridmer)
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'


def _f(tam, ruta=None):
    try:
        return ImageFont.truetype(ruta or FUENTE, tam)
    except Exception:
        return ImageFont.load_default()


def _fondo_oscuro(W, H, rojo=False):
    im = Image.new('RGB', (W, H), (10, 8, 12))
    d = ImageDraw.Draw(im)
    for r in range(int(W * 0.7), 0, -8):
        c = int(55 * (1 - r / (W * 0.7)))
        d.ellipse([W / 2 - r, H / 2 - r * 0.7, W / 2 + r, H / 2 + r * 0.7],
                  fill=(12 + c + (25 if rojo else 0), 8 + c // 3, 12 + c // 3))
    return im


def _texto_centrado(d, W, y, txt, f, col, borde=6):
    w = d.textlength(txt, font=f)
    d.text(((W - w) / 2, y), txt, font=f, fill=col, stroke_width=borde, stroke_fill=(0, 0, 0))


def escena_ficha(nombre, sub, foto, salida, W=1600, H=1000):
    """Ficha de persona: foto a la izquierda, nombre grande y quién es."""
    im = _fondo_oscuro(W, H)
    d = ImageDraw.Draw(im)
    if foto and os.path.exists(foto):
        ph = ImageOps.fit(Image.open(foto).convert('RGB'), (520, 640), Image.LANCZOS)
        ph = ImageOps.grayscale(ph).convert('RGB') if 'B/N' in (sub or '') else ph
        im.paste(ph, (110, (H - 640) // 2))
        d.rectangle([110, (H - 640) // 2, 630, (H + 640) // 2], outline=(220, 30, 30), width=8)
        x0 = 700
    else:
        x0 = 140
    f1, f2 = _f(96), _f(50, MONO)
    lineas = textwrap.wrap(nombre.upper(), 14)[:2]
    y = H / 2 - 60 - 55 * len(lineas)
    for ln in lineas:
        d.text((x0, y), ln, font=f1, fill=(255, 255, 255), stroke_width=5, stroke_fill=(0, 0, 0)); y += 108
    d.rectangle([x0, y + 10, x0 + 140, y + 20], fill=(220, 30, 30))
    for ln in textwrap.wrap((sub or '').upper(), 26)[:3]:
        y += 70
        d.text((x0, y), ln, font=f2, fill=(230, 210, 210))
    im.save(salida, quality=92)
    return salida


def escena_fecha(texto, sub, salida, W=1600, H=1000):
    """Cartel de fecha / lugar / cifra en pantalla completa."""
    im = _fondo_oscuro(W, H, rojo=True)
    d = ImageDraw.Draw(im)
    lineas = textwrap.wrap(texto.upper(), 16)[:3]
    tam = 150 if len(lineas) == 1 else 120
    y = H / 2 - (len(lineas) * (tam + 10)) / 2 - (40 if sub else 0)
    for ln in lineas:
        _texto_centrado(d, W, y, ln, _f(tam), (255, 255, 255), 8); y += tam + 10
    if sub:
        _texto_centrado(d, W, y + 30, sub.upper(), _f(56, MONO), (235, 60, 60), 3)
    im.save(salida, quality=92)
    return salida


def escena_cita(texto, autor, salida, W=1600, H=1000):
    """Documento / carta / declaración en papel viejo."""
    im = Image.new('RGB', (W, H), (16, 12, 10))
    papel = Image.new('RGB', (1260, 820), (226, 214, 188))
    dp = ImageDraw.Draw(papel)
    import random as _r
    for _ in range(2500):
        x, y = _r.randrange(1260), _r.randrange(820)
        c = _r.randrange(185, 225)
        dp.point((x, y), fill=(c, c - 10, c - 30))
    f = _f(58, MONO)
    lineas = textwrap.wrap('“' + texto.strip('"“” ') + '”', 32)[:8]
    y = max(70, (820 - len(lineas) * 80 - (90 if autor else 0)) // 2)
    for ln in lineas:
        dp.text((80, y), ln, font=f, fill=(35, 28, 22)); y += 80
    if autor:
        dp.text((80, y + 30), '— ' + autor, font=_f(46, MONO), fill=(140, 20, 20))
    papel = papel.rotate(-2, expand=True, fillcolor=(16, 12, 10))
    im.paste(papel, ((W - papel.width) // 2, (H - papel.height) // 2))
    im.save(salida, quality=92)
    return salida


def escena_mapa(img_satelite, lugar, salida, W=1600, H=1000):
    """Mapa satelital con marcador rojo y nombre del lugar."""
    im = ImageOps.fit(Image.open(img_satelite).convert('RGB'), (W, H), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    for r, a in ((70, 60), (46, 120)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(230, 30, 30), width=6)
    d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=(230, 30, 30))
    _texto_centrado(d, W, 70, lugar.upper(), _f(100), (255, 255, 255), 8)
    d.text((30, H - 50), 'Imagen satelital: Esri, Maxar', font=_f(26, MONO), fill=(230, 230, 230),
           stroke_width=2, stroke_fill=(0, 0, 0))
    im.save(salida, quality=92)
    return salida
