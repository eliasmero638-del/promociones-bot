"""Hoja de ambientes de "El último cliente": la calle con árboles y faroles, el taller por dentro con sus luces y el carro."""
import os
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops, ImageEnhance

FUENTE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'InterDisplay-Black.otf')
OUT = os.environ.get('KIT_OUT', '.') + '/'
rnd = random.Random(4)


def grad(w, h, a, b):
    t = np.linspace(0, 1, h)[:, None, None]
    return Image.fromarray((np.array(a) * (1 - t) + np.array(b) * t).repeat(w, 1).astype(np.uint8))


def luz(base, dibuja, r):
    L = Image.new('RGB', base.size)
    dibuja(ImageDraw.Draw(L))
    return ImageChops.add(base.convert('RGB'), L.filter(ImageFilter.GaussianBlur(r)))


def lluvia(im, n, zona, alfa=120):
    capa = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    x0, y0, x1, y1 = zona
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        L = rnd.uniform(25, 60)
        d.line([(x, y), (x - 4, y + L)], fill=(205, 215, 240, int(alfa * rnd.uniform(0.5, 1))), width=2)
    im = im.convert('RGBA')
    im.alpha_composite(capa)
    return im.convert('RGB')


def arbol(d, x, base, alto, ancho, oscuro, claro):
    """Árbol de copa frondosa: muchas hojas en capas, más claras arriba a la izquierda (luz de luna)."""
    d.polygon([(x - ancho * 0.07, base), (x - ancho * 0.04, base - alto * 0.55), (x + ancho * 0.04, base - alto * 0.55),
               (x + ancho * 0.07, base)], fill=(24, 18, 16))
    for j in range(5):
        a = -math.pi / 2 + (j - 2) * 0.5
        d.line([(x, base - alto * 0.45), (x + math.cos(a) * ancho * 0.35, base - alto * 0.45 + math.sin(a) * alto * 0.25)],
               fill=(24, 18, 16), width=max(3, int(ancho / 30)))
    for capa in range(3):
        for j in range(26):
            cx = x + rnd.gauss(0, ancho * 0.28)
            cy = base - alto * rnd.uniform(0.5, 1.0)
            r = ancho * rnd.uniform(0.08, 0.16)
            t = capa / 2 * (0.6 + 0.4 * (cx < x))
            col = tuple(int(oscuro[i] + (claro[i] - oscuro[i]) * t) for i in range(3))
            d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], fill=col)


# ---------------- 1. LA CALLE ----------------
def calle(W=1080, H=640):
    im = grad(W, H, (12, 18, 36), (30, 34, 50))
    d = ImageDraw.Draw(im)
    for _ in range(14):                                                     # nubes
        x, y = rnd.uniform(0, W), rnd.uniform(10, 180)
        d.ellipse([x - 160, y - 40, x + 160, y + 40], fill=(30, 36, 56))
    im = im.filter(ImageFilter.GaussianBlur(10))
    d = ImageDraw.Draw(im)
    d.ellipse([820, 60, 890, 130], fill=(220, 222, 206))
    im = luz(im, lambda L: L.ellipse([760, 0, 950, 190], fill=(70, 80, 110)), 40)
    d = ImageDraw.Draw(im)
    d.polygon([(0, 380), (200, 300), (420, 340), (640, 280), (860, 330), (1080, 300), (1080, 420), (0, 420)], fill=(16, 20, 28))
    d.polygon([(560, 300), (600, 250), (640, 300)], fill=(20, 22, 30))       # iglesia en el cerro
    d.rectangle([585, 250, 615, 300], fill=(20, 22, 30))
    d.rectangle([594, 268, 606, 282], fill=(230, 180, 90))
    for (x, a, w_) in [(80, 380, 300), (1000, 420, 330), (300, 300, 230)]:
        arbol(d, x, 470, a, w_, (10, 22, 16), (40, 66, 52))
    casas = [(380, 150, 140), (540, 170, 120), (700, 160, 150), (860, 140, 130)]
    for (x, w_, h_) in casas:
        d.rectangle([x, 470 - h_, x + w_, 470], fill=(70, 58, 52))
        d.polygon([(x - 12, 470 - h_), (x + w_ / 2, 470 - h_ - 50), (x + w_ + 12, 470 - h_)], fill=(92, 40, 32))
        d.rectangle([x + 20, 470 - h_ + 30, x + 56, 470 - h_ + 70], fill=(30, 26, 26))
    d.rectangle([0, 470, W, H], fill=(24, 24, 30))
    d.rectangle([0, 470, W, 488], fill=(46, 42, 42))                          # vereda
    faroles = [(330, 230), (760, 260)]
    for (fx, fy) in faroles:
        d.rectangle([fx - 5, fy, fx + 5, 480], fill=(26, 26, 30))
        d.line([(fx, fy), (fx + 34, fy - 6)], fill=(26, 26, 30), width=6)
    def L(dl):
        for (fx, fy) in faroles:
            dl.ellipse([fx + 14, fy - 18, fx + 54, fy + 8], fill=(255, 220, 150))
            dl.polygon([(fx + 20, fy), (fx + 48, fy), (fx + 150, 480), (fx - 80, 480)], fill=(90, 70, 40))
        dl.rectangle([700, 384, 736, 414], fill=(140, 100, 50))
    im = luz(im, L, 18)
    d = ImageDraw.Draw(im)
    for (fx, fy) in faroles:
        d.ellipse([fx + 22, fy - 12, fx + 46, fy + 2], fill=(255, 240, 200))
    ref = im.crop((0, 300, W, 470)).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(6))
    ref = ImageEnhance.Brightness(ref).enhance(0.4)
    im.paste(Image.blend(im.crop((0, 488, W, 658)).resize((W, 170)), ref, 0.6).crop((0, 0, W, H - 488)), (0, 488))
    return lluvia(im, 420, (0, 0, W, H), 110)


# ---------------- 2. EL CARRO ----------------
def carro(W=1000, H=420, luces=True):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([30, 170, W - 30, 330], radius=40, fill=255)                       # carrocería
    d.polygon([(250, 175), (330, 70), (650, 66), (760, 175)], fill=255)                    # cabina
    A = np.asarray(m, np.float32) / 255
    yy = np.linspace(0, 1, H)[:, None]
    rojo = np.array([180, 30, 28], np.float32)
    base = rojo * (1.25 - 0.9 * np.clip((yy - 0.3) / 0.6, 0, 1))[..., None] * np.ones((1, W, 1))
    brillo = np.exp(-((yy - 0.47) / 0.025) ** 2)[..., None] * np.array([120, 90, 90])     # línea de brillo
    col = np.clip(base + brillo, 0, 255)
    rng = np.random.default_rng(2)
    oxido = (rng.random((H, W)) < 0.004)
    col[oxido] = [96, 46, 26]
    img = Image.fromarray(np.dstack([col, A * 255]).astype(np.uint8), 'RGBA')
    d = ImageDraw.Draw(img)
    for poly in ([(272, 170), (340, 84), (480, 82), (480, 170)], [(500, 170), (500, 82), (640, 80), (735, 170)]):
        d.polygon(poly, fill=(36, 50, 66))
    d.polygon([(300, 160), (350, 92), (380, 92), (330, 160)], fill=(80, 100, 120))         # reflejo en vidrio
    d.polygon([(520, 160), (540, 92), (556, 92), (538, 160)], fill=(70, 90, 110))
    d.rounded_rectangle([20, 238, W - 20, 256], radius=8, fill=(205, 205, 212))            # moldura cromada
    d.line([(24, 242), (W - 24, 242)], fill=(250, 250, 255), width=3)
    d.rounded_rectangle([W - 60, 300, W, 330], radius=8, fill=(190, 190, 196))             # parachoques
    d.rounded_rectangle([0, 300, 60, 330], radius=8, fill=(190, 190, 196))
    d.line([(490, 176), (490, 320)], fill=(110, 18, 18), width=3)                          # puertas
    d.line([(740, 180), (740, 320)], fill=(110, 18, 18), width=3)
    d.rounded_rectangle([420, 268, 460, 276], radius=3, fill=(200, 200, 200))
    d.rounded_rectangle([680, 268, 720, 276], radius=3, fill=(200, 200, 200))
    d.polygon([(40, 190), (110, 215), (90, 265), (36, 250)], fill=(120, 20, 20))           # abolladura
    d.line([(46, 200), (100, 225), (84, 258)], fill=(70, 10, 10), width=4)
    d.rounded_rectangle([W - 52, 196, W - 22, 236], radius=8, fill=(255, 244, 200))         # faro bueno
    d.rounded_rectangle([22, 196, 52, 236], radius=8, fill=(50, 52, 56))                    # faro roto
    d.line([(26, 200), (48, 232)], fill=(200, 200, 200), width=2)
    d.line([(30, 230), (46, 202)], fill=(170, 170, 170), width=2)
    for x in (210, 790):                                                                   # llantas con aro
        d.ellipse([x - 82, 250, x + 82, 414], fill=(18, 18, 20))
        d.ellipse([x - 48, 284, x + 48, 380], fill=(150, 152, 158))
        d.ellipse([x - 40, 292, x + 40, 372], fill=(110, 112, 118))
        for j in range(6):
            a = j * math.pi / 3
            d.line([(x, 332), (x + math.cos(a) * 38, 332 + math.sin(a) * 38)], fill=(170, 172, 178), width=5)
        d.ellipse([x - 10, 322, x + 10, 342], fill=(200, 200, 205))
    if luces:
        g = Image.new('RGB', (W, H))
        ImageDraw.Draw(g).ellipse([W - 90, 170, W + 30, 260], fill=(255, 230, 160))
        g = g.filter(ImageFilter.GaussianBlur(20))
        rgb = ImageChops.add(img.convert('RGB'), g)
        img = Image.merge('RGBA', (*rgb.split(), img.getchannel('A')))
    return img


# ---------------- 3. EL TALLER ----------------
def taller(W=1080, H=760, con_carro=True):
    im = grad(W, H, (58, 52, 50), (30, 28, 30))
    d = ImageDraw.Draw(im)
    for y in range(0, 520, 46):                                                 # pared de bloques
        off = 0 if (y // 46) % 2 else 50
        for x in range(-off, W, 100):
            d.rectangle([x + 2, y + 2, x + 98, y + 44], fill=(60 + rnd.randint(-6, 6), 54, 50))
    d.rectangle([0, 520, W, H], fill=(44, 44, 48))                              # piso de cemento
    for _ in range(6):
        x, y = rnd.uniform(0, W), rnd.uniform(560, 740)
        d.ellipse([x - 70, y - 14, x + 70, y + 14], fill=(30, 30, 34))           # manchas de aceite
    d.rectangle([60, 120, 420, 380], fill=(120, 86, 54))                         # tablero de herramientas
    for j in range(8):
        x = 90 + j * 42
        d.line([(x, 140), (x, 230 + (j % 3) * 30)], fill=(170, 174, 182), width=8)
        d.ellipse([x - 12, 222 + (j % 3) * 30, x + 12, 246 + (j % 3) * 30], outline=(170, 174, 182), width=5)
    for j in range(3):
        d.rectangle([110 + j * 100, 290, 170 + j * 100, 360], fill=(150, 154, 160), outline=(40, 40, 44), width=3)
    d.rectangle([780, 160, 1040, 470], fill=(70, 60, 52))                         # repisa con latas
    for r in range(3):
        d.rectangle([780, 250 + r * 100, 1040, 262 + r * 100], fill=(96, 80, 64))
        for j in range(6):
            c = [(180, 40, 36), (40, 90, 150), (200, 160, 40), (60, 120, 70)][rnd.randint(0, 3)]
            d.rectangle([792 + j * 40, 190 + r * 100, 822 + j * 40, 250 + r * 100], fill=c, outline=(30, 26, 24), width=2)
    for j in range(3):                                                           # llantas apiladas
        d.ellipse([440, 410 - j * 50, 620, 470 - j * 50], fill=(22, 22, 24), outline=(50, 50, 54), width=4)
    d.rectangle([640, 330, 760, 520], fill=(160, 34, 30), outline=(30, 20, 18), width=4)   # caja de herramientas
    for j in range(4):
        d.rectangle([652, 350 + j * 40, 748, 380 + j * 40], fill=(140, 28, 26), outline=(30, 20, 18), width=2)
    # luces: tubo fluorescente (parpadea en el video) y lámpara colgante
    def L(dl):
        dl.rectangle([300, 40, 780, 60], fill=(200, 230, 220))
        dl.polygon([(300, 60), (780, 60), (1080, 760), (0, 760)], fill=(36, 48, 44))
        dl.polygon([(910, 120), (950, 120), (1080, 520), (780, 520)], fill=(90, 70, 36))
    im = luz(im, L, 40)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([300, 38, 780, 62], radius=10, fill=(235, 252, 245))
    d.line([(930, 0), (930, 96)], fill=(20, 20, 20), width=4)
    d.chord([890, 80, 970, 150], 180, 360, fill=(40, 46, 40))
    d.ellipse([918, 112, 942, 128], fill=(255, 240, 200))
    im = im.convert('RGBA')
    if not con_carro:
        return im.convert('RGB')
    car = carro(900, 378)
    sombra = Image.new('L', (W, H), 0)
    ImageDraw.Draw(sombra).ellipse([110, 690, 1010, 750], fill=210)
    im = Image.composite(Image.new('RGBA', (W, H), (0, 0, 0, 255)), im, sombra.filter(ImageFilter.GaussianBlur(16)))
    im.alpha_composite(car, (90, 360))
    return im.convert('RGB')


if __name__ == '__main__':
    W = 1080
    hoja = Image.new('RGB', (W, 1920), (10, 9, 14))
    d = ImageDraw.Draw(hoja)
    f = ImageFont.truetype(FUENTE, 54)
    f2 = ImageFont.truetype(FUENTE, 30)
    d.text((W / 2, 48), 'EL ÚLTIMO CLIENTE · AMBIENTES', font=f, fill=(245, 220, 120), anchor='mm')
    hoja.paste(calle(), (0, 90))
    d.text((24, 104), 'LA CALLE: árboles, faroles, lluvia, la iglesia del cerro', font=f2, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    hoja.paste(taller(), (0, 740))
    d.text((24, 754), 'EL TALLER: tubo de luz, lámpara, herramientas, latas, llantas', font=f2, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    fondo = grad(W, 410, (24, 22, 30), (12, 10, 16)).convert('RGBA')
    fondo.alpha_composite(carro(980, 412), (50, 0))
    hoja.paste(fondo.convert('RGB'), (0, 1505))
    d.text((24, 1515), 'EL CARRO DEL 78: abollado, faro roto, óxido', font=f2, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    arr = np.asarray(hoja).astype(np.float32)
    arr += np.random.default_rng(0).normal(0, 5, arr.shape)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(OUT + 'ambientes.jpg', quality=92)
    print('ok')
