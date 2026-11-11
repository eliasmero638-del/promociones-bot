"""Portada de los videos largos (11-nov, aprobada por el dueño): FOTOS REALES + texto clickbait con franja roja de pincel,
palabras clave en amarillo, etiqueta amarilla, flecha roja y foto "rota".
cambios.json: "portada": {"fondo": "esc_03.jpg", "foto": "esc_05.jpg" (la persona), "recorte": "esc_14.jpg" (objeto
sobre fondo blanco, opcional), "lineas": ["Se *ENAMORÓ* de un", "*EXTRATERRESTRE*", "y dijo que tuvo un *HIJO* con él"],
"etiqueta": "La historia de Elizabeth Klarer"}   (*palabra* = amarillo)"""
import math, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageOps

W, H = 1280, 720
import glob, os
NEGRA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'InterDisplay-Black.otf')
MAQ = next(iter(glob.glob('/usr/share/fonts/**/*Courier*10*Pitch*Bold*', recursive=True) +
                glob.glob('/usr/share/fonts/**/FreeMonoBold*', recursive=True) +
                glob.glob('/usr/share/fonts/**/DejaVuSansMono-Bold*', recursive=True)), NEGRA)
rnd = random.Random(7)


def fondo(path):
    im = ImageOps.fit(Image.open(path).convert('RGB'), (W, H), centering=(0.5, 0.4))
    im = ImageEnhance.Color(im).enhance(0.35)
    a = np.asarray(im).astype(float) / 255
    a = a * np.array([0.55, 0.62, 0.85]) * 0.75                       # noche azulada
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.75 * (((xx - W * 0.55) / W) ** 2 + ((yy - H * 0.45) / H) ** 2) ** 0.8
    a = a * np.clip(v, 0.25, 1)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')


def foto_rota(path, ancho, angulo):
    f = ImageOps.fit(Image.open(path).convert('RGB'), (ancho, int(ancho * 1.15)), centering=(0.5, 0.45))
    f = ImageOps.grayscale(f).convert('RGB'); f = ImageEnhance.Contrast(f).enhance(1.4)
    b = 14
    p = Image.new('RGBA', (f.width + 2 * b, f.height + 2 * b), (245, 242, 232, 255)); p.paste(f, (b, b))
    m = Image.new('L', p.size, 255); d = ImageDraw.Draw(m)               # borde roto arriba y a la derecha
    pts = [(0, 0)] + [(x, rnd.randint(0, 16)) for x in range(0, p.width, 14)] + [(p.width, 0)]
    d.polygon(pts, fill=0)
    pts = [(p.width, 0)] + [(p.width - rnd.randint(0, 16), y) for y in range(0, p.height, 14)] + [(p.width, p.height)]
    d.polygon(pts, fill=0)
    p.putalpha(m)
    return p.rotate(angulo, expand=True, resample=Image.BICUBIC)


def recorte(path, alto):
    """Objeto sobre fondo blanco → recortado (quita lo blanco)."""
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(int)
    from PIL import ImageDraw as _D
    claro = Image.fromarray(((a.min(2) > 150) & (np.ptp(a, 2) < 30)).astype(np.uint8) * 255)
    rel = claro.copy()
    for c in [(0, 0), (rel.width - 1, 0), (0, rel.height - 1), (rel.width - 1, rel.height - 1)]:
        _D.floodfill(rel, c, 128)                     # solo el fondo claro conectado a los bordes
    mascara = np.asarray(rel) != 128
    m = Image.fromarray((mascara * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.5))
    im = im.convert('RGBA'); im.putalpha(m)
    im = im.crop(m.getbbox())
    k = alto / im.height
    return im.resize((int(im.width * k), alto), Image.LANCZOS)


def sombra(img, capa, xy, r=18, o=(10, 12)):
    s = Image.new('RGBA', capa.size, (0, 0, 0, 0)); s.putalpha(capa.split()[3].point(lambda v: v * 0.8))
    s2 = Image.new('RGBA', img.size, (0, 0, 0, 0)); s2.paste(s, (xy[0] + o[0], xy[1] + o[1]), s)
    img.alpha_composite(s2.filter(ImageFilter.GaussianBlur(r))); img.alpha_composite(capa, xy)


def brillo(img, cx, cy, r, color):
    g = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(r * 0.6)))


def franja_pincel(img, caja):
    """Mancha roja tipo brocha detrás del texto."""
    x0, y0, x1, y1 = caja
    capa = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(capa)
    for k in range(90):
        y = rnd.uniform(y0 - 6, y1 - 30); h = rnd.uniform(34, 70)
        xa = x0 + rnd.uniform(-30, 25); xb = x1 + rnd.uniform(-40, 30)
        col = rnd.choice([(196, 18, 18), (170, 10, 12), (222, 40, 26), (140, 6, 8)])
        d.rounded_rectangle([xa, y, xb, y + h], radius=int(h / 2), fill=col + (rnd.randint(170, 235),))
    capa = capa.filter(ImageFilter.GaussianBlur(1.2))
    # textura de pelos de brocha
    ruido = Image.effect_noise(img.size, 60).point(lambda v: 255 if v > 150 else 0).filter(ImageFilter.GaussianBlur(0.6))
    al = np.asarray(capa.split()[3]).astype(float) * (0.75 + 0.25 * np.asarray(ruido) / 255)
    capa.putalpha(Image.fromarray(al.astype(np.uint8)))
    brillo(img, (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * 0.35, (255, 120, 20, 70))
    img.alpha_composite(capa)


def texto(d, xy, partes, tam, borde=7):
    """partes: [(texto, color)] en una línea, con borde negro grueso."""
    f = ImageFont.truetype(NEGRA, tam)
    x, y = xy
    for t, c in partes:
        d.text((x + 5, y + 7), t, font=f, fill=(0, 0, 0, 200))
        d.text((x, y), t, font=f, fill=c, stroke_width=borde, stroke_fill=(10, 10, 10))
        x += f.getlength(t)
    return x


def ancho(partes, tam):
    f = ImageFont.truetype(NEGRA, tam)
    return sum(f.getlength(t) for t, _ in partes)


def flecha(img, a, b, curva=-80):
    d = ImageDraw.Draw(img)
    pts = []
    for i in range(41):
        t = i / 40
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + curva
        x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * mx + t ** 2 * b[0]
        y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * my + t ** 2 * b[1]
        pts.append((x, y))
    d.line(pts, fill=(255, 255, 255), width=20, joint='curve'); d.line(pts, fill=(225, 25, 25), width=12, joint='curve')
    (x1, y1), (x2, y2) = pts[-4], pts[-1]
    ang = math.atan2(y2 - y1, x2 - x1)
    def pt(r, da):
        return (x2 + r * math.cos(ang + da), y2 + r * math.sin(ang + da))
    tri = [pt(14, 0), pt(-34, 0.75), pt(-34, -0.75)]
    d.polygon([(x + 0, y + 0) for x, y in tri], fill=(225, 25, 25), outline=(255, 255, 255), width=4)


def _partes(linea):
    Y, B = (255, 222, 0), (255, 255, 255)
    out = []
    for i, t in enumerate(linea.split('*')):
        if t:
            out.append((t, Y if i % 2 else B))
    return out


def hacer(fondo_p, salida, lineas, etiqueta='', foto_p=None, recorte_p=None):
    img = fondo(fondo_p)
    brillo(img, W * 0.80, H * 0.30, 260, (120, 170, 255, 70))
    if recorte_p:
        try:
            cam = ImageEnhance.Contrast(recorte(recorte_p, 330)).enhance(1.15)
            brillo(img, 1010, 230, 230, (255, 220, 160, 60))
            sombra(img, cam.rotate(-8, expand=True, resample=Image.BICUBIC), (min(830, W - cam.width - 10), 40))
        except Exception:
            recorte_p = None
    if foto_p:
        rota = foto_rota(foto_p, 330 if recorte_p else 400, 6)
        x = 30 if recorte_p else W - rota.width - 30
        sombra(img, rota, (x, 20))
    # tamaños: cada línea ocupa como mucho 800 px de ancho
    filas = []
    for l in lineas:
        p = _partes(l)
        tam = 108
        while tam > 40 and ancho(p, tam) > 800:
            tam -= 2
        if len(lineas) > 1 and all(c == (255, 255, 255) for _, c in p):
            tam = min(tam, 64)
        filas.append((p, tam))
    alto = sum(int(t * 1.08) for _, t in filas)
    y0 = H - alto - (90 if etiqueta else 40)
    cajas, y = [], y0
    for p, tam in filas:
        cajas.append((40, y - 6, 40 + ancho(p, tam) + 30, y + tam * 1.12)); y += int(tam * 1.08)
    franja_pincel(img, (cajas[0][0] - 10, cajas[0][1] - 10, max(c[2] for c in cajas) + 10, cajas[-1][3] + 4))
    d = ImageDraw.Draw(img); y = y0
    for p, tam in filas:
        texto(d, (55, y), p, tam); y += int(tam * 1.08)
    if etiqueta:
        f = ImageFont.truetype(MAQ, 34)
        w = int(f.getlength(etiqueta)) + 40
        et = Image.new('RGBA', (w, 58), (0, 0, 0, 0)); de = ImageDraw.Draw(et)
        de.polygon([(6, 4), (w, 0), (w - 8, 54), (0, 58)], fill=(250, 214, 30, 255))
        de.text((20, 10), etiqueta, font=f, fill=(15, 15, 15))
        sombra(img, et.rotate(1.5, expand=True), (70, min(y + 12, H - 66)), r=8, o=(5, 6))
    if recorte_p and foto_p:
        flecha(img, (560, y0 - 60), (840, 190), curva=-90)
    out = ImageEnhance.Contrast(img.convert('RGB')).enhance(1.08)
    ImageEnhance.Sharpness(out).enhance(1.3).save(salida, quality=93)
    return salida
