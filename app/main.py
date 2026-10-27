# Clipero (versión inicial): por ahora solo confirma que el servidor está vivo.
# Las funciones de grabar, detectar y enviar se agregan en las próximas versiones.
import os, time, json, datetime
DATA = os.environ.get('CLIPERO_DATA', '/var/lib/clipero')
while True:
    st = {'vivo': True, 'hora': datetime.datetime.now().isoformat(timespec='seconds'), 'version': 'v0-latido'}
    with open(os.path.join(DATA, 'estado.json'), 'w') as f: json.dump(st, f)
    time.sleep(60)
