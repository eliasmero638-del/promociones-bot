"""Sube a la rama `entregas` los videos que Claude editó, para que el servidor los baje y entregue a su hora.

  python3 tools/entregar.py FECHA CARPETA_EID [CARPETA_EID ...]
Cada CARPETA_EID se llama como el eid (fb1, fb2, largo1…) y contiene fb.mp4/short.mp4/largo.mp4 + miniatura.jpg.
Reemplaza el contenido de la rama (no acumula videos viejos). Necesita estar dentro de un clon del repo.
"""
import json, os, shutil, subprocess, sys, tempfile

PARTE = 90 * 1024 * 1024


def sh(*c, cwd=None):
    subprocess.run(list(c), check=True, cwd=cwd)


def main():
    fecha, carpetas = sys.argv[1], sys.argv[2:]
    repo = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True, check=True).stdout.strip()
    tmp = tempfile.mkdtemp()
    sh('git', 'init', '-q', '-b', 'entregas', tmp)
    base = os.path.join(tmp, 'entregas', fecha)
    os.makedirs(base)
    videos = []
    for c in carpetas:
        eid = os.path.basename(os.path.normpath(c))
        archivos = {}
        for tipo in ('fb', 'short', 'largo'):
            mp4 = os.path.join(c, f'{tipo}.mp4')
            if not os.path.exists(mp4):
                continue
            partes, k = [], 0
            with open(mp4, 'rb') as f:
                while True:
                    b = f.read(PARTE)
                    if not b:
                        break
                    n = f'{eid}_{tipo}.mp4.{k:02d}'
                    open(os.path.join(base, n), 'wb').write(b)
                    partes.append(n); k += 1
            archivos[tipo] = partes
        shutil.copy(os.path.join(c, 'miniatura.jpg'), os.path.join(base, f'{eid}_miniatura.jpg'))
        guion = open(os.path.join(c, 'guion.txt')).read() if os.path.exists(os.path.join(c, 'guion.txt')) else ''
        cambios = json.load(open(os.path.join(c, 'cambios.json'))) if os.path.exists(os.path.join(c, 'cambios.json')) else {}
        videos.append({'eid': eid, 'archivos': archivos, 'miniatura': f'{eid}_miniatura.jpg', 'guion': guion,
                       'cambios': {k: cambios[k] for k in ('titulo_video', 'titulo_youtube', 'texto_facebook') if k in cambios}})
    json.dump({'fecha': fecha, 'videos': videos}, open(os.path.join(base, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
    sh('git', 'add', '-A', cwd=tmp)
    sh('git', '-c', 'user.name=Claude', '-c', 'user.email=noreply@anthropic.com', 'commit', '-q', '-m',
       f'Videos editados por Claude {fecha}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', cwd=tmp)
    sh('git', 'push', '-q', '-f', repo, 'entregas:entregas', cwd=tmp)
    print('subido:', [(v['eid'], list(v['archivos'])) for v in videos])


if __name__ == '__main__':
    main()
