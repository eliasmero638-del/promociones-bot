"""Foto con historia para Ridmer TV (11-nov). Facebook también paga las FOTOS con la monetización de contenido.
Uso: python3 tools/foto_post.py foto_real.jpg "TITULAR CON *PALABRA* EN AMARILLO" salida/foto.jpg [foto2.jpg]
Hace una imagen 1080x1350: la foto real arriba (o dos fotos lado a lado) y abajo una franja negra con el titular en
letra grande (las *palabras* van en amarillo). El texto largo de la historia va en "texto_foto" del plan."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

W, H, FR = 1080, 1350, 360
LETRA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'InterDisplay-Black.otf')


def hacer(foto, titular, salida, foto2=None):
    img = Image.new('RGB', (W, H), (0, 0, 0))
    alto = H - FR
    if foto2:
        a = ImageOps.fit(Image.open(foto).convert('RGB'), (W // 2 - 3, alto))
        b = ImageOps.fit(Image.open(foto2).convert('RGB'), (W // 2 - 3, alto))
        img.paste(a, (0, 0)); img.paste(b, (W // 2 + 3, 0))
    else:
        img.paste(ImageOps.fit(Image.open(foto).convert('RGB'), (W, alto), centering=(0.5, 0.4)), (0, 0))
    img = ImageEnhance.Contrast(img).enhance(1.06)
    d = ImageDraw.Draw(img)
    partes = [(t, i % 2 == 1) for i, t in enumerate(titular.split('*')) if t]
    palabras = [(w, am) for t, am in partes for w in t.split()]
    for tam in range(96, 40, -4):
        f = ImageFont.truetype(LETRA, tam)
        lineas, act, ancho = [], [], 0
        for w, am in palabras:
            lw = f.getlength(w + ' ')
            if act and ancho + lw > W - 70:
                lineas.append(act); act, ancho = [], 0
            act.append((w, am)); ancho += lw
        if act:
            lineas.append(act)
        if len(lineas) * tam * 1.15 <= FR - 50:
            break
    y = alto + (FR - len(lineas) * tam * 1.15) / 2
    for l in lineas:
        tw = sum(f.getlength(w + ' ') for w, _ in l) - f.getlength(' ')
        x = (W - tw) / 2
        for w, am in l:
            d.text((x, y), w, font=f, fill=(255, 214, 0) if am else (255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
            x += f.getlength(w + ' ')
        y += tam * 1.15
    d.rectangle([0, alto - 6, W, alto], fill=(220, 30, 30))
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    img.save(salida, quality=92)
    print(salida)


if __name__ == '__main__':
    hacer(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
