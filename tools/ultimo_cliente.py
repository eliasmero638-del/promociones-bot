"""Arma "El último cliente" (canal de terror) con el kit de dibujo: 16 tomas animadas sincronizadas con la voz.
Uso: python3 tools/ultimo_cliente.py <material/FECHA/ult1> <salida>"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance, ImageFont, ImageOps

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP)
import montaje  # noqa: E402
from kit import elenco, caras3, ambientes, calle2  # noqa: E402

MAT, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
FUENTE = os.path.join(os.path.dirname(APP), 'assets', 'InterDisplay-Black.otf')
rnd = random.Random(5)


def ease(x):
    x = max(0.0, min(1.0, x))
    return (1 - math.cos(math.pi * x)) / 2


def fnt(n):
    return ImageFont.truetype(FUENTE, n)


# ---------------------------------------------------------------- fondos (se pintan una vez)
print('pintando fondos...')
CALLE = calle2.calle(1080, 900)
TALLER = ambientes.taller(1080, 760, con_carro=False)
CARRO = ambientes.carro(900, 378)
CARRO_SIN_LUZ = ambientes.carro(900, 378, luces=False)


def a_vertical(img, zoom=1.0, fx=0.5, fy=0.5):
    """Recorta una imagen horizontal a 9:16 (escala para cubrir la altura) con zoom y encuadre."""
    s = H / img.height * zoom
    w2, h2 = img.width * s, img.height * s
    x0 = (w2 - W) * fx
    y0 = (h2 - H) * fy
    box = (x0 / s, y0 / s, (x0 + W) / s, (y0 + H) / s)
    return img.crop(tuple(int(v) for v in box)).resize((W, H), Image.BICUBIC), s, box


GOTAS = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.7, 1.3), rnd.random() < 0.3) for _ in range(380)]


def lluvia(im, t, fuerza=1.0, zona=None):
    capa = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for (x, y0, s, cerca) in GOTAS:
        if zona and not (zona[0] <= x <= zona[2]):
            continue
        L = 80 if cerca else 42
        y = (y0 + t * 2500 * s) % (H + L) - L
        if zona and not (zona[1] <= y <= zona[3]):
            continue
        d.line([(x, y), (x - 5, y + L)], fill=(205, 215, 240, int((140 if cerca else 85) * fuerza)), width=3 if cerca else 2)
    im = im.convert('RGBA')
    im.alpha_composite(capa)
    return im


def resplandor(im, x, y, r, col, a):
    g = Image.new('RGB', (W, H))
    ImageDraw.Draw(g).ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * a) for c in col))
    rgb = ImageChops.add(im.convert('RGB'), g.filter(ImageFilter.GaussianBlur(r / 2.5)))
    return rgb.convert('RGBA')


def relampago(im, t, t0, fuerza=0.7):
    q = t - t0
    if 0 <= q < 0.4:
        a = fuerza if q < 0.06 else (0.0 if q < 0.12 else fuerza * 0.7 * (1 - (q - 0.12) / 0.28))
        im = Image.blend(im.convert('RGB'), Image.new('RGB', (W, H), (210, 222, 255)), max(0, a)).convert('RGBA')
    return im


def pegar(im, sp, x, y_pie, escala=1.0, alfa=1.0):
    if escala != 1.0:
        sp = sp.resize((int(sp.width * escala), int(sp.height * escala)), Image.BICUBIC)
    if alfa < 1:
        sp = sp.copy()
        sp.putalpha(sp.getchannel('A').point(lambda v: int(v * alfa)))
    im.alpha_composite(sp, (int(x - sp.width / 2), int(y_pie - sp.height)))
    return im


def sombra_pie(im, x, y, ancho, a=170):
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).ellipse([x - ancho / 2, y - ancho * 0.08, x + ancho / 2, y + ancho * 0.08], fill=a)
    return Image.composite(Image.new('RGBA', (W, H), (0, 0, 0, 255)), im, m.filter(ImageFilter.GaussianBlur(16)))


def parpadea(t, cada=3.1, fase=0.0):
    return ((t + fase) % cada) < 0.13


def habla(t, env):
    """¿Boca abierta? según el volumen de la voz en ese momento."""
    i = int(t * 25)
    return 0 <= i < len(env) and env[i] > 0.35 and (int(t * 12) % 2 == 0)


# ---------------------------------------------------------------- voz y tiempos
info = json.load(open(os.path.join(MAT, 'info.json')))
segs = info['segmentos']
dur_voz = info['duracion_voz']
TEMPO = 0.82                                           # voz más pausada y un poco más grave (más tenebrosa)
for s_ in segs:
    s_['t0'] /= TEMPO
info['palabras'] = [[a_ / TEMPO, b_ / TEMPO, {'Revícelo': 'Revíselo'}.get(w_, w_)] for a_, b_, w_ in info['palabras']]
dur_voz /= TEMPO
CORTE = segs[15]['t0'] - 0.05                          # hueco para el susto antes del epílogo
GAP = 1.9
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(MAT, 'voz.flac'), '-filter_complex',
                f"[0:a]aresample=48000,asetrate=48000*0.94,aresample=48000,atempo={TEMPO / 0.94:.4f},asplit[x][y];"
                f"[x]atrim=0:{CORTE:.3f},asetpts=PTS-STARTPTS[a];[y]atrim={CORTE:.3f},asetpts=PTS-STARTPTS[b];"
                f"anullsrc=r=48000:cl=mono,atrim=0:{GAP}[s];[a][s][b]concat=n=3:v=0:a=1[o]", '-map', '[o]', '-ar', '48000', '-ac', '1',
                f'{OUT}/voz.wav'], check=True)
for s_ in segs[15:]:
    s_['t0'] += GAP
info['palabras'] = [[a_ + (GAP if a_ >= CORTE else 0), b_ + (GAP if a_ >= CORTE else 0), w_] for a_, b_, w_ in info['palabras']]
dur_voz += GAP
raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', f'{OUT}/voz.wav', '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'])
a = np.frombuffer(raw, np.float32)
env = np.array([np.sqrt(np.mean(a[k:k + 320] ** 2)) for k in range(0, len(a), 320)])
env = env / (np.percentile(env, 90) + 1e-6)
COLA = 3.0
TOTAL = dur_voz + COLA
t0s = [s['t0'] for s in segs] + [TOTAL]


def con_hombros(cab, quien):
    """Pone hombros (traje o overol) bajo una cabeza de primer plano para que no quede el cuello cortado."""
    w, h = cab.size
    out = Image.new('RGBA', (w, int(h * 1.25)), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    col, col2 = ((96, 64, 38), (70, 46, 26)) if quien == 'cliente' else ((44, 74, 132), (30, 52, 96))
    y0 = h * 0.86
    d.rounded_rectangle([w * 0.02, y0, w * 0.98, h * 1.25 + 40], radius=int(w * 0.18), fill=col)
    d.rounded_rectangle([w * 0.6, y0 + 10, w * 0.98, h * 1.25 + 40], radius=int(w * 0.18), fill=col2)
    if quien == 'cliente':
        d.polygon([(w * 0.4, y0 - 4), (w * 0.5, h * 1.12), (w * 0.6, y0 - 4)], fill=(222, 220, 208))
        d.polygon([(w * 0.48, y0 + 6), (w * 0.52, y0 + 6), (w * 0.53, h * 1.1), (w * 0.47, h * 1.1)], fill=(110, 18, 26))
    else:
        d.polygon([(w * 0.4, y0 - 4), (w * 0.5, y0 + h * 0.08), (w * 0.6, y0 - 4)], fill=(222, 220, 208))
    out.alpha_composite(cab)
    return out


# ---------------------------------------------------------------- tomas
def toma_00(t, d, T0):             # gancho: la cara del cliente bajo la lluvia, relámpago, ojos que brillan
    cab = con_hombros(caras3.cabeza('cliente', 'fijo', 1000, cerrados=parpadea(t, 2.6, 1.0)), 'cliente')
    im = Image.fromarray(np.array(Image.new('RGB', (W, H), (8, 12, 22)))).convert('RGBA')
    z = 1.0 + 0.12 * ease(t / d)
    c = cab.resize((int(cab.width * z), int(cab.height * z)), Image.BICUBIC)
    im.alpha_composite(c, (int(W / 2 - c.width / 2), int(H * 0.5 - c.height * 0.45)))
    im = relampago(im, t, 1.2)
    if t > d * 0.6:
        top = H * 0.5 - c.height * 0.45
        for ex in (-64, 64):
            im = resplandor(im, W / 2 + ex * 1.667 * z, top + (552 - 27) * z, 34, (200, 230, 255), 0.6 * ease((t - d * 0.6) / 0.6))
    return lluvia(im, t + T0)


def toma_01(t, d, T0):             # la calle de Montecristi, paneo hacia el taller (casa amarilla)
    im, s, box = a_vertical(CALLE, 1.0 + 0.1 * ease(t / d), 0.15 + 0.12 * ease(t / d), 0.5)
    im = im.convert('RGBA')
    im = relampago(im, t, d * 0.55, 0.5)
    return lluvia(im, t + T0)


def fondo_taller(z=1.0, fx=0.5, fy=0.6):
    im, s, box = a_vertical(TALLER, z, fx, fy)
    return im.convert('RGBA'), s, box


def a_pant(px, py, s, box):
    return (px - box[0]) * s, (py - box[1]) * s


def tubo(im, t, s, box, fuerza=1.0):
    on = 0.25 if (math.sin(t * 19) > 0.95 or 0.8 < (t % 3.7) < 0.9) else 1.0
    if on < 1:
        im = Image.blend(im.convert('RGB'), Image.new('RGB', (W, H)), 0.25).convert('RGBA')
    x, y = a_pant(540, 50, s, box)
    return resplandor(im, x, y, 300, (170, 210, 200), 0.35 * on * fuerza)


def toma_02(t, d, T0):             # Don Beto trabajando de madrugada, cansado
    im, s, box = fondo_taller(1.0, 0.4)
    x = W * 0.25 + W * 0.35 * ease(t / d)
    bob = 6 * abs(math.sin(t * 6))
    sp = elenco.personaje('beto', 'cansado', 'quieto', 1150, cerrados=parpadea(t, 2.8))
    im = sombra_pie(im, x, H * 0.93, 380)
    im = pegar(im, sp, x, H * 0.93 - bob)
    im = tubo(im, t, s, box)
    return im


def portón(t, con_cliente=0.0, luces=0.0, charco=False, escala_cli=1.0):
    """El portón abierto visto desde adentro: calle con lluvia, farol, y lo que aparezca."""
    im = Image.new('RGBA', (W, H), (48, 42, 40, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, H, 80):
        d.line([(0, y), (W, y)], fill=(42, 36, 34), width=3)
    X0, X1, Y0, Y1 = 140, 940, 380, 1500
    afuera = calle2.grad(X1 - X0, Y1 - Y0, (18, 24, 44), (30, 32, 44)).convert('RGBA')
    da = ImageDraw.Draw(afuera)
    for j in range(6):
        x = j * 150 - 30
        h_ = 300 + (j * 53) % 160
        da.rectangle([x, 800 - h_, x + 130, 800], fill=(28, 28, 38))
        da.polygon([(x - 10, 800 - h_), (x + 65, 760 - h_), (x + 140, 800 - h_)], fill=(36, 26, 26))
    da.rectangle([0, 800, X1 - X0, Y1 - Y0], fill=(22, 22, 28))
    im.alpha_composite(afuera, (X0, Y0))
    d = ImageDraw.Draw(im)
    d.rectangle([X0 - 30, Y0 - 30, X1 + 30, Y0], fill=(84, 66, 50))
    d.rectangle([X0 - 30, Y0, X0, Y1], fill=(84, 66, 50))
    d.rectangle([X1, Y0, X1 + 30, Y1], fill=(78, 62, 46))
    d.rectangle([0, Y1, W, H], fill=(40, 40, 44))
    im = resplandor(im, 760, 760, 90, (255, 220, 150), 0.7)              # farol
    if luces > 0:                                                          # faros que se acercan
        for fx in (480, 640):
            im = resplandor(im, fx, 1180, 60 + 260 * luces, (255, 240, 200), 0.5 + 0.5 * luces)
    if charco:
        d = ImageDraw.Draw(im)
        d.ellipse([360, 1420, 720, 1500], fill=(60, 66, 84))
        d.ellipse([400, 1440, 680, 1490], fill=(90, 96, 120))
    if con_cliente > 0:
        sp = elenco.personaje('cliente', 'fijo', 'quieto', 1050, cerrados=parpadea(t, 3.3, 0.5))
        sp = ImageEnhance.Brightness(sp).enhance(0.75)
        im = sombra_pie(im, 540, 1500, 320)
        im = pegar(im, sp, 540, 1500, escala_cli, con_cliente)
    return lluvia(im, t, 1.0, (X0, Y0, X1, Y1))


def toma_03(t, d, T0):             # guardando herramientas... dos luces en la lluvia
    im = portón(T0 + t, luces=ease((t - d * 0.4) / (d * 0.6)))
    sp = elenco.personaje('beto', 'miedo' if t > d * 0.6 else 'cansado', 'miedo' if t > d * 0.65 else 'quieto', 1300)
    im = pegar(im, sp, 880, H + 120)
    return im


def toma_04(t, d, T0):             # el carro rojo entra despacio
    im, s, box = fondo_taller(1.0, 0.5)
    k = ease(t / d)
    car = CARRO.resize((int(CARRO.width * s * 0.42), int(CARRO.height * s * 0.42)), Image.BICUBIC)
    x = -car.width + (W * 0.5 + car.width * 0.5) * k
    y = H * 0.9 - car.height + 4 * math.sin(t * 28)
    im = sombra_pie(im, x + car.width / 2, H * 0.9, car.width * 0.9)
    im.alpha_composite(car, (int(x), int(y)))
    im = resplandor(im, x + car.width - 20, y + car.height * 0.52, 200, (255, 236, 180), 0.6)
    return tubo(im, t, s, box)


def toma_05(t, d, T0):             # del carro bajó un hombre pálido
    return portón(T0 + t, con_cliente=min(1, t / 0.8), escala_cli=1.0 + 0.12 * ease(t / d))


def toma_06(t, d, T0):             # "Revíselo, por favor..." habla
    cab = con_hombros(caras3.cabeza('cliente', 'fijo', 1100, hablar=habla(T0 + t, env), cerrados=parpadea(t, 3.0, 0.4)), 'cliente')
    im = Image.new('RGBA', (W, H), (14, 16, 26, 255))
    im = resplandor(im, 860, 300, 260, (255, 210, 140), 0.4)
    z = 1.0 + 0.08 * ease(t / d)
    c = cab.resize((int(cab.width * z), int(cab.height * z)), Image.BICUBIC)
    im.alpha_composite(c, (int(W / 2 - c.width / 2), int(H * 0.52 - c.height * 0.45)))
    return lluvia(im, T0 + t, 0.6)


def tablero(t, d):
    im = Image.new('RGBA', (W, H), (20, 10, 10, 255))
    dd = ImageDraw.Draw(im)
    dd.rounded_rectangle([60, 520, 1020, 1500], radius=80, fill=(90, 22, 20), outline=(30, 10, 8), width=10)
    dd.rounded_rectangle([110, 600, 970, 1420], radius=60, fill=(40, 30, 28))
    cx, cy, R = 540, 1010, 300
    dd.ellipse([cx - R - 30, cy - R - 30, cx + R + 30, cy + R + 30], fill=(170, 172, 178))
    dd.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(232, 222, 196))
    for j in range(60):
        a = j / 60 * 2 * math.pi
        r1 = R * (0.84 if j % 5 else 0.76)
        dd.line([(cx + math.sin(a) * r1, cy - math.cos(a) * r1), (cx + math.sin(a) * R * 0.92, cy - math.cos(a) * R * 0.92)],
                fill=(40, 30, 26), width=6 if j % 5 == 0 else 3)
    f = fnt(54)
    for n in range(1, 13):
        a = n / 12 * 2 * math.pi
        dd.text((cx + math.sin(a) * R * 0.62, cy - math.cos(a) * R * 0.62), str(n), font=f, fill=(40, 30, 26), anchor='mm')
    ah = (3 + 17 / 60) / 12 * 2 * math.pi
    am = 17 / 60 * 2 * math.pi
    dd.line([(cx, cy), (cx + math.sin(ah) * R * 0.5, cy - math.cos(ah) * R * 0.5)], fill=(20, 16, 14), width=18)
    dd.line([(cx, cy), (cx + math.sin(am) * R * 0.8, cy - math.cos(am) * R * 0.8)], fill=(20, 16, 14), width=10)
    dd.line([(cx, cy), (cx + math.sin(am + 0.02 * math.sin(t * 40)) * R * 0.9, cy - math.cos(am) * R * 0.9)], fill=(170, 30, 30), width=4)
    dd.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=(30, 26, 24))
    dd.polygon([(cx - R * 0.7, cy - R * 0.6), (cx - R * 0.3, cy - R * 0.9), (cx - R * 0.1, cy - R * 0.85), (cx - R * 0.55, cy - R * 0.5)],
               fill=(255, 255, 255, 60))                                              # reflejo del vidrio
    dd.line([(cx - 120, cy - 260), (cx + 60, cy + 40)], fill=(60, 60, 60), width=3)   # vidrio rajado
    dd.line([(cx + 60, cy + 40), (cx + 200, cy + 10)], fill=(60, 60, 60), width=3)
    return im


def toma_07(t, d, T0):             # el reloj detenido en 3:17
    im = tablero(t, d)
    z = 1.0 + 0.25 * ease(t / d)
    im = im.resize((int(W * z), int(H * z)), Image.BICUBIC).crop((int(W * (z - 1) / 2), int(H * (z - 1) / 2) + int(40 * z),
                                                                 int(W * (z - 1) / 2) + W, int(H * (z - 1) / 2) + H + int(40 * z)))
    luz = 0.5 + 0.5 * (math.sin(t * 2) > -0.6)
    im = Image.blend(Image.new('RGB', (W, H)), im.convert('RGB'), 0.55 + 0.45 * luz).convert('RGBA')
    return im


def toma_08(t, d, T0):             # el capó abierto, motor frío
    im, s, box = fondo_taller(1.08, 0.55)
    car = CARRO_SIN_LUZ.resize((int(CARRO.width * s * 0.42), int(CARRO.height * s * 0.42)), Image.BICUBIC)
    x, y = W * 0.44 - car.width * 0.5, H * 0.86 - car.height
    im = sombra_pie(im, x + car.width / 2, H * 0.86, car.width * 0.9)
    im.alpha_composite(car, (int(x), int(y)))
    d_ = ImageDraw.Draw(im)
    hx = x + car.width * 0.76
    d_.polygon([(hx, y + car.height * 0.42), (x + car.width * 1.0, y + car.height * 0.42), (x + car.width * 1.04, y - car.height * 0.25),
                (hx + 30, y - car.height * 0.2)], fill=(150, 26, 24), outline=(30, 10, 8))                  # capó levantado
    sp = elenco.personaje('beto', 'normal', 'quieto', 1150, cerrados=parpadea(t, 2.5))
    im = sombra_pie(im, W * 0.86, H * 0.95, 300)
    im = pegar(im, sp, W * 0.86, H * 0.95)
    im = resplandor(im, hx + 60, y + car.height * 0.2, 180, (150, 190, 255), 0.25 + 0.1 * math.sin(t * 5))
    return tubo(im, t, s, box)


def foto_cliente():
    cab = caras3.cabeza('cliente', 'fijo', 380)
    g = ImageOps.grayscale(cab.convert('RGB')).convert('RGB')
    marco = Image.new('RGB', (360, 440), (236, 230, 214))
    fondo = Image.new('RGB', (320, 360), (150, 146, 138))
    m = cab.getchannel('A').resize((320, int(320 * cab.height / cab.width))).crop((0, 0, 320, 360))
    fondo.paste(g.resize((320, int(320 * cab.height / cab.width))).crop((0, 0, 320, 360)), (0, 0), m)
    marco.paste(fondo, (20, 20))
    return marco


FOTO = foto_cliente()


def periodico(ancho=860):
    p = Image.new('RGB', (ancho, int(ancho * 1.25)), (214, 196, 150))
    d = ImageDraw.Draw(p)
    d.text((ancho / 2, 50), 'EL DIARIO MANABITA', font=fnt(44), fill=(40, 32, 24), anchor='mm')
    d.line([(30, 86), (ancho - 30, 86)], fill=(40, 32, 24), width=4)
    d.text((ancho / 2, 112), '14 DE OCTUBRE DE 1957', font=fnt(24), fill=(60, 50, 40), anchor='mm')
    d.text((ancho / 2, 180), 'TRÁGICO ACCIDENTE', font=fnt(62), fill=(30, 24, 18), anchor='mm')
    d.text((ancho / 2, 250), 'EN LA VÍA A MONTECRISTI', font=fnt(48), fill=(30, 24, 18), anchor='mm')
    car = ImageOps.grayscale(CARRO_SIN_LUZ.convert('RGB')).convert('RGB').rotate(-14, expand=True, fillcolor=(120, 116, 108))
    car = car.resize((ancho - 120, int((ancho - 120) * car.height / car.width)))
    foto = Image.new('RGB', (ancho - 80, 420), (110, 106, 100))
    foto.paste(car, (20, 60))
    p.paste(foto, (40, 300))
    d.text((ancho / 2, 760), 'Conductor muere dentro de su carro rojo', font=fnt(30), fill=(50, 40, 30), anchor='mm')
    for j in range(10):
        d.line([(50, 810 + j * 26), (ancho - 50 - (j % 3) * 60, 810 + j * 26)], fill=(120, 108, 84), width=8)
    arr = np.asarray(p).astype(np.float32)
    arr *= (0.9 + 0.1 * np.random.default_rng(4).random(arr.shape[:2]))[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))


PERIODICO = periodico()


def toma_09(t, d, T0):             # la guantera: foto del cliente y un recorte
    im = Image.new('RGBA', (W, H), (18, 14, 14, 255))
    dd = ImageDraw.Draw(im)
    dd.rounded_rectangle([60, 600, 1020, 1500], radius=40, fill=(70, 20, 18))
    dd.rectangle([140, 700, 940, 1300], fill=(14, 10, 10))
    k = ease(t / (d * 0.6))
    im.alpha_composite(PERIODICO.rotate(8, expand=True, fillcolor=(14, 10, 10)).resize((560, 720)).convert('RGBA'), (360, int(1100 - 320 * k)))
    im.alpha_composite(FOTO.rotate(-10, expand=True, fillcolor=(14, 10, 10)).convert('RGBA'), (170, int(1180 - 360 * k)))
    im = resplandor(im, 400, 900, 380, (255, 220, 160), 0.35)                       # luz de la linterna
    return im


def toma_10(t, d, T0):             # el recorte del periódico
    im = Image.new('RGBA', (W, H), (16, 12, 10, 255))
    z = 1.0 + 0.18 * ease(t / d)
    p = PERIODICO.resize((int(980 * z), int(1225 * z)))
    im.alpha_composite(p.convert('RGBA'), (int(W / 2 - p.width / 2), int(H / 2 - p.height / 2)))
    if int(t * 7) % 9 == 0:
        im = Image.blend(im.convert('RGB'), Image.new('RGB', (W, H)), 0.4).convert('RGBA')
    return im


def toma_11(t, d, T0):             # el portón vacío, solo un charco
    im = portón(T0 + t, charco=True)
    sp = elenco.personaje('beto', 'miedo', 'quieto', 1300)
    return pegar(im, sp, 900, H + 140)


def toma_12(t, d, T0):             # las luces se encienden solas y el motor arranca
    im, s, box = fondo_taller(1.0, 0.5)
    im = Image.blend(im.convert('RGB'), Image.new('RGB', (W, H)), 0.45).convert('RGBA')
    car = (CARRO if t > d * 0.35 else CARRO_SIN_LUZ).resize((int(CARRO.width * s * 0.42), int(CARRO.height * s * 0.42)), Image.BICUBIC)
    vib = (6 * math.sin(t * 40)) if t > d * 0.55 else 0
    x, y = W * 0.5 - car.width / 2, H * 0.9 - car.height + vib
    im.alpha_composite(car, (int(x), int(y)))
    if t > d * 0.35:
        on = 1.0 if (t > d * 0.5 or int(t * 12) % 2) else 0.3
        im = resplandor(im, x + car.width - 20, y + car.height * 0.52, 320, (255, 236, 180), 0.8 * on)
    if t > d * 0.55:                                                                  # humo
        capa = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dc = ImageDraw.Draw(capa)
        for j in range(16):
            q = ((t - d * 0.55) * 0.6 + j * 0.13) % 1
            r = 40 + 160 * q
            dc.ellipse([x + 60 - r - 80 * q, y + car.height * 0.6 - 300 * q - r, x + 60 + r, y + car.height * 0.6 - 300 * q + r],
                       fill=(120, 120, 130, int(90 * (1 - q))))
        im.alpha_composite(capa.filter(ImageFilter.GaussianBlur(14)))
    return im


def toma_13(t, d, T0):             # Don Beto retrocede, aterrado, iluminado por los faros
    im, s, box = fondo_taller(1.1, 0.15)
    im = Image.blend(im.convert('RGB'), Image.new('RGB', (W, H)), 0.5).convert('RGBA')
    x = W * 0.6 - W * 0.25 * ease(t / d)
    sp = elenco.personaje('beto', 'miedo', 'miedo', 1250)
    im = sombra_pie(im, x, H * 0.94, 340)
    im = pegar(im, sp, x + 4 * math.sin(t * 30), H * 0.94)
    return resplandor(im, W + 100, H * 0.7, 520, (255, 236, 180), 0.55)


def toma_14(t, d, T0):             # "Ya son las tres y diecisiete" — la cara junto a su oreja
    im = Image.new('RGBA', (W, H), (10, 10, 14, 255))
    beto = con_hombros(caras3.cabeza('beto', 'miedo', 1000), 'beto')
    cli = caras3.cabeza('cliente', 'fijo', 900, hablar=habla(T0 + t, env))
    im.alpha_composite(beto, (int(W * 0.62 - beto.width / 2), int(H * 0.5 - beto.height * 0.4)))
    k = ease(t / d)
    cli = cli.copy()
    cli.putalpha(cli.getchannel('A').point(lambda v: int(v * (0.3 + 0.7 * k))))
    im.alpha_composite(cli, (int(W * 0.12 - cli.width / 2 + 120 * k), int(H * 0.36 - cli.height * 0.4)))
    return im


def toma_15(t, d, T0):             # epílogo: la calle bajo la lluvia, se aleja; luces en el taller
    im, s, box = a_vertical(CALLE, 1.15 - 0.15 * ease(t / d), 0.27, 0.5)
    im = im.convert('RGBA')
    x, y = (250 + 110 - box[0]) * s, (560 - box[1]) * s
    im = resplandor(im, x, y, 120, (255, 236, 180), 0.5 + 0.2 * math.sin(t * 3))
    im = relampago(im, t, d * 0.35, 0.45)
    return lluvia(im, T0 + t)


def susto(t):
    cab = con_hombros(caras3.cabeza('cliente', 'fijo', 1500, hablar=True), 'cliente')
    im = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    if t < 0.15:
        return im
    q = t - 0.15
    z = 1.5 - 0.35 * min(1, q / 0.25)
    c = cab.resize((int(cab.width * z), int(cab.height * z)), Image.BILINEAR)
    im.alpha_composite(c, (int(W / 2 - c.width / 2), int(H / 2 - c.height * 0.45)))
    r, g, b, a_ = im.split()
    off = int(20 * max(0.2, 1 - q * 2))
    im = Image.merge('RGBA', (ImageChops.offset(r, off, 0), g, ImageChops.offset(b, -off, 0), a_))
    if q < 0.12:
        im.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * (1 - q / 0.12)))))
    m = 50
    dx, dy = 30 * math.sin(t * 61) * max(0.1, 1 - q), 30 * math.cos(t * 53) * max(0.1, 1 - q)
    return im.crop((m + dx, m + dy, W - m + dx, H - m + dy)).resize((W, H))


TOMAS = [toma_00, toma_01, toma_02, toma_03, toma_04, toma_05, toma_06, toma_07, toma_08, toma_09, toma_10, toma_11,
         toma_12, toma_13, toma_14, toma_15]

# ---------------------------------------------------------------- render
yy, xx = np.mgrid[0:H, 0:W]
VIG = (1 - 0.5 * np.clip(((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1))[..., None].astype(np.float32)
GRANOS = [np.random.default_rng(i).normal(0, 6, (H, W, 1)).astype(np.float32) for i in range(6)]


def acabado(im, i):
    arr = np.asarray(im.convert('RGB')).astype(np.float32)
    sh = np.clip(1 - arr.mean(2, keepdims=True) / 140, 0, 1)
    arr = arr + sh * np.array([-6, 4, 14], np.float32) + (1 - sh) * np.array([8, 2, -6], np.float32)
    arr = arr * VIG + GRANOS[i % 6]
    return np.clip(arr, 0, 255).astype(np.uint8).tobytes()


if os.environ.get('PRUEBA'):                           # hoja de prueba: un cuadro de cada toma
    hoja = Image.new('RGB', (W // 4 * 6, H // 4 * 3))
    for k_, f_ in enumerate(TOMAS + [lambda t, d, T0: susto(0.5)]):
        d_ = (t0s[k_ + 1] - t0s[k_]) if k_ < len(TOMAS) else 1.4
        fr = Image.frombytes('RGB', (W, H), acabado(f_(d_ * 0.7, d_, t0s[k_] if k_ < len(TOMAS) else 0), 0))
        hoja.paste(fr.resize((W // 4, H // 4)), ((k_ % 6) * W // 4, (k_ // 6) * H // 4))
    hoja.save(f'{OUT}/prueba.jpg', quality=85)
    sys.exit()
p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', f'{OUT}/cuerpo.mp4'], stdin=subprocess.PIPE)
n = int(TOTAL * FPS)
T_SUSTO = CORTE + 0.15                                 # el susto llena el hueco después de "ya son las tres y diecisiete"
for i in range(n):
    t = i / FPS
    if T_SUSTO <= t < T_SUSTO + 1.4:
        im = susto(t - T_SUSTO)
    else:
        k = max(j for j in range(len(TOMAS)) if t0s[j] <= t + 1e-6)
        k = min(k, len(TOMAS) - 1)
        d = t0s[k + 1] - t0s[k] if k + 1 < len(t0s) else TOTAL - t0s[k]
        ti = t - t0s[k]
        im = TOMAS[k](ti, d, t0s[k])
        if ti < 0.25 and k > 0:                        # entrada desde negro
            im = Image.blend(Image.new('RGB', (W, H)), im.convert('RGB'), ti / 0.25)
    p.stdin.write(acabado(im, i))
    if i % 300 == 0:
        print(f'{t:.0f}/{TOTAL:.0f}s', flush=True)
p.stdin.close(); p.wait()

# ---------------------------------------------------------------- audio
SFX = montaje.SFX
lluvia_a = 'anoisesrc=color=pink:a=0.5:r=48000,highpass=f=800,lowpass=f=7000,volume=0.22'
eventos = [(segs[1]['t0'] + (segs[2]['t0'] - segs[1]['t0']) * 0.55, 'trueno'), (1.2, 'trueno'),
           (segs[15]['t0'] + (TOTAL - segs[15]['t0']) * 0.35, 'trueno')]
fa = [f"[0:a]aresample=48000,aformat=channel_layouts=stereo,aecho=0.8:0.5:50|100:0.18|0.08,apad=whole_dur={TOTAL:.2f},volume=1.3[v]",
      f"[1:a]atrim=0:{TOTAL:.2f},volume=0.14,afade=t=in:d=2,afade=t=out:st={TOTAL - 3:.2f}:d=3[m]",
      f"{lluvia_a},atrim=0:{TOTAL:.2f},aformat=channel_layouts=stereo[r]"]
lab = ['[v]', '[m]', '[r]']
ins = ['-i', f'{OUT}/voz.wav', '-stream_loop', '-1', '-i', montaje.MUSICA]
k = 2
for j, (t, _) in enumerate(eventos):
    fa.append(f"anoisesrc=color=brown:a=1:r=48000:d=3,lowpass=f=170,afade=t=in:d=0.04,afade=t=out:st=0.3:d=2.6,volume=2.2,"
              f"adelay={int(t * 1000)}|{int(t * 1000)},aformat=channel_layouts=stereo[tr{j}]")
    lab.append(f'[tr{j}]')
for j, (t, dd) in enumerate([(segs[4]['t0'], 4.0), (segs[12]['t0'] + 1.5, 4.0)]):   # motor
    fa.append(f"sine=f=46:d={dd}:r=48000,volume=0.5,afade=t=in:d=0.5,afade=t=out:st={dd - 0.8}:d=0.8,"
              f"adelay={int(t * 1000)}|{int(t * 1000)},aformat=channel_layouts=stereo[mo{j}]")
    lab.append(f'[mo{j}]')
ins += ['-stream_loop', '-1', '-i', os.path.join(SFX, 'heart_slow.mp3'), '-i', os.path.join(SFX, 'riser2.mp3'),
        '-i', os.path.join(SFX, 'golpe_terror.mp3'), '-i', os.path.join(SFX, 'susp_impact.mp3')]
t_lat = segs[13]['t0']
fa.append(f"[2:a]atrim=0:{T_SUSTO - t_lat + 0.2:.2f},volume=0.9,adelay={int(t_lat * 1000)}|{int(t_lat * 1000)}[lat]")
fa.append(f"[3:a]volume=0.45,adelay={int((T_SUSTO - 2) * 1000)}|{int((T_SUSTO - 2) * 1000)}[ris]")
fa.append(f"[4:a]volume=1.0,adelay={int(T_SUSTO * 1000 + 150)}|{int(T_SUSTO * 1000 + 150)}[g1]")
fa.append(f"[5:a]volume=0.9,adelay={int(T_SUSTO * 1000 + 150)}|{int(T_SUSTO * 1000 + 150)}[g2]")
lab += ['[lat]', '[ris]', '[g1]', '[g2]']
fa.append(''.join(lab) + f"amix=inputs={len(lab)}:normalize=0:duration=first,atrim=0:{TOTAL:.2f},loudnorm=I=-14:TP=-1:LRA=11[a]")
subprocess.run(['ffmpeg', '-v', 'error', '-y'] + ins + ['-filter_complex', ';'.join(fa), '-map', '[a]', '-ar', '48000', '-ac', '2',
                f'{OUT}/mezcla.wav'], check=True)

# subtítulos palabra por palabra + título
pal = [tuple(x) for x in info['palabras']]
ass = f'{OUT}/subs.ass'
montaje._ass(pal, W, H, 'EL ÚLTIMO CLIENTE', ass, rotulos=[(a_, b_, '') for a_, b_ in zip(t0s[:-1], t0s[1:])])
lineas = [l for l in open(ass) if not l.rstrip().endswith(',RIDMER')]
open(ass, 'w').write(''.join(lineas))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/cuerpo.mp4', '-i', f'{OUT}/mezcla.wav', '-filter_complex',
                f"[0:v]subtitles='{ass}':fontsdir='{os.path.dirname(FUENTE)}',format=yuv420p[v]", '-map', '[v]', '-map', '1:a',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-maxrate', '7M', '-bufsize', '14M', '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart', '-t', f'{TOTAL:.3f}', f'{OUT}/El_ultimo_cliente.mp4'], check=True)
print('listo', round(TOTAL, 1), 's')
