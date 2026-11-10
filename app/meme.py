"""Clips en formato MEME (pedido del dueño, 10-nov): franja negra arriba con una frase cómica en letra blanca grande
(con emojis a color) y abajo el momento de cerca, vertical, 5-25 s, audio original, sin música ni subtítulos.
Lo que pega: caras/reacciones fuertes + una frase del día a día ("Tu pana que…", "Yo cuando…", "Cómo será que…")."""
import os, re, subprocess
from PIL import Image, ImageDraw, ImageFont

APP = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(APP, '..', 'assets')
LETRA = next((p for p in (os.path.join(ASSETS, 'InterDisplay-Black.otf'),
                          '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf') if os.path.exists(p)), None)
EMOJI = next((p for p in (os.path.join(ASSETS, 'NotoColorEmoji.ttf'),
                          '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf') if os.path.exists(p)), None)
W, H = 720, 1280
FRANJA = 400                     # alto de la franja negra de arriba
_EMO = re.compile('([\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]+)')


def _trozos(linea):
    """Parte una línea en texto normal y emojis."""
    return [(t, bool(_EMO.fullmatch(t))) for t in _EMO.split(linea) if t]


def _ancho(linea, f, fe, k):
    w = 0
    for t, es_emo in _trozos(linea):
        if es_emo:
            w += len(t.replace('️', '').replace('‍', '')) * 109 * k + 6
        else:
            w += f.getlength(t)
    return w


def franja(frase, path):
    """PNG 720x400 negro con la frase centrada (se achica sola para que entre)."""
    frase = re.sub(r'\s+', ' ', frase).strip()
    fe = ImageFont.truetype(EMOJI, 109) if EMOJI else None
    if not fe:
        frase = _EMO.sub('', frase).strip()
    for tam in range(92, 34, -4):
        f = ImageFont.truetype(LETRA, tam)
        k = tam / 109 * 0.95
        lineas, act = [], ''
        for p in frase.split(' '):
            prueba = (act + ' ' + p).strip()
            if _ancho(prueba, f, fe, k) <= W - 50:
                act = prueba
            else:
                if act:
                    lineas.append(act)
                act = p
        if act:
            lineas.append(act)
        alto = len(lineas) * tam * 1.18
        if alto <= FRANJA - 40 and all(_ancho(l, f, fe, k) <= W - 40 for l in lineas):
            break
    im = Image.new('RGB', (W, FRANJA), (0, 0, 0))
    d = ImageDraw.Draw(im)
    y = (FRANJA - alto) / 2
    for l in lineas:
        x = (W - _ancho(l, f, fe, k)) / 2
        for t, es_emo in _trozos(l):
            if es_emo and fe:
                for ch in t.replace('️', '').replace('‍', ''):
                    e = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
                    ImageDraw.Draw(e).text((0, 0), ch, font=fe, embedded_color=True)
                    e = e.crop(e.getbbox() or (0, 0, 1, 1))
                    lado = int(tam * 1.0)
                    e = e.resize((lado, int(lado * e.size[1] / max(1, e.size[0]))), Image.LANCZOS)
                    im.paste(e, (int(x), int(y + tam * 0.08)), e)
                    x += lado + 6
            elif not es_emo:
                d.text((x, y), t, font=f, fill=(255, 255, 255))
                x += f.getlength(t)
        y += tam * 1.18
    im.save(path)
    return path


def hacer(entrada, ini, fin, frase, cara_x, salida):
    """entrada: video horizontal del momento. ini/fin en segundos de ese video. cara_x: 0-1 dónde está la cara."""
    dur = max(3.0, min(30.0, fin - ini))
    png = salida.replace('.mp4', '_franja.png')
    franja(frase, png)
    abajo = H - FRANJA                                         # 880 px para el video
    try:
        cx = max(0.0, min(1.0, float(cara_x)))
    except Exception:
        cx = 0.5
    # recorte del video original con la proporción de la zona de abajo (720x880), centrado en la cara
    crop = (f"crop=w='min(iw,ih*{W}/{abajo})':h=ih:"
            f"x='max(0,min(iw-ow,iw*{cx:.3f}-ow/2))':y=0,scale={W}:{abajo},setsar=1")
    fc = (f"[0:v]{crop}[v];[1:v]scale={W}:{FRANJA}[t];"
          f"[t][v]vstack=inputs=2,format=yuv420p[o]")
    r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{max(0.0, ini):.2f}', '-t', f'{dur:.2f}', '-i', entrada,
                        '-loop', '1', '-t', f'{dur:.2f}', '-i', png, '-filter_complex', fc, '-map', '[o]', '-map', '0:a?',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-maxrate', '3M', '-bufsize', '6M',
                        '-c:a', 'aac', '-b:a', '128k', '-af', 'loudnorm=I=-14:TP=-1.5', '-shortest',
                        '-movflags', '+faststart', salida], capture_output=True, text=True)
    try:
        os.remove(png)
    except Exception:
        pass
    if r.returncode != 0:
        print('[meme] error', r.stderr[-400:], flush=True)
        return None
    return salida
