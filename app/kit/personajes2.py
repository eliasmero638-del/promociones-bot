"""Personajes v2 (estilo dibujo animado, con volumen): cada parte se dibuja en su capa y se sombrea (sombra abajo-derecha,
luz de borde arriba-izquierda), proporciones de adulto, manos con dedos, caras expresivas."""
import os
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

F = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'InterDisplay-Black.otf')
OUT = os.environ.get('KIT_OUT', '.') + '/'
T = (24, 16, 14)
SS = 3


def fnt(n):
    return ImageFont.truetype(F, n)


class Capa:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def P(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def poly(self, pts, fill, ol=T, w=3):
        self.d.polygon(self.P(pts), fill=fill, outline=ol, width=int(w * SS) if ol else 0)

    def ell(self, x0, y0, x1, y1, fill, ol=T, w=3):
        self.d.ellipse([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fill, outline=ol, width=int(w * SS) if ol else 0)

    def rect(self, x0, y0, x1, y1, fill, ol=T, w=3, r=0):
        self.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=int(r * SS), fill=fill, outline=ol,
                                 width=int(w * SS) if ol else 0)

    def line(self, pts, col=T, w=3):
        self.d.line(self.P(pts), fill=col, width=max(1, int(w * SS)), joint='curve')

    def miembro(self, pts, grosor, col, ol=T):
        self.line(pts, ol, grosor + 6)
        self.line(pts, col, grosor)
        for x, y in (pts[0], pts[-1]):
            r = grosor / 2
            self.ell(x - r, y - r, x + r, y + r, col, ol=None)

    def fin(self, sombra=True, d=10, osc=0.42, rim=(150, 190, 255), rim_a=0.35):
        im = self.im.resize((self.w, self.h), Image.LANCZOS)
        if not sombra:
            return im
        a = im.getchannel('A')
        sh = ImageChops.subtract(a, ImageChops.offset(a, -d, -d)).filter(ImageFilter.GaussianBlur(d / 2))
        lt = ImageChops.subtract(a, ImageChops.offset(a, d // 2, d // 2)).filter(ImageFilter.GaussianBlur(d / 3))
        sh = ImageChops.multiply(sh, a)
        lt = ImageChops.multiply(lt, a)
        rgb = im.convert('RGB')
        oscuro = Image.blend(rgb, Image.new('RGB', rgb.size, (20, 14, 30)), osc)
        rgb = Image.composite(oscuro, rgb, sh)
        claro = Image.blend(rgb, Image.new('RGB', rgb.size, rim), rim_a)
        rgb = Image.composite(claro, rgb, lt.point(lambda v: v // 2))
        return Image.merge('RGBA', (*rgb.split(), a))


def juntar(w, h, capas):
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for c in capas:
        out.alpha_composite(c)
    return out


def mano(C, x, y, s, piel, ang=0.0, abierta=True):
    C.ell(x - 17 * s, y - 16 * s, x + 17 * s, y + 22 * s, piel)                        # palma tipo guante
    C.ell(x - 22 * s, y - 6 * s, x - 6 * s, y + 10 * s, piel)                          # pulgar
    for j in range(3):
        C.line([(x - 8 * s + j * 8 * s, y + 6 * s), (x - 8 * s + j * 8 * s, y + 18 * s)], T, 1.5 * s)


def cara(C, cx, cy, s, piel, piel_s, expr='normal', bigote=True, edad=True, ojo_col=(60, 40, 30), muerto=False):
    """Cabeza con orejas, nariz, cejas, ojos con iris y párpado, boca según la expresión."""
    C.ell(cx - 58 * s, cy - 72 * s, cx + 58 * s, cy + 72 * s, piel)                       # cabeza ovalada
    C.ell(cx - 70 * s, cy - 10 * s, cx - 50 * s, cy + 26 * s, piel)                       # orejas
    C.ell(cx + 50 * s, cy - 10 * s, cx + 70 * s, cy + 26 * s, piel)
    C.ell(cx + 18 * s, cy - 60 * s, cx + 52 * s, cy + 66 * s, piel_s, ol=None)            # sombra lateral de la cara
    abre = {'miedo': 1.45, 'normal': 1.0, 'cansado': 0.55, 'fijo': 1.15}.get(expr, 1.0)
    for sd in (-1, 1):
        ex = cx + sd * 24 * s
        if muerto:
            C.ell(ex - 19 * s, cy - 20 * s, ex + 19 * s, cy + 8 * s, (70, 74, 86), ol=None)   # ojera hundida
        if muerto:
            C.ell(ex - 15 * s, cy - 15 * s, ex + 15 * s, cy + 5 * s, (22, 20, 26), ol=None)
            C.ell(ex - 3 * s, cy - 8 * s, ex + 3 * s, cy - 2 * s, (235, 240, 245), ol=None)
            continue
        C.ell(ex - 14 * s, cy - 14 * s * abre, ex + 14 * s, cy + 6 * s * abre, (245, 242, 232), w=2)
        ri = 7.5 * s
        C.ell(ex - ri, cy - 4 * s - ri, ex + ri, cy - 4 * s + ri, ojo_col, ol=None)
        if not muerto:
            C.ell(ex - 3 * s, cy - 7 * s, ex + 3 * s, cy - 1 * s, T, ol=None)
            C.ell(ex + 1 * s, cy - 9 * s, ex + 4 * s, cy - 6 * s, (255, 255, 255), ol=None)
        if expr == 'cansado':
            C.rect(ex - 15 * s, cy - 16 * s, ex + 15 * s, cy - 4 * s, piel, ol=None)
            C.line([(ex - 15 * s, cy - 4 * s), (ex + 15 * s, cy - 4 * s)], T, 2.5 * s)
        ceja = {'miedo': (-10, -6), 'normal': (-2, 0), 'cansado': (2, 4), 'fijo': (2, -2)}.get(expr, (0, 0))
        C.line([(ex - 15 * s * sd * -1, cy - 28 * s + ceja[0] * s), (ex + 16 * s * sd * -1 * -1, cy - 28 * s + ceja[1] * s)],
               (36, 26, 22), 6 * s)
    C.poly([(cx - 2 * s, cy + 2 * s), (cx + 12 * s, cy + 26 * s), (cx - 8 * s, cy + 28 * s)], piel_s, w=2)  # nariz
    if edad:
        for sd in (-1, 1):
            C.line([(cx + sd * 30 * s, cy + 16 * s), (cx + sd * 36 * s, cy + 36 * s)], piel_s, 2.5 * s)
        C.line([(cx - 18 * s, cy - 44 * s), (cx + 18 * s, cy - 44 * s)], piel_s, 2 * s)
    if expr == 'miedo':
        C.ell(cx - 13 * s, cy + 40 * s, cx + 13 * s, cy + 66 * s, (70, 20, 20), w=2.5)
    elif expr == 'fijo':
        C.d.arc([(cx - 34 * s) * SS, (cy + 22 * s) * SS, (cx + 34 * s) * SS, (cy + 56 * s) * SS], 15, 165, fill=T, width=int(4 * s * SS))
    else:
        C.line([(cx - 14 * s, cy + 50 * s), (cx + 14 * s, cy + 50 * s)], T, 3.5 * s)
    if bigote:
        C.poly([(cx - 34 * s, cy + 42 * s), (cx - 4 * s, cy + 30 * s), (cx, cy + 34 * s), (cx + 4 * s, cy + 30 * s),
                (cx + 34 * s, cy + 42 * s), (cx + 26 * s, cy + 48 * s), (cx, cy + 42 * s), (cx - 26 * s, cy + 48 * s)], (34, 24, 20), w=2)


def don_beto(alto=900, expr='normal', pose='quieto', sin_cabeza=False):
    w, h = int(alto * 0.62), alto
    s = alto / 900
    cx = w / 2
    piel, piel_s = (174, 116, 76), (146, 92, 58)
    azul, azul_s = (44, 74, 132), (30, 52, 96)
    capas = []
    C = Capa(w, h)                                                     # piernas y botas
    for sd in (-1, 1):
        C.miembro([(cx + sd * 34 * s, 560 * s), (cx + sd * 38 * s, 700 * s), (cx + sd * 40 * s, 830 * s)], 58 * s, azul_s)
        C.rect(cx + sd * 42 * s - 44 * s, 822 * s, cx + sd * 42 * s + 50 * s, 880 * s, (52, 34, 24), r=18 * s)
    capas.append(C.fin())
    C = Capa(w, h)                                                     # torso con overol
    C.poly([(cx - 118 * s, 330 * s), (cx + 118 * s, 330 * s), (cx + 100 * s, 600 * s), (cx - 100 * s, 600 * s)], azul)
    C.ell(cx - 128 * s, 300 * s, cx - 60 * s, 380 * s, azul)
    C.ell(cx + 60 * s, 300 * s, cx + 128 * s, 380 * s, azul)
    C.line([(cx, 340 * s), (cx, 590 * s)], (24, 44, 84), 3 * s)        # cierre
    C.rect(cx - 82 * s, 380 * s, cx - 22 * s, 430 * s, azul_s, w=2)   # bolsillo
    C.rect(cx + 26 * s, 376 * s, cx + 92 * s, 404 * s, (236, 230, 216), w=2, r=4 * s)
    C.d.text(((cx + 31 * s) * SS, (378 * s) * SS), 'BETO', font=fnt(int(20 * s * SS)), fill=(190, 34, 34))
    for (x, y, r) in ((cx + 50 * s, 470 * s, 22 * s), (cx - 60 * s, 540 * s, 16 * s)):
        C.ell(x - r, y - r * 0.7, x + r, y + r * 0.7, (40, 40, 44), ol=None)   # manchas de grasa
    C.rect(cx - 104 * s, 560 * s, cx + 104 * s, 600 * s, azul_s, ol=None)
    capas.append(C.fin())
    C = Capa(w, h)                                                     # brazos y manos
    if pose == 'miedo':
        C.miembro([(cx - 100 * s, 345 * s), (cx - 170 * s, 300 * s), (cx - 168 * s, 210 * s)], 46 * s, azul)
        mano(C, cx - 166 * s, 190 * s, s * 1.1, piel, ang=math.pi)
        C.miembro([(cx + 100 * s, 345 * s), (cx + 170 * s, 300 * s), (cx + 168 * s, 210 * s)], 46 * s, azul)
        mano(C, cx + 166 * s, 190 * s, s * 1.1, piel, ang=math.pi)
    else:
        C.miembro([(cx - 104 * s, 345 * s), (cx - 130 * s, 470 * s), (cx - 120 * s, 580 * s)], 46 * s, azul)
        mano(C, cx - 120 * s, 600 * s, s * 1.1, piel)
        C.miembro([(cx + 104 * s, 345 * s), (cx + 136 * s, 460 * s), (cx + 150 * s, 560 * s)], 46 * s, azul)
        mano(C, cx + 150 * s, 580 * s, s * 1.1, piel)
        C.line([(cx + 156 * s, 600 * s), (cx + 214 * s, 700 * s)], (160, 164, 172), 16 * s)          # llave
        C.ell(cx + 196 * s, 684 * s, cx + 236 * s, 724 * s, (160, 164, 172), w=2)
        C.ell(cx + 208 * s, 696 * s, cx + 224 * s, 712 * s, (0, 0, 0, 0), ol=None)
    capas.append(C.fin())
    C = Capa(w, h)                                                     # cuello, cabeza, gorra
    hs, cy = 1.32 * s, 222 * s
    C.rect(cx - 30 * s, 290 * s, cx + 30 * s, 340 * s, piel_s, ol=None)
    C.poly([(cx - 40 * s, 320 * s), (cx, 352 * s), (cx + 40 * s, 320 * s)], (230, 226, 214), w=2)   # camiseta
    cara(C, cx, cy, hs, piel, piel_s, expr=expr)
    for j in range(7):                                                 # canas en las patillas
        C.line([(cx - 58 * hs, cy - 40 * hs + j * 6 * hs), (cx - 50 * hs, cy - 38 * hs + j * 6 * hs)], (205, 205, 205), 2 * s)
    C.d.chord([(cx - 64 * hs) * SS, (cy - 92 * hs) * SS, (cx + 64 * hs) * SS, (cy + 10 * hs) * SS], 180, 360, fill=(186, 38, 36),
              outline=T, width=int(3 * SS))
    C.poly([(cx - 10 * hs, cy - 44 * hs), (cx + 104 * hs, cy - 50 * hs), (cx + 110 * hs, cy - 34 * hs), (cx - 8 * hs, cy - 32 * hs)],
           (150, 28, 28))
    C.ell(cx - 6 * hs, cy - 96 * hs, cx + 6 * hs, cy - 84 * hs, (150, 28, 28), w=2)
    capas.append(C.fin(d=8))
    return juntar(w, h, capas[:-1] if sin_cabeza else capas)


def cliente(alto=900, expr='fijo', sin_cabeza=False):
    w, h = int(alto * 0.6), alto
    s = alto / 900
    cx = w / 2
    piel, piel_s = (178, 190, 194), (138, 150, 158)
    traje, traje_s = (104, 70, 42), (74, 48, 28)
    capas = []
    C = Capa(w, h)
    for sd in (-1, 1):
        C.miembro([(cx + sd * 30 * s, 580 * s), (cx + sd * 32 * s, 720 * s), (cx + sd * 34 * s, 840 * s)], 52 * s, traje_s)
        C.rect(cx + sd * 36 * s - 40 * s, 836 * s, cx + sd * 36 * s + 44 * s, 880 * s, (26, 20, 16), r=14 * s)
    capas.append(C.fin(rim=(120, 200, 255), rim_a=0.5))
    C = Capa(w, h)
    C.poly([(cx - 100 * s, 330 * s), (cx + 100 * s, 330 * s), (cx + 92 * s, 620 * s), (cx - 92 * s, 620 * s)], traje)
    C.ell(cx - 112 * s, 300 * s, cx - 50 * s, 372 * s, traje)
    C.ell(cx + 50 * s, 300 * s, cx + 112 * s, 372 * s, traje)
    C.poly([(cx - 34 * s, 330 * s), (cx, 450 * s), (cx + 34 * s, 330 * s)], (224, 222, 210), w=2)             # camisa
    C.poly([(cx - 8 * s, 344 * s), (cx + 8 * s, 344 * s), (cx + 6 * s, 450 * s), (cx, 462 * s), (cx - 6 * s, 450 * s)], (110, 18, 26), w=2)
    for sd in (-1, 1):                                                                                        # solapas
        C.poly([(cx + sd * 34 * s, 330 * s), (cx + sd * 70 * s, 340 * s), (cx + sd * 16 * s, 470 * s)], traje_s, w=2)
    for j in range(10):                                                                                       # gotas
        x = cx + random.Random(j).uniform(-90, 90) * s
        y = random.Random(j + 9).uniform(350, 840) * s
        C.ell(x - 4 * s, y, x + 4 * s, y + 14 * s, (160, 200, 240), ol=None)
    capas.append(C.fin(rim=(120, 200, 255), rim_a=0.5))
    C = Capa(w, h)
    for sd in (-1, 1):
        C.miembro([(cx + sd * 92 * s, 350 * s), (cx + sd * 112 * s, 480 * s), (cx + sd * 108 * s, 600 * s)], 42 * s, traje)
        mano(C, cx + sd * 108 * s, 622 * s, s * 1.15, piel)
    capas.append(C.fin(rim=(120, 200, 255), rim_a=0.5))
    C = Capa(w, h)
    hs, cy = 1.25 * s, 225 * s
    C.rect(cx - 26 * s, 290 * s, cx + 26 * s, 340 * s, piel_s, ol=None)
    cara(C, cx, cy, hs * 0.95, piel, piel_s, expr=expr, bigote=False, edad=False, muerto=True)
    C.ell(cx - 50 * hs, cy + 14 * hs, cx - 22 * hs, cy + 50 * hs, piel_s, ol=None)                         # mejillas hundidas
    C.ell(cx + 22 * hs, cy + 14 * hs, cx + 50 * hs, cy + 50 * hs, piel_s, ol=None)
    C.d.arc([(cx - 38 * hs) * SS, (cy + 14 * hs) * SS, (cx + 38 * hs) * SS, (cy + 52 * hs) * SS], 10, 170, fill=T, width=int(4 * hs * SS))
    for j in range(6):
        x = cx - 25 * hs + j * 10 * hs
        C.line([(x, cy + 44 * hs), (x, cy + 50 * hs)], (215, 215, 205), 3 * hs)                                # dientes
    C.rect(cx - 104 * hs, cy - 66 * hs, cx + 104 * hs, cy - 50 * hs, (54, 40, 30), r=8 * hs)                  # sombrero
    C.rect(cx - 64 * hs, cy - 138 * hs, cx + 64 * hs, cy - 58 * hs, (66, 50, 38), r=18 * hs)
    C.rect(cx - 64 * hs, cy - 82 * hs, cx + 64 * hs, cy - 68 * hs, (28, 20, 16), ol=None)
    for sd in (-1, 1):
        C.line([(cx + sd * 52 * hs, cy - 50 * hs), (cx + sd * 58 * hs, cy + 30 * hs)], (40, 42, 48), 5 * s)      # pelo mojado
    capas.append(C.fin(d=8, rim=(120, 200, 255), rim_a=0.55))
    out = juntar(w, h, capas[:-1] if sin_cabeza else capas)
    halo = out.filter(ImageFilter.GaussianBlur(alto / 35))
    halo = Image.merge('RGBA', (*Image.new('RGB', out.size, (110, 190, 255)).split(), halo.getchannel('A').point(lambda v: v * 2 // 5)))
    fin = Image.new('RGBA', out.size, (0, 0, 0, 0))
    fin.alpha_composite(halo)
    fin.alpha_composite(out)
    return fin


def grad(w, h, a, b):
    t = np.linspace(0, 1, h)
    arr = np.array(a)[None, :] * (1 - t[:, None]) + np.array(b)[None, :] * t[:, None]
    return Image.fromarray(arr[:, None, :].astype(np.uint8).repeat(w, 1))


if __name__ == '__main__':
    W, H = 1080, 1350
    im = grad(W, H, (34, 30, 52), (12, 10, 20)).convert('RGBA')
    d = ImageDraw.Draw(im)
    d.text((W / 2, 64), 'EL ÚLTIMO CLIENTE', font=fnt(70), fill=(245, 220, 120), anchor='mm', stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((W / 2, 124), 'personajes v2 · se mueven, parpadean y hablan', font=fnt(28), fill=(200, 200, 215), anchor='mm')
    b = don_beto(760, 'normal')
    c = cliente(760)
    im.alpha_composite(b, (30, 190))
    im.alpha_composite(c, (W - c.width - 30, 190))
    caras = [don_beto(700, 'cansado'), don_beto(700, 'miedo', pose='miedo')]
    for j, cb in enumerate(caras):
        cab = cb.crop((cb.width // 2 - 150, 40, cb.width // 2 + 150, 300))
        im.alpha_composite(cab, (20 + j * 300, 1010))
    cc = cliente(700)
    cab = cc.crop((cc.width // 2 - 150, 40, cc.width // 2 + 150, 300))
    im.alpha_composite(cab, (W - 340, 1010))
    for txt, x, y in (('DON BETO', 30 + b.width // 2, 965), ('EL CLIENTE', W - 30 - c.width // 2, 965),
                      ('cansado', 170, 1300), ('con miedo', 470, 1300), ('su sonrisa', W - 190, 1300)):
        d.text((x, y), txt, font=fnt(40 if y < 1000 else 30), fill=(255, 255, 255), anchor='mm', stroke_width=3, stroke_fill=(0, 0, 0))
    im.convert('RGB').save(OUT + 'personajes_v2.jpg', quality=92)
    print('ok')
