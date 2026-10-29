"""Fuentes gratis y sin cuota para Ridmer: Wikipedia (casos reales) y Google Noticias (urgentes)."""
import random, re, time, html
import xml.etree.ElementTree as ET
import requests

UA = {'User-Agent': 'RidmerVideos/1.0 (https://github.com/eliasmero638-del/promociones-bot)'}
WIKI = 'https://es.wikipedia.org/w/api.php'
BUSQUEDAS = ['desaparición misteriosa', 'caso sin resolver', 'misterio sin resolver', 'sobrevivió accidente aéreo',
             'único superviviente', 'naufragio supervivientes', 'asesino en serie capturado', 'secuestro rescate',
             'fenómeno inexplicable', 'muerte misteriosa', 'expedición desaparecida', 'barco fantasma',
             'crimen sin resolver', 'leyenda urbana origen real', 'rescate milagroso', 'perdido en la selva sobrevivió',
             'mina rescate atrapados', 'avión desaparecido', 'fraude famoso estafador', 'fuga de prisión famosa']


def _get(params, timeout=30):
    p = dict(params, format='json', formatversion=2)
    return requests.get(WIKI, params=p, headers=UA, timeout=timeout).json()


def candidatos(n=10, excluir=''):
    """Artículos reales de Wikipedia con suficiente historia (título, intro, url)."""
    excl = excluir.lower()
    vistos, res = set(), []
    for q in random.sample(BUSQUEDAS, 4):
        try:
            r = _get({'action': 'query', 'list': 'search', 'srsearch': q, 'srlimit': 25, 'srnamespace': 0})
        except Exception:
            continue
        for it in r.get('query', {}).get('search', []):
            t = it['title']
            if t in vistos or t.lower()[:30] in excl or it.get('size', 0) < 9000 or t.startswith(('Anexo', 'Lista')):
                continue
            vistos.add(t)
            res.append(t)
    random.shuffle(res)
    out = []
    for t in res[:n * 2]:
        try:
            r = _get({'action': 'query', 'prop': 'extracts|info', 'exintro': 1, 'explaintext': 1, 'titles': t,
                      'inprop': 'url', 'redirects': 1})
            pg = r['query']['pages'][0]
            intro = (pg.get('extract') or '').strip()
            if len(intro) > 250:
                out.append({'titulo': pg['title'], 'intro': intro[:900], 'url': pg.get('fullurl', '')})
        except Exception:
            continue
        if len(out) >= n:
            break
    return out


def articulo(titulo, max_chars=14000):
    """Texto completo del artículo + url + imágenes (urls de Commons)."""
    r = _get({'action': 'query', 'prop': 'extracts|info|images', 'explaintext': 1, 'titles': titulo, 'inprop': 'url',
              'redirects': 1, 'imlimit': 30})
    pg = r['query']['pages'][0]
    texto = re.sub(r'\n==+ (Referencias|Enlaces externos|Véase también|Bibliografía|Notas) ==+[\s\S]*', '',
                   pg.get('extract') or '')
    imgs = []
    nombres = [i['title'] for i in pg.get('images', []) if re.search(r'\.(jpe?g|png)$', i['title'], re.I)
               and not re.search(r'(?i)logo|icon|flag|bandera|escudo|commons-|wiki|symbol|map_', i['title'])]
    if nombres:
        try:
            ri = _get({'action': 'query', 'prop': 'imageinfo', 'iiprop': 'url|size', 'iiurlwidth': 1600,
                       'titles': '|'.join(nombres[:20])})
            for p in ri['query']['pages']:
                ii = (p.get('imageinfo') or [{}])[0]
                if ii.get('width', 0) >= 500:
                    imgs.append(ii.get('thumburl') or ii.get('url'))
        except Exception:
            pass
    return {'titulo': pg.get('title', titulo), 'texto': texto[:max_chars], 'url': pg.get('fullurl', ''), 'imagenes': imgs}


CONSULTA_EN = ('earthquake OR tsunami OR eruption OR hurricane OR disaster OR attack OR explosion OR dies OR "has died" '
               'OR "dead at"')
CONSULTA_URG = ('terremoto OR sismo OR tsunami OR erupción OR huracán OR catástrofe OR tragedia OR atentado OR '
                'explosión OR "muere" OR "murió" OR "fallece" OR "falleció"')


def noticias(q=CONSULTA_URG, horas=24, region='EC'):
    """Titulares de Google Noticias publicados DE VERDAD en las últimas `horas` (se revisa la fecha de cada uno)."""
    from email.utils import parsedate_to_datetime
    from datetime import timezone
    url = ('https://news.google.com/rss/search?q=' + requests.utils.quote(f'{q} when:{max(1, int(horas))}h') +
           ('&hl=es-419&gl=EC&ceid=EC:es-419' if region == 'EC' else '&hl=en-US&gl=US&ceid=US:en'))
    try:
        raiz = ET.fromstring(requests.get(url, headers=UA, timeout=30).content)
    except Exception:
        return []
    out, ahora = [], time.time()
    for it in raiz.iter('item'):
        try:
            fh = parsedate_to_datetime(it.findtext('pubDate') or '')
            if fh.tzinfo is None:
                fh = fh.replace(tzinfo=timezone.utc)
            edad = (ahora - fh.timestamp()) / 3600
        except Exception:
            continue                                   # sin fecha = no se usa
        if edad < -1 or edad > horas:
            continue
        out.append({'titulo': html.unescape(it.findtext('title') or ''),
                    'fecha': it.findtext('pubDate') or '', 'edad_h': round(edad, 1), 'region': region,
                    'fuente': (it.find('source').text if it.find('source') is not None else ''),
                    'url': it.findtext('link') or '',
                    'resumen': re.sub('<[^>]+>', ' ', html.unescape(it.findtext('description') or ''))[:300]})
    return out[:40]
