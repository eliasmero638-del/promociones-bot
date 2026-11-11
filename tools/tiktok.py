"""Videos para TikTok (11-nov, pedido del dueño). Metricool (plan gratis: 20 publicaciones al mes) publica en TikTok desde un
link público; este script deja el video en la rama `tiktok` del repo (público) y da el link.
Plan del dueño: los ~15 AVANCES del mes (cada día de video largo, 19:30) + el MEJOR video de Facebook de la semana
(domingo 20:00). Nunca más de 20 al mes.

  python3 tools/tiktok.py guardar FECHA video.mp4 EID "título" "texto"   → comprime, sube y muestra el link público
  python3 tools/tiktok.py cuenta                                           → cuántas publicaciones de TikTok van este mes
  python3 tools/tiktok.py sumar EID                                        → anota una publicación programada
  python3 tools/tiktok.py indice                                           → lista de videos guardados (últimos 8 días)

La rama `tiktok` se rehace en UN solo commit (force push) con los videos de los últimos 8 días, para que el repo no crezca."""
import datetime, json, os, shutil, subprocess, sys, tempfile

REPO = 'https://github.com/eliasmero638-del/promociones-bot'
RAW = 'https://raw.githubusercontent.com/eliasmero638-del/promociones-bot/tiktok/'
LIMITE = 20


def _git(*a, cwd):
    subprocess.run(['git', *a], cwd=cwd, check=True, capture_output=True)


def _clonar():
    d = tempfile.mkdtemp(prefix='tt_')
    r = subprocess.run(['git', 'clone', '-q', '--depth', '1', '-b', 'tiktok', REPO, d], capture_output=True)
    if r.returncode != 0:                       # la rama todavía no existe
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        _git('init', '-q', cwd=d); _git('remote', 'add', 'origin', REPO, cwd=d)
    return d


def _publicar(d, msg):
    """Commit único (rama huérfana) con lo que hay en d."""
    tmp = tempfile.mkdtemp(prefix='tt2_')
    _git('init', '-q', cwd=tmp); _git('remote', 'add', 'origin', REPO, cwd=tmp)
    _git('checkout', '-q', '--orphan', 'tiktok', cwd=tmp)
    for x in os.listdir(d):
        if x != '.git':
            (shutil.copytree if os.path.isdir(os.path.join(d, x)) else shutil.copy)(os.path.join(d, x), os.path.join(tmp, x))
    _git('add', '-A', cwd=tmp)
    _git('-c', 'user.name=Claude', '-c', 'user.email=noreply@anthropic.com', 'commit', '-q', '-m', msg, cwd=tmp)
    # usa las credenciales del repo actual si las hay
    url = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True,
                         cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip() or REPO
    _git('push', '-q', '-f', url, 'tiktok', cwd=tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def _leer(d, nombre, defecto):
    p = os.path.join(d, nombre)
    return json.load(open(p)) if os.path.exists(p) else defecto


def guardar(fecha, video, eid, titulo='', texto=''):
    d = _clonar()
    limite = (datetime.date.fromisoformat(fecha) - datetime.timedelta(days=8)).isoformat()
    for x in list(os.listdir(d)):                                       # borrar lo de hace más de 8 días
        if x[:4].isdigit() and x < limite:
            shutil.rmtree(os.path.join(d, x), ignore_errors=True)
    os.makedirs(os.path.join(d, fecha), exist_ok=True)
    dst = os.path.join(d, fecha, f'{eid}.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vf', "scale='min(720,iw)':-2", '-c:v', 'libx264',
                    '-preset', 'veryfast', '-crf', '26', '-maxrate', '2500k', '-bufsize', '5000k', '-c:a', 'aac',
                    '-b:a', '128k', '-movflags', '+faststart', dst], check=True)
    if os.path.getsize(dst) > 48 * 1024 * 1024:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vf', "scale='min(540,iw)':-2", '-c:v', 'libx264',
                        '-preset', 'veryfast', '-crf', '30', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', dst],
                       check=True)
    idx = [x for x in _leer(d, 'indice.json', []) if x['fecha'] >= limite and not (x['fecha'] == fecha and x['eid'] == eid)]
    idx.append({'fecha': fecha, 'eid': eid, 'titulo': titulo, 'texto': texto, 'url': RAW + f'{fecha}/{eid}.mp4'})
    json.dump(idx, open(os.path.join(d, 'indice.json'), 'w'), ensure_ascii=False, indent=1)
    _publicar(d, f'tiktok {fecha} {eid}')
    shutil.rmtree(d, ignore_errors=True)
    print(RAW + f'{fecha}/{eid}.mp4')


def cuenta():
    d = _clonar()
    mes = datetime.date.today().strftime('%Y-%m')
    c = _leer(d, 'contador.json', {}).get(mes, [])
    shutil.rmtree(d, ignore_errors=True)
    print(f'{len(c)}/{LIMITE} publicaciones de TikTok en {mes}: {", ".join(c) or "ninguna"}')
    return len(c)


def sumar(eid):
    d = _clonar()
    mes = datetime.date.today().strftime('%Y-%m')
    c = _leer(d, 'contador.json', {})
    c.setdefault(mes, []).append(eid)
    json.dump({mes: c[mes]}, open(os.path.join(d, 'contador.json'), 'w'), ensure_ascii=False)
    _publicar(d, f'tiktok cuenta {mes} {eid}')
    shutil.rmtree(d, ignore_errors=True)
    print(f'{len(c[mes])}/{LIMITE} este mes')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'guardar':
        guardar(a[1], a[2], a[3], a[4] if len(a) > 4 else '', a[5] if len(a) > 5 else '')
    elif a and a[0] == 'cuenta':
        cuenta()
    elif a and a[0] == 'sumar':
        sumar(a[1])
    elif a and a[0] == 'indice':
        d = _clonar(); print(json.dumps(_leer(d, 'indice.json', []), ensure_ascii=False, indent=1)); shutil.rmtree(d)
    else:
        print(__doc__)
