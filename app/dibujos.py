"""Escenas DIBUJADAS y animadas para Ridmer (estilo de los cuentos): personajes con movimiento, luces, polvo,
rocas, temblor de cámara. Cada escena es una pequeña película a pantalla completa (anim_*.mp4, sin audio).

Uso:  escena('mina', salida, segundos, W, H, evento='sismo', n=5)
Escenas: mina (camina, sismo, atrapados, rescate, capsula), carretera (pasa, recoge), ciudad (calma, sismo),
         linternas (búsqueda de noche), pista (avión que no frena).
Todo es una RECREACIÓN dibujada: no muestra a personas reales.
"""
import math, os, random, subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageFont

APP = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(os.path.dirname(APP), 'assets', 'InterDisplay-Black.otf')
FPS = 30
TINTA = (28, 20, 16)


def _f(n):
    try:
        return ImageFont.truetype(FUENTE, n)
    except Exception:
        return ImageFont.load_default()


def _ease(x):
    x = max(0.0, min(1.0, x))
    return (1 - math.cos(math.pi * x)) / 2


def _mezcla(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def _degradado(W, H, arriba, abajo):
    im = Image.new('RGB', (1, 256))
    for y in range(256):
        im.putpixel((0, y), _mezcla(arriba, abajo, y / 255))
    return im.resize((W, H), Image.BILINEAR)


# ---------------------------------------------------------------- personajes
_CACHE = {}


def persona(pose='quieto', fase=0.0, casco=False, ropa=(40, 70, 120), piel=(214, 168, 128), alto=300, mira=1,
            luz=False, linterna=False):
    """Sprite RGBA de una persona caricatura (contorno oscuro, como los cuentos). Ancla: pies al centro abajo.
    pose: quieto | camina | corre | miedo | sentado | pide (brazo extendido, autoestop)."""
    clave = (pose, round(fase * 12) % 12 if pose in ('camina', 'corre') else 0, casco, ropa, piel, alto, mira, luz, linterna)
    if clave in _CACHE:
        return _CACHE[clave]
    voltear, mira = mira < 0, 1                 # se dibuja mirando a la derecha y se voltea al final
    SS = 3
    w, h = int(alto * 0.9), int(alto * 1.15)
    im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = alto / 300 * SS
    cx, pie = w * SS / 2, h * SS - 4 * SS
    ol = int(4 * k)
    ph = 2 * math.pi * fase
    sw = {'camina': 0.45, 'corre': 0.85}.get(pose, 0.0)
    sentado = pose == 'sentado'
    cadera = pie - (60 if sentado else 120) * k
    hombro = cadera - 95 * k
    cabeza = hombro - 42 * k

    def miembro(x0, y0, ang, largo, grosor, color, codo=0.0):
        x1 = x0 + math.sin(ang) * largo * 0.5 * k * mira
        y1 = y0 + math.cos(ang) * largo * 0.5 * k
        x2 = x1 + math.sin(ang + codo) * largo * 0.5 * k * mira
        y2 = y1 + math.cos(ang + codo) * largo * 0.5 * k
        d.line([(x0, y0), (x1, y1), (x2, y2)], fill=TINTA, width=int(grosor * k + 2 * ol), joint='curve')
        d.line([(x0, y0), (x1, y1), (x2, y2)], fill=color, width=int(grosor * k), joint='curve')
        return x2, y2

    pantalon = _mezcla(ropa, (0, 0, 0), 0.35)
    # piernas
    if sentado:
        for s in (-1, 1):
            d.line([(cx + s * 14 * k, cadera), (cx + s * 14 * k + 70 * k * mira, cadera)], fill=TINTA, width=int(34 * k))
            d.line([(cx + s * 14 * k + 70 * k * mira, cadera), (cx + s * 14 * k + 70 * k * mira, pie)], fill=TINTA,
                   width=int(34 * k))
            d.line([(cx + s * 14 * k, cadera), (cx + s * 14 * k + 70 * k * mira, cadera)], fill=pantalon, width=int(26 * k))
            d.line([(cx + s * 14 * k + 70 * k * mira, cadera), (cx + s * 14 * k + 70 * k * mira, pie - 6 * k)],
                   fill=pantalon, width=int(26 * k))
    else:
        for s in (-1, 1):
            a = s * sw * math.sin(ph)
            x2, y2 = miembro(cx + s * 10 * k, cadera, a, 120, 26, pantalon, codo=-abs(a) * 0.6 if pose == 'corre' else 0)
            d.ellipse([x2 - 18 * k, y2 - 8 * k, x2 + 22 * k * mira, y2 + 8 * k], fill=TINTA)
    # cuerpo
    d.rounded_rectangle([cx - 38 * k, hombro - 6 * k, cx + 38 * k, cadera + 14 * k], radius=int(26 * k), fill=ropa,
                        outline=TINTA, width=ol)
    if casco:                                                  # franjas reflectivas de overol minero
        for yy in (hombro + 40 * k, hombro + 70 * k):
            d.line([(cx - 34 * k, yy), (cx + 34 * k, yy)], fill=(225, 225, 210), width=int(8 * k))
    # brazos
    if pose == 'miedo':
        for s in (-1, 1):
            miembro(cx + s * 30 * k, hombro + 8 * k, math.pi + s * 0.5, 100, 20, ropa, codo=-s * 0.9)
    elif pose == 'pide':
        miembro(cx - 30 * k * mira, hombro + 8 * k, 0.15, 100, 20, ropa)
        x2, y2 = miembro(cx + 30 * k * mira, hombro + 8 * k, 1.7, 100, 20, ropa, codo=-0.6)
        d.ellipse([x2 - 10 * k, y2 - 14 * k, x2 + 10 * k, y2 + 6 * k], fill=piel, outline=TINTA, width=ol)
    else:
        for s in (-1, 1):
            a = -s * sw * math.sin(ph) * 0.9 + (0.25 if sentado else 0.08)
            x2, y2 = miembro(cx + s * 30 * k, hombro + 8 * k, a, 105, 20, ropa, codo=-0.5 if pose == 'corre' else 0.15)
            d.ellipse([x2 - 11 * k, y2 - 11 * k, x2 + 11 * k, y2 + 11 * k], fill=piel, outline=TINTA, width=ol)
            if linterna and s == 1:
                d.rectangle([x2, y2 - 7 * k, x2 + 34 * k * mira, y2 + 7 * k], fill=(60, 60, 60), outline=TINTA, width=ol)
    # cuello y cabeza
    d.rectangle([cx - 10 * k, cabeza + 20 * k, cx + 10 * k, hombro + 4 * k], fill=piel)
    d.ellipse([cx - 34 * k, cabeza - 40 * k, cx + 34 * k, cabeza + 34 * k], fill=piel, outline=TINTA, width=ol)
    ox = 12 * k * mira
    if pose == 'miedo':
        for s in (-1, 1):
            d.ellipse([cx + ox + s * 12 * k - 7 * k, cabeza - 10 * k, cx + ox + s * 12 * k + 7 * k, cabeza + 6 * k],
                      fill=(250, 250, 250), outline=TINTA, width=int(2 * k))
            d.ellipse([cx + ox + s * 12 * k - 3 * k, cabeza - 5 * k, cx + ox + s * 12 * k + 3 * k, cabeza + 1 * k],
                      fill=TINTA)
        d.ellipse([cx + ox - 7 * k, cabeza + 12 * k, cx + ox + 7 * k, cabeza + 26 * k], fill=TINTA)
    else:
        for s in (-1, 1):
            d.ellipse([cx + ox + s * 12 * k - 4 * k, cabeza - 6 * k, cx + ox + s * 12 * k + 4 * k, cabeza + 3 * k],
                      fill=TINTA)
        d.line([(cx + ox - 9 * k, cabeza + 17 * k), (cx + ox + 9 * k, cabeza + 17 * k)], fill=TINTA, width=int(3 * k))
    if casco:
        d.chord([cx - 40 * k, cabeza - 50 * k, cx + 40 * k, cabeza + 10 * k], 180, 360, fill=(240, 196, 30),
                outline=TINTA, width=ol)
        d.rectangle([cx - 46 * k, cabeza - 22 * k, cx + 46 * k, cabeza - 14 * k], fill=(220, 175, 20), outline=TINTA,
                    width=int(2 * k))
        lx = cx + 34 * k * mira
        d.ellipse([lx - 10 * k, cabeza - 40 * k, lx + 10 * k, cabeza - 20 * k], fill=(255, 250, 200) if luz else (90, 90, 90),
                  outline=TINTA, width=int(2 * k))
    else:
        d.chord([cx - 35 * k, cabeza - 42 * k, cx + 35 * k, cabeza + 4 * k], 180, 360, fill=(45, 30, 22))
    out = im.resize((w, h), Image.LANCZOS)
    if voltear:
        out = out.transpose(Image.FLIP_LEFT_RIGHT)
    _CACHE[clave] = out
    return out


def pegar(lienzo, sprite, x, y, alfa=1.0):
    """Pega el sprite con los pies en (x, y)."""
    if alfa < 1:
        sprite = sprite.copy()
        sprite.putalpha(sprite.getchannel('A').point(lambda v: int(v * alfa)))
    lienzo.alpha_composite(sprite, (int(x - sprite.width / 2), int(y - sprite.height)))


def cabeza_luz(x, y, alto, mira=1):
    """Posición de la lámpara del casco de una persona con pies en (x, y)."""
    k = alto / 300
    return x + 34 * k * mira, y - (120 + 95 + 42 + 30) * k


# ---------------------------------------------------------------- luces y efectos
class Luces:
    """Capa de luz a 1/4 de resolución: conos de linterna y halos; se desenfoca y se suma a la imagen."""

    def __init__(self, W, H, oscuro=0.0):
        self.q = 4
        self.W, self.H = W, H
        self.im = Image.new('RGB', (W // self.q, H // self.q), (0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def cono(self, x, y, ang, largo, abre=0.35, color=(255, 236, 170), fuerza=0.55):
        q = self.q
        p0 = (x / q, y / q)
        p1 = ((x + math.cos(ang - abre) * largo) / q, (y + math.sin(ang - abre) * largo) / q)
        p2 = ((x + math.cos(ang + abre) * largo) / q, (y + math.sin(ang + abre) * largo) / q)
        self.d.polygon([p0, p1, p2], fill=tuple(int(c * fuerza) for c in color))

    def halo(self, x, y, r, color=(255, 200, 120), fuerza=0.6):
        q = self.q
        for j in range(4):
            rr = r * (1 - j * 0.22) / q
            c = tuple(int(v * fuerza * (0.35 + 0.22 * j)) for v in color)
            self.d.ellipse([x / q - rr, y / q - rr, x / q + rr, y / q + rr], fill=c)

    def aplicar(self, base):
        luz = self.im.filter(ImageFilter.GaussianBlur(6)).resize((self.W, self.H), Image.BILINEAR)
        from PIL import ImageChops
        return Image.merge('RGBA', (*ImageChops.add(base.convert('RGB'), luz).split(), base.getchannel('A')))


def temblor(img, fuerza, t, margen=40):
    """Sacudida de cámara (fuerza 0..1)."""
    if fuerza <= 0.01:
        return img
    W, H = img.size
    dx = (math.sin(t * 61) + 0.6 * math.sin(t * 37)) * margen * 0.6 * fuerza
    dy = (math.cos(t * 53) + 0.6 * math.sin(t * 29)) * margen * 0.6 * fuerza
    return img.crop((margen + dx, margen + dy, W - margen + dx, H - margen + dy)).resize((W, H), Image.BILINEAR)


def roca(d, x, y, r, semilla, color=(92, 74, 60)):
    rnd = random.Random(semilla)
    pts = []
    for j in range(7):
        a = j / 7 * 2 * math.pi + rnd.uniform(-0.3, 0.3)
        rr = r * rnd.uniform(0.7, 1.15)
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    d.polygon(pts, fill=color, outline=TINTA, width=max(2, int(r / 6)))


def polvo(lienzo, cx, cy, t, fuerza, semilla=1, ancho=500, color=(150, 130, 110)):
    """Nube de polvo que crece y se desvanece (se dibuja a 1/4 de resolución: rápido)."""
    q = 4
    capa = Image.new('RGBA', (lienzo.width // q, lienzo.height // q), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    rnd = random.Random(semilla)
    for j in range(26):
        x = cx + rnd.uniform(-ancho, ancho) * (0.4 + t * 0.6)
        y = cy + rnd.uniform(-ancho * 0.25, ancho * 0.25) - t * rnd.uniform(10, 90)
        r = rnd.uniform(40, 120) * (0.5 + t) * lienzo.width / 1080
        a = int(110 * fuerza * rnd.uniform(0.4, 1))
        d.ellipse([(x - r) / q, (y - r) / q, (x + r) / q, (y + r) / q], fill=color + (a,))
    lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(5)).resize(lienzo.size, Image.BILINEAR))


# ---------------------------------------------------------------- escenas
def _mina(W, H, d, evento='camina', n=5, **kw):
    rnd = random.Random(7)
    vertical = H > W
    u = W / 1080 if vertical else H / 1080
    techo, piso = (int(H * 0.47), int(H * 0.64)) if vertical else (int(H * 0.40), int(H * 0.80))
    sup = int(H * 0.16) if vertical else int(H * 0.12)
    # fondo fijo: cielo, cerros, capas de tierra, piedras, túnel con vigas
    f = Image.new('RGBA', (W, H))
    f.paste(_degradado(W, sup + 40, (6, 10, 24), (24, 30, 52)), (0, 0))
    df = ImageDraw.Draw(f)
    for _ in range(60):
        x, y = rnd.uniform(0, W), rnd.uniform(0, sup * 0.8)
        df.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(200, 205, 230))
    cerros = [(0, sup)] + [(x, sup - rnd.uniform(20, 90) * u) for x in range(0, W + 120, 120)] + [(W, sup)]
    df.polygon(cerros + [(W, sup + 40), (0, sup + 40)], fill=(58, 46, 40), outline=TINTA)
    tierra = _degradado(W, H - sup, (104, 78, 56), (52, 38, 30))
    f.paste(tierra, (0, sup))
    df = ImageDraw.Draw(f)
    for j in range(5):
        y = sup + (H - sup) * (j + 1) / 6
        df.line([(x, y + 14 * math.sin(x / 140 + j)) for x in range(0, W + 20, 20)], fill=(70, 52, 40), width=int(5 * u))
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(sup + 30, H)
        if techo - 40 < y < piso + 40:
            continue
        roca(df, x, y, rnd.uniform(8, 26) * u, rnd.random(), color=_mezcla((120, 96, 74), (60, 46, 36), rnd.random()))
    borde = lambda y0, s: [(x, y0 + s * rnd.uniform(0, 16) * u) for x in range(0, W + 30, 30)]
    df.polygon(borde(techo, 1) + [(W, piso)] + borde(piso, -1)[::-1], fill=(34, 27, 22))
    df.rectangle([0, piso, W, piso + 22 * u], fill=(46, 36, 28))
    for x in range(int(90 * u), W, int(330 * u)):                          # vigas de madera
        for xx in (x, x + 200 * u):
            df.rectangle([xx - 11 * u, techo + 6 * u, xx + 11 * u, piso], fill=(120, 82, 46), outline=TINTA, width=3)
        df.rectangle([x - 22 * u, techo, x + 222 * u, techo + 24 * u], fill=(132, 90, 50), outline=TINTA, width=3)
    focos = [x + 100 * u for x in range(int(90 * u), W, int(330 * u))]
    alto = (piso - techo) * 0.78
    grietas = []
    for j in range(6):
        x0, pts = rnd.uniform(0.1, 0.9) * W, []
        x, y = x0, techo + 20 * u
        for _ in range(8):
            pts.append((x, y))
            x += rnd.uniform(-50, 50) * u
            y -= rnd.uniform(15, 45) * u
        grietas.append(pts)
    caidas = [(rnd.uniform(0.05, 0.95) * W, rnd.uniform(0.15, 0.9), rnd.uniform(10, 30) * u, rnd.random()) for _ in range(40)]
    escombro = [(rnd.uniform(0, W * 0.42), rnd.uniform(0, 1), rnd.uniform(26, 60) * u, rnd.random()) for _ in range(46)]
    pozo = W * (0.78 if vertical else 0.72)

    def cuadro(t):
        im = f.copy()
        dr = ImageDraw.Draw(im)
        L = Luces(W, H)
        p = t / d
        sacude = 0.0
        sw = 0.0
        if evento == 'sismo':
            sacude = _ease((p - 0.15) / 0.25) * (1 - 0.3 * _ease((p - 0.8) / 0.2))
            sw = sacude * 0.5
            for pts in grietas:
                m = int(len(pts) * _ease((p - 0.2) / 0.5))
                if m > 1:
                    dr.line(pts[:m], fill=(20, 14, 10), width=int(5 * u))
            for (x, t0, r, s) in caidas:
                tt = p - t0
                if tt > 0:
                    y = techo + 20 * u + 2600 * u * tt * tt
                    roca(dr, x, min(y, piso - r * 0.6), r, s)
        if evento in ('atrapados', 'rescate', 'capsula', 'maquina'):
            quita = 0.55 * _ease(p) if evento == 'maquina' else 0.0
            for (x, y_, r, s) in escombro:
                if evento == 'maquina' and x > W * 0.42 * (1 - quita):
                    continue
                yy = piso - r * 0.5 - y_ * (piso - techo) * 0.85 * (1 - x / (W * 0.45)) ** 0.5
                roca(dr, x, yy, r, s)
        if evento == 'maquina':                                       # cargador a control remoto sacando roca
            mx = W * 0.42 * (1 - quita) + 40 * u + 18 * u * math.sin(t * 3)
            my = piso - 6 * u
            dr.rounded_rectangle([mx + 60 * u, my - 150 * u, mx + 330 * u, my - 40 * u], radius=int(14 * u),
                                 fill=(232, 182, 30), outline=TINTA, width=4)
            dr.rectangle([mx + 200 * u, my - 220 * u, mx + 300 * u, my - 150 * u], fill=(50, 50, 55), outline=TINTA, width=4)
            ang = 0.25 * math.sin(t * 3)
            bx, by = mx + 60 * u, my - 100 * u
            ex, ey = bx - 70 * u * math.cos(ang), by + 70 * u * math.sin(ang)
            dr.line([(bx, by), (ex, ey)], fill=TINTA, width=int(22 * u))
            dr.polygon([(ex, ey - 40 * u), (ex - 70 * u, ey - 30 * u), (ex - 80 * u, ey + 40 * u), (ex, ey + 40 * u)],
                       fill=(200, 155, 25), outline=TINTA)
            for wx in (mx + 110 * u, mx + 280 * u):
                dr.ellipse([wx - 48 * u, my - 90 * u, wx + 48 * u, my + 6 * u], fill=(30, 30, 30), outline=TINTA, width=4)
                dr.ellipse([wx - 18 * u, my - 60 * u, wx + 18 * u, my - 24 * u], fill=(110, 110, 110))
            L.halo(mx + 330 * u, my - 120 * u, 70 * u, color=(255, 255, 220), fuerza=0.5)
            if math.sin(t * 4) > 0.3:
                L.halo(mx + 250 * u, my - 230 * u, 30 * u, color=(255, 140, 0), fuerza=0.9)
        for j, x in enumerate(focos):                                   # focos colgando (se mecen con el sismo)
            a = sw * math.sin(t * 7 + j)
            bx, by = x + math.sin(a) * 50 * u, techo + 24 * u + math.cos(a) * 50 * u
            dr.line([(x, techo + 24 * u), (bx, by)], fill=TINTA, width=3)
            parpadeo = 1.0
            if evento in ('sismo', 'atrapados') and (j % 2 == 0):
                parpadeo = 0.15 if math.sin(t * 23 + j * 3) > 0.6 else 1.0
            dr.ellipse([bx - 9 * u, by - 9 * u, bx + 9 * u, by + 9 * u], fill=(255, 220, 140) if parpadeo > 0.5 else (90, 80, 60))
            L.halo(bx, by, 150 * u, fuerza=0.5 * parpadeo)
        # mineros
        gente = []
        if evento in ('camina', 'sismo'):
            for i in range(n):
                vel = 0 if (evento == 'sismo' and p > 0.3) else 70 * u
                x = W * 0.12 + i * 150 * u + t * vel - (n - 1) * 40 * u
                pose = 'camina' if vel else ('miedo' if evento == 'sismo' else 'quieto')
                gente.append((x, pose, (t * 1.6 + i * 0.3) % 1, 1))
        elif evento in ('atrapados', 'rescate', 'capsula', 'maquina'):
            for i in range(n):
                x = W * (0.72 if evento == 'maquina' else 0.55) + i * 95 * u
                pose = 'sentado' if i % 2 else 'quieto'
                gente.append((x, pose, 0, -1 if i % 3 == 0 else 1))
        for (x, pose, fa, mira) in gente:
            sp = persona(pose, fa, casco=True, ropa=(214, 110, 30), alto=alto, mira=mira, luz=True)
            pegar(im, sp, x, piso + 4 * u)
            lx, ly = cabeza_luz(x, piso, alto, mira)
            ang = (0.12 if mira > 0 else math.pi - 0.12) + 0.25 * math.sin(t * 1.3 + x)
            L.cono(lx, ly, ang, 420 * u, 0.22, fuerza=0.3)
        if evento == 'rescate':                                       # perforadora que baja hasta el refugio
            fondo_p = sup + (techo - sup) * _ease(p * 1.1)
            dr.rectangle([pozo - 26 * u, sup, pozo + 26 * u, fondo_p], fill=(26, 20, 16))
            dr.rectangle([pozo - 10 * u, sup - 120 * u, pozo + 10 * u, fondo_p - 30 * u], fill=(150, 150, 160), outline=TINTA)
            giro = t * 9
            dr.polygon([(pozo - 26 * u, fondo_p - 30 * u), (pozo + 26 * u, fondo_p - 30 * u), (pozo, fondo_p + 20 * u)],
                       fill=(200, 200, 210) if math.sin(giro) > 0 else (150, 150, 160), outline=TINTA)
            dr.polygon([(pozo - 70 * u, sup), (pozo + 70 * u, sup), (pozo + 20 * u, sup - 170 * u), (pozo - 20 * u, sup - 170 * u)],
                       outline=(220, 60, 40), width=int(6 * u))
            L.halo(pozo, fondo_p, 90 * u, color=(255, 160, 90), fuerza=0.4)
        if evento == 'capsula':                                        # cápsula que sube por el pozo
            dr.rectangle([pozo - 40 * u, sup, pozo + 40 * u, techo + 10 * u], fill=(22, 18, 14))
            cy = techo - (techo - sup) * _ease(p)
            dr.rounded_rectangle([pozo - 34 * u, cy - 150 * u, pozo + 34 * u, cy], radius=int(18 * u), fill=(235, 235, 235),
                                 outline=TINTA, width=4)
            for yy, c in ((cy - 120 * u, (200, 30, 30)), (cy - 40 * u, (30, 60, 160))):
                dr.rectangle([pozo - 34 * u, yy, pozo + 34 * u, yy + 16 * u], fill=c)
            dr.rectangle([pozo - 50 * u, sup - 200 * u, pozo + 50 * u, sup], outline=(200, 200, 210), width=int(8 * u))
            dr.ellipse([pozo - 20 * u, sup - 230 * u, pozo + 20 * u, sup - 190 * u], outline=(200, 200, 210), width=int(6 * u))
            L.halo(pozo, cy - 75 * u, 160 * u, color=(255, 255, 230), fuerza=0.35)
        im = L.aplicar(im)
        if evento == 'sismo' and p > 0.35:
            polvo(im, W * 0.5, piso - 60 * u, (p - 0.35) / 0.65, min(1, (p - 0.35) * 3), ancho=W * 0.6)
        if evento == 'atrapados':
            polvo(im, W * 0.3, piso - 80 * u, 0.6 + 0.2 * math.sin(t), 0.35, semilla=3, ancho=W * 0.4)
        return temblor(im, sacude, t)
    if evento in ('rescate', 'capsula'):
        return cuadro, {'z': 1.2, 'fx': (pozo / W - 0.1, pozo / W - 0.05), 'fy': 0.42}
    if evento == 'maquina':
        return cuadro, {'z': 1.6, 'fx': (0.3, 0.55), 'fy': (techo + piso) / 2 / H}
    return cuadro, {'z': 1.75, 'fx': (0.38, 0.6), 'fy': (techo + piso) / 2 / H}


def _carretera(W, H, d, evento='pasa', n=3, **kw):
    rnd = random.Random(4)
    vertical = H > W
    u = W / 1080 if vertical else H / 1080
    hor = int(H * 0.5)
    via = int(H * 0.62)
    f = Image.new('RGBA', (W, H))
    f.paste(_degradado(W, hor, (4, 6, 20), (26, 30, 60)), (0, 0))
    df = ImageDraw.Draw(f)
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(0, hor * 0.9)
        df.ellipse([x - 1.6, y - 1.6, x + 1.6, y + 1.6], fill=(210, 215, 240))
    df.ellipse([W * 0.72, H * 0.12, W * 0.72 + 120 * u, H * 0.12 + 120 * u], fill=(235, 232, 210))
    df.polygon([(0, hor)] + [(x, hor - 40 * u - 50 * u * math.sin(x / 300)) for x in range(0, W + 40, 40)] + [(W, hor), (W, H), (0, H)],
               fill=(14, 20, 22))
    df.rectangle([0, via - 50 * u, W, via + 60 * u], fill=(38, 38, 42))
    for x in range(0, W, int(160 * u)):
        df.rectangle([x, via + 2 * u, x + 80 * u, via + 10 * u], fill=(200, 190, 120))
    df.rectangle([0, via + 60 * u, W, H], fill=(16, 22, 18))
    arboles = [(rnd.uniform(0, W * 2), rnd.uniform(0.7, 1.2)) for _ in range(14)]
    alto = 230 * u

    def auto(dr, x, y, s=1.0):
        c = (230, 230, 225)
        dr.rounded_rectangle([x - 170 * u, y - 70 * u, x + 170 * u, y], radius=int(24 * u), fill=c, outline=TINTA, width=4)
        dr.polygon([(x - 95 * u, y - 70 * u), (x - 55 * u, y - 125 * u), (x + 70 * u, y - 125 * u), (x + 110 * u, y - 70 * u)],
                   fill=c, outline=TINTA, width=4)
        dr.polygon([(x - 80 * u, y - 72 * u), (x - 48 * u, y - 115 * u), (x + 5 * u, y - 115 * u), (x + 5 * u, y - 72 * u)],
                   fill=(40, 50, 70))
        dr.polygon([(x + 15 * u, y - 72 * u), (x + 15 * u, y - 115 * u), (x + 62 * u, y - 115 * u), (x + 95 * u, y - 72 * u)],
                   fill=(40, 50, 70))
        for xx in (x - 100 * u, x + 100 * u):
            dr.ellipse([xx - 36 * u, y - 30 * u, xx + 36 * u, y + 40 * u], fill=(20, 20, 20), outline=TINTA)
            dr.ellipse([xx - 14 * u, y - 9 * u, xx + 14 * u, y + 19 * u], fill=(120, 120, 120))

    def cuadro(t):
        im = f.copy()
        dr = ImageDraw.Draw(im)
        L = Luces(W, H)
        p = t / d
        if evento == 'recoge':
            if p < 0.4:
                ax = W + 260 * u - (W * 0.5 + 260 * u) * _ease(p / 0.4)
            elif p < 0.7:
                ax = W * 0.5
            else:
                ax = W * 0.5 - (W * 0.9) * _ease((p - 0.7) / 0.3)
        else:
            ax = W + 300 * u - (W + 600 * u) * p
        for (x, s) in arboles:
            xx = (x - t * 40 * u) % (W * 2) - W * 0.3
            dr.polygon([(xx, via - 60 * u), (xx - 60 * u * s, via - 60 * u), (xx, via - 330 * u * s), (xx + 60 * u * s, via - 60 * u)],
                       fill=(10, 16, 14))
        suben = evento == 'recoge'
        for i in range(n):
            x = W * 0.42 + i * 90 * u
            alfa = 1.0
            if suben and p > 0.45:
                alfa = max(0.0, 1 - (p - 0.45) / 0.15)
            if alfa > 0:
                pose = 'pide' if i == 0 else 'quieto'
                pegar(im, persona(pose, 0, ropa=[(170, 60, 90), (60, 110, 160), (200, 160, 60)][i % 3], alto=alto,
                                  piel=(222, 180, 140), mira=1), x, via - 52 * u, alfa)
        auto(dr, ax, via + 10 * u)
        L.cono(ax - 165 * u, via - 35 * u, math.pi + 0.05, 900 * u, 0.18, fuerza=0.8)
        L.halo(ax + 165 * u, via - 35 * u, 40 * u, color=(255, 40, 30), fuerza=0.7)
        return L.aplicar(im)
    return cuadro, {'z': 1.6, 'fx': (0.45, 0.55), 'fy': 0.55}


def _ciudad(W, H, d, evento='sismo', **kw):
    rnd = random.Random(9)
    vertical = H > W
    u = W / 1080 if vertical else H / 1080
    suelo = int(H * 0.72)
    f = Image.new('RGBA', (W, H))
    f.paste(_degradado(W, H, (8, 10, 26), (40, 34, 60)), (0, 0))
    df = ImageDraw.Draw(f)
    edif = []
    x = -20 * u
    while x < W:
        w = rnd.uniform(110, 220) * u
        h = rnd.uniform(0.18, 0.42) * H
        edif.append((x, w, h, rnd.random()))
        x += w + rnd.uniform(4, 20) * u
    df.rectangle([0, suelo, W, H], fill=(24, 24, 28))
    ventanas = []
    for (x, w, h, s) in edif:
        df.rectangle([x, suelo - h, x + w, suelo], fill=_mezcla((30, 30, 44), (52, 46, 64), s), outline=TINTA, width=3)
        for yy in range(int(suelo - h + 24 * u), int(suelo - 20 * u), int(46 * u)):
            for xx in range(int(x + 18 * u), int(x + w - 26 * u), int(40 * u)):
                if rnd.random() < 0.55:
                    ventanas.append((xx, yy, rnd.random()))
    grietas = [[(rnd.uniform(0, W), suelo)] for _ in range(5)]
    for g in grietas:
        for _ in range(7):
            x0, y0 = g[-1]
            g.append((x0 + rnd.uniform(-60, 60) * u, y0 - rnd.uniform(30, 70) * u))
    caidas = [(rnd.uniform(0, W), rnd.uniform(0.25, 0.9), rnd.uniform(8, 24) * u, rnd.random()) for _ in range(30)]

    def cuadro(t):
        im = f.copy()
        dr = ImageDraw.Draw(im)
        L = Luces(W, H)
        p = t / d
        fuerza = _ease((p - 0.1) / 0.2) * (1 - 0.4 * _ease((p - 0.75) / 0.25)) if evento == 'sismo' else 0
        for (x, y, s) in ventanas:
            apagada = evento == 'sismo' and p > 0.25 + s * 0.4
            if not apagada:
                dr.rectangle([x, y, x + 18 * u, y + 24 * u], fill=(255, 214, 120))
                L.halo(x + 9 * u, y + 12 * u, 26 * u, fuerza=0.25)
        if evento == 'sismo':
            for g in grietas:
                m = int(len(g) * _ease((p - 0.25) / 0.4))
                if m > 1:
                    dr.line(g[:m], fill=(10, 8, 8), width=int(6 * u))
            for (x, t0, r, s) in caidas:
                tt = p - t0
                if tt > 0:
                    roca(dr, x, min(suelo * 0.4 + 2400 * u * tt * tt, suelo - r * 0.5), r, s, color=(110, 104, 100))
        im = L.aplicar(im)
        if evento == 'sismo' and p > 0.35:
            polvo(im, W * 0.5, suelo - 40 * u, (p - 0.35) / 0.65, 0.8, ancho=W * 0.7, color=(130, 120, 115))
        return temblor(im, fuerza, t)
    return cuadro, {'z': 1.3, 'fx': (0.42, 0.58), 'fy': 0.6}


def _linternas(W, H, d, n=4, **kw):
    rnd = random.Random(5)
    u = W / 1080 if H > W else H / 1080
    suelo = int(H * 0.7)
    f = Image.new('RGBA', (W, H))
    f.paste(_degradado(W, H, (4, 8, 16), (14, 22, 30)), (0, 0))
    df = ImageDraw.Draw(f)
    for capa, (col, k) in enumerate([((18, 28, 34), 0.8), ((10, 18, 22), 1.0)]):
        for _ in range(12):
            x = rnd.uniform(-50, W + 50)
            a = rnd.uniform(0.35, 0.6) * H * k
            df.polygon([(x - 70 * u * k, suelo + capa * 30 * u), (x, suelo - a), (x + 70 * u * k, suelo + capa * 30 * u)], fill=col)
            df.rectangle([x - 8 * u, suelo - 20 * u, x + 8 * u, suelo + 40 * u], fill=col)
    df.rectangle([0, suelo + 20 * u, W, H], fill=(10, 16, 14))
    alto = 250 * u

    def cuadro(t):
        im = f.copy()
        L = Luces(W, H)
        for i in range(n):
            x = W * 0.15 + i * (W * 0.7 / max(1, n - 1)) + 20 * u * math.sin(t * 0.7 + i)
            mira = 1 if i % 2 == 0 else -1
            pegar(im, persona('camina', (t * 0.9 + i * 0.25) % 1, ropa=(50, 60, 50), alto=alto, mira=mira, linterna=True),
                  x, suelo + 30 * u)
            ang = (0.25 if mira > 0 else math.pi - 0.25) + 0.45 * math.sin(t * 0.8 + i * 1.7)
            L.cono(x + 60 * u * mira, suelo + 30 * u - alto * 0.55, ang, 520 * u, 0.12, color=(230, 240, 255), fuerza=0.38)
        im = L.aplicar(im)
        polvo(im, W * 0.5, suelo, 0.5 + 0.2 * math.sin(t * 0.3), 0.25, semilla=8, ancho=W, color=(120, 130, 140))
        return im
    return cuadro, {'z': 1.6, 'fx': (0.4, 0.6), 'fy': 0.6}


def _pista(W, H, d, **kw):
    rnd = random.Random(2)
    u = W / 1080 if H > W else H / 1080
    suelo = int(H * 0.66)
    f = Image.new('RGBA', (W, H))
    f.paste(_degradado(W, H, (14, 16, 26), (46, 44, 56)), (0, 0))
    df = ImageDraw.Draw(f)
    df.rectangle([0, suelo, W, H], fill=(30, 30, 34))
    df.rectangle([0, suelo, W * 0.72, suelo + 40 * u], fill=(54, 54, 58))
    for x in range(0, int(W * 0.72), int(70 * u)):
        df.ellipse([x - 5 * u, suelo - 5 * u, x + 5 * u, suelo + 5 * u], fill=(255, 240, 160))
    bx = W * 0.86
    df.rectangle([bx - 90 * u, suelo - 260 * u, bx + 160 * u, suelo], fill=(60, 56, 64), outline=TINTA, width=4)
    lluvia = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.7, 1.3)) for _ in range(160)]

    def avion(dr, x, y, ang):
        c, s = math.cos(ang), math.sin(ang)
        def P(px, py):
            return (x + (px * c - py * s) * u, y + (px * s + py * c) * u)
        dr.polygon([P(-260, -20), P(200, -24), P(250, 0), P(200, 22), P(-260, 18)], fill=(225, 225, 230), outline=TINTA)
        dr.polygon([P(-230, -18), P(-280, -110), P(-240, -110), P(-170, -18)], fill=(200, 30, 40), outline=TINTA)
        dr.polygon([P(-40, 4), P(-110, 70), P(-60, 70), P(40, 4)], fill=(190, 190, 200), outline=TINTA)
        for k in range(8):
            dr.ellipse([*P(-170 + k * 40, -10), *P(-160 + k * 40, 0)], fill=(60, 80, 110))

    def cuadro(t):
        im = f.copy()
        dr = ImageDraw.Draw(im)
        L = Luces(W, H)
        p = t / d
        if p < 0.3:
            k = _ease(p / 0.3)
            x, y, ang = -300 * u + (W * 0.25 + 300 * u) * k, suelo - 300 * u * (1 - k) - 30 * u, 0.12 * (1 - k)
        else:
            k = min(1.0, (p - 0.3) / 0.45)
            x, y, ang = W * 0.25 + (W * 0.55) * k, suelo - 30 * u, 0
        for (lx, ly, s) in lluvia:
            yy = (ly + t * 1400 * s * u) % H
            dr.line([(lx, yy), (lx - 8 * u, yy + 34 * u)], fill=(150, 160, 190), width=2)
        avion(dr, x, y, ang)
        L.halo(x + 240 * u, y, 60 * u, color=(255, 255, 230), fuerza=0.6)
        im = L.aplicar(im)
        if p > 0.75:                                       # choque: destello y fuego
            q = (p - 0.75) / 0.25
            capa = Image.new('RGBA', (W, H), (255, 240, 200, int(220 * max(0, 1 - q * 4))))
            im.alpha_composite(capa)
            fuego = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            dd = ImageDraw.Draw(fuego)
            for j in range(18):
                r = (60 + j * 9) * u * (0.6 + q)
                fx = bx + 30 * u * math.sin(t * 9 + j)
                fy = suelo - 80 * u - j * 12 * u * q
                dd.ellipse([fx - r * 0.5, fy - r * 0.5, fx + r * 0.5, fy + r * 0.5],
                           fill=(255, 120 + j * 6, 30, 70))
            im.alpha_composite(fuego.filter(ImageFilter.GaussianBlur(10)))
            polvo(im, bx, suelo - 200 * u, q, 0.8, ancho=W * 0.3, color=(40, 36, 36))
        return temblor(im, max(0.0, 1 - (p - 0.75) * 5) if p > 0.75 else 0, t)
    return cuadro, {'z': 1.5, 'fx': (0.3, 0.7), 'fy': 0.6}


ESCENAS = {'mina': _mina, 'carretera': _carretera, 'ciudad': _ciudad, 'linternas': _linternas, 'pista': _pista}


def escena(nombre, salida, d, W, H, letrero='', **kw):
    """Graba la escena dibujada `nombre` de `d` segundos. `letrero`: texto pequeño arriba (p. ej. 'RECREACIÓN')."""
    cam = {'z': 1.0, 'fx': (0.5, 0.5), 'fy': 0.5}
    z0 = 1.0
    if H > W:                                     # vertical: se dibuja más grande y la cámara encuadra la acción
        _, cam = ESCENAS[nombre](W, H, 0.1, **kw)
        z0 = cam['z']
    WW, HH = int(W * z0) // 2 * 2, int(H * z0) // 2 * 2
    cuadro, _ = ESCENAS[nombre](WW, HH, d, **kw)
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', salida],
                         stdin=subprocess.PIPE)
    rot = None
    if letrero:
        fu = _f(int(30 * (W / 1080 if H > W else H / 1080)))
        rot = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(rot)
        tw = dr.textlength(letrero, font=fu)
        y = int(H * 0.22) if H > W else int(H * 0.06)
        dr.rounded_rectangle([W - tw - 70, y, W - 30, y + 54], radius=10, fill=(0, 0, 0, 150))
        dr.text((W - tw - 50, y + 10), letrero, font=fu, fill=(235, 235, 235))
    for i in range(int(d * FPS)):
        im = cuadro(i / FPS)
        if z0 > 1:
            k = _ease(i / max(1, d * FPS - 1))
            fx = cam['fx'][0] + (cam['fx'][1] - cam['fx'][0]) * k
            x0 = min(max(0, int(fx * WW - W / 2)), WW - W)
            y0 = min(max(0, int(cam['fy'] * HH - H / 2)), HH - H)
            im = im.crop((x0, y0, x0 + W, y0 + H))
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        if rot:
            im.alpha_composite(rot)
        p.stdin.write(im.convert('RGB').tobytes())
    p.stdin.close()
    p.wait()
    return salida


if __name__ == '__main__':
    import sys
    # prueba: python3 dibujos.py mina sismo salida.mp4 [segundos] [h]
    nom, ev, sal = sys.argv[1:4]
    seg = float(sys.argv[4]) if len(sys.argv) > 4 else 4
    W_, H_ = (1920, 1080) if (len(sys.argv) > 5 and sys.argv[5] == 'h') else (1080, 1920)
    escena(nom, sal, seg, W_, H_, evento=ev, letrero='RECREACIÓN')
