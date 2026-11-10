"""Kit de animación en ESTILO PLANO (como los canales de historias animadas) para Ridmer.

Se dibuja en un lienzo grande (1440x2560 vertical o 2560x1440 horizontal) y la cámara recorta y reduce al tamaño final,
así todo sale suave. Uso típico en un script de escena (lo llama tools/editar.py con: salida segundos W H):

    import sys; sys.path.insert(0, RUTA_APP)
    import plano as P
    sal, d, W, H = P.args()
    P.lienzo(W, H)
    fondo = P.ciudad_noche(P.CW * 2)
    def cuadro(t):
        img = fondo.crop((int(200 * t), 0, int(200 * t) + P.CW, P.CH)).copy()
        P.persona(img, P.CW * 0.4, P.SUELO(), 300, 'policia', 'camina', phi=t * 6.5)
        return P.camara(img, 1.1 + 0.05 * t, P.CW * 0.45, P.CH * 0.6)
    P.grabar(cuadro, sal, d)

Piezas: ciudad_noche, cielo_tormenta/nubes/lluvia/rayo, avion, selva, arroyo, mar, persona (8 tipos, poses camina,
corre, apunta, rodilla, manos_arriba, quieto, cae), carro (normal o policía), faro, luces_policia, niebla, camara
(zoom, paneo, sacudida), titulo_golpe (título que entra de golpe con destello), destello, vineta, grabar.
"""
import math, os, random, subprocess, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

APP = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(APP, '..', 'assets', 'InterDisplay-Black.otf')
if not os.path.exists(FUENTE):
    FUENTE = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FPS = 30
S = 2
W, H = 1080, 1920          # salida
CW, CH = 1440, 2560        # lienzo de dibujo
NAVY = (38, 50, 92)
NAVY_D = (27, 36, 68)
SKIN = (233, 190, 160)
SKIN_D = (205, 160, 130)
REFL = (226, 222, 70)
random.seed(7)


def args():
    """(salida, segundos, W, H) desde la línea de comandos que usa editar.py"""
    a = sys.argv
    return a[1], float(a[2]) if len(a) > 2 else 4.0, int(a[3]) if len(a) > 3 else 1080, int(a[4]) if len(a) > 4 else 1920


def lienzo(w, h):
    global W, H, CW, CH
    W, H = int(w), int(h)
    CW, CH = (1440, 2560) if H >= W else (2560, 1440)
    return CW, CH


def SUELO():
    return int(CH * 0.86)


def ease(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


# ------------------------------------------------------------------ fondos
def fachadas(ancho, alto, noche=0.55):
    im = Image.new('RGB', (ancho, alto), (40, 44, 70))
    d = ImageDraw.Draw(im)
    pal = [(196, 120, 82), (214, 170, 92), (120, 150, 160), (176, 92, 80), (150, 120, 160), (220, 190, 130), (110, 130, 110)]
    x = -40
    while x < ancho:
        w = random.randint(260, 420)
        h = random.randint(int(alto * 0.55), int(alto * 0.85))
        c = random.choice(pal)
        c = tuple(int(v * (1 - noche) + 30 * noche) for v in c)
        top = alto - h
        d.rectangle([x, top, x + w, alto], fill=c)
        # techo
        if random.random() < 0.5:
            d.polygon([(x - 10, top), (x + w // 2, top - random.randint(90, 200)), (x + w + 10, top)], fill=tuple(int(v * 0.6) for v in c))
        else:
            d.rectangle([x - 8, top - 26, x + w + 8, top], fill=tuple(int(v * 0.75) for v in c))
        # ventanas
        cols = max(2, w // 110)
        for r in range(6):
            for k in range(cols):
                wx = x + 34 + k * (w - 68) / max(1, cols - 1) - 26 if cols > 1 else x + w // 2 - 26
                wy = top + 70 + r * 150
                if wy + 100 > alto - 60:
                    break
                lit = random.random() < 0.45
                col = (255, 200, 120) if lit else tuple(int(v * 0.45) for v in c)
                d.rounded_rectangle([wx, wy, wx + 52, wy + 92], 22, fill=col)
        x += w + random.randint(0, 14)
    return im


def plaza(ancho, alto):
    im = Image.new('RGB', (ancho, alto), (70, 66, 80))
    d = ImageDraw.Draw(im)
    for y in range(0, alto, 28):
        for x in range(-30 + (y // 28 % 2) * 30, ancho, 62):
            t = y / alto
            c = int(80 + 30 * t + random.randint(-8, 8))
            d.ellipse([x, y, x + 54, y + 22], fill=(c, c - 4, c + 10))
    return im


def fondo_ciudad(ancho):
    alto_f = int(CH * 0.62)
    f = fachadas(ancho, alto_f).filter(ImageFilter.GaussianBlur(9 * S // 2))
    bg = Image.new('RGB', (ancho, CH), (30, 32, 56))
    # cielo degradado
    d = ImageDraw.Draw(bg)
    for y in range(CH):
        t = y / CH
        d.line([(0, y), (ancho, y)], fill=(int(28 + 30 * t), int(30 + 26 * t), int(60 + 30 * t)))
    bg.paste(f, (0, int(CH * 0.08)))
    p = plaza(ancho, CH - int(CH * 0.66)).filter(ImageFilter.GaussianBlur(2))
    bg.paste(p, (0, int(CH * 0.66)))
    # farolas desenfocadas
    o = Image.new('RGBA', bg.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(o)
    for x in range(200, ancho, 700):
        od.ellipse([x - 60, int(CH * 0.38) - 60, x + 60, int(CH * 0.38) + 60], fill=(255, 210, 140, 120))
    o = o.filter(ImageFilter.GaussianBlur(30))
    bg = Image.alpha_composite(bg.convert('RGBA'), o)
    return bg


def niebla(alpha=170):
    o = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    for i in range(14):
        y = int(CH * (0.62 + 0.03 * i))
        d.ellipse([-400 + random.randint(-200, 200), y, CW + 400, y + 260], fill=(200, 205, 230, alpha // 6))
    return o.filter(ImageFilter.GaussianBlur(60))




def ciudad_noche(ancho=None):
    return fondo_ciudad(ancho or CW * 2)


def degradado(ancho, alto, arriba, abajo):
    im = Image.new('RGB', (ancho, alto))
    d = ImageDraw.Draw(im)
    for y in range(alto):
        k = y / max(1, alto - 1)
        d.line([(0, y), (ancho, y)], fill=tuple(int(arriba[i] + (abajo[i] - arriba[i]) * k) for i in range(3)))
    return im


def cielo_tormenta(ancho=None):
    """Cielo de tormenta con capas de nubes (base fija). Usa nubes(t) encima para que se muevan."""
    ancho = ancho or CW * 2
    im = degradado(ancho, CH, (18, 22, 38), (52, 58, 82)).convert('RGBA')
    o = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    rnd = random.Random(11)
    for _ in range(70):
        x, y = rnd.randint(-200, ancho), rnd.randint(0, CH)
        r = rnd.randint(160, 480)
        c = rnd.randint(40, 80)
        d.ellipse([x - r * 1.6, y - r * 0.6, x + r * 1.6, y + r * 0.6], fill=(c, c + 4, c + 18, 120))
    return Image.alpha_composite(im, o.filter(ImageFilter.GaussianBlur(40)))


_NUBES = {}


def nubes(img, t, vel=220, alfa=150, semilla=3):
    """Capa de nubes cercanas que pasan rápido (sensación de velocidad)."""
    key = (img.size, semilla)
    if key not in _NUBES:
        w = img.size[0] * 2
        o = Image.new('RGBA', (w, img.size[1]), (0, 0, 0, 0))
        d = ImageDraw.Draw(o)
        rnd = random.Random(semilla)
        for _ in range(40):
            x, y, r = rnd.randint(0, w), rnd.randint(0, img.size[1]), rnd.randint(120, 380)
            c = rnd.randint(70, 110)
            d.ellipse([x - r * 1.8, y - r * 0.5, x + r * 1.8, y + r * 0.5], fill=(c, c + 4, c + 16, alfa))
        _NUBES[key] = o.filter(ImageFilter.GaussianBlur(30))
    o = _NUBES[key]
    w = o.size[0] // 2
    off = int(t * vel) % w
    capa = o.crop((off, 0, off + img.size[0], img.size[1]))
    img.alpha_composite(capa)
    return img


def lluvia(img, t, n=260, largo=90, ang=0.25, alfa=90, semilla=4):
    d = ImageDraw.Draw(img)
    rnd = random.Random(semilla)
    w, h = img.size
    for _ in range(n):
        x0, y0, v = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(1800, 2600)
        y = (y0 + t * v) % (h + largo) - largo
        x = (x0 + t * v * ang) % w
        d.line([(x, y), (x + largo * ang, y + largo)], fill=(190, 200, 230, alfa), width=3)
    return img


def rayo(img, x, semilla=1, grosor=10):
    """Dibuja un rayo ramificado desde arriba hasta ~60 % de la altura y un brillo azul alrededor."""
    rnd = random.Random(semilla)
    o = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    pts = [(x, 0)]
    y = 0
    while y < img.size[1] * 0.6:
        y += rnd.randint(60, 140)
        pts.append((pts[-1][0] + rnd.randint(-90, 90), y))
    d.line(pts, fill=(235, 240, 255, 255), width=grosor)
    for k in range(2, len(pts) - 1, 3):
        a = pts[k]
        d.line([a, (a[0] + rnd.choice((-1, 1)) * rnd.randint(80, 200), a[1] + rnd.randint(100, 220))], fill=(220, 228, 255, 230), width=grosor // 2)
    glow = o.filter(ImageFilter.GaussianBlur(28))
    img.alpha_composite(glow); img.alpha_composite(glow); img.alpha_composite(o)
    return img


def destello(img, a, color=(255, 255, 255)):
    """Cubre la imagen con un color (0..1). Útil para rayos, golpes y cortes."""
    if a <= 0:
        return img
    capa = Image.new(img.mode, img.size, color + ((int(255 * min(1, a)),) if img.mode == 'RGBA' else ()))
    if img.mode == 'RGBA':
        img.alpha_composite(capa)
        return img
    return Image.blend(img, capa, min(1, a))


def avion(img, cx, cy, k=1.0, ang=0.0, t=0.0, roto=False, fuego=False, color=(226, 228, 236)):
    """Avión de hélice (tipo Electra) de perfil hacia la derecha. ang en grados (+ = nariz abajo).
    roto=True: se parte en dos detrás del ala."""
    L, Hf = 1100 * k, 150 * k
    lay = Image.new('RGBA', (int(L * 1.5), int(L * 1.0)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ox, oy = lay.size[0] / 2 - L / 2, lay.size[1] / 2
    sep = 160 * k if roto else 0
    ventana = (60, 76, 104)
    # cola (parte trasera)
    xc = ox - sep
    d.rounded_rectangle([xc, oy - Hf / 2, xc + L * 0.5, oy + Hf / 2], Hf * 0.45, fill=color)
    d.polygon([(xc + 10 * k, oy - Hf * 0.3), (xc + 110 * k, oy - Hf * 0.3), (xc + 40 * k, oy - Hf * 1.9), (xc - 20 * k, oy - Hf * 1.9)], fill=color)
    d.polygon([(xc + 10 * k, oy), (xc + 160 * k, oy), (xc + 60 * k, oy + 40 * k)], fill=(200, 202, 212))
    d.rectangle([xc, oy - 10 * k, xc + L * 0.5, oy + 14 * k], fill=(40, 90, 170))
    # parte delantera
    xf = ox + L * 0.5
    d.rounded_rectangle([xf - Hf * 0.45, oy - Hf / 2, xf + L * 0.5, oy + Hf / 2], Hf * 0.5, fill=color)
    d.ellipse([xf + L * 0.42, oy - Hf / 2, xf + L * 0.56, oy + Hf / 2], fill=color)
    d.rectangle([xf - Hf * 0.45, oy - 10 * k, xf + L * 0.52, oy + 14 * k], fill=(40, 90, 170))
    d.polygon([(xf + L * 0.47, oy - Hf * 0.42), (xf + L * 0.53, oy - Hf * 0.3), (xf + L * 0.47, oy - Hf * 0.15)], fill=ventana)
    for i in range(10):
        wx = ox + 60 * k + i * 88 * k - (sep if ox + 60 * k + i * 88 * k < xf else 0)
        d.rounded_rectangle([wx, oy - Hf * 0.3, wx + 34 * k, oy - Hf * 0.05], 10 * k, fill=ventana)
    # ala y motores con hélices girando
    d.polygon([(xf - 40 * k, oy + 10 * k), (xf + 170 * k, oy + 10 * k), (xf + 60 * k, oy + 120 * k), (xf - 120 * k, oy + 120 * k)], fill=(190, 192, 204))
    for mx in (xf - 30 * k, xf + 110 * k):
        d.rounded_rectangle([mx, oy + 30 * k, mx + 120 * k, oy + 74 * k], 18 * k, fill=(170, 172, 184))
        a = t * 40
        for s in range(3):
            aa = a + s * 2.094
            d.line([(mx + 124 * k, oy + 52 * k), (mx + 124 * k + 8 * k * math.cos(aa), oy + 52 * k + 60 * k * math.sin(aa))], fill=(60, 60, 66), width=int(9 * k))
        if fuego and mx < xf:
            for q in range(6):
                rr = (40 + q * 18) * k * (0.8 + 0.2 * math.sin(t * 30 + q))
                d.ellipse([mx - q * 40 * k - rr, oy + 52 * k - rr * 0.6, mx - q * 40 * k + rr, oy + 52 * k + rr * 0.6],
                          fill=(255, 150 - q * 15, 40, 220 - q * 30))
    lay = lay.rotate(-ang, resample=Image.BICUBIC, center=(lay.size[0] / 2, lay.size[1] / 2))
    img.alpha_composite(lay, (int(cx - lay.size[0] / 2), int(cy - lay.size[1] / 2)))
    return img


def selva(ancho=None, noche=False):
    """Selva en capas: fondo desenfocado, troncos y hojas grandes. Devuelve la imagen base (RGBA)."""
    ancho = ancho or CW * 2
    top, bot = ((14, 30, 30), (30, 52, 40)) if noche else ((120, 168, 150), (60, 100, 70))
    im = degradado(ancho, CH, top, bot).convert('RGBA')
    rnd = random.Random(21)
    for capa, (n, esc, osc_, blur) in enumerate([(26, 0.6, 0.55, 14), (18, 0.9, 0.42, 6), (12, 1.3, 0.3, 0)]):
        o = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(o)
        for _ in range(n):
            x = rnd.randint(-100, ancho + 100)
            tw = int(rnd.randint(40, 80) * esc)
            c = tuple(int(v * osc_) for v in (90, 110, 70))
            d.rectangle([x, 0, x + tw, CH], fill=c + (255,))
            for _ in range(5):
                hy, hr = rnd.randint(0, int(CH * 0.7)), int(rnd.randint(140, 320) * esc)
                cc = tuple(int(v * osc_) for v in (60, rnd.randint(110, 150), 70))
                d.ellipse([x - hr, hy - hr * 0.6, x + tw + hr, hy + hr * 0.6], fill=cc + (255,))
        for _ in range(int(14 * esc)):               # hojas grandes del suelo
            x, y = rnd.randint(0, ancho), int(CH * rnd.uniform(0.78, 1.0))
            r = int(rnd.randint(120, 260) * esc)
            c = tuple(int(v * osc_ * 1.3) for v in (50, 120, 60))
            d.pieslice([x - r, y - r, x + r, y + r], rnd.randint(180, 230), rnd.randint(300, 350), fill=c + (255,))
        if blur:
            o = o.filter(ImageFilter.GaussianBlur(blur))
        im.alpha_composite(o)
    rayos = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(rayos)
    for k in range(6):
        x = rnd.randint(0, ancho)
        d.polygon([(x, 0), (x + 120, 0), (x + 520, CH), (x + 260, CH)], fill=(255, 250, 200, 0 if noche else 40))
    im.alpha_composite(rayos.filter(ImageFilter.GaussianBlur(40)))
    return im


def arroyo(img, y, alto=260, t=0.0):
    d = ImageDraw.Draw(img)
    w = img.size[0]
    d.rectangle([0, y, w, y + alto], fill=(70, 110, 120, 255))
    for k in range(40):
        x = (k * 173 + t * 160) % (w + 200) - 100
        yy = y + 20 + (k * 37) % (alto - 40)
        d.line([(x, yy), (x + 90, yy)], fill=(170, 200, 210, 160), width=5)
    return img


def mar(ancho, t=0.0, noche=True):
    im = degradado(ancho, CH, (20, 26, 50) if noche else (120, 170, 210), (10, 30, 50) if noche else (40, 90, 140)).convert('RGBA')
    d = ImageDraw.Draw(im)
    for k in range(60):
        y = int(CH * 0.55 + k * 22)
        x = (k * 97 + t * 80) % 300 - 300
        while x < ancho:
            d.arc([x, y, x + 200, y + 40], 200, 340, fill=(140, 170, 200, 120), width=4)
            x += 300
    return im


def camara(img, zoom=1.0, cx=None, cy=None, sacudir=0.0, t=0.0):
    """Recorta el lienzo (zoom 1 = todo) centrado en cx, cy y lo reduce a W x H. sacudir: px de temblor."""
    cx = CW / 2 if cx is None else cx
    cy = CH / 2 if cy is None else cy
    if sacudir:
        cx += sacudir * math.sin(t * 53.0)
        cy += sacudir * math.cos(t * 47.0)
    w, h = CW / zoom, CH / zoom
    x0 = min(max(0, cx - w / 2), img.size[0] - w)
    y0 = min(max(0, cy - h / 2), img.size[1] - h)
    return img.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).convert('RGB').resize((W, H), Image.LANCZOS)


_VIN = {}


def vineta(im, fuerza=0.55):
    key = (im.size, fuerza)
    if key not in _VIN:
        v = Image.new('L', im.size, 0)
        ImageDraw.Draw(v).ellipse([-im.size[0] * 0.35, -im.size[1] * 0.15, im.size[0] * 1.35, im.size[1] * 1.15], fill=255)
        _VIN[key] = v.filter(ImageFilter.GaussianBlur(min(im.size) // 6)).point(lambda p: int(255 - (255 - p) * fuerza))
    return Image.composite(im, Image.new('RGB', im.size, (0, 0, 0)), _VIN[key])


def titulo_golpe(im, texto, t, t0=0.0, color=(255, 255, 255), acento=(230, 40, 40), y=0.42):
    """Título que entra de golpe (grande → normal en 0,25 s) con sombra. Última palabra en rojo."""
    if t < t0:
        return im
    p = min(1.0, (t - t0) / 0.25)
    esc = 1.0 + 0.6 * (1 - ease(p))
    d = ImageDraw.Draw(im)
    tam = int(W * 0.11 * esc)
    f = ImageFont.truetype(FUENTE, tam)
    pal = texto.upper().split()
    lineas = [' '.join(pal[:-1]), pal[-1]] if len(pal) > 2 else [' '.join(pal)]
    yy = H * y - len(lineas) * tam * 0.55
    for i, ln in enumerate(lineas):
        col = acento if (i == len(lineas) - 1 and len(lineas) > 1) else color
        d.text((W / 2 + 5, yy + 6), ln, font=f, fill=(0, 0, 0), anchor='mm')
        d.text((W / 2, yy), ln, font=f, fill=col, anchor='mm')
        yy += tam * 1.08
    if p < 1:
        im = destello(im, 0.5 * (1 - p))
    return im


def grabar(cuadro, salida, d, fps=FPS):
    """cuadro(t) -> imagen RGB de W x H. Escribe un mp4 sin audio (editar.py le pone voz y música)."""
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps),
                           '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', salida],
                          stdin=subprocess.PIPE)
    n = int(round(d * fps))
    for i in range(n):
        im = cuadro(i / fps)
        if im.size != (W, H):
            im = im.resize((W, H), Image.LANCZOS)
        ff.stdin.write(im.convert('RGB').tobytes())
    ff.stdin.close()
    ff.wait()
    return salida


# ------------------------------------------------------------------ figuras
def capsula(d, a, b, w, col):
    d.line([a, b], fill=col, width=int(w))
    r = w / 2
    for p in (a, b):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)


def pierna(d, cadera, th, be, L, w, col, zapato):
    rodilla = (cadera[0] + L * math.sin(th), cadera[1] + L * math.cos(th))
    sa = th - be
    tobillo = (rodilla[0] + L * math.sin(sa), rodilla[1] + L * math.cos(sa))
    capsula(d, cadera, rodilla, w, col)
    capsula(d, rodilla, tobillo, w * 0.88, col)
    fx = tobillo[0]
    d.rounded_rectangle([fx - w * 0.45, tobillo[1] - w * 0.35, fx + w * 1.15, tobillo[1] + w * 0.38], w * 0.3, fill=zapato)
    return tobillo



def rueda(d, c, r, ang):
    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(18, 18, 22))
    ri = r * 0.6
    d.ellipse([c[0] - ri, c[1] - ri, c[0] + ri, c[1] + ri], fill=(150, 154, 166))
    for k in range(5):
        a = ang + k * 2 * math.pi / 5
        capsula(d, c, (c[0] + ri * 0.85 * math.cos(a), c[1] + ri * 0.85 * math.sin(a)), r * 0.13, (95, 98, 110))
    rc = r * 0.16
    d.ellipse([c[0] - rc, c[1] - rc, c[0] + rc, c[1] + rc], fill=(60, 62, 70))


def carro(img, x, suelo, k, dist, color=(26, 27, 32), policia_=False, t=0.0):
    """Carro de perfil hacia la derecha. x = parte trasera; k = escala; dist = distancia recorrida (gira ruedas)."""
    d = ImageDraw.Draw(img)
    L, Hc = 900 * k, 300 * k
    r = 80 * k
    base = suelo - r * 0.55
    # sombra
    d.ellipse([x - 20 * k, suelo - 18 * k, x + L + 20 * k, suelo + 18 * k], fill=(18, 18, 26))
    d.rounded_rectangle([x, base - Hc * 0.55, x + L, base], 46 * k, fill=color)
    d.polygon([(x + L * 0.08, base - Hc * 0.55), (x + L * 0.17, base - Hc * 1.02), (x + L * 0.66, base - Hc * 1.02),
               (x + L * 0.8, base - Hc * 0.55)], fill=color)
    vid = (60, 74, 98) if not policia_ else (70, 86, 112)
    d.polygon([(x + L * 0.15, base - Hc * 0.6), (x + L * 0.2, base - Hc * 0.94), (x + L * 0.4, base - Hc * 0.94), (x + L * 0.4, base - Hc * 0.6)], fill=vid)
    d.polygon([(x + L * 0.43, base - Hc * 0.6), (x + L * 0.43, base - Hc * 0.94), (x + L * 0.64, base - Hc * 0.94), (x + L * 0.75, base - Hc * 0.6)], fill=vid)
    d.line([(x + L * 0.47, base - Hc * 0.9), (x + L * 0.6, base - Hc * 0.66)], fill=(140, 160, 190), width=int(10 * k))
    if not policia_:
        # conductor con casco (silueta)
        hx, hy = x + L * 0.58, base - Hc * 0.74
        d.ellipse([hx - 44 * k, hy - 46 * k, hx + 44 * k, hy + 40 * k], fill=(40, 48, 36))
    else:
        d.rectangle([x, base - Hc * 0.36, x + L, base - Hc * 0.22], fill=(40, 90, 200))
        f = ImageFont.truetype(FUENTE, int(70 * k))
        d.text((x + L * 0.5, base - Hc * 0.42), 'POLICÍA', font=f, fill=(40, 90, 200), anchor='mm')
        on = int(t * 6) % 2
        d.rounded_rectangle([x + L * 0.33, base - Hc * 1.12, x + L * 0.43, base - Hc * 1.02], 8 * k, fill=(60, 120, 255) if on else (40, 60, 120))
        d.rounded_rectangle([x + L * 0.43, base - Hc * 1.12, x + L * 0.53, base - Hc * 1.02], 8 * k, fill=(255, 60, 60) if not on else (120, 40, 40))
    d.line([(x + L * 0.42, base - Hc * 0.5), (x + L * 0.42, base - Hc * 0.05)], fill=tuple(max(0, v - 12) for v in color), width=int(6 * k))
    d.rounded_rectangle([x + L - 40 * k, base - Hc * 0.45, x + L + 4 * k, base - Hc * 0.32], 10 * k, fill=(255, 236, 170))
    d.rounded_rectangle([x - 4 * k, base - Hc * 0.45, x + 26 * k, base - Hc * 0.3], 8 * k, fill=(200, 30, 40))
    ang = dist / r
    for cxw in (x + L * 0.2, x + L * 0.8):
        rueda(d, (cxw, suelo - r), r, ang)


def faro(img, x, y, largo, alfa=70):
    o = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    d.polygon([(x, y - 10), (x + largo, y - 160), (x + largo, y + 200), (x, y + 14)], fill=(255, 238, 180, alfa))
    o = o.filter(ImageFilter.GaussianBlur(26))
    return Image.alpha_composite(img, o)


def luces_policia(img, x, y, t):
    o = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    on = int(t * 6) % 2
    col = (60, 120, 255, 120) if on else (255, 50, 50, 110)
    d.ellipse([x - 500, y - 400, x + 500, y + 400], fill=col)
    o = o.filter(ImageFilter.GaussianBlur(120))
    return Image.alpha_composite(img, o)




# ------------------------------------------------------------------ personajes v2
TIPOS = {
    'policia':    dict(camisa=(38, 50, 92), pantalon=(32, 42, 78), piel=(233, 190, 160), cabeza='gorra', extra='reflectivo', zapato=(22, 22, 28)),
    'soldado':    dict(camisa=(84, 96, 62), pantalon=(74, 84, 56), piel=(40, 40, 44), cabeza='casco', extra='chaleco', zapato=(30, 28, 24)),
    'mujer':      dict(camisa=(142, 46, 58), pantalon=(40, 36, 44), piel=(226, 180, 150), cabeza='pelo_largo', extra='abrigo', zapato=(30, 22, 22), fino=0.85),
    'nino':       dict(camisa=(232, 178, 60), pantalon=(60, 90, 150), piel=(214, 168, 130), cabeza='pelo_corto', extra='', zapato=(200, 60, 50), nino=True),
    'anciano':    dict(camisa=(120, 92, 70), pantalon=(80, 78, 84), piel=(222, 182, 156), cabeza='pelo_gris', extra='baston', zapato=(50, 36, 30), encorvado=0.18),
    'encapuchado': dict(camisa=(34, 34, 40), pantalon=(46, 48, 58), piel=(30, 28, 30), cabeza='capucha', extra='', zapato=(220, 220, 225)),
    'medico':     dict(camisa=(238, 240, 244), pantalon=(70, 150, 140), piel=(200, 150, 115), cabeza='pelo_corto', extra='bata', zapato=(230, 230, 235)),
    'senor':      dict(camisa=(54, 56, 66), pantalon=(46, 48, 58), piel=(190, 140, 105), cabeza='pelo_corto', extra='corbata', zapato=(26, 22, 20)),
}


def osc(c, f=0.72):
    return tuple(int(v * f) for v in c[:3])


def cap(d, a, b, w, col):
    d.line([a, b], fill=col, width=max(1, int(w)))
    r = w / 2
    for p in (a, b):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)


def _pierna(d, cadera, th, be, L, w, col, zap, sh=None):
    rod = (cadera[0] + L * math.sin(th), cadera[1] + L * math.cos(th))
    sa = th - be
    tob = (rod[0] + L * math.sin(sa), rod[1] + L * math.cos(sa))
    cap(d, cadera, rod, w, col)
    cap(d, rod, tob, w * 0.82, col if sh is None else sh)
    d.rounded_rectangle([tob[0] - w * 0.42, tob[1] - w * 0.3, tob[0] + w * 1.15, tob[1] + w * 0.34], w * 0.28, fill=zap)
    return rod, tob


def _pose(pose, phi):
    """devuelve (piernas [(th, be)]x2 lejana/cercana, brazos [(a, f)]x2, inclinación)"""
    s, c = math.sin, math.cos
    if pose == 'camina':
        def pg(p): return 0.42 * s(p), 0.06 + 0.9 * max(0.0, c(p)) ** 1.4
        return [pg(phi + math.pi), pg(phi)], [(-0.38 * s(phi + math.pi), 0.3 + 0.3 * max(0, s(phi + math.pi))),
                                              (-0.38 * s(phi), 0.3 + 0.3 * max(0, s(phi)))], 0.03
    if pose == 'corre':
        def pg(p): return 0.75 * s(p), 0.25 + 1.5 * max(0.0, c(p))
        return [pg(phi + math.pi), pg(phi)], [(-0.9 * s(phi + math.pi), 1.5), (-0.9 * s(phi), 1.5)], 0.22
    if pose == 'apunta':
        return [(-0.25, 0.05), (0.22, 0.1)], [(math.pi / 2 - 0.05, 0.0), (math.pi / 2 + 0.02, 0.0)], 0.0
    if pose == 'rodilla':
        return [(-0.1, 0.0), (1.45, 1.55)], [(0.25, 0.4), (0.6, 0.9)], 0.05
    if pose == 'cae':
        return [(0.7 + 0.25 * s(phi * 1.7), 1.1), (-0.35 + 0.25 * s(phi * 1.3), 0.7)], \
               [(math.pi - 0.7 + 0.3 * s(phi * 2.1), 0.3), (math.pi - 1.3 + 0.3 * s(phi * 1.9), 0.5)], 0.0
    if pose == 'manos_arriba':
        return [(-0.08, 0.02), (0.08, 0.02)], [(math.pi - 0.35, 0.5), (math.pi - 0.2, 0.5)], 0.0
    return [(-0.06, 0.03), (0.06, 0.03)], [(0.08, 0.12), (-0.05, 0.15)], 0.0


def persona(img, x, suelo, u, tipo='policia', pose='quieto', phi=0.0, rim=(255, 168, 90), luz='der', arma=None, mira='der', giro=0.0):
    """tipo: policia, soldado, mujer, nino, anciano, encapuchado, medico, senor. pose: quieto, camina, corre, apunta,
    rodilla, manos_arriba, cae (phi = fase del paso; avanza ~6.5 por segundo al caminar). giro: grados (caídas)."""
    T = TIPOS[tipo]
    if T.get('nino'):
        u *= 0.62
    fino = T.get('fino', 1.0)
    pad = int(3.2 * u)
    Wl, Hl = int(6.4 * u), int(5.6 * u)
    lay = Image.new('RGBA', (Wl, Hl), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ox, sy = Wl / 2, Hl - 0.3 * u                     # pies en sy
    legs, arms, tilt = _pose(pose, phi)
    tilt += T.get('encorvado', 0.0)
    L = 1.0 * u
    wl = 0.24 * u * fino
    if pose == 'rodilla':
        cadera = (ox, sy - L * 1.0 - 0.1 * u)
    else:
        low = max(L * math.cos(t) + L * math.cos(t - b) for t, b in legs)
        cadera = (ox, sy - low - 0.32 * wl)
    LT = 1.25 * u * (0.92 if T.get('nino') else 1.0)
    hombro = (cadera[0] + LT * math.sin(tilt), cadera[1] - LT * math.cos(tilt))
    LA = 0.78 * u
    wa = 0.17 * u * fino
    cam, pan, piel, zap = T['camisa'], T['pantalon'], T['piel'], T['zapato']

    def brazo(a, f, col, mano_col):
        a2 = a + tilt
        codo = (hombro[0] + LA * math.sin(a2), hombro[1] + LA * math.cos(a2))
        mu = (codo[0] + LA * 0.92 * math.sin(a2 + f), codo[1] + LA * 0.92 * math.cos(a2 + f))
        cap(d, hombro, codo, wa, col)
        cap(d, codo, mu, wa * 0.9, col)
        r = wa * 0.55
        d.ellipse([mu[0] - r, mu[1] - r, mu[0] + r, mu[1] + r], fill=mano_col)
        return codo, mu

    # --- lado lejano (más oscuro)
    brazo(*arms[0], osc(cam), osc(piel))
    if pose == 'rodilla':
        # pierna lejana: muslo hacia abajo, canilla atrás en el suelo
        rod = (cadera[0] + 0.15 * u, sy - 0.12 * u)
        cap(d, cadera, rod, wl, osc(pan)); cap(d, rod, (rod[0] - L * 0.95, sy - 0.1 * u), wl * 0.82, osc(pan))
        d.rounded_rectangle([rod[0] - L * 1.15, sy - 0.25 * u, rod[0] - L * 0.85, sy], 0.06 * u, fill=osc(zap))
    else:
        _pierna(d, cadera, *legs[0], L, wl, osc(pan), osc(zap))
    # --- abrigo / bata (detrás de la pierna cercana)
    largo = T['extra'] in ('abrigo', 'bata')
    # --- pierna cercana
    if pose == 'rodilla':
        rod = (cadera[0] + L * 0.95, cadera[1] + 0.05 * u)
        cap(d, cadera, rod, wl, pan); cap(d, rod, (rod[0], sy - 0.1 * u), wl * 0.82, pan)
        d.rounded_rectangle([rod[0] - wl * 0.4, sy - 0.25 * u, rod[0] + wl * 1.2, sy], 0.06 * u, fill=zap)
    else:
        _pierna(d, cadera, *legs[1], L, wl, pan, zap)
    # --- torso (trapecio redondeado inclinado)
    def rot(px, py):
        cs, sn = math.cos(tilt), math.sin(tilt)
        return (cadera[0] + px * cs - py * sn, cadera[1] + px * sn + py * cs)
    hw, ww = 0.27 * u * fino, 0.21 * u * fino
    ytop = -LT - 0.08 * u
    cuerpo = [rot(-ww, 0.1 * u), rot(-hw, ytop + 0.12 * u), rot(-hw + 0.08 * u, ytop), rot(hw - 0.08 * u, ytop),
              rot(hw, ytop + 0.12 * u), rot(ww, 0.1 * u)]
    d.polygon(cuerpo, fill=cam)
    # sombra de la espalda (mitad trasera)
    d.polygon([rot(-ww, 0.1 * u), rot(-hw, ytop + 0.12 * u), rot(-hw + 0.08 * u, ytop), rot(-hw * 0.25, ytop), rot(-ww * 0.25, 0.1 * u)], fill=osc(cam, 0.82))
    if largo:
        col = cam if T['extra'] == 'bata' else cam
        d.polygon([rot(-hw, ytop + 0.3 * u), rot(hw, ytop + 0.3 * u), rot(hw + 0.12 * u, 0.85 * u), rot(-hw - 0.08 * u, 0.85 * u)], fill=col)
        d.polygon([rot(-hw, ytop + 0.3 * u), rot(-hw * 0.2, ytop + 0.3 * u), rot(-hw * 0.2, 0.85 * u), rot(-hw - 0.08 * u, 0.85 * u)], fill=osc(col, 0.85))
        if T['extra'] == 'bata':
            d.line([rot(hw * 0.55, ytop + 0.1 * u), rot(hw * 0.75, 0.85 * u)], fill=(200, 204, 212), width=int(0.025 * u))
    ex = T['extra']
    if ex == 'reflectivo':
        d.polygon([rot(-hw, -LT * 0.55), rot(hw, -LT * 0.55), rot(hw, -LT * 0.47), rot(-hw, -LT * 0.47)], fill=(226, 222, 70))
    if ex in ('reflectivo', '', 'corbata', 'baston'):
        d.polygon([rot(-ww - 0.01 * u, -0.02 * u), rot(ww + 0.01 * u, -0.02 * u), rot(ww + 0.01 * u, 0.08 * u), rot(-ww - 0.01 * u, 0.08 * u)], fill=osc(pan, 0.6))
    if ex == 'chaleco':
        d.rounded_rectangle([0, 0, 1, 1], 1)
        d.polygon([rot(-hw - 0.04 * u, ytop + 0.18 * u), rot(hw + 0.05 * u, ytop + 0.18 * u), rot(ww + 0.06 * u, -0.08 * u), rot(-ww - 0.05 * u, -0.08 * u)], fill=(58, 64, 44))
        for k in range(3):
            yy = ytop + 0.5 * u + k * 0.22 * u
            d.polygon([rot(0.0, yy), rot(hw * 0.9, yy), rot(hw * 0.9, yy + 0.14 * u), rot(0.0, yy + 0.14 * u)], fill=(70, 78, 52))
    if ex == 'corbata':
        d.polygon([rot(0.05 * u, ytop + 0.05 * u), rot(0.11 * u, ytop + 0.05 * u), rot(0.1 * u, ytop + 0.55 * u), rot(0.07 * u, ytop + 0.6 * u)], fill=(150, 30, 40))
        d.polygon([rot(0.02 * u, ytop), rot(0.14 * u, ytop), rot(0.08 * u, ytop + 0.1 * u)], fill=(235, 235, 240))
    # --- cuello y cabeza
    hr = 0.27 * u * (1.18 if T.get('nino') else 1.0)
    cuello = rot(0.03 * u, ytop - 0.02 * u)
    hc = (cuello[0] + 0.02 * u + hr * 0.15 * math.sin(tilt), cuello[1] - hr * 1.05)
    cap(d, cuello, (hc[0], hc[1] + hr * 0.5), 0.13 * u, osc(piel, 0.88))
    cx, cy = hc
    cab = T['cabeza']
    if cab == 'pelo_largo':
        d.ellipse([cx - hr * 1.15, cy - hr * 1.05, cx + hr * 0.6, cy + hr * 1.9], fill=(46, 30, 24))
    d.ellipse([cx - hr, cy - hr * 1.05, cx + hr, cy + hr], fill=piel)
    d.ellipse([cx + hr * 0.8, cy - hr * 0.05, cx + hr * 1.13, cy + hr * 0.3], fill=piel)          # nariz
    d.ellipse([cx - hr * 0.2, cy - hr * 0.05, cx + hr * 0.1, cy + hr * 0.38], fill=osc(piel, 0.86))   # oreja
    if cab == 'gorra':
        d.chord([cx - hr * 1.03, cy - hr * 1.3, cx + hr * 1.03, cy + hr * 0.5], 180, 360, fill=osc(cam, 0.75))
        d.rounded_rectangle([cx - hr * 0.1, cy - hr * 0.42, cx + hr * 1.6, cy - hr * 0.22], hr * 0.1, fill=(18, 22, 40))
        d.ellipse([cx + hr * 0.05, cy - hr * 1.05, cx + hr * 0.38, cy - hr * 0.72], fill=(212, 180, 70))
    elif cab == 'casco':
        d.chord([cx - hr * 1.2, cy - hr * 1.45, cx + hr * 1.2, cy + hr * 0.75], 180, 360, fill=(70, 80, 54))
        d.rectangle([cx - hr * 1.2, cy - hr * 0.38, cx + hr * 1.2, cy - hr * 0.3], fill=(56, 64, 42))
    elif cab in ('pelo_corto', 'pelo_gris'):
        pc = (40, 30, 26) if cab == 'pelo_corto' else (205, 205, 210)
        d.chord([cx - hr * 1.04, cy - hr * 1.12, cx + hr * 1.0, cy + hr * 0.55], 160, 360, fill=pc)
        d.pieslice([cx - hr * 1.04, cy - hr * 1.0, cx + hr * 0.2, cy + hr * 0.9], 120, 270, fill=pc)
    elif cab == 'pelo_largo':
        d.chord([cx - hr * 1.06, cy - hr * 1.12, cx + hr * 1.02, cy + hr * 0.4], 170, 360, fill=(46, 30, 24))
    elif cab == 'capucha':
        d.ellipse([cx - hr * 1.25, cy - hr * 1.3, cx + hr * 1.05, cy + hr * 1.15], fill=osc(cam, 1.15))
        d.ellipse([cx + hr * 0.05, cy - hr * 0.75, cx + hr * 1.1, cy + hr * 0.85], fill=(14, 14, 18))
    # --- brazo cercano y objetos
    codo, mano = brazo(*arms[1], cam, piel)
    if arma == 'pistola':
        d.rounded_rectangle([mano[0] - 0.04 * u, mano[1] - 0.17 * u, mano[0] + 0.36 * u, mano[1] - 0.04 * u], 0.03 * u, fill=(22, 22, 26))
        d.rectangle([mano[0] - 0.02 * u, mano[1] - 0.06 * u, mano[0] + 0.08 * u, mano[1] + 0.14 * u], fill=(22, 22, 26))
    elif arma == 'rifle':
        d.polygon([(mano[0] - 0.75 * u, mano[1] + 0.02 * u), (mano[0] + 0.85 * u, mano[1] - 0.12 * u), (mano[0] + 0.85 * u, mano[1] - 0.02 * u),
                   (mano[0] - 0.55 * u, mano[1] + 0.18 * u), (mano[0] - 0.8 * u, mano[1] + 0.22 * u)], fill=(26, 26, 22))
        d.rectangle([mano[0] - 0.1 * u, mano[1], mano[0] + 0.02 * u, mano[1] + 0.22 * u], fill=(26, 26, 22))
    if ex == 'baston':
        d.line([mano, (mano[0] + 0.12 * u, sy)], fill=(90, 60, 36), width=int(0.06 * u))

    # --- luz: borde iluminado en un lado y sombra suave en el otro
    A = lay.split()[3]
    k = max(2, int(0.035 * u))
    dx = -k if luz == 'der' else k
    borde = ImageChops.subtract(A, ImageChops.offset(A, dx, 0))
    borde = borde.filter(ImageFilter.GaussianBlur(0.6))
    rim_l = Image.new('RGBA', lay.size, rim + (0,)); rim_l.putalpha(borde.point(lambda v: int(v * 0.85)))
    som = ImageChops.subtract(A, ImageChops.offset(A, -dx * 4, 0)).filter(ImageFilter.GaussianBlur(k))
    som_l = Image.new('RGBA', lay.size, (10, 12, 30, 0)); som_l.putalpha(som.point(lambda v: int(v * 0.35)))
    lay = Image.alpha_composite(lay, som_l)
    lay = Image.alpha_composite(lay, rim_l)
    lay.putalpha(ImageChops.multiply(lay.split()[3], A))
    if mira == 'izq':
        lay = lay.transpose(Image.FLIP_LEFT_RIGHT)
    if giro:
        lay = lay.rotate(giro, resample=Image.BICUBIC, center=(ox, sy - 1.9 * u))
    # sombra en el piso
    if pose != 'cae':
        sd = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sd).ellipse([x - 0.9 * u, suelo - 0.12 * u, x + 0.9 * u, suelo + 0.12 * u], fill=(0, 0, 0, 90))
        img.alpha_composite(sd.filter(ImageFilter.GaussianBlur(0.08 * u)))
    img.alpha_composite(lay, (int(x - ox), int(suelo - sy)))
    return img


# ------------------------------------------------------------------ fotos reales con estilo (nunca planas)
def polaroid_anim(foto, salida, d, w=1080, h=1920, pie='', estilo='polaroid', dato='', semilla=0):
    """Anima una foto real: 'polaroid' (cae con rebote, inclinada, con cinta y pie de foto) o 'duo' (teñida de color
    con marco rojo y un DATO grande que entra de golpe). Fondo: la misma foto desenfocada y oscura."""
    from PIL import ImageOps, ImageEnhance
    lienzo(w, h)
    rnd = random.Random(semilla)
    src = Image.open(foto).convert('RGB')
    fondo = ImageEnhance.Brightness(ImageOps.fit(src, (W, H)).filter(ImageFilter.GaussianBlur(28))).enhance(0.38).convert('RGBA')
    vert = H >= W
    if estilo == 'duo':
        g = ImageOps.grayscale(ImageOps.fit(src, (int(W * 0.84), int(H * 0.56)) if vert else (int(W * 0.55), int(H * 0.6))))
        ph = ImageOps.colorize(g, black=(20, 10, 40), white=(255, 130, 90), mid=(160, 40, 80))
        card = Image.new('RGBA', (ph.size[0] + 24, ph.size[1] + 24), (230, 40, 40, 255))
        card.paste(ph, (12, 12))
    else:
        pw = int(W * 0.72) if vert else int(H * 0.62)
        ph = ImageEnhance.Color(ImageOps.fit(src, (pw, int(pw * 1.02)))).enhance(0.9)
        card = Image.new('RGBA', (pw + 70, int(pw * 1.02) + 70 + (110 if pie else 60)), (246, 243, 236, 255))
        card.paste(ph, (35, 35))
        if pie:
            f = ImageFont.truetype(FUENTE, int(pw * 0.07))
            ImageDraw.Draw(card).text((card.size[0] / 2, card.size[1] - 70), pie, font=f, fill=(40, 40, 50), anchor='mm')
    rot_fin = rnd.choice((-1, 1)) * rnd.uniform(3, 6) if estilo != 'duo' else 0
    cinta = Image.new('RGBA', (int(card.size[0] * 0.38), int(card.size[0] * 0.11)), (240, 230, 190, 185))
    fdato = ImageFont.truetype(FUENTE, int(W * 0.13)) if dato else None

    def cuadro(t):
        img = fondo.copy()
        p = min(1.0, t / 0.45)
        caida = (1 - ease(p)) * (-H * 0.9) + (math.sin(min(1, (t - 0.45) / 0.35) * math.pi) * -18 if 0.45 < t < 0.8 else 0)
        zoom = 1.0 + 0.06 * ease(t / max(d, 0.1))
        ang = rot_fin + (1 - ease(p)) * 14 * (1 if rot_fin >= 0 else -1) + 0.6 * math.sin(t * 0.8)
        c = card.resize((int(card.size[0] * zoom), int(card.size[1] * zoom)), Image.BICUBIC)
        if estilo != 'duo' and t > 0.4:
            ci = cinta.rotate(rnd.uniform(-4, 4) if False else 6, expand=True)
            c.alpha_composite(ci, (int(c.size[0] / 2 - ci.size[0] / 2), 0))
        c = c.rotate(ang, expand=True, resample=Image.BICUBIC)
        x = int(W / 2 - c.size[0] / 2)
        y = int((H * (0.44 if (dato and vert) else (0.42 if dato else 0.5))) - c.size[1] / 2 + caida)
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 170), (x + 22, y + 30), c.split()[3])
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)))
        img.alpha_composite(c, (x, y))
        im = img.convert('RGB')
        if dato and t > 0.5:
            q = min(1.0, (t - 0.5) / 0.22)
            esc = 1 + 0.7 * (1 - ease(q))
            fd = ImageFont.truetype(FUENTE, int(W * 0.13 * esc))
            dd = ImageDraw.Draw(im)
            yd = y + c.size[1] + H * 0.06 if vert else H * 0.86
            dd.text((W / 2 + 5, yd + 6), dato, font=fd, fill=(0, 0, 0), anchor='mm')
            dd.text((W / 2, yd), dato, font=fd, fill=(255, 255, 255), anchor='mm')
        if t < 0.08:
            im = destello(im, 0.25)
        return vineta(im, 0.45)
    return grabar(cuadro, salida, d)


# ------------------------------------------------------------------ personajes v3 (con cara, de frente / 3/4)
try:
    from gente3 import figura, PERSONAS  # noqa: F401  (ver gente3.py)
except Exception:
    pass
