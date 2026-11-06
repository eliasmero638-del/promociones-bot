"""Caras v3: rostros con rasgos de verdad (pómulos, mandíbula, nariz con fosas, labios, párpados, ojeras, arrugas, barba
de días), pintados con sombras suaves. Sirven para primeros planos y para las cabezas de los personajes animados."""
import os
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

F = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'InterDisplay-Black.otf')


def blob(Wd, Hd, x, y, rx, ry, ang=0.0):
    yy, xx = np.mgrid[0:Hd, 0:Wd].astype(np.float32)
    c, s = math.cos(ang), math.sin(ang)
    u = ((xx - x) * c + (yy - y) * s) / rx
    v = (-(xx - x) * s + (yy - y) * c) / ry
    return np.exp(-(u * u + v * v) * 1.6)


def cabeza(tipo='beto', expr='normal', S=600, hablar=False, cerrados=False):
    """Devuelve RGBA de S x 1.2S con la cabeza (y cuello) pintada."""
    Wd, Hd = S, int(S * 1.2)
    k = S / 600
    cx, cy = Wd / 2, Hd * 0.46
    if tipo == 'beto':
        piel = np.array([178, 120, 82], np.float32)
        sombra_col = np.array([96, 56, 40], np.float32)
        luz_col = np.array([226, 170, 128], np.float32)
    else:
        piel = np.array([172, 182, 186], np.float32)
        sombra_col = np.array([70, 74, 92], np.float32)
        luz_col = np.array([214, 222, 226], np.float32)
    # silueta: cráneo + pómulos + mandíbula
    m = Image.new('L', (Wd, Hd), 0)
    d = ImageDraw.Draw(m)
    jaw = 0.78 if tipo == 'beto' else 0.66
    pts = []
    for j in range(60):
        a = j / 60 * 2 * math.pi
        rx = 175 * k
        ry = 225 * k
        x = math.sin(a) * rx
        y = -math.cos(a) * ry
        if y > 0:                                   # parte de abajo: mandíbula más angosta
            x *= 1 - (1 - jaw) * (y / ry) ** 1.6
        if -40 * k < y < 70 * k:                    # pómulos
            x *= 1.04
        pts.append((cx + x, cy + y))
    d.polygon(pts, fill=255)
    d.rectangle([cx - 70 * k, cy + 150 * k, cx + 70 * k, cy + 290 * k], fill=255)       # cuello
    for s_ in (-1, 1):                                                                  # orejas
        d.ellipse([cx + s_ * 175 * k - 28 * k, cy - 30 * k, cx + s_ * 175 * k + 28 * k, cy + 60 * k], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1.2 * k))
    A = np.asarray(m, np.float32) / 255
    # sombreado: luz desde arriba-izquierda
    sh = np.zeros((Hd, Wd), np.float32)
    sh += 0.85 * blob(Wd, Hd, cx + 170 * k, cy + 40 * k, 120 * k, 260 * k)              # lado derecho en sombra
    for s_ in (-1, 1):
        sh += (1.1 if tipo != 'beto' else 0.7) * blob(Wd, Hd, cx + s_ * 62 * k, cy - 18 * k, 58 * k, 36 * k)   # cuencas
        sh += 0.35 * blob(Wd, Hd, cx + s_ * 105 * k, cy + 80 * k, 40 * k, 70 * k)        # bajo pómulos
    sh += 0.55 * blob(Wd, Hd, cx + 14 * k, cy + 92 * k, 34 * k, 16 * k)                 # bajo la nariz
    sh += 0.45 * blob(Wd, Hd, cx, cy + 168 * k, 70 * k, 22 * k)                         # bajo el labio / barbilla
    sh += 0.9 * blob(Wd, Hd, cx, cy + 215 * k, 120 * k, 40 * k)                         # sombra de la mandíbula en el cuello
    sh += 0.6 * blob(Wd, Hd, cx, cy - 210 * k, 200 * k, 70 * k)                         # sombra de gorra/sombrero
    hl = np.zeros_like(sh)
    hl += 0.7 * blob(Wd, Hd, cx - 50 * k, cy - 120 * k, 90 * k, 50 * k)                 # frente
    hl += 0.8 * blob(Wd, Hd, cx - 4 * k, cy + 30 * k, 12 * k, 60 * k)                   # puente de la nariz
    hl += 0.6 * blob(Wd, Hd, cx - 92 * k, cy + 42 * k, 40 * k, 26 * k)                  # pómulo izquierdo
    hl += 0.4 * blob(Wd, Hd, cx - 10 * k, cy + 186 * k, 30 * k, 14 * k)                 # barbilla
    sh = np.clip(sh, 0, 1)[..., None]
    hl = np.clip(hl, 0, 1)[..., None]
    col = piel * (1 - sh) + sombra_col * sh
    col = col * (1 - hl * 0.6) + luz_col * hl * 0.6
    rng = np.random.default_rng(3)
    col *= 0.95 + 0.05 * rng.random((Hd, Wd, 1))                                         # textura de piel
    if tipo == 'beto':                                                                    # barba de días
        barba = blob(Wd, Hd, cx, cy + 150 * k, 150 * k, 80 * k) * (rng.random((Hd, Wd)) < 0.35)
        col = col * (1 - 0.35 * barba[..., None])
    img = Image.fromarray(np.dstack([np.clip(col, 0, 255), A * 255]).astype(np.uint8), 'RGBA')
    d = ImageDraw.Draw(img)
    T = (36, 22, 18) if tipo == 'beto' else (20, 20, 26)
    # orejas: pliegue interior
    for s_ in (-1, 1):
        d.arc([cx + s_ * 175 * k - 16 * k, cy - 14 * k, cx + s_ * 175 * k + 16 * k, cy + 44 * k], 90 if s_ < 0 else 270,
               270 if s_ < 0 else 90, fill=tuple(int(v) for v in sombra_col), width=int(5 * k))
    # ojos
    abre = {'miedo': 1.35, 'normal': 1.0, 'cansado': 0.6, 'fijo': 1.0}.get(expr, 1.0)
    for s_ in (-1, 1):
        ex, ey = cx + s_ * 64 * k, cy - 16 * k
        if tipo == 'beto':
            d.ellipse([ex - 34 * k, ey - 15 * k * abre, ex + 34 * k, ey + 15 * k * abre], fill=(236, 230, 218))
            ir = 13 * k
            d.ellipse([ex - ir, ey - ir, ex + ir, ey + ir], fill=(88, 56, 34))
            d.ellipse([ex - ir * 0.6, ey - ir * 0.6, ex + ir * 0.6, ey + ir * 0.6], fill=(56, 34, 20))
            d.ellipse([ex - 5 * k, ey - 5 * k, ex + 5 * k, ey + 5 * k], fill=(10, 8, 8))
            d.ellipse([ex - 8 * k, ey - 9 * k, ex - 2 * k, ey - 3 * k], fill=(255, 255, 255))
            d.arc([ex - 36 * k, ey - 20 * k * abre, ex + 36 * k, ey + 16 * k * abre], 195, 345, fill=T, width=int(6 * k))  # párpado
            d.arc([ex - 30 * k, ey - 8 * k, ex + 30 * k, ey + 18 * k * abre], 20, 160, fill=tuple(int(v) for v in sombra_col), width=int(3 * k))
            if expr == 'cansado':
                d.chord([ex - 36 * k, ey - 20 * k, ex + 36 * k, ey + 10 * k], 180, 360, fill=tuple(int(v) for v in piel))
                d.line([(ex - 34 * k, ey - 4 * k), (ex + 34 * k, ey - 4 * k)], fill=T, width=int(5 * k))
        else:                                                                           # cliente: pupilas chiquitas
            d.ellipse([ex - 30 * k, ey - 13 * k, ex + 30 * k, ey + 13 * k], fill=(196, 200, 196))
            d.ellipse([ex - 5 * k, ey - 5 * k, ex + 5 * k, ey + 5 * k], fill=(10, 10, 12))
            d.arc([ex - 32 * k, ey - 18 * k, ex + 32 * k, ey + 14 * k], 195, 345, fill=T, width=int(5 * k))
        if cerrados:
            d.ellipse([ex - 38 * k, ey - 22 * k, ex + 38 * k, ey + 20 * k], fill=tuple(int(v) for v in piel))
            d.arc([ex - 34 * k, ey - 14 * k, ex + 34 * k, ey + 8 * k], 20, 160, fill=T, width=int(5 * k))
        # ceja con pelitos
        dy = {'miedo': -18, 'normal': 0, 'cansado': 6, 'fijo': 4}.get(expr, 0) * k
        incl = {'miedo': -10, 'fijo': 8}.get(expr, 0) * k
        for j in range(16):
            t = j / 15
            x = ex - s_ * 40 * k + s_ * t * 80 * k
            y = ey - 46 * k + dy - math.sin(t * math.pi) * 10 * k + (incl if (s_ * (t - 0.5)) < 0 else -incl) * abs(t - 0.5)
            d.line([(x, y + 6 * k), (x + s_ * 10 * k, y - 3 * k)], fill=(40, 28, 24) if tipo == 'beto' else (60, 60, 64), width=int(5 * k))
    # nariz
    nc = tuple(int(v) for v in sombra_col)
    d.arc([cx - 30 * k, cy + 56 * k, cx + 30 * k, cy + 96 * k], 20, 160, fill=nc, width=int(5 * k))
    for s_ in (-1, 1):
        d.ellipse([cx + s_ * 14 * k - 7 * k, cy + 78 * k, cx + s_ * 14 * k + 7 * k, cy + 88 * k], fill=(50, 30, 26) if tipo == 'beto' else (60, 60, 70))
    d.ellipse([cx - 8 * k, cy + 58 * k, cx + 6 * k, cy + 70 * k], fill=tuple(int(v) for v in luz_col))
    # boca
    if tipo == 'beto':
        if expr == 'miedo':
            d.ellipse([cx - 24 * k, cy + 120 * k, cx + 24 * k, cy + 168 * k], fill=(66, 22, 22))
            d.ellipse([cx - 16 * k, cy + 150 * k, cx + 16 * k, cy + 166 * k], fill=(150, 70, 70))
        elif hablar:
            d.ellipse([cx - 26 * k, cy + 122 * k, cx + 26 * k, cy + 152 * k], fill=(70, 26, 24))
            d.ellipse([cx - 16 * k, cy + 140 * k, cx + 16 * k, cy + 150 * k], fill=(150, 76, 70))
        else:
            d.chord([cx - 34 * k, cy + 118 * k, cx + 34 * k, cy + 148 * k], 0, 180, fill=(132, 70, 60))
            d.line([(cx - 34 * k, cy + 132 * k), (cx + 34 * k, cy + 132 * k)], fill=(60, 26, 22), width=int(4 * k))
        for j in range(70):                                                              # bigote con pelos
            t = j / 69
            x = cx - 70 * k + t * 140 * k
            y0 = cy + 104 * k + abs(t - 0.5) * 40 * k
            d.line([(x, y0 - 12 * k), (x + (t - 0.5) * 16 * k, y0 + 18 * k)], fill=(28, 20, 18), width=int(4 * k))
        for s_ in (-1, 1):                                                               # arrugas
            d.arc([cx + s_ * 60 * k - 40 * k, cy + 50 * k, cx + s_ * 60 * k + 40 * k, cy + 150 * k], 100 if s_ < 0 else 0,
                   180 if s_ < 0 else 80, fill=nc, width=int(3 * k))
            d.line([(cx + s_ * 100 * k, cy - 10 * k), (cx + s_ * 118 * k, cy - 20 * k)], fill=nc, width=int(2 * k))
        for j in range(3):
            d.arc([cx - 90 * k, cy - 150 * k + j * 20 * k, cx + 90 * k, cy - 110 * k + j * 20 * k], 200, 340, fill=nc, width=int(2 * k))
    else:                                                                               # cliente: sonrisa larga y fina
        if hablar:
            d.chord([cx - 56 * k, cy + 110 * k, cx + 56 * k, cy + 176 * k], 0, 180, fill=(24, 14, 18))
        d.arc([cx - 70 * k, cy + 96 * k, cx + 70 * k, cy + 156 * k], 15, 165, fill=(30, 20, 24), width=int(6 * k))
        for j in range(9):
            x = cx - 44 * k + j * 11 * k
            d.line([(x, cy + 146 * k), (x, cy + 154 * k)], fill=(205, 200, 180), width=int(5 * k))
        d.line([(cx - 60 * k, cy + 130 * k), (cx - 72 * k, cy + 122 * k)], fill=(30, 20, 24), width=int(4 * k))
        d.line([(cx + 60 * k, cy + 130 * k), (cx + 72 * k, cy + 122 * k)], fill=(30, 20, 24), width=int(4 * k))
    # pelo / gorra / sombrero
    if tipo == 'beto':
        for j in range(90):                                                              # pelo con canas a los lados
            s_ = -1 if j % 2 else 1
            x = cx + s_ * random.Random(j).uniform(150, 172) * k
            y = cy - random.Random(j + 50).uniform(40, 150) * k
            c = (200, 200, 200) if j % 3 == 0 else (40, 34, 30)
            d.line([(x, y), (x + s_ * 4 * k, y + 22 * k)], fill=c, width=int(3 * k))
        d.chord([cx - 190 * k, cy - 270 * k, cx + 190 * k, cy - 40 * k], 180, 360, fill=(176, 34, 32))
        d.chord([cx - 190 * k, cy - 270 * k, cx + 190 * k, cy - 40 * k], 280, 360, fill=(140, 24, 24))
        d.polygon([(cx - 30 * k, cy - 160 * k), (cx + 250 * k, cy - 168 * k), (cx + 262 * k, cy - 140 * k), (cx - 20 * k, cy - 132 * k)],
                  fill=(150, 26, 26))
        d.arc([cx - 190 * k, cy - 270 * k, cx + 190 * k, cy - 40 * k], 180, 360, fill=(30, 16, 14), width=int(5 * k))
    else:
        d.rounded_rectangle([cx - 270 * k, cy - 210 * k, cx + 270 * k, cy - 178 * k], radius=int(14 * k), fill=(52, 38, 28))
        d.rounded_rectangle([cx - 160 * k, cy - 360 * k, cx + 160 * k, cy - 196 * k], radius=int(30 * k), fill=(64, 48, 36))
        d.rectangle([cx - 160 * k, cy - 236 * k, cx + 160 * k, cy - 208 * k], fill=(26, 18, 14))
        for j in range(14):                                                               # pelo mojado pegado
            s_ = -1 if j % 2 else 1
            x = cx + s_ * random.Random(j).uniform(140, 168) * k
            d.line([(x, cy - 180 * k), (x + s_ * 6 * k, cy + random.Random(j).uniform(0, 60) * k)], fill=(30, 30, 36), width=int(5 * k))
        for j in range(8):                                                                # gotas en la cara
            x = cx + random.Random(j + 3).uniform(-120, 120) * k
            y = cy + random.Random(j + 7).uniform(-120, 160) * k
            d.ellipse([x - 4 * k, y, x + 4 * k, y + 14 * k], fill=(200, 220, 240))
    img = img.filter(ImageFilter.GaussianBlur(0.7 * k))
    return img


if __name__ == '__main__':
    W, H = 1080, 1350
    fondo = Image.new('RGB', (W, H), (18, 16, 26))
    yy = np.linspace(0, 1, H)[:, None, None]
    fondo = Image.fromarray((np.array([40, 34, 56]) * (1 - yy) + np.array([10, 8, 14]) * yy).repeat(W, 1).astype(np.uint8))
    im = fondo.convert('RGBA')
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(F, 60)
    d.text((W / 2, 60), 'CARAS CON RASGOS', font=f, fill=(245, 220, 120), anchor='mm', stroke_width=4, stroke_fill=(0, 0, 0))
    a = cabeza('beto', 'normal', 500)
    b = cabeza('cliente', 'fijo', 500)
    im.alpha_composite(a, (20, 130))
    im.alpha_composite(b, (W - 520, 130))
    for j, e in enumerate(['cansado', 'miedo']):
        c = cabeza('beto', e, 330)
        im.alpha_composite(c, (60 + j * 360, 860))
    f2 = ImageFont.truetype(F, 34)
    for t, x, y in (('DON BETO', 270, 760), ('EL CLIENTE', W - 270, 760), ('cansado', 225, 1300), ('con miedo', 585, 1300)):
        d.text((x, y), t, font=f2, fill=(255, 255, 255), anchor='mm', stroke_width=3, stroke_fill=(0, 0, 0))
    im.convert('RGB').save('/tmp/claude-0/-home-claude/892f978d-49cb-5753-ad70-2df73d3cf53c/scratchpad/ter/caras_v3.jpg', quality=93)
    print('ok')
