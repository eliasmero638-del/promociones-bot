"""Genera pistas de música cinematográfica propias (sin derechos de autor) en assets/musica/.
Uso: python3 tools/musica_cine.py"""
import os, subprocess
import numpy as np

SR = 44100
DUR = 96.0
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'musica')
rng = np.random.default_rng(5)
t = np.arange(int(SR * DUR)) / SR


def lp(x, a):            # filtro pasa-bajos simple (a pequeño = más oscuro)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y


def lp_fast(x, a):
    from scipy.signal import lfilter
    return lfilter([a], [1, a - 1], x)


try:
    import scipy  # noqa
    LP = lp_fast
except Exception:
    LP = lp


def saw(f, tt, det=0.0):
    ph = (f * (1 + det)) * tt
    return 2 * (ph - np.floor(ph + 0.5))


def env(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def golpe(f0=110, f1=42, d=1.2, ruido=0.25):
    n = int(SR * d); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt * 18)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 3.5)
    s += ruido * rng.standard_normal(n) * np.exp(-tt * 40)
    return s


def poner(buf, x, t0, g=1.0):
    i = int(t0 * SR)
    j = min(len(buf), i + len(x))
    if i < len(buf):
        buf[i:j] += g * x[:j - i]


def pad(freqs, tt, oscuro=0.004):
    s = sum(saw(f, tt, d) for f in freqs for d in (-0.004, 0.0, 0.005))
    return LP(s, oscuro)


def guardar(nombre, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    os.makedirs(BASE, exist_ok=True)
    wav = os.path.join(BASE, nombre + '.wav')
    import wave
    st = np.stack([x, np.roll(x, int(SR * 0.012))], 1)          # estéreo leve
    with wave.open(wav, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-af', 'afade=t=in:d=0.05,loudnorm=I=-16:TP=-1.5',
                    '-b:a', '192k', os.path.join(BASE, nombre + '.mp3')], check=True)
    os.remove(wav)
    print('ok', nombre)


# 1) TENSIÓN: dron grave + pulso tipo latido + cuerdas en trémolo que suben
x = np.zeros_like(t)
x += 0.5 * pad([55, 82.4], t, 0.003)
x += 0.15 * pad([220, 261.6, 311.1], t, 0.01) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 24 - 1.5)) * (1 + 0.35 * np.sin(2 * np.pi * 9 * t))
for b in np.arange(0, DUR, 1.0):
    poner(x, golpe(90, 40, 0.9, 0.1), b, 0.9)
    poner(x, golpe(80, 38, 0.6, 0.05), b + 0.28, 0.5)
for b in np.arange(8, DUR, 16):
    poner(x, golpe(160, 35, 2.2, 0.5), b, 1.3)
guardar('tension', x)

# 2) ÉPICO: tambores tipo taiko + acordes oscuros (Am - F - C - E)
x = np.zeros_like(t)
acordes = [[110, 130.8, 164.8], [87.3, 110, 130.8], [65.4, 98, 130.8], [82.4, 103.8, 123.5]]
for k, a0 in enumerate(np.arange(0, DUR, 4.0)):
    n = int(4.0 * SR); tt = np.arange(n) / SR
    ch = pad(acordes[k % 4], tt, 0.006) * env(n, 0.4, 0.6)
    poner(x, 0.45 * ch, a0)
patron = [0, 0.75, 1.5, 2.0, 2.5, 3.0, 3.25, 3.5]
for b in np.arange(0, DUR, 4.0):
    for p_ in patron:
        poner(x, golpe(120, 45, 1.0, 0.35), b + p_, 0.8 if p_ in (0, 2.0) else 0.5)
guardar('epico', x)

# 3) MISTERIO: arpegio menor tipo piano + colchón suave
x = np.zeros_like(t)
x += 0.25 * pad([73.4, 110], t, 0.002)
notas = [220, 261.6, 329.6, 392, 329.6, 261.6, 246.9, 293.7]
for k, b in enumerate(np.arange(0, DUR, 0.5)):
    f = notas[k % len(notas)] * (0.5 if (k // 16) % 2 else 1)
    n = int(1.6 * SR); tt = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * 2.6)
    poner(x, 0.35 * s, b)
guardar('misterio', x)
