"""Escenas DIBUJADAS de TERROR (canal de leyendas): río de noche con niebla, pueblo, bosque, la mujer de blanco
y el susto final. Se registran en dibujos.ESCENAS, así que se piden igual: dibujos.escena('rio', ..., evento='llorona').
"""
import math, random
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import dibujos as D
from dibujos import TINTA, _ease, _mezcla, _degradado, Luces, persona, pegar, temblor


def _niebla(W, H, semilla, alfa=70, color=(170, 180, 200)):
    """Franja de niebla (doble de ancho para moverla en bucle)."""
    rnd = random.Random(semilla)
    q = 4
    im = Image.new('RGBA', (W * 2 // q, H // q), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(40):
        x, y = rnd.uniform(0, W * 2 / q), rnd.uniform(H * 0.35 / q, H * 0.65 / q)
        rx, ry = rnd.uniform(60, 220) / q * W / 1080, rnd.uniform(20, 60) / q * W / 1080
        d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=color + (int(alfa * rnd.uniform(0.4, 1)),))
    return im.filter(ImageFilter.GaussianBlur(10)).resize((W * 2, H), Image.BILINEAR)


def _poner_niebla(im, capa, t, vel, dy=0):
    W = im.width
    x = int((t * vel) % W)
    im.alpha_composite(capa.crop((x, 0, x + W, capa.height)), (0, dy))


def _arbol(d, x, base, alto, ancho, col, rnd):
    d.polygon([(x - ancho * 0.08, base), (x - ancho * 0.05, base - alto * 0.6), (x + ancho * 0.05, base - alto * 0.6),
               (x + ancho * 0.08, base)], fill=col)
    for j in range(7):                                     # copa irregular
        cx = x + rnd.uniform(-ancho * 0.4, ancho * 0.4)
        cy = base - alto * rnd.uniform(0.55, 1.0)
        r = ancho * rnd.uniform(0.25, 0.45)
        d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], fill=col)
    for j in range(4):                                     # ramas secas
        a = rnd.uniform(-2.4, -0.7)
        x0, y0 = x, base - alto * rnd.uniform(0.4, 0.8)
        d.line([(x0, y0), (x0 + math.cos(a) * ancho * 0.6, y0 + math.sin(a) * ancho * 0.5)], fill=col, width=max(2, int(ancho / 40)))


def llorona(t, alto, cara=False, alfa=1.0):
    """Sprite de la mujer de blanco: vestido largo y rasgado que ondea, pelo negro hasta la cintura tapando la cara,
    brazos largos con dedos flacos, brillo fantasmal."""
    w, h = int(alto * 0.8), int(alto * 1.1)
    SS = 2
    im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = alto / 600 * SS
    cx = w * SS / 2
    top = h * SS - alto * SS * 1.0
    cab = top + 70 * k
    # vestido: hombros angostos, se abre hacia abajo con jirones que ondean
    borde = []
    for j in range(19):
        x = cx - 170 * k + j * (340 / 18) * k
        largo = 600 + (30 if j % 3 == 0 else 0) + 20 * math.sin(j * 2.3)
        borde.append((x + 10 * k * math.sin(t * 2.5 + j), top + largo * k + 16 * k * math.sin(t * 3 + j * 0.9)))
    d.polygon([(cx - 48 * k, cab + 68 * k), (cx + 48 * k, cab + 68 * k), (cx + 120 * k, cab + 300 * k)] + borde[::-1] +
              [(cx - 120 * k, cab + 300 * k)], fill=(222, 228, 234, 225))
    for j in range(8):                                     # pliegues y manchas
        x = cx - 120 * k + j * 34 * k
        d.line([(cx + (x - cx) * 0.25, cab + 100 * k), (x + 8 * k * math.sin(t * 2 + j), top + 590 * k)],
               fill=(170, 180, 192, 190), width=int(3 * k))
    # brazos largos, colgando, con dedos flacos
    for s in (-1, 1):
        sway = 6 * k * math.sin(t * 1.7 + s)
        hx, hy = cx + s * 95 * k + sway, cab + 330 * k
        d.line([(cx + s * 46 * k, cab + 80 * k), (cx + s * 80 * k, cab + 200 * k), (hx, hy)], fill=(150, 158, 168, 240),
               width=int(20 * k), joint='curve')
        for f_ in range(4):
            d.line([(hx, hy), (hx + s * (f_ - 1.5) * 6 * k, hy + (48 + 6 * f_) * k)], fill=(176, 184, 190, 240), width=int(5 * k))
    # cabeza y pelo largo y desordenado
    d.ellipse([cx - 40 * k, cab - 50 * k, cx + 40 * k, cab + 50 * k], fill=(196, 202, 208, 240))
    pelo = []
    for j in range(13):                                    # coronilla redonda
        ang = math.pi + j / 12 * math.pi
        pelo.append((cx + math.cos(ang) * 50 * k, cab - 8 * k + math.sin(ang) * 58 * k))
    pelo += [(cx + 54 * k, cab + 100 * k)]
    for j in range(11):                                    # puntas desiguales
        x = cx + 58 * k - j * 11.6 * k
        pelo.append((x + 5 * k * math.sin(t * 2 + j), cab + (170 + 40 * ((j * 7) % 3)) * k))
    pelo += [(cx - 54 * k, cab + 100 * k)]
    d.polygon(pelo, fill=(12, 10, 12, 245))
    for j in range(16):                                    # mechones sueltos
        x0 = cx - 52 * k + j * 7 * k
        largo = (190 + 50 * math.sin(j * 1.9)) * k
        d.line([(x0, cab - 40 * k), (x0 + 10 * k * math.sin(t * 2 + j), cab + largo)], fill=(8, 6, 8, 230), width=int(5 * k))
    if cara:
        d.rectangle([cx - 10 * k, cab - 25 * k, cx + 12 * k, cab + 40 * k], fill=(176, 182, 186, 250))
        d.ellipse([cx - 5 * k, cab - 8 * k, cx + 6 * k, cab + 4 * k], fill=(0, 0, 0, 255))
    im = im.resize((w, h), Image.LANCZOS)
    brillo = im.filter(ImageFilter.GaussianBlur(alto / 25))
    brillo = Image.merge('RGBA', (*Image.new('RGB', im.size, (190, 215, 255)).split(), brillo.getchannel('A').point(lambda v: v * 2 // 3)))
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(brillo)
    out.alpha_composite(im)
    if alfa < 1:
        out.putalpha(out.getchannel('A').point(lambda v: int(v * alfa)))
    return out


def _cielo_noche(W, H, rnd, luna=(0.7, 0.13)):
    f = Image.new('RGBA', (W, H))
    f.paste(_degradado(W, H, (4, 6, 14), (22, 28, 44)), (0, 0))
    d = ImageDraw.Draw(f)
    for _ in range(120):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H * 0.45)
        r = rnd.uniform(0.8, 2.2)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(190, 196, 220))
    lx, ly = W * luna[0], H * luna[1]
    R = W * 0.05
    d.ellipse([lx - R, ly - R, lx + R, ly + R], fill=(196, 200, 190))
    for _ in range(5):                                      # cráteres
        a, rr = rnd.uniform(0, 6.28), rnd.uniform(0, R * 0.6)
        r = rnd.uniform(R * 0.08, R * 0.2)
        d.ellipse([lx + math.cos(a) * rr - r, ly + math.sin(a) * rr - r, lx + math.cos(a) * rr + r, ly + math.sin(a) * rr + r],
                  fill=(176, 180, 170))
    return f, (lx, ly, R)


def _rio(W, H, d, evento='calma', **kw):
    rnd = random.Random(11)
    u = W / 1080 if H > W else H / 1080
    agua0, agua1 = int(H * 0.56), int(H * 0.80)
    f, (lx, ly, R) = _cielo_noche(W, H, rnd)
    df = ImageDraw.Draw(f)
    df.polygon([(0, agua0)] + [(x, agua0 - 120 * u - 80 * u * math.sin(x / (260 * u))) for x in range(0, W + 40, 40)] + [(W, agua0)],
               fill=(12, 16, 22))
    for j in range(9):                                      # árboles de las orillas
        x = rnd.choice([rnd.uniform(-60, W * 0.3), rnd.uniform(W * 0.7, W + 60)])
        _arbol(df, x, agua0 + 10 * u, rnd.uniform(380, 620) * u, rnd.uniform(220, 340) * u, (8, 10, 14), rnd)
    df.rectangle([0, agua0, W, agua1], fill=(10, 18, 30))
    df.rectangle([0, agua1, W, H], fill=(8, 10, 10))
    for _ in range(26):                                     # juncos del primer plano (base)
        x = rnd.uniform(0, W)
        df.line([(x, H), (x + rnd.uniform(-30, 30) * u, agua1 - rnd.uniform(40, 200) * u)], fill=(6, 8, 8), width=int(5 * u))
    n1, n2 = _niebla(W, H, 1, 80), _niebla(W, H, 2, 60)
    reflejos = [(rnd.uniform(-1, 1), rnd.uniform(0, 1), rnd.uniform(0.5, 1.5)) for _ in range(60)]

    def cuadro(t):
        p = t / d
        im = f.copy()
        dr = ImageDraw.Draw(im)
        L = Luces(W, H)
        L.halo(lx, ly, R * 4, color=(150, 170, 230), fuerza=0.22)
        for (rx, ry, s) in reflejos:                       # reflejo de la luna temblando en el agua
            y = agua0 + 20 * u + ry * (agua1 - agua0 - 40 * u)
            ancho = (40 + 120 * (1 - ry)) * u * (0.6 + 0.4 * math.sin(t * 2 * s + rx * 9))
            x = lx + rx * 90 * u * (0.4 + ry)
            dr.line([(x - ancho / 2, y), (x + ancho / 2, y)], fill=(150, 160, 190), width=max(2, int(3 * u)))
        if evento == 'orilla':                             # una mujer camina con dos niños hacia el río (siluetas)
            x = W * (0.1 + 0.32 * _ease(p))
            for j, (alto, dx) in enumerate([(300 * u, 0), (150 * u, 70 * u), (135 * u, 125 * u)]):
                sp = persona('camina', (t * 0.9 + j * 0.3) % 1, ropa=(16, 18, 24), piel=(16, 18, 24), alto=alto)
                pegar(im, sp, x - dx, agua0 + 4 * u, alfa=max(0.0, 1 - max(0, p - 0.7) / 0.3))
        if evento == 'salpica':                            # salpicadura y ondas en el centro
            cx, cy = W * 0.5, agua0 + 120 * u
            q = min(1.0, p * 1.6)
            for j in range(18):
                a = math.pi * (0.15 + 0.7 * j / 17)
                v = (300 + 120 * math.sin(j * 7)) * u
                x = cx + math.cos(a) * v * q
                y = cy - math.sin(a) * v * q * 1.6 + 900 * u * q * q
                if y < cy + 10 * u:
                    dr.ellipse([x - 8 * u, y - 8 * u, x + 8 * u, y + 8 * u], fill=(190, 200, 225))
            for j in range(4):
                r = (p * 1.2 - j * 0.18)
                if r > 0:
                    rr = r * 420 * u
                    dr.ellipse([cx - rr, cy - rr * 0.18, cx + rr, cy + rr * 0.18], outline=(120, 135, 165), width=max(2, int(4 * u)))
        im = L.aplicar(im)
        _poner_niebla(im, n1, t, 30 * u, int(H * 0.12))
        if evento in ('llorona', 'cerca'):
            alto = (900 if evento == 'cerca' else 640) * u
            alfa = 0.85 + 0.15 * math.sin(t * 17) if math.sin(t * 5.3) > -0.85 else 0.25    # parpadea
            sp = llorona(t, alto, alfa=alfa)
            y = agua0 + 70 * u + 14 * u * math.sin(t * 1.4) + (alto * 0.25 if evento == 'cerca' else 0)
            x = W * 0.5 + (0 if evento == 'cerca' else 40 * u * math.sin(t * 0.5))
            pegar(im, sp, x, y)
        _poner_niebla(im, n2, t, -50 * u, int(H * 0.28))
        return im
    z = 1.12
    return cuadro, {'z': z, 'fx': (0.47, 0.53), 'fy': 0.52}


def _pueblo(W, H, d, evento='noche', **kw):
    rnd = random.Random(21)
    u = W / 1080 if H > W else H / 1080
    suelo = int(H * 0.66)
    f, (lx, ly, R) = _cielo_noche(W, H, rnd, luna=(0.25, 0.12))
    df = ImageDraw.Draw(f)
    df.polygon([(0, suelo)] + [(x, suelo - 260 * u - 140 * u * math.sin(x / (380 * u) + 1)) for x in range(0, W + 40, 40)] + [(W, suelo)],
               fill=(14, 18, 24))
    casas, ventanas = [], []
    x = -40 * u
    while x < W:
        w_ = rnd.uniform(180, 260) * u
        h_ = rnd.uniform(130, 200) * u
        casas.append((x, w_, h_))
        x += w_ + rnd.uniform(10, 40) * u
    # iglesia
    ix = W * 0.62
    df.rectangle([ix, suelo - 420 * u, ix + 110 * u, suelo], fill=(54, 46, 44), outline=TINTA, width=3)
    df.polygon([(ix - 10 * u, suelo - 420 * u), (ix + 55 * u, suelo - 500 * u), (ix + 120 * u, suelo - 420 * u)], fill=(70, 40, 34))
    df.line([(ix + 55 * u, suelo - 500 * u), (ix + 55 * u, suelo - 560 * u)], fill=(40, 34, 30), width=int(8 * u))
    df.line([(ix + 35 * u, suelo - 540 * u), (ix + 75 * u, suelo - 540 * u)], fill=(40, 34, 30), width=int(8 * u))
    for (x, w_, h_) in casas:
        if ix - 20 * u < x < ix + 120 * u:
            continue
        df.rectangle([x, suelo - h_, x + w_, suelo], fill=(98, 72, 56), outline=TINTA, width=3)
        df.polygon([(x - 18 * u, suelo - h_), (x + w_ / 2, suelo - h_ - 70 * u), (x + w_ + 18 * u, suelo - h_)], fill=(110, 46, 34),
                   outline=TINTA)
        df.rectangle([x + w_ * 0.42, suelo - 90 * u, x + w_ * 0.58, suelo], fill=(40, 28, 22))
        if rnd.random() < 0.7:
            ventanas.append((x + w_ * 0.15, suelo - h_ * 0.75, rnd.random()))
    df.rectangle([0, suelo, W, H], fill=(36, 30, 26))
    df.polygon([(W * 0.42, suelo), (W * 0.58, suelo), (W * 0.9, H), (W * 0.1, H)], fill=(40, 34, 30))
    n1 = _niebla(W, H, 5, 70)
    puerta = (casas[1][0] + casas[1][1] * 0.5, suelo) if len(casas) > 1 else (W * 0.3, suelo)

    def cuadro(t):
        p = t / d
        im = f.copy()
        dr = ImageDraw.Draw(im)
        L = Luces(W, H)
        L.halo(lx, ly, R * 4, color=(150, 170, 230), fuerza=0.2)
        for (x, y, s) in ventanas:
            on = not (evento == 'abandono' and s < 0.3 and p > 0.6)
            dr.rectangle([x, y, x + 46 * u, y + 46 * u], fill=(250, 196, 100) if on else (30, 24, 20), outline=TINTA)
            if on:
                L.halo(x + 23 * u, y + 23 * u, 70 * u, color=(255, 170, 80), fuerza=0.4 + 0.08 * math.sin(t * 7 + s * 9))
        if evento == 'abandono':                         # él se va por el camino; ella y los niños se quedan
            k = _ease(p)
            alto = (330 - 230 * k) * u
            hx = W * 0.5 + 40 * u * k
            hy = H * 0.92 - (H * 0.92 - suelo) * k
            pegar(im, persona('camina', (t * 1.1) % 1, ropa=(20, 22, 28), piel=(20, 22, 28), alto=alto, mira=-1), hx, hy)
            px, py = puerta
            for j, (alto_, dx) in enumerate([(260 * u, 0), (130 * u, 60 * u), (120 * u, -60 * u)]):
                pegar(im, persona('quieto', 0, ropa=(18, 20, 26), piel=(18, 20, 26), alto=alto_), px + dx, py + 6 * u)
        im = L.aplicar(im)
        _poner_niebla(im, n1, t, 25 * u, int(H * 0.22))
        return im
    return cuadro, {'z': 1.1, 'fx': (0.45, 0.55), 'fy': 0.55}


def _bosque(W, H, d, evento='lejos', **kw):
    rnd = random.Random(31)
    u = W / 1080 if H > W else H / 1080
    suelo = int(H * 0.72)
    f = Image.new('RGBA', (W, H))
    f.paste(_degradado(W, H, (6, 10, 14), (20, 28, 30)), (0, 0))
    df = ImageDraw.Draw(f)
    for capa, col in enumerate([(22, 30, 32), (14, 20, 22), (8, 12, 12)]):
        for _ in range(9 + capa * 3):
            _arbol(df, rnd.uniform(-80, W + 80), suelo + capa * 40 * u, rnd.uniform(700, 1100) * u * (0.7 + capa * 0.2),
                   rnd.uniform(200, 320) * u, col, rnd)
    df.rectangle([0, suelo + 60 * u, W, H], fill=(6, 8, 8))
    n1, n2 = _niebla(W, H, 7, 90, (120, 140, 150)), _niebla(W, H, 8, 70, (120, 140, 150))

    def cuadro(t):
        p = t / d
        im = f.copy()
        _poner_niebla(im, n1, t, 20 * u, int(H * 0.25))
        if evento == 'lejos':
            alfa = 0.7 if math.sin(t * 2.1) > -0.3 else 0.0                # aparece y desaparece entre los árboles
            x = W * (0.35 + 0.25 * (int(t / 1.2) % 3) / 2)
            pegar(im, llorona(t, 260 * u, alfa=alfa), x, suelo - 10 * u)
        if evento == 'oscuro':                                              # latido: la oscuridad respira
            k = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 1.1)
            im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(120 + 80 * k))))
        _poner_niebla(im, n2, t, -35 * u, int(H * 0.38))
        return im
    return cuadro, {'z': 1.15, 'fx': (0.45, 0.55), 'fy': 0.55}


def _susto(W, H, d, **kw):
    """Cara de la mujer de blanco que salta a la pantalla (con destello, temblor y separación de colores)."""
    u = W / 1080 if H > W else H / 1080
    import numpy as np
    cw, ch = W, H
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    cx, cy = cw / 2, ch * 0.47
    k = cw / 1080
    # piel: óvalo con sombra hacia los bordes (pálida, gris azulada)
    rx, ry = 330 * k, 480 * k
    r = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    piel = np.clip(1.15 - r ** 3, 0, 1)
    def hueco(x0, y0, ax, ay, fuerza):
        rr = np.sqrt(((xx - x0) / ax) ** 2 + ((yy - y0) / ay) ** 2)
        return fuerza * np.clip(1.25 - rr, 0, 1) ** 1.2
    osc = np.zeros_like(piel)
    for s_ in (-1, 1):
        osc += hueco(cx + s_ * 125 * k, cy - 70 * k, 110 * k, 95 * k, 1.6)          # cuencas de los ojos
        osc += hueco(cx + s_ * 190 * k, cy + 120 * k, 90 * k, 180 * k, 0.45)         # mejillas hundidas
    osc += hueco(cx, cy + 270 * k, 120 * k, 190 * k, 2.2)                           # boca abierta, estirada
    osc += hueco(cx, cy + 80 * k, 30 * k, 70 * k, 0.5)                              # nariz
    v = np.clip(piel * (1 - np.clip(osc, 0, 1)), 0, 1)
    rgb = np.stack([v * 176, v * 186, v * 192], -1)
    rng = np.random.default_rng(3)
    rgb *= (0.92 + 0.08 * rng.random((ch, cw, 1)))                                 # textura de piel
    a = np.clip(piel * 3, 0, 1) * 255
    cara = Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), 'RGBA')
    dc = ImageDraw.Draw(cara)
    for s_ in (-1, 1):                                                             # pupilas blancas diminutas
        dc.ellipse([cx + s_ * 118 * k - 9 * k, cy - 78 * k, cx + s_ * 118 * k + 9 * k, cy - 60 * k], fill=(240, 240, 235, 255))
    for j in range(8):                                                              # venas oscuras
        x0 = cx + rng.uniform(-260, 260) * k
        y0 = cy + rng.uniform(-300, 300) * k
        pts = [(x0, y0)]
        for _ in range(5):
            x0 += rng.uniform(-40, 40) * k; y0 += rng.uniform(-40, 40) * k
            pts.append((x0, y0))
        dc.line(pts, fill=(70, 70, 90, 120), width=int(3 * k))
    pelo = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    dp = ImageDraw.Draw(pelo)
    for j in range(140):                                                            # pelo mojado cayendo sobre la cara
        x0 = cx + rng.uniform(-520, 520) * k
        lado = abs(x0 - cx) / (330 * k)
        y1 = ch if lado > 0.8 else cy + rng.uniform(-200, 420) * k
        pts = [(x0 + rng.uniform(-40, 40) * k, cy - 560 * k)]
        for q_ in range(1, 7):
            pts.append((x0 + 25 * k * math.sin(q_ * 1.3 + j), cy - 560 * k + (y1 - cy + 560 * k) * q_ / 6))
        dp.line(pts, fill=(6, 5, 7, int(rng.uniform(150, 255))), width=int(rng.uniform(3, 12) * k))
    cara.alpha_composite(pelo.filter(ImageFilter.GaussianBlur(1.2)))
    cara = cara.filter(ImageFilter.GaussianBlur(1.5))

    def cuadro(t):
        im = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        if t < 0.18:
            return im
        q = t - 0.18
        z = (1.35 - 0.3 * min(1, q / 0.25) + 0.02 * math.sin(q * 40)) * 1.35
        cw2, ch2 = int(W * z), int(H * z)
        c = cara.resize((cw2, ch2), Image.BILINEAR)
        im.alpha_composite(c, (int((W - cw2) / 2), int((H - ch2) / 2)))
        r, g, b, a = im.split()                                              # separación de colores (glitch)
        off = int(18 * u * max(0.2, 1 - q * 2))
        r = ImageChops.offset(r, off, 0)
        b = ImageChops.offset(b, -off, 0)
        im = Image.merge('RGBA', (r, g, b, a))
        if q < 0.12:
            im.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * (1 - q / 0.12)))))
        if int(q * 30) % 7 == 0:                                             # líneas de interferencia
            dr = ImageDraw.Draw(im)
            y = random.Random(int(q * 30)).uniform(0, H)
            dr.rectangle([0, y, W, y + 30 * u], fill=(255, 255, 255, 60))
        return temblor(im, max(0.15, 1 - q * 1.5), t, margen=60)
    return cuadro, {'z': 1.0, 'fx': (0.5, 0.5), 'fy': 0.5}


D.ESCENAS.update({'rio': _rio, 'pueblo': _pueblo, 'bosque': _bosque, 'susto': _susto})
