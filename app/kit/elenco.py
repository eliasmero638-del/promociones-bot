"""Elenco del kit de terror: personajes de cuerpo entero (cuerpo con volumen de personajes2 + cara con rasgos de caras3),
con variantes para animar (parpadeo, boca hablando, miedo). Todo en caché."""
from PIL import Image
from . import personajes2 as P2, caras3 as C3

_cache = {}


def personaje(quien='beto', expr='normal', pose='quieto', alto=900, hablar=False, cerrados=False):
    clave = (quien, expr, pose, int(alto), hablar, cerrados)
    if clave in _cache:
        return _cache[clave]
    s = alto / 900
    if quien == 'beto':
        cuerpo = P2.don_beto(alto, 'normal', pose=pose, sin_cabeza=True)
        S = int(255 * s)
        cab = C3.cabeza('beto', expr, S, hablar=hablar, cerrados=cerrados)
        cy_body = 214 * s
    else:
        cuerpo = P2.cliente(alto, 'fijo', sin_cabeza=True)
        S = int(250 * s)
        cab = C3.cabeza('cliente', expr, S, hablar=hablar, cerrados=cerrados)
        cy_body = 222 * s
    out = cuerpo.copy()
    x = int(cuerpo.width / 2 - cab.width / 2)
    y = int(cy_body - cab.height * 0.46)
    ext = Image.new('RGBA', (cuerpo.width, cuerpo.height), (0, 0, 0, 0))
    ext.alpha_composite(cab, (max(0, x), max(0, y)) if x >= 0 and y >= 0 else (0, 0))
    if x < 0 or y < 0:
        big = Image.new('RGBA', (cuerpo.width + 400, cuerpo.height + 400), (0, 0, 0, 0))
        big.alpha_composite(cuerpo, (200, 200))
        big.alpha_composite(cab, (x + 200, y + 200))
        out = big.crop((200, 200, 200 + cuerpo.width, 200 + cuerpo.height))
    else:
        out.alpha_composite(ext)
    _cache[clave] = out
    return out
