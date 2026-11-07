"""Canal de terror, estilo POV (primera persona): "No contestes". 16 tomas sincronizadas con la voz (material del servidor).
Uso: python3 tools/no_contestes.py <material/FECHA/nc1> <salida>   (PRUEBA=1 → hoja con un cuadro de cada toma)"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP)
import montaje, dibujos, terror  # noqa: E401,E402
from kit import calle2  # noqa: E402

MAT, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
FUENTE = os.path.join(os.path.dirname(APP), 'assets', 'InterDisplay-Black.otf')
rnd = random.Random(9)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def ease(x):
    x = max(0.0, min(1.0, x))
    return (1 - math.cos(math.pi * x)) / 2


def fnt(n):
    return ImageFont.truetype(FUENTE, n)


def linterna(im, cx, cy, r=560, amb=0.08, on=1.0, tinte=(1.0, 0.97, 0.88)):
    arr = np.asarray(im.convert('RGB')).astype(np.float32)
    r2 = ((xx - cx) ** 2 + ((yy - cy) * 0.8) ** 2) / (r * r)
    luz = amb + 1.25 * np.clip(1.25 - r2, 0, 1) ** 1.6 * on
    return Image.fromarray(np.clip(arr * luz[..., None] * np.array(tinte, np.float32), 0, 255).astype(np.uint8))


def oscurecer(im, k):
    return Image.blend(im.convert('RGB'), Image.new('RGB', (W, H)), k)


def glow(im, x, y, r, col, a):
    g = Image.new('RGB', (W, H))
    ImageDraw.Draw(g).ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * a) for c in col))
    return ImageChops.add(im.convert('RGB'), g.filter(ImageFilter.GaussianBlur(r / 2.5)))


def mano_camara(t):                                   # caminar: balanceo de cámara
    return 14 * math.sin(t * 2 * math.pi * 0.9), 10 * abs(math.sin(t * 2 * math.pi * 0.9))


# ---------------------------------------------------------------- PASILLO (perspectiva)
FOCO = 760


def proy(x, y, z, cam):
    dz = max(0.05, z - cam[2])
    return (W / 2 + FOCO * (x - cam[0]) / dz, H * 0.46 + FOCO * (y - cam[1]) / dz)


def niebla(col, z, cz, k=0.17):
    f = math.exp(-max(0, z - cz) * k)
    return tuple(int(c * f) for c in col)


def pasillo(t, cz, puerta_der=0.0, luz_fondo=(40, 46, 60)):
    cam = (0.03 * math.sin(t * 2.1), 0.035 * math.sin(t * 2 * math.pi * 0.9), cz)
    im = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(im)
    for z in np.arange(12, cz + 0.2, -0.5):
        z0, z1 = z, max(z - 0.5, cz + 0.15)
        d.polygon([proy(-1, 1.2, z0, cam), proy(1, 1.2, z0, cam), proy(1, 1.2, z1, cam), proy(-1, 1.2, z1, cam)],
                  fill=niebla((88, 68, 50) if int(z * 2) % 2 else (80, 62, 46), z, cz))
        d.polygon([proy(-1, -1, z0, cam), proy(1, -1, z0, cam), proy(1, -1, z1, cam), proy(-1, -1, z1, cam)], fill=niebla((66, 62, 58), z, cz))
        for lado, col in ((-1, (112, 100, 82)), (1, (104, 94, 78))):          # paredes de madera/caña
            d.polygon([proy(lado, -1, z0, cam), proy(lado, 1.2, z0, cam), proy(lado, 1.2, z1, cam), proy(lado, -1, z1, cam)],
                      fill=niebla(col, z, cz))
            for k in range(4):
                zz = z0 - k * 0.125
                d.line([proy(lado, -1, zz, cam), proy(lado, 1.2, zz, cam)], fill=niebla((84, 74, 60), zz, cz), width=2)
    d.polygon([proy(-1, -1, 12, cam), proy(1, -1, 12, cam), proy(1, 1.2, 12, cam), proy(-1, 1.2, 12, cam)], fill=niebla((92, 84, 70), 12, cz))
    d.polygon([proy(-0.4, -0.3, 12, cam), proy(0.4, -0.3, 12, cam), proy(0.4, 1.2, 12, cam), proy(-0.4, 1.2, 12, cam)], fill=luz_fondo)
    za, zb = 8.0, 9.1                                      # puerta del cuarto de la mamá (derecha)
    d.polygon([proy(1, -0.35, za, cam), proy(1, 1.2, za, cam), proy(1, 1.2, zb, cam), proy(1, -0.35, zb, cam)],
              fill=(20, 22, 30) if puerta_der > 0 else niebla((80, 56, 40), za, cz))
    if puerta_der > 0:
        ab = puerta_der * 1.2
        xe, ze = 1 + math.sin(ab) * 1.1, za + math.cos(ab) * 1.1
        d.polygon([proy(1, -0.35, za, cam), proy(1, 1.2, za, cam), proy(xe, 1.2, ze, cam), proy(xe, -0.35, ze, cam)],
                  fill=niebla((84, 58, 40), za, cz))
    return im, cam


# ---------------------------------------------------------------- AFUERA: árboles que se mecen, neblina, casa de campo
print('pintando árboles...')


def sprite_arbol(alto, semilla):
    random.seed(semilla)
    calle2.rnd.seed(semilla)
    lienzo = Image.new('RGBA', (int(alto * 1.0), int(alto * 1.05)), (0, 0, 0, 0))
    calle2.arbol(lienzo, lienzo.width / 2, lienzo.height - 2, alto, oscuro=(8, 16, 14), medio=(18, 34, 30), claro=(46, 70, 70))
    return lienzo


ARBOLES = [sprite_arbol(900, s) for s in (1, 2, 3)]
NIEBLA = terror._niebla(W, H, 4, 110, (150, 160, 176))
NIEBLA2 = terror._niebla(W, H, 5, 80, (150, 160, 176))
CIELO, (LX, LY, LR) = terror._cielo_noche(W, H, random.Random(3), luna=(0.78, 0.1))


def mecer(sp, t, fase):
    a = 2.2 * math.sin(t * 1.3 + fase) + 1.0 * math.sin(t * 3.1 + fase)
    return sp.rotate(a, resample=Image.BICUBIC, center=(sp.width / 2, sp.height))


def afuera(t, z=1.0, foco=(0.5, 0.5)):
    im = CIELO.copy()
    d = ImageDraw.Draw(im)
    d.polygon([(0, H * 0.52)] + [(x, H * 0.5 - 60 * math.sin(x / 300)) for x in range(0, W + 40, 40)] + [(W, H * 0.52), (W, H), (0, H)],
              fill=(14, 20, 20))
    for j, (x, esc) in enumerate([(120, 0.9), (930, 1.0), (520, 0.6)]):
        sp = mecer(ARBOLES[j], t, j * 1.7)
        sp = sp.resize((int(sp.width * esc), int(sp.height * esc)))
        im.alpha_composite(sp, (int(x - sp.width / 2), int(H * 0.62 - sp.height)))
    d.rectangle([0, int(H * 0.62), W, H], fill=(12, 18, 16))
    for x in range(0, W, 140):                                 # cerca de palos
        d.line([(x, H * 0.62), (x + 4, H * 0.56)], fill=(26, 24, 20), width=8)
    d.line([(0, H * 0.585), (W, H * 0.585)], fill=(26, 24, 20), width=3)
    x = int((t * 30) % W)
    im.alpha_composite(NIEBLA.crop((x, 0, x + W, H)), (0, int(H * 0.18)))
    if z != 1.0:
        cw, ch = W / z, H / z
        cx, cy = W * foco[0], H * foco[1]
        im = im.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.BICUBIC)
    return im


def casa_campo(t):
    """Casa de caña sobre pilotes (típica del campo manabita), una ventana prendida, árboles y neblina."""
    im = afuera(t)
    d = ImageDraw.Draw(im)
    x0, x1, y0, y1 = 250, 830, 760, 1080
    for x in range(x0 + 20, x1, 110):
        d.rectangle([x, y1, x + 18, y1 + 160], fill=(40, 30, 22))           # pilotes
    d.rectangle([x0, y0, x1, y1], fill=(96, 76, 52))
    for x in range(x0, x1, 12):
        d.line([(x, y0), (x, y1)], fill=(80, 62, 42), width=3)               # caña picada
    d.polygon([(x0 - 60, y0 + 10), (540, y0 - 170), (x1 + 60, y0 + 10)], fill=(60, 56, 54))   # techo de zinc
    for x in range(x0 - 40, x1 + 50, 26):
        d.line([(x, y0 + 6), (540 + (x - 540) * 0.1, y0 - 160)], fill=(48, 46, 44), width=2)
    d.rectangle([600, 860, 700, 960], fill=(230, 170, 80))                   # ventana prendida
    d.line([(650, 860), (650, 960)], fill=(40, 30, 20), width=6)
    d.rectangle([340, 880, 440, 1080], fill=(40, 30, 22))                    # puerta
    d.polygon([(330, y1 + 160), (380, y1), (420, y1), (470, y1 + 160)], fill=(50, 40, 30))   # escalera
    im = glow(im, 650, 910, 160, (255, 180, 90), 0.5).convert('RGBA')
    x = int((t * 45) % W)
    im.alpha_composite(NIEBLA2.crop((x, 0, x + W, H)), (0, int(H * 0.33)))
    return im


# ---------------------------------------------------------------- SALA
def sala(t, abuela=0.0, ventana_luz=1.0, vela=True):
    im = calle2.grad(W, H, (34, 30, 30), (16, 14, 14)).convert('RGBA')
    d = ImageDraw.Draw(im)
    for x in range(0, W, 14):
        d.line([(x, 0), (x, H * 0.72)], fill=(30, 26, 26), width=2)
    vx0, vy0, vx1, vy1 = 600, 420, 1000, 1000                                 # ventana
    d.rectangle([vx0, vy0, vx1, vy1], fill=(int(40 * ventana_luz), int(56 * ventana_luz), int(86 * ventana_luz)))
    for j in range(1, 5):
        d.line([(vx0 + j * (vx1 - vx0) / 5, vy0), (vx0 + j * (vx1 - vx0) / 5, vy1)], fill=(18, 16, 16), width=8)
    d.rectangle([vx0 - 20, vy0 - 20, vx1 + 20, vy0], fill=(44, 34, 26))
    sw = 18 * math.sin(t * 0.9)                                                # cortina que se mueve
    d.polygon([(vx0 - 10, vy0), (vx0 + 90 + sw, vy0), (vx0 + 60 + sw * 1.5, vy1 + 40), (vx0 - 10, vy1 + 40)], fill=(70, 40, 36))
    d.rectangle([0, int(H * 0.72), W, H], fill=(30, 24, 20))
    d.rounded_rectangle([40, 1180, 560, 1460], radius=40, fill=(46, 36, 34))   # sofá
    d.rounded_rectangle([60, 1080, 540, 1220], radius=40, fill=(54, 42, 38))
    d.rectangle([660, 1300, 900, 1330], fill=(50, 38, 28))                     # mesa con vela
    d.rectangle([700, 1330, 716, 1480], fill=(40, 30, 22)); d.rectangle([844, 1330, 860, 1480], fill=(40, 30, 22))
    if vela:
        d.rectangle([770, 1230, 790, 1300], fill=(220, 210, 190))
        fl = 1 + 0.15 * math.sin(t * 17) + 0.08 * math.sin(t * 31)
        d.ellipse([772, 1200 - 10 * fl, 788, 1232], fill=(255, 200, 100))
    if abuela > 0:                                                             # la abuela sentada a tu lado
        a = int(255 * abuela)
        ab = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        da = ImageDraw.Draw(ab)
        da.polygon([(60, H), (110, 1150), (330, 1100), (420, 1230), (440, H)], fill=(24, 22, 26, a))             # rebozo
        da.ellipse([150, 860, 330, 1080], fill=(150, 120, 98, a))                                              # cara
        da.ellipse([140, 830, 340, 960], fill=(196, 192, 186, a))                                              # pelo canoso
        da.ellipse([190, 790, 270, 860], fill=(196, 192, 186, a))                                              # moño
        for sd in (-1, 1):
            da.ellipse([240 + sd * 34 - 10, 980, 240 + sd * 34 + 10, 992], fill=(30, 20, 18, a))
        for j in range(4):
            da.arc([180, 1000 + j * 12, 300, 1040 + j * 12], 20, 160, fill=(110, 84, 66, a), width=3)          # arrugas
        da.line([(222, 1046), (262, 1046 + 6 * math.sin(t * 9))], fill=(60, 30, 26, a), width=5)              # boca que habla
        im.alpha_composite(ab)
    im = glow(im, 780, 1220, 260, (255, 170, 80), 0.55 if vela else 0)
    im = glow(im, 800, 700, 340, (90, 120, 180), 0.25 * ventana_luz)
    return im


def ventana(t, mujer=0.0, escala=1.0, giro=0.0, linterna_on=False):
    """Mirando por la ventana con rejas: afuera los árboles se mecen; la mujer alta de espaldas entre la neblina."""
    im = afuera(t, 1.0 + 0.3 * escala - 0.3, (0.5, 0.5)).convert('RGBA')
    if mujer > 0:
        alto = int(1100 * escala)
        sp = terror.llorona(t, alto, cara=giro > 0.7, alfa=mujer)
        if giro > 0:                                                          # la cabeza gira sin mover el cuerpo
            d = ImageDraw.Draw(sp)
            cx = sp.width / 2
            k = alto / 600
            cab = sp.height - alto * 1.0 + 70 * k
            if giro > 0.35:
                d.ellipse([cx + 10 * k * giro, cab - 30 * k, cx + 46 * k * giro, cab + 40 * k], fill=(200, 205, 210, 240))   # mejilla pálida
            if giro > 0.75:
                for sd in (-1, 1):
                    d.ellipse([cx + sd * 16 * k - 9 * k, cab - 14 * k, cx + sd * 16 * k + 9 * k, cab + 4 * k], fill=(0, 0, 0, 255))
                d.ellipse([cx - 12 * k, cab + 16 * k, cx + 12 * k, cab + 48 * k], fill=(0, 0, 0, 255))
        im.alpha_composite(sp, (int(W * 0.5 - sp.width / 2), int(H * 0.64 - sp.height)))
    d = ImageDraw.Draw(im)
    for j in range(1, 6):                                                     # rejas y marco de la ventana
        d.line([(j * W / 6, 0), (j * W / 6, H)], fill=(10, 8, 8), width=16)
    d.rectangle([0, 0, W, 60], fill=(30, 22, 18)); d.rectangle([0, H - 220, W, H], fill=(30, 22, 18))
    if linterna_on:
        im = linterna(im, W / 2 + 30 * math.sin(t * 2), H * 0.45 + 20 * math.sin(t * 3), 620, 0.3, on=0.6)
        im = glow(im, W / 2 - 120, H * 0.35, 90, (255, 255, 240), 0.35)      # reflejo en el vidrio
    return im


def cama(t):
    im = calle2.grad(W, H, (26, 30, 44), (10, 10, 16)).convert('RGBA')
    d = ImageDraw.Draw(im)
    d.rectangle([700, 300, 980, 760], fill=(44, 60, 92))                      # ventanita con luz de luna
    d.rectangle([0, 1100, W, H], fill=(24, 22, 26))
    d.rounded_rectangle([60, 1000, 1020, 1560], radius=30, fill=(50, 44, 56))   # cama
    resp = 14 * math.sin(t * 2 * math.pi * 0.25)
    d.ellipse([140, 880 - resp, 900, 1240 - resp], fill=(86, 78, 96))          # cobija que sube y baja
    d.ellipse([120, 860, 330, 1000], fill=(150, 116, 94))                       # cabeza dormida
    d.ellipse([110, 840, 320, 940], fill=(20, 16, 16))                          # pelo
    im = glow(im, 840, 530, 400, (90, 120, 180), 0.35)
    return linterna(im, W / 2 + 30 * math.sin(t), H * 0.55, 700, 0.18)


def gateando(im, q, cam):
    """La cosa que se arrastra en cuatro patas por el pasillo (se acerca a saltos)."""
    z = 11.5 - 8.5 * q
    base = proy(0, 1.2, z, cam)
    k = FOCO / max(0.3, z - cam[2]) / 600
    d = ImageDraw.Draw(im)
    x, y = base
    sh = 30 * k * math.sin(q * 40)
    d.ellipse([x - 160 * k, y - 300 * k + sh, x + 160 * k, y - 150 * k + sh], fill=(8, 8, 10))            # torso
    for sd in (-1, 1):
        d.line([(x + sd * 120 * k, y - 230 * k), (x + sd * 260 * k, y - 360 * k), (x + sd * 230 * k, y)], fill=(8, 8, 10), width=max(2, int(34 * k)))
        d.line([(x + sd * 80 * k, y - 200 * k), (x + sd * 150 * k, y - 420 * k), (x + sd * 180 * k, y)], fill=(8, 8, 10), width=max(2, int(30 * k)))
    d.ellipse([x - 70 * k, y - 300 * k, x + 70 * k, y - 160 * k], fill=(150, 152, 150))                   # cara pálida, mirando hacia arriba
    for sd in (-1, 1):
        d.ellipse([x + sd * 26 * k - 12 * k, y - 250 * k, x + sd * 26 * k + 12 * k, y - 226 * k], fill=(0, 0, 0))
    for j in range(14):
        xx_ = x - 90 * k + j * 13 * k
        d.line([(xx_, y - 300 * k), (xx_ + 4 * k, y - 60 * k)], fill=(6, 6, 8), width=max(1, int(6 * k)))
    return im


def mano_abuela(im, q):
    d = ImageDraw.Draw(im)
    x = -300 + 520 * min(1, q * 3)
    y = 1250
    d.rounded_rectangle([x - 420, y - 60, x + 40, y + 70], radius=50, fill=(24, 22, 26))                  # manga del rebozo
    d.ellipse([x - 10, y - 80, x + 170, y + 90], fill=(150, 118, 96))
    for j in range(4):
        d.line([(x + 150, y - 60 + j * 40), (x + 260, y - 40 + j * 44)], fill=(150, 118, 96), width=34)
        d.line([(x + 200, y - 52 + j * 42), (x + 230, y - 44 + j * 42)], fill=(110, 84, 66), width=3)
    d.line([(x + 60, y - 70), (x + 200, y - 110)], fill=(150, 118, 96), width=40)                          # pulgar
    return im


def altar(t):
    im = calle2.grad(W, H, (196, 170, 130), (120, 96, 70)).convert('RGBA')   # luz de la mañana
    d = ImageDraw.Draw(im)
    d.rectangle([0, 1320, W, H], fill=(90, 66, 46))
    d.rectangle([240, 560, 840, 1240], fill=(70, 50, 34))                        # marco
    d.rectangle([280, 600, 800, 1200], fill=(150, 146, 136))
    d.ellipse([400, 700, 680, 1020], fill=(120, 116, 108))                       # foto de la abuela (sepia)
    d.ellipse([380, 650, 700, 860], fill=(210, 206, 196)); d.ellipse([480, 610, 600, 700], fill=(210, 206, 196))
    for sd in (-1, 1):
        d.ellipse([540 + sd * 50 - 14, 860, 540 + sd * 50 + 14, 878], fill=(40, 36, 32))
    for j in range(3):
        d.arc([460, 900 + j * 14, 620, 950 + j * 14], 20, 160, fill=(90, 86, 80), width=3)
    d.polygon([(280, 1200), (800, 1200), (800, 1240), (280, 1240)], fill=(70, 50, 34))
    d.polygon([(600, 560), (840, 560), (840, 800)], fill=(10, 10, 10))           # cinta negra de luto
    for x in (180, 900):                                                         # velas
        d.rectangle([x - 18, 1150, x + 18, 1320], fill=(236, 230, 214))
        d.ellipse([x - 9, 1110 + 4 * math.sin(t * 13 + x), x + 9, 1152], fill=(255, 190, 90))
    d.rectangle([150, 1320, 930, 1340], fill=(60, 44, 30))
    for j in range(7):                                                           # flores
        x = 300 + j * 80
        d.line([(x, 1320), (x + 10, 1260)], fill=(50, 90, 40), width=5)
        d.ellipse([x - 4, 1236, x + 26, 1266], fill=(240, 160, 40))
    im = glow(im, 180, 1130, 120, (255, 180, 90), 0.5)
    return glow(im, 900, 1130, 120, (255, 180, 90), 0.5)


def celular(t, llamada=False):
    im = Image.new('RGB', (W, H), (6, 6, 8))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 1300, W, H], fill=(20, 16, 14))
    vib = 6 * math.sin(t * 60) if llamada and int(t * 2) % 2 == 0 else 0
    x0, y0 = 300 + vib, 620
    d.rounded_rectangle([x0, y0, x0 + 480, y0 + 960], radius=60, fill=(20, 20, 24))
    d.rounded_rectangle([x0 + 20, y0 + 20, x0 + 460, y0 + 940], radius=44, fill=(30, 40, 60) if llamada else (14, 16, 22))
    d.text((x0 + 240, y0 + 210), '3:17', font=fnt(120), fill=(235, 238, 245), anchor='mm')
    if llamada:
        d.text((x0 + 240, y0 + 420), 'MAMÁ', font=fnt(64), fill=(255, 255, 255), anchor='mm')
        d.text((x0 + 240, y0 + 490), 'llamada entrante', font=fnt(30), fill=(190, 200, 220), anchor='mm')
        d.ellipse([x0 + 80, y0 + 760, x0 + 180, y0 + 860], fill=(220, 50, 50))
        d.ellipse([x0 + 300, y0 + 760, x0 + 400, y0 + 860], fill=(50, 190, 80))
    return glow(im, x0 + 240, y0 + 480, 420, (90, 120, 200), 0.6 if llamada else 0.2)


def parpados(im, q):
    """Despertar: los párpados se abren (barras negras) y la imagen se enfoca."""
    a = ease(q)
    im = im.filter(ImageFilter.GaussianBlur(14 * (1 - a)))
    d = ImageDraw.Draw(im)
    h = int(H / 2 * (1 - a))
    d.rectangle([0, 0, W, h], fill=(0, 0, 0)); d.rectangle([0, H - h, W, H], fill=(0, 0, 0))
    return im


# ---------------------------------------------------------------- voz
info = json.load(open(os.path.join(MAT, 'info.json')))
segs = info['segmentos']
VEL = 0.93
for s_ in segs:
    s_['t0'] /= VEL
info['palabras'] = [[a_ / VEL, b_ / VEL, {'árbones.': 'árboles.', 'árbones': 'árboles'}.get(w_, w_)] for a_, b_, w_ in info['palabras']]
dur_voz = info['duracion_voz'] / VEL
CORTE = segs[15]['t0'] + 0.0
# voz natural: solo un poco mas lenta (sin cambiar el tono), un poco mas de cuerpo y un eco de cuarto suave
fv = (f"[0:a]aresample=48000,atempo={VEL:.4f},bass=g=3:f=120,"
      f"aecho=0.8:0.6:45|95:0.18|0.09,volume=1.0[o]")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(MAT, 'voz.flac'), '-filter_complex', fv, '-map', '[o]', '-ac', '1',
                f'{OUT}/voz.wav'], check=True)
raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', f'{OUT}/voz.wav', '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'])
COLA = 2.6
TOTAL = dur_voz + COLA
t0s = [s['t0'] for s in segs] + [TOTAL]


# ---------------------------------------------------------------- tomas
def T00(t, d, T0):
    im, cam = pasillo(t, 0.15 * t)
    return linterna(im, W / 2 + 40 * math.sin(t * 2.7), H * 0.47 + 25 * math.sin(t * 2.1))


def T01(t, d, T0):
    im = casa_campo(T0 + t)
    z = 1.0 + 0.14 * ease(t / d)
    bx, by = mano_camara(t)
    cw, ch = W / z, H / z
    return im.convert('RGB').crop((int((W - cw) / 2 + bx), int((H - ch) / 2 + by), int((W + cw) / 2 + bx), int((H + ch) / 2 + by))).resize((W, H))


def T02(t, d, T0):
    return sala(T0 + t)


def T03(t, d, T0):
    return sala(T0 + t, abuela=min(1, t / 0.8))


def T04(t, d, T0):
    base = sala(T0 + t, vela=False, ventana_luz=0.8)
    base = oscurecer(base, 0.35)
    im = parpados(base, t / 1.8)
    if t > d * 0.55:
        return celular(t)
    return im


def T05(t, d, T0):
    return ventana(T0 + t, 0.0, 1.0)


def T06(t, d, T0):
    return ventana(T0 + t, min(1, t / 1.0), 0.5, linterna_on=True)


def T07(t, d, T0):
    return ventana(T0 + t, 1.0, 0.55 + 0.25 * ease(t / d), linterna_on=True)


def T08(t, d, T0):
    return ventana(T0 + t, 1.0, 0.82 + 0.06 * ease(t / d), giro=ease((t - d * 0.35) / (d * 0.6)), linterna_on=True)


def T09(t, d, T0):
    im, cam = pasillo(t, 0.5 * t, puerta_der=min(1, 0.3 + t / d))
    bx, by = mano_camara(t)
    return linterna(im, W / 2 + bx * 2, H * 0.47 + by)


def T10(t, d, T0):
    return cama(T0 + t)


def T11(t, d, T0):
    im, cam = pasillo(t, 1.0, luz_fondo=(10, 10, 14))
    im = linterna(im, W / 2 + 20 * math.sin(t * 2), H * 0.47, 600, 0.06)
    if t > d * 0.6:                                         # dos ojos al fondo
        im = glow(im, W / 2 - 18, H * 0.43, 10, (220, 230, 255), 0.9)
        im = glow(im, W / 2 + 18, H * 0.43, 10, (220, 230, 255), 0.9)
    return im


def T12(t, d, T0):
    im, cam = pasillo(t, 1.0, luz_fondo=(10, 10, 14))
    q = (int(t * 2.2) / (d * 2.2))                          # se acerca a saltos
    im = gateando(im, min(1, q), cam)
    on = 0.05 if (int(t * 13) % 3 == 0 or t > d * 0.85) else 1.0
    return linterna(im, W / 2 + 30 * math.sin(t * 9), H * 0.5, 600, 0.04, on)


def T13(t, d, T0):
    if t < d * 0.45:
        im, cam = pasillo(t, 1.0, luz_fondo=(10, 10, 14))
        im = linterna(im, W / 2 - 300 * ease(t / 0.4), H * 0.5, 600, 0.05).convert('RGBA')
        im = mano_abuela(im, t)
        ang = -8 * ease(t / 0.4)
        return im.rotate(ang, resample=Image.BICUBIC).convert('RGB')
    q = (t - d * 0.45) / (d * 0.55)                         # cuarto oscuro, puerta que se cierra
    im = Image.new('RGB', (W, H), (4, 4, 6))
    dd = ImageDraw.Draw(im)
    ancho = int(300 * (1 - ease(q * 3)))
    dd.rectangle([W / 2 - ancho / 2, 400, W / 2 + ancho / 2, 1500], fill=(30, 30, 40))
    return im


def T14(t, d, T0):
    im = altar(T0 + t)
    z = 1.0 + 0.25 * ease(t / d)
    cw, ch = W / z, H / z
    return im.convert('RGB').crop((int((W - cw) / 2), int((H - ch) / 2 - 80 * (z - 1)), int((W + cw) / 2), int((H + ch) / 2 - 80 * (z - 1)))).resize((W, H))


def T15(t, d, T0):
    return celular(T0 + t, llamada=True)


TOMAS = [T00, T01, T02, T03, T04, T05, T06, T07, T08, T09, T10, T11, T12, T13, T14, T15]
SUSTO = terror._susto(W, H, 2)[0]
T_SUSTO = dur_voz + 0.25
VIG = (1 - 0.5 * np.clip(((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1))[..., None]
GR = [np.random.default_rng(i).normal(0, 7, (H, W, 1)).astype(np.float32) for i in range(6)]


def acabado(im, i):
    arr = np.asarray(im.convert('RGB')).astype(np.float32)
    arr[..., 0] = np.roll(arr[..., 0], 2, axis=1); arr[..., 2] = np.roll(arr[..., 2], -2, axis=1)
    arr = arr * VIG + GR[i % 6]
    return np.clip(arr, 0, 255).astype(np.uint8).tobytes()


def cuadro(t):
    if t >= T_SUSTO:
        return SUSTO(t - T_SUSTO + 0.2).convert('RGB')
    k = max(j for j in range(len(TOMAS)) if t0s[j] <= t + 1e-6)
    d = t0s[k + 1] - t0s[k]
    ti = t - t0s[k]
    im = TOMAS[k](ti, d, t0s[k]).convert('RGB')
    if ti < 0.3 and k > 0:
        im = Image.blend(Image.new('RGB', (W, H)), im, ti / 0.3)
    return im


if os.environ.get('PRUEBA'):
    hoja = Image.new('RGB', (W // 4 * 6, H // 4 * 3))
    for k_ in range(len(TOMAS) + 1):
        t_ = (t0s[k_] + t0s[k_ + 1]) / 2 if k_ < len(TOMAS) else T_SUSTO + 0.6
        fr = Image.frombytes('RGB', (W, H), acabado(cuadro(t_), 0))
        hoja.paste(fr.resize((W // 4, H // 4)), ((k_ % 6) * W // 4, (k_ // 6) * H // 4))
    hoja.save(f'{OUT}/prueba.jpg', quality=85)
    sys.exit()

p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', f'{OUT}/cuerpo.mp4'], stdin=subprocess.PIPE)
for i in range(int(TOTAL * FPS)):
    p.stdin.write(acabado(cuadro(i / FPS), i))
    if i % 300 == 0:
        print(f'{i / FPS:.0f}/{TOTAL:.0f}s', flush=True)
p.stdin.close(); p.wait()

# ---------------------------------------------------------------- sonido: la voz manda; ambiente y efectos bajitos
S = montaje.SFX
ev = []
fa = [f"[0:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={TOTAL:.2f},volume=1.0[v]",
      f"[1:a]atrim=0:{TOTAL:.2f},volume=0.07,afade=t=in:d=2,afade=t=out:st={TOTAL - 2:.2f}:d=2[m]",
      f"anoisesrc=color=brown:a=0.4:r=48000:d={TOTAL:.2f},lowpass=f=300,volume=0.12,aformat=channel_layouts=stereo[viento]"]
lab = ['[v]', '[m]', '[viento]']
k = 0
for seg, dur in ((0, None), (9, None)):                                            # pasos al caminar por el pasillo
    a, b = t0s[seg], t0s[seg + 1]
    for j in range(int((b - a) / 0.65)):
        tt = a + 0.3 + j * 0.65
        fa.append(f"anoisesrc=color=brown:a=0.7:r=48000:d=0.16,lowpass=f=240,afade=t=out:st=0.03:d=0.13,volume=0.35,"
                  f"adelay={int(tt * 1000)}|{int(tt * 1000)},aformat=channel_layouts=stereo[p{k}]")
        lab.append(f'[p{k}]'); k += 1
tc = t0s[9] + (t0s[10] - t0s[9]) * 0.5                                              # puerta que cruje
fa.append(f"sine=f=200:r=48000:d=1.6,vibrato=f=8:d=0.9,afade=t=in:d=0.4,afade=t=out:st=1.0:d=0.6,volume=0.05,"
          f"adelay={int(tc * 1000)}|{int(tc * 1000)},aformat=channel_layouts=stereo[cr]")
lab.append('[cr]')
tz = t0s[12]                                                                         # zumbido de la linterna que falla
fa.append(f"sine=f=120:r=48000:d={t0s[13] - tz:.2f},tremolo=f=13:d=1,volume=0.04,adelay={int(tz * 1000)}|{int(tz * 1000)},"
          f"aformat=channel_layouts=stereo[zz]")
lab.append('[zz]')
ins = ['-i', f'{OUT}/voz.wav', '-stream_loop', '-1', '-i', montaje.MUSICA, '-stream_loop', '-1', '-i', os.path.join(S, 'heart_slow.mp3'),
       '-i', os.path.join(S, 'golpe_terror.mp3'), '-i', os.path.join(S, 'susp_impact.mp3'), '-i', os.path.join(S, 'riser2.mp3')]
tl = t0s[11]
fa.append(f"[2:a]atrim=0:{t0s[13] - tl:.2f},volume=0.35,adelay={int(tl * 1000)}|{int(tl * 1000)}[lat]")
fa.append(f"[3:a]volume=0.75,adelay={int(T_SUSTO * 1000)}|{int(T_SUSTO * 1000)}[g1]")
fa.append(f"[4:a]volume=0.6,adelay={int(T_SUSTO * 1000)}|{int(T_SUSTO * 1000)}[g2]")
fa.append(f"[5:a]volume=0.2,adelay={int((T_SUSTO - 1.8) * 1000)}|{int((T_SUSTO - 1.8) * 1000)}[ri]")
lab += ['[lat]', '[g1]', '[g2]', '[ri]']
# 1) efectos y musica aparte (todas las entradas con duracion fija)
fa[0] = f"anullsrc=r=48000:cl=stereo:d={TOTAL:.2f}[v]"
fa.append(''.join(lab) + f"amix=inputs={len(lab)}:normalize=0:duration=longest,apad=whole_dur={TOTAL:.2f},atrim=0:{TOTAL:.2f}[a]")
subprocess.run(['ffmpeg', '-v', 'error', '-y'] + ins + ['-filter_complex', ';'.join(fa), '-map', '[a]', '-ar', '48000', '-ac', '2',
                f'{OUT}/fx.wav'], check=True)
# 2) voz + efectos: la voz va completa hasta el final
fm = (f"[0:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={TOTAL:.2f},atrim=0:{TOTAL:.2f}[v];"
      f"[1:a]volume=0.8[f];[v][f]amix=inputs=2:normalize=0:duration=longest,atrim=0:{TOTAL:.2f},loudnorm=I=-14:TP=-1:LRA=9[a]")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/voz.wav', '-i', f'{OUT}/fx.wav', '-filter_complex', fm,
                '-map', '[a]', '-ar', '48000', '-ac', '2', f'{OUT}/mezcla.wav'], check=True)
ass = f'{OUT}/subs.ass'
montaje._ass([tuple(x) for x in info['palabras']], W, H, 'NO CONTESTES', ass, rotulos=[(a_, b_, '') for a_, b_ in zip(t0s[:-1], t0s[1:])])
_l = [l for l in open(ass) if not l.rstrip().endswith(',RIDMER')]
open(ass, 'w').write(''.join(_l))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/cuerpo.mp4', '-i', f'{OUT}/mezcla.wav', '-filter_complex',
                f"[0:v]subtitles='{ass}':fontsdir='{os.path.dirname(FUENTE)}',format=yuv420p[v]", '-map', '[v]', '-map', '1:a',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-maxrate', '7M', '-bufsize', '14M', '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart', '-t', f'{TOTAL:.3f}', f'{OUT}/No_contestes.mp4'], check=True)
print('listo', round(TOTAL, 1))
