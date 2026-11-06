"""Calle v2: casas de pueblo latino (repello con textura, teja por filas, rejas, balcón, zócalo, grietas, cables)
y árboles con ramas que se abren y copa con volumen (sombra abajo, luz de luna arriba, hojas sueltas)."""
import os
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance

OUT = os.environ.get('KIT_OUT', '.') + '/'
rnd = random.Random(11)
T = (22, 16, 14)


def grad(w, h, a, b):
    t = np.linspace(0, 1, h)[:, None, None]
    return Image.fromarray((np.array(a) * (1 - t) + np.array(b) * t).repeat(w, 1).astype(np.uint8))


def textura(w, h, col, var=14, semilla=0):
    rng = np.random.default_rng(semilla)
    n = rng.normal(0, 1, (h // 6 + 1, w // 6 + 1))
    n = np.asarray(Image.fromarray(((n + 3) * 40).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 120 - 1
    fino = rng.normal(0, 0.35, (h, w))
    arr = np.array(col, np.float32)[None, None, :] + (n + fino)[..., None] * var
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))


# ------------------------------------------------------------ árboles
def rama(d, x, y, ang, largo, grosor, nivel, puntas):
    x2, y2 = x + math.cos(ang) * largo, y + math.sin(ang) * largo
    d.line([(x, y), (x2, y2)], fill=(30, 22, 18), width=max(1, int(grosor)))
    if nivel == 0 or largo < 14:
        puntas.append((x2, y2))
        return
    for da in (-0.45 + rnd.uniform(-0.15, 0.15), 0.4 + rnd.uniform(-0.15, 0.15)) + ((rnd.uniform(-0.1, 0.1),) if nivel > 3 else ()):
        rama(d, x2, y2, ang + da, largo * rnd.uniform(0.66, 0.8), grosor * 0.68, nivel - 1, puntas)


def arbol(lienzo, x, base, alto, luna=(-1, -1), oscuro=(12, 26, 20), medio=(26, 50, 38), claro=(70, 104, 92)):
    W, H = lienzo.size
    capa = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    # tronco con corteza
    g = alto * 0.06
    d.polygon([(x - g * 1.4, base), (x - g * 0.7, base - alto * 0.35), (x + g * 0.7, base - alto * 0.35), (x + g * 1.5, base)],
              fill=(42, 32, 26))
    for j in range(6):
        xx = x - g + j * g * 0.4
        d.line([(xx, base - 4), (xx + rnd.uniform(-3, 3), base - alto * 0.33)], fill=(28, 20, 16), width=2)
    d.polygon([(x + g * 0.2, base), (x + g * 0.1, base - alto * 0.35), (x + g * 0.7, base - alto * 0.35), (x + g * 1.5, base)],
              fill=(26, 20, 16))                                                    # lado en sombra
    puntas = []
    rama(d, x, base - alto * 0.33, -math.pi / 2, alto * 0.24, g * 1.2, 5, puntas)
    # copa: racimos de hojas, sombra abajo-derecha, luz de luna arriba-izquierda
    cx = np.mean([p[0] for p in puntas]); cy = np.mean([p[1] for p in puntas])
    racimos = puntas + [(cx + rnd.gauss(0, alto * 0.18), cy + rnd.gauss(0, alto * 0.1)) for _ in range(20)]
    for paso, col, dx, dy, esc in ((0, oscuro, 6, 8, 1.0), (1, medio, 0, 0, 0.82), (2, claro, -7, -9, 0.42)):
        for (px, py) in racimos:
            r = alto * rnd.uniform(0.06, 0.1) * esc
            if paso == 2 and (px - cx) > alto * 0.05:
                continue
            for _ in range(5):
                ox, oy = rnd.gauss(0, r * 0.5), rnd.gauss(0, r * 0.4)
                rr = r * rnd.uniform(0.5, 0.9)
                d.ellipse([px + ox + dx - rr, py + oy + dy - rr * 0.8, px + ox + dx + rr, py + oy + dy + rr * 0.8], fill=col)
    for _ in range(int(alto * 1.2)):                                                  # hojitas sueltas en el borde
        a = rnd.uniform(0, 2 * math.pi)
        rr = alto * rnd.uniform(0.2, 0.32)
        px, py = cx + math.cos(a) * rr * 1.1, cy + math.sin(a) * rr * 0.75
        d.ellipse([px - 4, py - 2, px + 4, py + 2], fill=medio if rnd.random() < 0.6 else oscuro)
    capa = capa.filter(ImageFilter.GaussianBlur(0.6))
    lienzo.alpha_composite(capa)


# ------------------------------------------------------------ casas
def casa(lienzo, x, suelo, w, h, color, semilla, luz_ventana=False, balcon=False):
    W, H = lienzo.size
    rs = random.Random(semilla)
    pared = textura(int(w), int(h), color, 10, semilla)
    pd = ImageDraw.Draw(pared)
    pd.rectangle([0, h - h * 0.18, w, h], fill=tuple(int(c * 0.55) for c in color))            # zócalo pintado
    for _ in range(1):                                                                          # repello caído: ladrillo
        px, py = rs.uniform(10, w - 70), rs.uniform(20, h * 0.6)
        pw, ph = rs.uniform(30, 50), rs.uniform(22, 34)
        pd.polygon([(px, py), (px + pw, py + 4), (px + pw - 6, py + ph), (px + 4, py + ph - 3)], fill=(120, 64, 46))
        for yy in range(int(py) + 6, int(py + ph) - 4, 10):
            pd.line([(px + 4, yy), (px + pw - 8, yy)], fill=(90, 46, 34), width=2)
    for _ in range(2):                                                                          # grietas
        px, py = rs.uniform(10, w - 10), rs.uniform(0, h * 0.4)
        pts = [(px, py)]
        for _ in range(5):
            px += rs.uniform(-10, 10); py += rs.uniform(8, 20); pts.append((px, py))
        pd.line(pts, fill=tuple(int(c * 0.5) for c in color), width=2)
    # puerta de madera y ventanas con reja
    dw, dh = w * 0.24, h * 0.55
    dx = w * 0.15
    pd.rectangle([dx, h - dh, dx + dw, h], fill=(70, 44, 30), outline=T, width=3)
    for j in range(3):
        pd.rectangle([dx + 8, h - dh + 10 + j * dh / 3, dx + dw - 8, h - dh + dh / 3 - 4 + j * dh / 3], outline=(50, 30, 20), width=3)
    pd.ellipse([dx + dw - 18, h - dh / 2 - 4, dx + dw - 10, h - dh / 2 + 4], fill=(180, 150, 80))
    vx, vy, vw, vh = w * 0.52, h * 0.3, w * 0.34, h * 0.34
    pd.rectangle([vx, vy, vx + vw, vy + vh], fill=(230, 170, 80) if luz_ventana else (28, 26, 30), outline=T, width=3)
    if luz_ventana:
        pd.rectangle([vx + 6, vy + 6, vx + vw * 0.45, vy + vh - 6], fill=(170, 110, 60))        # cortina
    for j in range(1, 6):
        pd.line([(vx + j * vw / 6, vy), (vx + j * vw / 6, vy + vh)], fill=(20, 20, 22), width=4)  # reja
    pd.line([(vx, vy + vh / 2), (vx + vw, vy + vh / 2)], fill=(20, 20, 22), width=4)
    pd.rectangle([vx - 6, vy + vh, vx + vw + 6, vy + vh + 8], fill=tuple(int(c * 0.8) for c in color))
    # sombra del alero sobre la pared
    sh = Image.new('L', pared.size, 0)
    ImageDraw.Draw(sh).rectangle([0, 0, w, 22], fill=150)
    pared = Image.composite(Image.new('RGB', pared.size, (10, 8, 10)), pared, sh.filter(ImageFilter.GaussianBlur(8)))
    lienzo.paste(pared, (int(x), int(suelo - h)))
    d = ImageDraw.Draw(lienzo)
    # techo de teja por filas
    tx0, tx1, ty = x - 26, x + w + 26, suelo - h
    alto_t = 56
    d.polygon([(tx0, ty), (tx1, ty), (tx1 - 12, ty - alto_t), (tx0 + 12, ty - alto_t)], fill=(110, 46, 32))
    for fila in range(4):
        yy = ty - fila * alto_t / 4
        for xx in range(int(tx0 + 6), int(tx1 - 6), 22):
            d.arc([xx, yy - 14, xx + 22, yy + 4], 0, 180, fill=(70, 26, 18), width=3)
            d.line([(xx + 3, yy - 2), (xx + 11, yy - 5)], fill=(150, 76, 54), width=2)         # brillo de cada teja
    d.line([(tx0, ty), (tx1, ty)], fill=(50, 20, 14), width=5)
    if balcon:
        by = suelo - h * 0.62
        d.rectangle([x + w * 0.48, by, x + w * 0.92, by + 10], fill=(40, 34, 30))
        for j in range(9):
            bx = x + w * 0.5 + j * w * 0.05
            d.line([(bx, by), (bx, by - 40)], fill=(30, 28, 28), width=4)
        d.line([(x + w * 0.48, by - 40), (x + w * 0.92, by - 40)], fill=(30, 28, 28), width=5)
    if luz_ventana:
        g = Image.new('RGB', (W, H))
        ImageDraw.Draw(g).rectangle([x + vx - 30, suelo - h + vy - 20, x + vx + vw + 30, suelo - h + vy + vh + 60], fill=(110, 70, 30))
        rgb = ImageChops.add(lienzo.convert('RGB'), g.filter(ImageFilter.GaussianBlur(40)))
        lienzo.paste(rgb)


def calle(W=1080, H=900):
    im = grad(W, H, (10, 16, 34), (34, 38, 54)).convert('RGBA')
    d = ImageDraw.Draw(im)
    nub = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dn = ImageDraw.Draw(nub)
    for _ in range(26):
        x, y = rnd.uniform(-100, W + 100), rnd.uniform(0, 260)
        dn.ellipse([x - 200, y - 50, x + 200, y + 50], fill=(40, 48, 74, 160))
        dn.ellipse([x - 140, y - 60, x + 120, y + 10], fill=(70, 80, 110, 90))                    # borde con luz de luna
    im.alpha_composite(nub.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(im)
    d.ellipse([840, 70, 916, 146], fill=(228, 230, 214))
    g = Image.new('RGB', (W, H)); ImageDraw.Draw(g).ellipse([760, -10, 1000, 230], fill=(60, 70, 100))
    im = Image.merge('RGBA', (*ImageChops.add(im.convert('RGB'), g.filter(ImageFilter.GaussianBlur(50))).split(), im.getchannel('A')))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 430), (240, 330), (460, 380), (700, 300), (900, 350), (1080, 320), (1080, 470), (0, 470)], fill=(18, 24, 32))
    d.polygon([(640, 312), (676, 262), (712, 312)], fill=(24, 26, 34)); d.rectangle([660, 262, 692, 312], fill=(24, 26, 34))
    d.rectangle([670, 280, 682, 294], fill=(240, 190, 100)); d.line([(676, 236), (676, 262)], fill=(24, 26, 34), width=4)
    d.line([(666, 246), (686, 246)], fill=(24, 26, 34), width=4)
    suelo = 640
    arbol(im, 120, suelo, 520)
    casas = [(250, 220, 250, (196, 170, 112), 1, True, False), (490, 200, 220, (106, 140, 160), 2, False, True),
             (710, 210, 260, (182, 118, 120), 3, True, False), (940, 190, 210, (150, 160, 120), 4, False, False)]
    for (x, w, h, c, s, lz, bal) in casas:
        casa(im, x, suelo, w, h, c, s, lz, bal)
    arbol(im, 1010, suelo + 10, 460)
    d = ImageDraw.Draw(im)
    d.line([(0, 250), (360, 300), (700, 270), (1080, 310)], fill=(14, 14, 18), width=3)          # cables de luz
    d.line([(0, 266), (360, 314), (700, 284), (1080, 324)], fill=(14, 14, 18), width=2)
    d.rectangle([0, suelo, W, suelo + 22], fill=(64, 60, 58))                                     # vereda
    d.rectangle([0, suelo + 22, W, H], fill=(26, 26, 32))                                          # calle
    faroles = [(420, 300), (860, 320)]
    for fx, fy in faroles:
        d.rectangle([fx - 6, fy, fx + 6, suelo], fill=(26, 26, 30))
        d.line([(fx, fy), (fx + 40, fy - 8)], fill=(26, 26, 30), width=7)
    g = Image.new('RGB', (W, H)); dg = ImageDraw.Draw(g)
    for fx, fy in faroles:
        dg.ellipse([fx + 20, fy - 22, fx + 64, fy + 6], fill=(255, 220, 150))
        dg.polygon([(fx + 26, fy), (fx + 56, fy), (fx + 190, suelo + 40), (fx - 110, suelo + 40)], fill=(100, 78, 44))
    im = Image.merge('RGBA', (*ImageChops.add(im.convert('RGB'), g.filter(ImageFilter.GaussianBlur(22))).split(), im.getchannel('A')))
    d = ImageDraw.Draw(im)
    for fx, fy in faroles:
        d.ellipse([fx + 28, fy - 14, fx + 54, fy + 2], fill=(255, 244, 210))
    rgb = im.convert('RGB')
    ref = rgb.crop((0, suelo - 260, W, suelo)).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(5))
    ref = ImageEnhance.Brightness(ref).enhance(0.42).resize((W, H - suelo - 22))
    base = rgb.crop((0, suelo + 22, W, H))
    rgb.paste(Image.blend(base, ref, 0.55), (0, suelo + 22))
    capa = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(capa)
    for _ in range(520):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H); L = rnd.uniform(25, 60)
        dl.line([(x, y), (x - 4, y + L)], fill=(205, 215, 240, int(rnd.uniform(50, 130))), width=2)
    rgb = rgb.convert('RGBA'); rgb.alpha_composite(capa)
    arr = np.asarray(rgb.convert('RGB')).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.45 * np.clip(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2, 0, 1)
    arr = arr * v[..., None] + np.random.default_rng(1).normal(0, 4, arr.shape)
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))


if __name__ == '__main__':
    calle().save(OUT + 'calle_v2.jpg', quality=93)
    print('ok')
