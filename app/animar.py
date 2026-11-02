"""Animaciones de Ridmer (las arma Claude al editar): ruta de un viaje sobre el mapa, recreación de una caída,
contador de cifras y línea de tiempo. Se dibujan cuadro a cuadro con PIL y se codifican con ffmpeg.
Todas producen un mp4 a pantalla completa (sin audio) con nombre anim_*.mp4."""
import math, os, subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

APP = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(os.path.dirname(APP), 'assets', 'InterDisplay-Black.otf')
FPS = 30
ROJO, BLANCO, AMARILLO = (225, 30, 30), (245, 245, 245), (255, 214, 0)


def _f(n):
    try:
        return ImageFont.truetype(FUENTE, n)
    except Exception:
        return ImageFont.load_default()


def _ease(x):
    x = max(0.0, min(1.0, x))
    return (1 - math.cos(math.pi * x)) / 2


class _Video:
    def __init__(self, salida, W, H):
        self.p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                                   '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
                                   '-pix_fmt', 'yuv420p', salida], stdin=subprocess.PIPE)

    def cuadro(self, im):
        self.p.stdin.write(im.convert('RGB').tobytes())

    def fin(self):
        self.p.stdin.close()
        self.p.wait()


def _fondo(img, W, H):
    """Fondo oscuro desenfocado + caja central (como las fotos) donde va el mapa."""
    base = ImageOps.fit(img, (W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(28))
    base = Image.blend(base, Image.new('RGB', (W, H), (0, 0, 0)), 0.55)
    return base


def _caja(W, H):
    if H > W:
        bw, bh = W, int(H * 0.55)
    else:
        bw, bh = W, H
    return (W - bw) // 2, (H - bh) // 2, bw, bh


def _avion(d, x, y, ang, s=1.0, color=BLANCO):
    """Silueta simple de avión (vista de arriba) centrada en x,y, apuntando a `ang` radianes."""
    pts = [(1.0, 0), (0.15, 0.12), (-0.1, 0.65), (-0.25, 0.65), (-0.1, 0.12), (-0.7, 0.1), (-0.85, 0.32), (-0.95, 0.32),
           (-0.88, 0), (-0.95, -0.32), (-0.85, -0.32), (-0.7, -0.1), (-0.1, -0.12), (-0.25, -0.65), (-0.1, -0.65),
           (0.15, -0.12)]
    c, si = math.cos(ang), math.sin(ang)
    k = 38 * s
    poly = [(x + (px * c - py * si) * k, y + (px * si + py * c) * k) for px, py in pts]
    d.polygon(poly, fill=color, outline=(0, 0, 0))


def _etiqueta(d, x, y, txt, tam=40, color=BLANCO):
    d.text((x, y), txt, font=_f(tam), fill=color, anchor='mm', stroke_width=5, stroke_fill=(0, 0, 0))


def _recreacion(d, W, H, y):
    d.text((W // 2, y), 'RECREACIÓN', font=_f(26), fill=(255, 255, 255), anchor='mm', stroke_width=3, stroke_fill=(0, 0, 0))


def ruta(sat, centro, km, a, b, na, nb, salida, d=6.0, W=1080, H=1920, corte=1.0, c=None, nc=''):
    """Línea animada de A a B sobre la imagen satelital (bbox definida por centro/km como fabrica._satelite).
    corte < 1: el avión se detiene antes (no llegó); c: punto del suceso (se marca en rojo al final)."""
    lat0, lon0 = centro
    dd = km / 111.0
    bbox = (lon0 - dd * 1.6, lat0 - dd, lon0 + dd * 1.6, lat0 + dd)        # x0, y0, x1, y1 (lon/lat)
    mapa = Image.open(sat).convert('RGB')
    mw, mh = mapa.size
    bx, by, bw, bh = _caja(W, H)
    esc = max(bw / mw, bh / mh)
    mapa = mapa.resize((int(mw * esc), int(mh * esc)), Image.LANCZOS)
    ox, oy = bx + (bw - mapa.width) // 2, by + (bh - mapa.height) // 2

    def px(p):
        lat, lon = p
        return (ox + (lon - bbox[0]) / (bbox[2] - bbox[0]) * mapa.width,
                oy + (bbox[3] - lat) / (bbox[3] - bbox[1]) * mapa.height)
    fondo = _fondo(mapa, W, H)
    A, B = px(a), px(b)
    C = px(c) if c else None
    v = _Video(salida, W, H)
    n = int(d * FPS)
    for i in range(n):
        t = i / FPS
        prog = _ease(t / (d * 0.75)) * corte
        im = fondo.copy()
        im.paste(mapa, (ox, oy))
        dr = ImageDraw.Draw(im, 'RGBA')
        dr.rectangle([bx, by, bx + bw, by + bh], outline=(255, 255, 255, 60), width=3)
        # ruta prevista (punteada) y recorrido real (sólido)
        for k in range(0, 100, 3):
            p0 = (A[0] + (B[0] - A[0]) * k / 100, A[1] + (B[1] - A[1]) * k / 100)
            p1 = (A[0] + (B[0] - A[0]) * (k + 1.5) / 100, A[1] + (B[1] - A[1]) * (k + 1.5) / 100)
            dr.line([p0, p1], fill=(255, 255, 255, 140), width=4)
        P = (A[0] + (B[0] - A[0]) * prog, A[1] + (B[1] - A[1]) * prog)
        dr.line([A, P], fill=AMARILLO, width=9)
        for (q, nombre) in ((A, na), (B, nb)):
            dr.ellipse([q[0] - 13, q[1] - 13, q[0] + 13, q[1] + 13], fill=BLANCO, outline=(0, 0, 0), width=3)
            _etiqueta(dr, min(max(q[0], bx + 130), bx + bw - 130), q[1] - 46, nombre, 40)
        _avion(dr, P[0], P[1], math.atan2(B[1] - A[1], B[0] - A[0]), 1.3)
        if C and t > d * 0.78:
            pulso = (t - d * 0.78) * 3
            for r in (30 + 40 * (pulso % 1), 15):
                dr.ellipse([C[0] - r, C[1] - r, C[0] + r, C[1] + r], outline=ROJO, width=7)
            if nc:
                _etiqueta(dr, min(max(C[0], bx + 130), bx + bw - 130), C[1] + 60, nc, 38, (255, 90, 90))
        dr.text((bx + 20, by + bh - 34), 'Imagen satelital: Esri, Maxar', font=_f(22), fill=(230, 230, 230, 200))
        v.cuadro(im)
    v.fin()
    return salida


def caida(sat, lugar, salida, d=6.0, W=1080, H=1920):
    """Recreación (ilustrativa) de un avión que cae en picada sobre el punto central del mapa, con estela,
    sacudida y destello de impacto."""
    mapa0 = Image.open(sat).convert('RGB')
    bx, by, bw, bh = _caja(W, H)
    mapa0 = ImageOps.fit(mapa0, (bw, bh), Image.LANCZOS)
    fondo = _fondo(mapa0, W, H)
    v = _Video(salida, W, H)
    n = int(d * FPS)
    T_IMP = d * 0.62
    cx, cy = bx + bw / 2, by + bh / 2
    sx, sy = bx + bw * 0.08, by - bh * 0.05
    for i in range(n):
        t = i / FPS
        z = 1 + 0.25 * _ease(t / d)
        mapa = mapa0.resize((int(bw * z), int(bh * z)), Image.LANCZOS)
        mapa = mapa.crop(((mapa.width - bw) // 2, (mapa.height - bh) // 2, (mapa.width - bw) // 2 + bw,
                          (mapa.height - bh) // 2 + bh))
        im = fondo.copy()
        sac = 0
        if T_IMP <= t < T_IMP + 0.8:
            sac = int(18 * math.sin(t * 70) * math.exp(-(t - T_IMP) * 5))
        im.paste(mapa, (bx + sac, by))
        dr = ImageDraw.Draw(im, 'RGBA')
        dr.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], outline=ROJO, width=6)
        if t < T_IMP:
            p = (t / T_IMP) ** 1.7                         # acelera al caer
            x, y = sx + (cx - sx) * p, sy + (cy - sy) * p
            for k in range(1, 18):                        # estela de humo
                pk = max(0.0, p - k * 0.025)
                xk, yk = sx + (cx - sx) * pk, sy + (cy - sy) * pk
                r = 6 + k * 1.6
                dr.ellipse([xk - r, yk - r, xk + r, yk + r], fill=(60, 60, 60, max(0, 150 - k * 8)))
            _avion(dr, x, y, math.atan2(cy - sy, cx - sx), 2.0 - 0.6 * p)
        else:
            k = t - T_IMP
            r = 40 + 420 * min(1.0, k / 0.9)
            a = int(max(0, 230 - 230 * k / 1.6))
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 140, 0, a // 2))
            dr.ellipse([cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5], fill=(255, 230, 120, a))
            if k < 0.12:
                dr.rectangle([0, 0, W, H], fill=(255, 255, 255, 170))
            for rr in (60 + 90 * ((k * 1.5) % 1), 40):
                dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=ROJO, width=7)
        _etiqueta(dr, W // 2, by + 60, lugar.upper(), 54)
        _recreacion(dr, W, H, by + bh - 40)
        v.cuadro(im)
    v.fin()
    return salida


def contador(n, texto, sub, salida, d=4.0, W=1080, H=1920, fondo_img=None):
    """Cifra que sube de 0 a n con golpe al final (ej.: 9 → "MUERTOS")."""
    if fondo_img:
        base = _fondo(Image.open(fondo_img).convert('RGB'), W, H)
    else:
        base = Image.new('RGB', (W, H), (14, 6, 8))
    v = _Video(salida, W, H)
    for i in range(int(d * FPS)):
        t = i / FPS
        p = _ease(t / (d * 0.55))
        val = int(round(n * p))
        im = base.copy()
        dr = ImageDraw.Draw(im, 'RGBA')
        g = 1.0 + (0.18 * math.exp(-(t - d * 0.55) * 6) if t >= d * 0.55 else 0)
        tam = int(260 * g)
        cy = H // 2 - 60
        dr.text((W // 2, cy), f'{val:,}'.replace(',', '.'), font=_f(tam), fill=ROJO if p >= 1 else BLANCO,
                anchor='mm', stroke_width=10, stroke_fill=(0, 0, 0))
        dr.text((W // 2, cy + 190), texto.upper(), font=_f(86), fill=BLANCO, anchor='mm', stroke_width=7,
                stroke_fill=(0, 0, 0))
        if sub:
            dr.text((W // 2, cy + 290), sub, font=_f(40), fill=(230, 230, 230), anchor='mm', stroke_width=4,
                    stroke_fill=(0, 0, 0))
        v.cuadro(im)
    v.fin()
    return salida


def linea_tiempo(hitos, salida, d=6.0, W=1080, H=1920):
    """Línea de tiempo vertical que se va llenando: hitos = [(fecha, texto), ...] (máx. 5)."""
    hitos = hitos[:5]
    v = _Video(salida, W, H)
    y0, y1 = int(H * 0.25), int(H * 0.75)
    paso = (y1 - y0) / max(1, len(hitos) - 1)
    for i in range(int(d * FPS)):
        t = i / FPS
        p = _ease(t / (d * 0.8))
        im = Image.new('RGB', (W, H), (12, 10, 16))
        dr = ImageDraw.Draw(im, 'RGBA')
        x = int(W * 0.22)
        dr.line([(x, y0), (x, y0 + (y1 - y0) * p)], fill=ROJO, width=10)
        for k, (f_, tx) in enumerate(hitos):
            yk = y0 + paso * k
            if (yk - y0) <= (y1 - y0) * p + 1:
                a = min(1.0, ((y1 - y0) * p - (yk - y0)) / 80 + 0.2)
                dr.ellipse([x - 22, yk - 22, x + 22, yk + 22], fill=ROJO, outline=BLANCO, width=5)
                dr.text((x + 50, yk - 34), f_.upper(), font=_f(44), fill=(255, 214, 0, int(255 * a)))
                dr.text((x + 50, yk + 18), tx, font=_f(34), fill=(240, 240, 240, int(255 * a)))
        v.cuadro(im)
    v.fin()
    return salida
