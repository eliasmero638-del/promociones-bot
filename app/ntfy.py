"""Notificaciones al celular con la app gratuita ntfy (ntfy.sh). Sin número de teléfono."""
import requests
import config as C


def activo():
    return bool(C.get().get('ntfy_tema'))


def enviar(titulo, texto, link='', imagen='', tema=None, prioridad=4):
    t = tema or C.get().get('ntfy_tema', '')
    if not t:
        return False, 'ntfy no configurado'
    d = {'topic': t, 'title': titulo, 'message': texto, 'priority': prioridad, 'tags': ['fire']}
    if link:
        d['click'] = link
        d['actions'] = [{'action': 'view', 'label': 'Ver y decidir', 'url': link}]
    if imagen:
        d['attach'] = imagen
    try:
        r = requests.post(C.get().get('ntfy_servidor', 'https://ntfy.sh'), json=d, timeout=30)
        return r.status_code == 200, r.text[:200]
    except Exception as e:
        return False, str(e)[:200]
