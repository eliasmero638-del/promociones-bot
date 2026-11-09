"""Personajes v3: ilustración semi-realista en estilo plano (frente / 3/4), con cara, pelo, ropa con pliegues y luz."""
import math
from PIL import Image, ImageDraw, ImageFilter, ImageChops


def curva(pts, n=8, cerrar=True):
    """Catmull-Rom: une puntos con curvas suaves y devuelve el polígono."""
    P = list(pts)
    if cerrar:
        P = [P[-1]] + P + [P[0], P[1]]
    else:
        P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    return out


def osc(c, f=0.8):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def miembro(d, a, b, wa, wb, col):
    """Brazo o pierna que se afina de wa a wb (polígono suave con extremos redondos)."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    nx, ny = -math.sin(ang), math.cos(ang)
    pts = [(a[0] + nx * wa / 2, a[1] + ny * wa / 2), (b[0] + nx * wb / 2, b[1] + ny * wb / 2),
           (b[0] - nx * wb / 2, b[1] - ny * wb / 2), (a[0] - nx * wa / 2, a[1] - ny * wa / 2)]
    d.polygon(pts, fill=col)
    d.ellipse([a[0] - wa / 2, a[1] - wa / 2, a[0] + wa / 2, a[1] + wa / 2], fill=col)
    d.ellipse([b[0] - wb / 2, b[1] - wb / 2, b[0] + wb / 2, b[1] + wb / 2], fill=col)


PERSONAS = {
    'juliane': dict(piel=(236, 196, 168), pelo=(92, 60, 38), pelo_tipo='largo', ojos=(70, 90, 110), mujer=True,
                    ropa='vestido', c1=(210, 222, 236), c2=(160, 176, 200), zapato=(240, 240, 240), edad=17),
    'policia': dict(piel=(210, 160, 122), pelo=(34, 26, 22), pelo_tipo='corto', ojos=(60, 40, 30), mujer=False,
                    ropa='uniforme', c1=(38, 52, 96), c2=(30, 40, 74), zapato=(24, 24, 28), gorra=True),
    'anciano': dict(piel=(226, 186, 160), pelo=(214, 214, 218), pelo_tipo='calvo', ojos=(70, 70, 80), mujer=False,
                    ropa='saco', c1=(122, 96, 72), c2=(86, 84, 92), zapato=(60, 40, 30), barba=True, lentes=True),
    'soldado': dict(piel=(186, 136, 100), pelo=(30, 24, 20), pelo_tipo='corto', ojos=(50, 36, 28), mujer=False,
                    ropa='militar', c1=(92, 104, 68), c2=(76, 86, 58), zapato=(40, 34, 28), casco=True),
    'nina': dict(piel=(200, 150, 112), pelo=(30, 22, 18), pelo_tipo='colitas', ojos=(50, 34, 26), mujer=True,
                 ropa='vestido', c1=(236, 120, 140), c2=(70, 90, 150), zapato=(230, 70, 80), nino=True),
}


def figura(nombre, u=240, expr='neutra', brazo='abajo', rim=(255, 186, 120)):
    """Devuelve una imagen RGBA del personaje de pie, de frente, un poco girado (3/4). u = alto de la cabeza."""
    C = PERSONAS[nombre]
    nino = C.get('nino')
    if nino:
        u = u * 0.8
    alto = (5.6 if nino else 7.6) * u
    Wc, Hc = int(3.4 * u), int(alto + 0.6 * u)
    im = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = Wc / 2
    e = 0.72 if nino else 1.0                 # escala del cuerpo bajo la cabeza
    y_hom = 1.75 * u
    y_cin = y_hom + 1.55 * u * e
    y_cad = y_hom + 2.25 * u * e
    y_rod = y_cad + 1.6 * u * e
    y_tob = y_rod + 1.55 * u * e
    hw = (0.78 if C['mujer'] else 0.95) * u * (0.85 if nino else 1)
    piel, c1, c2 = C['piel'], C['c1'], C['c2']
    # ---- piernas
    for s in (-1, 1):
        a = (cx + s * 0.3 * u, y_cad)
        k = (cx + s * 0.36 * u, y_rod)
        b = (cx + s * 0.38 * u, y_tob)
        colp = piel if C['ropa'] == 'vestido' else c2
        miembro(d, a, k, 0.62 * u * e, 0.4 * u * e, colp if s > 0 else osc(colp, 0.88))
        miembro(d, k, b, 0.4 * u * e, 0.27 * u * e, colp if s > 0 else osc(colp, 0.88))
        z = C['zapato']
        x0, x1 = (b[0] - 0.17 * u, b[0] + 0.24 * u) if s > 0 else (b[0] - 0.24 * u, b[0] + 0.17 * u)
        d.rounded_rectangle([x0, b[1] - 0.06 * u, x1, b[1] + 0.2 * u], 0.12 * u, fill=z)
        d.rectangle([x0 + 0.03 * u, b[1] + 0.15 * u, x1 - 0.03 * u, b[1] + 0.2 * u], fill=osc(z, 0.6))
        d.ellipse([x0 + 0.08 * u, b[1] - 0.02 * u, x0 + 0.2 * u, b[1] + 0.05 * u], fill=osc(z, 1.25))
    if C['ropa'] in ('uniforme', 'militar', 'saco'):            # botas / ruedo del pantalón
        for s in (-1, 1):
            d.line([(cx + s * 0.38 * u - 0.14 * u, y_tob - 0.04 * u), (cx + s * 0.38 * u + 0.14 * u, y_tob - 0.04 * u)],
                   fill=osc(c2, 0.7), width=int(0.05 * u))
    hx, hy = cx, 0.95 * u
    hwid = 0.42 * u * (1.05 if nino else 1)
    if C['pelo_tipo'] == 'largo':                                            # pelo detrás
        d.polygon(curva([(hx - hwid * 1.15, hy - 0.2 * u), (hx + hwid * 1.15, hy - 0.2 * u), (hx + hwid * 1.25, hy + 1.25 * u),
                         (hx, hy + 1.35 * u), (hx - hwid * 1.25, hy + 1.25 * u)], 6), fill=osc(C['pelo'], 0.8))
    # ---- torso / ropa
    torso = [(cx - hw, y_hom + 0.15 * u), (cx - hw * 0.9, y_hom - 0.05 * u), (cx, y_hom - 0.12 * u),
             (cx + hw * 0.9, y_hom - 0.05 * u), (cx + hw, y_hom + 0.15 * u), (cx + hw * 0.72, y_cin),
             (cx + hw * 0.8, y_cad), (cx - hw * 0.8, y_cad), (cx - hw * 0.72, y_cin)]
    d.polygon(curva(torso, 6), fill=c1)
    if C['ropa'] == 'vestido':
        falda = [(cx - hw * 0.72, y_cin), (cx + hw * 0.72, y_cin), (cx + hw * 1.15, y_rod - 0.15 * u),
                 (cx, y_rod - 0.05 * u), (cx - hw * 1.15, y_rod - 0.15 * u)]
        d.polygon(curva(falda, 6), fill=c1)
        for k in (-0.5, 0.0, 0.45):                               # pliegues
            d.line([(cx + k * hw * 0.6, y_cin + 0.2 * u), (cx + k * hw * 1.1, y_rod - 0.2 * u)], fill=osc(c1, 0.86), width=int(0.04 * u))
        d.rectangle([cx - hw * 0.72, y_cin - 0.06 * u, cx + hw * 0.72, y_cin + 0.06 * u], fill=c2)
    else:
        d.rectangle([cx - hw * 0.8, y_cad - 0.25 * u, cx + hw * 0.8, y_cad], fill=c2)       # cadera del pantalón
        d.rectangle([cx - hw * 0.76, y_cin + 0.05 * u, cx + hw * 0.76, y_cin + 0.2 * u], fill=(30, 26, 24))   # cinturón
        d.rectangle([cx - 0.12 * u, y_cin + 0.06 * u, cx + 0.12 * u, y_cin + 0.19 * u], fill=(200, 180, 110))
        d.line([(cx, y_hom), (cx, y_cin)], fill=osc(c1, 0.75), width=int(0.04 * u))              # botonera
        for k in range(4):
            yb = y_hom + 0.25 * u + k * 0.32 * u
            d.ellipse([cx - 0.05 * u, yb, cx + 0.05 * u, yb + 0.1 * u], fill=osc(c1, 0.6))
        d.line([(cx - hw * 0.5, y_hom + 0.5 * u), (cx - hw * 0.3, y_cin - 0.1 * u)], fill=osc(c1, 0.85), width=int(0.04 * u))
        d.line([(cx + hw * 0.55, y_hom + 0.6 * u), (cx + hw * 0.35, y_cin - 0.2 * u)], fill=osc(c1, 0.85), width=int(0.04 * u))
    if C['ropa'] == 'uniforme':
        for s in (-1, 1):
            d.rounded_rectangle([cx + s * hw * 0.55 - 0.22 * u, y_hom + 0.35 * u, cx + s * hw * 0.55 + 0.22 * u, y_hom + 0.7 * u], 0.05 * u, fill=osc(c1, 0.85))
        d.polygon([(cx + hw * 0.45, y_hom + 0.32 * u), (cx + hw * 0.6, y_hom + 0.25 * u), (cx + hw * 0.62, y_hom + 0.45 * u)], fill=(212, 182, 80))
        d.rectangle([cx - hw * 0.95, y_hom + 0.95 * u, cx + hw * 0.95, y_hom + 1.08 * u], fill=(226, 222, 80))
    if C['ropa'] == 'militar':
        d.polygon(curva([(cx - hw * 0.85, y_hom + 0.2 * u), (cx + hw * 0.85, y_hom + 0.2 * u), (cx + hw * 0.8, y_cin + 0.1 * u),
                         (cx - hw * 0.8, y_cin + 0.1 * u)], 4), fill=(70, 78, 50))
        for k in range(2):
            for s in (-1, 1):
                d.rounded_rectangle([cx + s * hw * 0.45 - 0.2 * u, y_hom + 0.6 * u + k * 0.45 * u, cx + s * hw * 0.45 + 0.2 * u,
                                     y_hom + 0.95 * u + k * 0.45 * u], 0.05 * u, fill=(84, 94, 62))
    if C['ropa'] == 'saco':
        d.polygon([(cx - 0.15 * u, y_hom - 0.05 * u), (cx + 0.15 * u, y_hom - 0.05 * u), (cx + 0.05 * u, y_cin), (cx - 0.05 * u, y_cin)], fill=(230, 226, 214))
        for s in (-1, 1):
            d.polygon([(cx + s * 0.15 * u, y_hom - 0.05 * u), (cx + s * 0.45 * u, y_hom + 0.2 * u), (cx + s * 0.08 * u, y_cin)], fill=osc(c1, 0.82))
    # ---- brazos
    for s in (-1, 1):
        sh = (cx + s * hw * 0.92, y_hom + 0.2 * u)
        if brazo == 'arriba' and s > 0:
            el, wr = (cx + s * hw * 1.3, y_hom - 0.6 * u), (cx + s * hw * 1.2, y_hom - 1.5 * u)
        elif brazo == 'cintura' and s < 0:
            el, wr = (cx + s * hw * 1.45, y_hom + 1.0 * u), (cx + s * hw * 0.8, y_cin)
        else:
            el = (cx + s * hw * 1.1, y_hom + 1.3 * u * e)
            wr = (cx + s * hw * 1.05, y_hom + 2.35 * u * e)
        manga = c1 if C['ropa'] != 'vestido' else c1
        col = manga if s > 0 else osc(manga, 0.88)
        miembro(d, sh, el, 0.4 * u * e, 0.3 * u * e, col)
        larga = C['ropa'] != 'vestido'
        miembro(d, el, wr, 0.3 * u * e, 0.23 * u * e, col if larga else (piel if s > 0 else osc(piel, 0.9)))
        if not larga:
            miembro(d, sh, (sh[0] + (el[0] - sh[0]) * 0.5, sh[1] + (el[1] - sh[1]) * 0.5), 0.42 * u * e, 0.36 * u * e, col)
        hp = piel if s > 0 else osc(piel, 0.9)                 # mano con pulgar
        r = 0.16 * u * e
        d.ellipse([wr[0] - r, wr[1] - r * 0.6, wr[0] + r, wr[1] + r * 1.4], fill=hp)
        d.ellipse([wr[0] - s * r * 1.1 - r * 0.35, wr[1] - r * 0.2, wr[0] - s * r * 1.1 + r * 0.35, wr[1] + r * 0.8], fill=hp)
    # ---- cuello y cabeza
    d.polygon([(cx - 0.2 * u, y_hom - 0.5 * u), (cx + 0.2 * u, y_hom - 0.5 * u), (cx + 0.24 * u, y_hom), (cx - 0.24 * u, y_hom)], fill=osc(piel, 0.85))
    hx, hy = cx, 0.95 * u
    hwid = 0.42 * u * (1.05 if nino else 1)
    cara = [(hx - hwid, hy - 0.25 * u), (hx - hwid * 0.95, hy + 0.15 * u), (hx - hwid * 0.6, hy + 0.48 * u), (hx, hy + 0.6 * u),
            (hx + hwid * 0.6, hy + 0.48 * u), (hx + hwid * 0.95, hy + 0.15 * u), (hx + hwid, hy - 0.25 * u),
            (hx + hwid * 0.7, hy - 0.58 * u), (hx, hy - 0.66 * u), (hx - hwid * 0.7, hy - 0.58 * u)]
    for s in (-1, 1):                                                         # orejas
        d.ellipse([hx + s * hwid - 0.09 * u, hy - 0.1 * u, hx + s * hwid + 0.09 * u, hy + 0.14 * u], fill=osc(piel, 0.9))
    d.polygon(curva(cara, 8), fill=piel)
    # ojos
    for s in (-1, 1):
        ex, ey = hx + s * 0.17 * u, hy - 0.02 * u
        d.ellipse([ex - 0.085 * u, ey - 0.045 * u, ex + 0.085 * u, ey + 0.045 * u], fill=(248, 246, 242))
        d.ellipse([ex - 0.045 * u + 0.01 * u, ey - 0.045 * u, ex + 0.045 * u + 0.01 * u, ey + 0.045 * u], fill=C['ojos'])
        d.ellipse([ex - 0.022 * u + 0.01 * u, ey - 0.022 * u, ex + 0.022 * u + 0.01 * u, ey + 0.022 * u], fill=(20, 16, 14))
        d.ellipse([ex + 0.012 * u, ey - 0.03 * u, ex + 0.03 * u, ey - 0.012 * u], fill=(255, 255, 255))
        d.arc([ex - 0.09 * u, ey - 0.06 * u, ex + 0.09 * u, ey + 0.05 * u], 190, 350, fill=osc(piel, 0.45), width=int(0.022 * u))
        cej = osc(C['pelo'], 0.9) if C['pelo_tipo'] != 'calvo' else (170, 170, 175)
        y_c = ey - (0.14 if expr != 'miedo' else 0.17) * u
        inc = -0.045 * u if expr == 'miedo' else (0.04 * u if expr == 'enojo' else 0)
        d.polygon([(ex - s * 0.1 * u, y_c + 0.02 * u + inc), (ex + s * 0.1 * u, y_c - 0.005 * u), (ex + s * 0.1 * u, y_c + 0.025 * u),
                   (ex - s * 0.1 * u, y_c + 0.05 * u + inc)], fill=cej)
    # nariz y boca
    d.polygon([(hx + 0.01 * u, hy + 0.03 * u), (hx + 0.07 * u, hy + 0.2 * u), (hx - 0.03 * u, hy + 0.22 * u)], fill=osc(piel, 0.84))
    by = hy + 0.36 * u
    if expr == 'miedo':
        d.ellipse([hx - 0.07 * u, by - 0.04 * u, hx + 0.07 * u, by + 0.08 * u], fill=(90, 40, 40))
    else:
        d.chord([hx - 0.12 * u, by - 0.05 * u, hx + 0.12 * u, by + 0.05 * u], 180, 360, fill=osc(piel, 0.62) if not C['mujer'] else (176, 92, 92))
        d.chord([hx - 0.1 * u, by - 0.04 * u, hx + 0.1 * u, by + 0.07 * u], 0, 180, fill=osc(piel, 0.75) if not C['mujer'] else (200, 110, 110))
    if C['mujer'] and not nino:
        for s in (-1, 1):
            d.ellipse([hx + s * 0.27 * u - 0.07 * u, hy + 0.14 * u, hx + s * 0.27 * u + 0.07 * u, hy + 0.22 * u], fill=(236, 160, 150))
    if C.get('barba'):
        d.polygon(curva([(hx - hwid * 0.95, hy + 0.12 * u), (hx - hwid * 0.6, hy + 0.5 * u), (hx, hy + 0.72 * u),
                         (hx + hwid * 0.6, hy + 0.5 * u), (hx + hwid * 0.95, hy + 0.12 * u), (hx + 0.15 * u, hy + 0.3 * u),
                         (hx - 0.15 * u, hy + 0.3 * u)], 6), fill=C['pelo'])
        d.chord([hx - 0.1 * u, by - 0.03 * u, hx + 0.1 * u, by + 0.05 * u], 0, 360, fill=(150, 90, 90))
    if C.get('lentes'):
        for s in (-1, 1):
            ex = hx + s * 0.17 * u
            d.rounded_rectangle([ex - 0.12 * u, hy - 0.08 * u, ex + 0.12 * u, hy + 0.07 * u], 0.04 * u, outline=(50, 40, 34), width=int(0.025 * u))
        d.line([(hx - 0.05 * u, hy - 0.03 * u), (hx + 0.05 * u, hy - 0.03 * u)], fill=(50, 40, 34), width=int(0.02 * u))
    # pelo / gorra / casco
    pc = C['pelo']
    if C['pelo_tipo'] in ('largo', 'corto', 'colitas'):
        top = [(hx - hwid * 1.06, hy + (0.1 if C['pelo_tipo'] == 'largo' else -0.12) * u), (hx - hwid * 1.05, hy - 0.45 * u),
               (hx - hwid * 0.5, hy - 0.74 * u), (hx + hwid * 0.4, hy - 0.76 * u), (hx + hwid * 1.05, hy - 0.45 * u),
               (hx + hwid * 1.06, hy + (0.1 if C['pelo_tipo'] == 'largo' else -0.12) * u), (hx + hwid * 0.8, hy - 0.3 * u),
               (hx + hwid * 0.2, hy - 0.42 * u), (hx - hwid * 0.5, hy - 0.32 * u), (hx - hwid * 0.85, hy - 0.22 * u)]
        d.polygon(curva(top, 6), fill=pc)
        for k in range(6):                                                    # mechones de luz
            x0 = hx - hwid * 0.6 + k * hwid * 0.22
            d.arc([x0 - 0.2 * u, hy - 0.72 * u, x0 + 0.2 * u, hy - 0.1 * u], 200, 280, fill=osc(pc, 1.35), width=int(0.02 * u))
        if C['pelo_tipo'] == 'colitas':
            for s in (-1, 1):
                d.ellipse([hx + s * hwid * 1.2 - 0.18 * u, hy - 0.4 * u, hx + s * hwid * 1.2 + 0.18 * u, hy + 0.15 * u], fill=pc)
                d.ellipse([hx + s * hwid * 1.02 - 0.05 * u, hy - 0.32 * u, hx + s * hwid * 1.02 + 0.05 * u, hy - 0.2 * u], fill=(236, 120, 140))
    elif C['pelo_tipo'] == 'calvo':
        for s in (-1, 1):
            d.polygon(curva([(hx + s * hwid * 1.05, hy - 0.3 * u), (hx + s * hwid * 1.12, hy + 0.05 * u), (hx + s * hwid * 0.9, hy + 0.1 * u),
                             (hx + s * hwid * 0.92, hy - 0.25 * u)], 4), fill=pc)
    if C.get('gorra'):
        d.chord([hx - hwid * 1.08, hy - 0.86 * u, hx + hwid * 1.08, hy - 0.05 * u], 180, 360, fill=osc(c1, 0.8))
        d.rectangle([hx - hwid * 1.08, hy - 0.5 * u, hx + hwid * 1.08, hy - 0.4 * u], fill=(20, 22, 36))
        d.chord([hx - hwid * 0.9, hy - 0.5 * u, hx + hwid * 0.9, hy - 0.2 * u], 0, 180, fill=(18, 20, 32))
        d.polygon([(hx, hy - 0.8 * u), (hx + 0.09 * u, hy - 0.62 * u), (hx - 0.09 * u, hy - 0.62 * u)], fill=(212, 182, 80))
    if C.get('casco'):
        d.chord([hx - hwid * 1.25, hy - 0.95 * u, hx + hwid * 1.25, hy + 0.25 * u], 180, 360, fill=(84, 94, 60))
        d.rectangle([hx - hwid * 1.25, hy - 0.36 * u, hx + hwid * 1.25, hy - 0.3 * u], fill=(64, 72, 46))
        d.line([(hx - hwid * 1.0, hy - 0.33 * u), (hx - hwid * 0.95, hy + 0.45 * u)], fill=(40, 40, 30), width=int(0.025 * u))
    # ---- luz: sombra suave a la izquierda, borde de luz a la derecha
    A = im.split()[3]
    grad = Image.linear_gradient('L').rotate(90).resize(im.size)       # 255 izquierda → 0 derecha
    som = ImageChops.multiply(A, grad.point(lambda v: int(v * 0.28)))
    capa = Image.new('RGBA', im.size, (12, 14, 34, 0)); capa.putalpha(som)
    im = Image.alpha_composite(im, capa)
    k = max(3, int(0.03 * u))
    borde = ImageChops.subtract(A, ImageChops.offset(A, -k, 0)).filter(ImageFilter.GaussianBlur(1))
    rl = Image.new('RGBA', im.size, rim + (0,)); rl.putalpha(borde.point(lambda v: int(v * 0.9)))
    im = Image.alpha_composite(im, rl)
    im.putalpha(A)
    return im
