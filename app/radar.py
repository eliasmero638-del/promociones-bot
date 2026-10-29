"""Radar Ridmer: de madrugada prepara los ENCARGOS del día para que Claude los edite.
Cada encargo trae: tema, texto fuente real (Wikipedia / noticias), fotos candidatas numeradas y una hoja de contacto."""
import json, os, re, time, random
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
import config as C, ia
import fuentes as wiki

DIR = os.path.join(C.DATA, 'encargos')
UA = {'User-Agent': 'RidmerVideos/1.0 (https://github.com/eliasmero638-del/promociones-bot)'}
FUENTE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'InterDisplay-Black.otf')


def log(*a):
    print(time.strftime('%H:%M:%S'), '[radar]', *a, flush=True)


def hay_largo(fecha):
    """Video largo un día sí y otro no."""
    return time.strptime(fecha, '%Y-%m-%d').tm_yday % 2 == 0


def _historial():
    try:
        return json.load(open(os.path.join(C.DATA, 'ridmer', 'historial.json'), encoding='utf-8'))
    except Exception:
        return []


def _commons(q, n=4):
    out = []
    try:
        r = requests.get('https://commons.wikimedia.org/w/api.php', headers=UA, timeout=30, params={
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': 10,
            'gsrsearch': f'{q} filetype:bitmap', 'prop': 'imageinfo', 'iiprop': 'url|size|mime', 'iiurlwidth': 1600}).json()
        for p in sorted((r.get('query') or {}).get('pages', {}).values(), key=lambda p: p.get('index', 99)):
            ii = (p.get('imageinfo') or [{}])[0]
            t = p.get('title', '').lower()
            if ii.get('mime') not in ('image/jpeg', 'image/png') or ii.get('width', 0) < 700:
                continue
            if re.search(r'logo|icon|flag|coat of arms|signature|diagram|map|chart|graph|\.svg|locator', t):
                continue
            out.append({'url': ii.get('thumburl') or ii.get('url'), 'desc': p.get('title', '')[5:90], 'q': q})
            if len(out) >= n:
                break
    except Exception as e:
        log('commons', q, e)
    return out


def _hoja(cands, carpeta):
    """Hoja de contacto numerada (para que Claude elija mirando)."""
    miniaturas = []
    for c in cands:
        try:
            r = requests.get(c['url'], headers=UA, timeout=40)
            im = Image.open(__import__('io').BytesIO(r.content)).convert('RGB')
            im.save(os.path.join(carpeta, f"c{c['n']:02d}.jpg"), quality=90)
            miniaturas.append((c['n'], ImageOps.fit(im, (400, 260))))
        except Exception:
            c['falla'] = True
    cols = 4
    filas = (len(miniaturas) + cols - 1) // cols or 1
    hoja = Image.new('RGB', (cols * 410 + 10, filas * 300 + 10), (20, 20, 20))
    d = ImageDraw.Draw(hoja)
    f = ImageFont.truetype(FUENTE, 40)
    for k, (n, im) in enumerate(miniaturas):
        x, y = 10 + (k % cols) * 410, 10 + (k // cols) * 300
        hoja.paste(im, (x, y))
        d.rectangle([x, y, x + 70, y + 50], fill=(220, 30, 30))
        d.text((x + 10, y + 3), str(n), font=f, fill=(255, 255, 255))
    hoja.save(os.path.join(carpeta, 'hoja.jpg'), quality=82)
    return [c for c in cands if not c.get('falla')]


def _consultas(titulo, texto):
    p = (f'Artículo: {titulo}\n{texto[:3000]}\n\nDame 7 búsquedas en INGLÉS para encontrar FOTOS REALES de este caso en '
         'Wikimedia Commons: personas reales, lugares reales, objetos, año. 2-5 palabras cada una, concretas. '
         'Responde SOLO JSON {"q": ["...", "..."]}')
    d = ia.groq_json(p, 0.3) if ia.groq_activa() else None
    qs = (d or {}).get('q') or []
    return [q for q in qs if isinstance(q, str)][:7] or [titulo]


def armar_encargo(eid, tipo, articulo_titulo, carpeta_dia, titulo_sugerido='', noticia=None):
    carpeta = os.path.join(carpeta_dia, eid)
    os.makedirs(carpeta, exist_ok=True)
    if noticia:
        texto = '\n'.join(f"- {x['titulo']} ({x['fuente']}, {x['fecha']}): {x['resumen']}" for x in noticia)
        url, imgs, titulo = noticia[0].get('url', ''), [], titulo_sugerido
    else:
        art = wiki.articulo(articulo_titulo)
        texto, url, imgs, titulo = art['texto'], art['url'], art['imagenes'], art['titulo']
    cands = [{'url': u, 'desc': 'foto del artículo', 'q': 'articulo'} for u in imgs[:8]]
    for q in _consultas(titulo, texto):
        cands += _commons(q, 3)
    vistos, unicos = set(), []
    for c in cands:
        if c['url'] not in vistos:
            vistos.add(c['url']); unicos.append(c)
    for n, c in enumerate(unicos[:24], 1):
        c['n'] = n
    unicos = _hoja(unicos[:24], carpeta)
    return {'eid': eid, 'tipo': tipo, 'titulo': titulo, 'titulo_sugerido': titulo_sugerido or titulo, 'fuente': url,
            'texto': texto[:9000], 'candidatos': [{'n': c['n'], 'desc': c['desc'], 'q': c['q']} for c in unicos],
            'hoja': f'{eid}/hoja.jpg'}


def preparar_dia(fecha=None):
    fecha = fecha or time.strftime('%Y-%m-%d')
    carpeta_dia = os.path.join(DIR, fecha)
    os.makedirs(carpeta_dia, exist_ok=True)
    hechos = ' '.join(h.get('titulo', '') for h in _historial()[-400:]).lower()
    encargos, n_fb = [], C.get().get('ridmer_fb_dia', 3)
    # 1) ¿noticia muy importante? ocupa el primer lugar
    try:
        import fabrica
        urg = fabrica.revisar_urgente()
        if urg and urg.get('noticias'):
            encargos.append(armar_encargo('fb1', 'fb', '', carpeta_dia, urg['titulo'], urg['noticias']))
    except Exception as e:
        log('urgente', e)
    # 2) casos reales de Wikipedia
    cands = wiki.candidatos(14, excluir=hechos)
    elegidos = []
    if cands and ia.groq_activa():
        lista = '\n'.join(f'{i}. {c["titulo"]}: {c["intro"][:300]}' for i, c in enumerate(cands))
        d = ia.groq_json('Canal de YouTube "Ridmer" (misterio, casos reales, sobrevivientes, sucesos extraños). '
                         'Ordena estos artículos REALES de más a menos impactante para un video viral '
                         '(misterio, giro, algo difícil de creer pero cierto). Descarta los aburridos.\n' + lista +
                         '\nResponde SOLO JSON {"orden": [números]}', 0.5)
        try:
            elegidos = [cands[i] for i in d['orden'] if isinstance(i, int) and i < len(cands)]
        except Exception:
            pass
    elegidos = elegidos or cands
    total = n_fb + (1 if hay_largo(fecha) else 0)
    k = 0
    for c in elegidos:
        if len(encargos) >= total:
            break
        tipo = 'fb' if sum(1 for e in encargos if e['tipo'] == 'fb') < n_fb else 'largo'
        eid = f"{tipo}{sum(1 for e in encargos if e['tipo'] == tipo) + 1}"
        try:
            encargos.append(armar_encargo(eid, tipo, c['titulo'], carpeta_dia))
            k += 1
        except Exception as e:
            log('encargo falló', c['titulo'], e)
    data = {'fecha': fecha, 'hay_largo': hay_largo(fecha), 'encargos': encargos, 'creado': time.time()}
    json.dump(data, open(os.path.join(carpeta_dia, 'encargos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('encargos listos', fecha, [e['eid'] + ': ' + e['titulo'] for e in encargos])
    return data


if __name__ == '__main__':
    import sys
    print(json.dumps(preparar_dia(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False)[:2000])
