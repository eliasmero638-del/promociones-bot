"""Bot de Telegram: manda clips con botones y recibe comandos."""
import json, time, threading
import requests
import config as C

_offset = 0


def _api(metodo, **kw):
    tok = C.get()['telegram_token']
    if not tok:
        return None
    files = kw.pop('files', None)
    try:
        r = requests.post(f'https://api.telegram.org/bot{tok}/{metodo}', data=kw, files=files,
                          timeout=120 if files else 40)
        return r.json()
    except Exception as e:
        print('telegram error', metodo, e, flush=True)
        return None


def texto(msg, chat=None, botones=None):
    for c in ([chat] if chat else C.get()['chat_ids']):
        kw = {'chat_id': c, 'text': msg, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'}
        if botones:
            kw['reply_markup'] = json.dumps({'inline_keyboard': botones})
        _api('sendMessage', **kw)


def video(path, caption, clip_id):
    botones = [[{'text': '✅ Me lo quedo', 'callback_data': f'ok:{clip_id}'},
                {'text': '❌ Descartar', 'callback_data': f'no:{clip_id}'}]]
    for c in C.get()['chat_ids']:
        kw = dict(chat_id=c, caption=caption[:1000], parse_mode='HTML', supports_streaming='true', width='720', height='1280')
        if not C.get().get('solo_enviar'):
            kw['reply_markup'] = json.dumps({'inline_keyboard': botones})
        with open(path, 'rb') as f:
            _api('sendVideo', files={'video': f}, **kw)


def escuchar(manejador):
    """Lee mensajes y botones. manejador(tipo, chat_id, dato, raw)."""
    global _offset

    def bucle():
        global _offset
        while True:
            if not C.get()['telegram_token']:
                time.sleep(15); continue
            r = _api('getUpdates', offset=_offset, timeout=30)
            if not r or not r.get('ok'):
                time.sleep(5); continue
            for u in r['result']:
                _offset = u['update_id'] + 1
                try:
                    if 'message' in u and 'text' in u['message']:
                        m = u['message']
                        manejador('msg', m['chat']['id'], m['text'].strip(), m)
                    elif 'callback_query' in u:
                        q = u['callback_query']
                        _api('answerCallbackQuery', callback_query_id=q['id'])
                        manejador('boton', q['message']['chat']['id'], q.get('data', ''), q)
                except Exception as e:
                    print('error manejando update', e, flush=True)
    threading.Thread(target=bucle, daemon=True).start()


def editar_caption(q, extra):
    m = q['message']
    _api('editMessageCaption', chat_id=m['chat']['id'], message_id=m['message_id'],
         caption=(m.get('caption', '') + '\n\n' + extra)[:1000])
