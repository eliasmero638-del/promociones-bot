"""Avisos a tu WhatsApp personal con CallMeBot (gratis, solo texto, a tu propio número)."""
import requests
import config as C


def activo():
    c = C.get()
    return bool(c.get('wa_telefono') and c.get('wa_apikey'))


def enviar(texto, telefono=None, apikey=None):
    c = C.get()
    tel = (telefono or c.get('wa_telefono', '')).replace(' ', '')
    key = apikey or c.get('wa_apikey', '')
    if not (tel and key):
        return False, 'WhatsApp no configurado'
    try:
        r = requests.get('https://api.callmebot.com/whatsapp.php',
                         params={'phone': tel, 'text': texto[:1500], 'apikey': key}, timeout=60)
        ok = r.status_code == 200 and 'error' not in r.text.lower()[:300]
        return ok, r.text[:200]
    except Exception as e:
        return False, str(e)[:200]
