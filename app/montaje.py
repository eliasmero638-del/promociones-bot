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
    fw, fh = (W, int(H * 0.62)) if H > W else (W, H)
    z = '(1+0.10*t/{d})' if i % 2 == 0 else '(1.10-0.10*t/{d})'
    z = z.format(d=max(d, 0.5))
    fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:3,eq=brightness=-0.33[bg];"
          f"[0:v]scale={fw}:{fh}:force_original_aspect_ratio=decrease[f0];"
          f"[f0]scale=w='trunc(iw*{z}/2)*2':h=-2:eval=frame[fg];"
          f"[bg][fg]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame,fps=30,format=yuv420p[v]")
    sh(['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-t', f'{d:.3f}', '-i', img, '-filter_complex', fc, '-map', '[v]',
        '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-an', salida])


def _ass(palabras, W, H, titulo, path, por_linea=4):
    vertical = H > W
    lineas, g = [], []
    for w in palabras:
        if g and (w[0] - g[-1][1] > 0.6):
            lineas.append(g); g = []
        g.append(w)
        if len(g) >= por_linea or re.search(r'[.?!,;:]$', w[2]):
            lineas.append(g); g = []
    if g:
        lineas.append(g)
    if vertical:
        estilos = ("Style: Cap,Inter Display Black,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,7,2,2,60,60,430,1\n"
                   "Style: Tit,Inter Display Black,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,7,0,8,60,60,170,1\n"
                   "Style: Mar,Inter Display Black,40,&H002020E0,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,6,0,1,3,0,8,60,60,95,1\n")
    else:
        estilos = "Style: Cap,Inter Display Black,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,6,2,2,120,120,70,1\n"
    ev = []
    fin = palabras[-1][1] + 1 if palabras else 1
    if vertical and titulo:
        ev.append(f'Dialogue: 1,0:00:00.00,{_t(fin + 30)},Mar,,0,0,0,,RIDMER')
        ev.append(f'Dialogue: 1,0:00:00.00,{_t(fin + 30)},Tit,,0,0,0,,{_esc(titulo.upper())}')
    for g in lineas:
        ev.append(f'Dialogue: 0,{_t(g[0][0])},{_t(g[-1][1] + 0.12)},Cap,,0,0,0,,{_esc(" ".join(x[2] for x in g)).upper()}')
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
    _ass(palabras, W, H, titulo if formato == 'vertical' else '', ass)
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
