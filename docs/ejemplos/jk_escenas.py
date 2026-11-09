"""Escenas a medida para la muestra de Juliane Koepcke (vuelo LANSA 508, 1971). Uso: python3 jk_escenas.py ESCENA salida seg W H"""
import math, random, sys
from PIL import Image, ImageDraw, ImageFilter
import plano as P

escena = sys.argv.pop(1)
sal, d, W, H = P.args()
P.lienzo(W, H)
CW, CH = P.CW, P.CH


def asiento_con_chica(u, phi, ang):
    """Fila de asientos azules con la chica atada, todo girando 'ang' grados."""
    lay = Image.new('RGBA', (int(5 * u), int(5 * u)), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    cx, cy = lay.size[0] / 2, lay.size[1] / 2
    for k in (-1, 0, 1):                                     # 3 asientos
        x = cx + k * 0.95 * u - 0.2 * u
        dd.rounded_rectangle([x - 0.42 * u, cy - 1.5 * u, x + 0.42 * u, cy + 0.2 * u], 0.18 * u, fill=(40, 70, 140, 255))
        dd.rounded_rectangle([x - 0.48 * u, cy + 0.05 * u, x + 0.5 * u, cy + 0.38 * u], 0.12 * u, fill=(34, 60, 120, 255))
    P.persona(lay, cx + 0.15 * u, cy + 1.75 * u, u * 0.95, 'mujer', 'cae', phi, rim=(150, 190, 255))
    dd.rectangle([cx - 0.2 * u, cy - 0.05 * u, cx + 0.55 * u, cy + 0.05 * u], fill=(30, 30, 34, 255))   # cinturón
    return lay.rotate(ang, resample=Image.BICUBIC)


# ------------------------------------------------------------------ 1) APERTURA: cae entre las nubes
def apertura():
    cielo = P.cielo_tormenta(CW)

    def cuadro(t):
        img = cielo.copy()
        P.nubes(img, t, vel=0, alfa=0)
        # avión que estalla allá arriba, lejos
        P.avion(img, CW * 0.72, CH * 0.12 - t * 40, 0.35, ang=25 + t * 8, t=t, roto=True, fuego=True)
        if t < 0.25:
            img = P.destello(img, 0.9 - t * 3.2, (255, 220, 160))
        # nubes que suben rápido = caída
        capa = Image.new('RGBA', img.size, (0, 0, 0, 0))
        P.nubes(capa, t * 1.0, vel=0, alfa=150, semilla=8)
        off = int((t * 2600) % CH)
        img.alpha_composite(capa.crop((0, CH - off, CW, CH)), (0, 0)) if off else None
        img.alpha_composite(capa.crop((0, 0, CW, CH - off)), (0, off)) if off < CH else None
        P.lluvia(img, t, n=180, ang=0.0, largo=160, alfa=70)
        lay = asiento_con_chica(300, t * 4, ang=math.sin(t * 2.2) * 35 + t * 40)
        img.alpha_composite(lay, (int(CW * 0.5 - lay.size[0] / 2), int(CH * 0.5 - lay.size[1] / 2)))
        z = 1.25 - 0.15 * P.ease(t / d)
        im = P.camara(img, z, CW * 0.5, CH * 0.5, sacudir=14, t=t)
        im = P.vineta(im, 0.6)
        return P.titulo_golpe(im, 'CAYÓ DE UN AVIÓN', t, t0=0.15, y=0.2)
    P.grabar(cuadro, sal, d)


# ------------------------------------------------------------------ 2) RAYO: golpea el avión y se parte
def rayo():
    cielo = P.cielo_tormenta(CW * 2)

    def cuadro(t):
        off = int(t * 260)
        img = cielo.crop((off, 0, off + CW, CH)).copy()
        P.nubes(img, t, vel=900, alfa=110)
        golpe = d * 0.38
        roto = t > golpe + 0.15
        sep = P.ease((t - golpe - 0.15) / 0.8) if roto else 0
        ang = 6 + (30 * sep if roto else 0)
        P.avion(img, CW * 0.48 + 60 * math.sin(t), CH * 0.48 + 260 * sep, 0.9, ang=ang, t=t, roto=roto, fuego=roto)
        if golpe <= t < golpe + 0.18:
            P.rayo(img, CW * 0.52, semilla=int(t * 30), grosor=14)
        P.lluvia(img, t, n=320)
        fl = 0.85 * max(0, 1 - abs(t - golpe) / 0.12) + 0.5 * max(0, 1 - abs(t - golpe - 0.3) / 0.1)
        img = P.destello(img, fl, (235, 240, 255))
        im = P.camara(img, 1.35 + 0.1 * P.ease(t / d), CW * 0.5, CH * 0.5, sacudir=30 if t > golpe else 6, t=t)
        return P.vineta(im, 0.55)
    P.grabar(cuadro, sal, d)


# ------------------------------------------------------------------ 3) CAE hacia la selva
def copas_desde_arriba(lado):
    """Selva vista desde el aire: copas redondas de muchos verdes, con un río serpenteando."""
    im = Image.new('RGBA', (lado, lado), (34, 70, 40, 255))
    dd = ImageDraw.Draw(im)
    rnd = random.Random(5)
    for _ in range(int(lado * lado / 9000)):
        x, y, r = rnd.randint(0, lado), rnd.randint(0, lado), rnd.randint(40, 120)
        g = rnd.randint(70, 140)
        dd.ellipse([x - r, y - r, x + r, y + r], fill=(int(g * 0.45), g, int(g * 0.5), 255))
        dd.ellipse([x - r * 0.5, y - r * 0.7, x + r * 0.3, y - r * 0.1], fill=(int(g * 0.6), int(g * 1.25), int(g * 0.6), 255))
    pts = [(lado * 0.1 + i * lado * 0.05, lado * 0.5 + math.sin(i * 0.6) * lado * 0.12) for i in range(20)]
    dd.line(pts, fill=(110, 140, 120, 255), width=int(lado * 0.025), joint='curve')
    return im


def cae_selva():
    lado = int(max(CW, CH) * 1.2)
    copa = copas_desde_arriba(lado)

    def cuadro(t):
        p = t / d
        z = 0.35 + 1.1 * P.ease(p) ** 1.3                    # la selva se acerca
        s_ = copa.resize((int(lado * z * 1.6), int(lado * z * 1.6)), Image.BILINEAR)
        img = Image.new('RGBA', (CW, CH), (34, 70, 40, 255))
        img.alpha_composite(s_, (int(CW / 2 - s_.size[0] / 2), int(CH / 2 - s_.size[1] / 2)))
        neb = Image.new('RGBA', img.size, (200, 210, 220, int(150 * (1 - p))))
        img.alpha_composite(neb)
        capa = Image.new('RGBA', img.size, (0, 0, 0, 0))
        P.nubes(capa, 0, vel=0, alfa=int(150 * (1 - p)), semilla=9)
        off = int((t * 2600) % CH)
        if off:
            img.alpha_composite(capa.crop((0, CH - off, CW, CH)), (0, 0))
        img.alpha_composite(capa.crop((0, 0, CW, CH - off)), (0, off))
        lay = asiento_con_chica(230, t * 5, ang=t * 160)
        img.alpha_composite(lay, (int(CW * 0.5 - lay.size[0] / 2), int(CH * 0.45 - lay.size[1] / 2)))
        im = P.camara(img, 1.1, CW * 0.5, CH * 0.5, sacudir=10, t=t)
        return P.vineta(im, 0.5)
    P.grabar(cuadro, sal, d)


# ------------------------------------------------------------------ 4) "sigue el agua": descubre el arroyo
def agua():
    base = P.selva(CW * 2)
    P.arroyo(base, int(CH * 0.8), 300)

    def cuadro(t):
        p = P.ease(t / d)
        off = int(200 + 500 * p)
        img = base.crop((off, 0, off + CW, CH)).copy()
        P.arroyo(img, int(CH * 0.8), 300, t=t)
        P.persona(img, CW * 0.3, int(CH * 0.79), 300, 'mujer', 'quieto', rim=(255, 220, 150))
        im = P.camara(img, 1.25 - 0.15 * p, CW * 0.45, CH * 0.62)
        return P.vineta(im, 0.5)
    P.grabar(cuadro, sal, d)


# ------------------------------------------------------------------ 5) camina 11 días junto al arroyo (contador de días)
def camina():
    base = P.selva(CW * 3)
    from PIL import ImageFont
    f = ImageFont.truetype(P.FUENTE, int(W * 0.08))
    f2 = ImageFont.truetype(P.FUENTE, int(W * 0.035))

    def cuadro(t):
        p = t / d
        off = int(t * 330)
        img = base.crop((off, 0, off + CW, CH)).copy()
        noche = 0.5 + 0.5 * math.sin(p * 2 * math.pi * 2.2)        # pasan días y noches
        P.arroyo(img, int(CH * 0.83), 260, t=t)
        P.persona(img, CW * 0.42, int(CH * 0.82), 280, 'mujer', 'camina', phi=t * 6.0, rim=(255, 210, 140))
        img = P.destello(img, 0.45 * (1 - noche), (10, 16, 40))
        im = P.camara(img, 1.1, CW * 0.45, CH * 0.62)
        im = P.vineta(im, 0.5)
        dd = ImageDraw.Draw(im)
        dia = min(11, 1 + int(p * 11.5))
        dd.text((W * 0.08 + 4, H * 0.24 + 4), f'DÍA {dia}', font=f, fill=(0, 0, 0))
        dd.text((W * 0.08, H * 0.24), f'DÍA {dia}', font=f, fill=(255, 255, 255))
        dd.text((W * 0.08, H * 0.24 + W * 0.1), 'SELVA AMAZÓNICA · PERÚ', font=f2, fill=(255, 210, 120))
        return im
    P.grabar(cuadro, sal, d)


# ------------------------------------------------------------------ 6) cierre: la selva desde arriba, cámara que se aleja
def cierre():
    base = P.selva(CW, noche=False)

    def cuadro(t):
        p = P.ease(t / d)
        img = base.copy()
        P.arroyo(img, int(CH * 0.82), 240, t=t)
        P.persona(img, CW * 0.55, int(CH * 0.81), 150, 'mujer', 'camina', phi=t * 5, rim=(255, 210, 150))
        im = P.camara(img, 1.6 - 0.6 * p, CW * 0.55, CH * 0.7 - 300 * p)
        return P.vineta(im, 0.6)
    P.grabar(cuadro, sal, d)


# ------------------------------------------------------------------ 0b) despegue: 24 de diciembre de 1971
def despegue():
    from PIL import ImageFont
    f = ImageFont.truetype(P.FUENTE, int(W * 0.075))
    f2 = ImageFont.truetype(P.FUENTE, int(W * 0.04))
    copa = P.selva(CW * 2, noche=False)

    def cuadro(t):
        p = t / d
        img = P.degradado(CW, CH, (40, 50, 90), (230, 150, 110)).convert('RGBA')
        piso = copa.crop((int(t * 120), 0, int(t * 120) + CW, CH)).resize((CW, int(CH * 0.35)))
        img.alpha_composite(piso, (0, int(CH * 0.68)))
        P.nubes(img, t, vel=160, alfa=70, semilla=12)
        P.avion(img, CW * (0.2 + 0.55 * p), CH * (0.5 - 0.12 * p), 0.6, ang=-6, t=t)
        im = P.camara(img, 1.08, CW * 0.5, CH * 0.5)
        im = P.vineta(im, 0.5)
        dd = ImageDraw.Draw(im)
        a = min(1.0, t / 0.4)
        y0 = H * 0.2
        for txt, ff, col, dy in (('24 DIC 1971', f, (255, 255, 255), 0), ('LIMA  →  PUCALLPA · PERÚ', f2, (255, 210, 120), W * 0.1)):
            dd.text((W / 2 + 4, y0 + dy + 4), txt, font=ff, fill=(0, 0, 0), anchor='mm')
            dd.text((W / 2, y0 + dy), txt, font=ff, fill=tuple(int(c * a) for c in col), anchor='mm')
        return im
    P.grabar(cuadro, sal, d)


{'despegue': despegue, 'apertura': apertura, 'rayo': rayo, 'cae_selva': cae_selva, 'agua': agua, 'camina': camina, 'cierre': cierre}[escena]()
