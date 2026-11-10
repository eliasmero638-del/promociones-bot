"""Efectos de sonido propios (sin derechos) para suspenso: viento, tic-tac, estática de radio, obturador de cámara,
dron grave que crece, golpe sordo, susurro de aire, campanada lejana. Uso: python3 tools/sfx_cine.py"""
import os, subprocess, wave
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'sfx')
rng = np.random.default_rng(3)


def lp(x, a):
    from scipy.signal import lfilter
    return lfilter([a], [1, a - 1], x)


def guardar(nombre, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.85
    wav = os.path.join(OUT, nombre + '.wav')
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-b:a', '160k', os.path.join(OUT, nombre + '.mp3')], check=True)
    os.remove(wav)


def env(n, a, r):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr)
    return e


t = lambda d: np.arange(int(d * SR)) / SR
# viento: ruido filtrado con ráfaga
n = int(3.0 * SR); x = lp(rng.standard_normal(n), 0.02) * env(n, 1.0, 1.5) * (1 + 0.5 * np.sin(2 * np.pi * 0.7 * t(3.0)))
guardar('viento', x)
# tic-tac de reloj (2 s)
x = np.zeros(int(2.0 * SR))
for k, b in enumerate(np.arange(0, 2.0, 0.5)):
    i = int(b * SR); m = int(0.03 * SR)
    f = 3200 if k % 2 == 0 else 2600
    x[i:i + m] += np.sin(2 * np.pi * f * t(0.03)) * np.exp(-t(0.03) * 160)
guardar('tictac', x)
# estática de radio (1,2 s)
n = int(1.2 * SR); x = rng.standard_normal(n) * env(n, 0.05, 0.3) * (0.6 + 0.4 * (rng.random(n) > 0.97))
x = x - lp(x, 0.05)
guardar('estatica', x)
# obturador de cámara antigua
x = np.zeros(int(0.5 * SR))
for b in (0.0, 0.09):
    i = int(b * SR); m = int(0.05 * SR)
    x[i:i + m] += rng.standard_normal(m) * np.exp(-t(0.05) * 90)
guardar('camara', x - lp(x, 0.1))
# dron grave que crece (2,5 s)
tt = t(2.5); x = (np.sin(2 * np.pi * 45 * tt) + 0.5 * np.sin(2 * np.pi * 90.5 * tt) + 0.2 * lp(rng.standard_normal(len(tt)), 0.01) * 20)
x *= np.linspace(0, 1, len(tt)) ** 2 * env(len(tt), 0.01, 0.15)
guardar('dron', x)
# golpe sordo (bajo, corto)
tt = t(1.2); f = 38 + 70 * np.exp(-tt * 20)
x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4)
guardar('sordo', x)
# susurro de aire (paso rápido)
n = int(0.8 * SR); x = lp(rng.standard_normal(n), 0.12) * np.sin(np.linspace(0, np.pi, n)) ** 2
guardar('aire', x)
# campanada lejana
tt = t(3.0); x = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) * a for f, d, a in ((220, 1.2, 1), (553, 2.0, 0.5), (884, 2.8, 0.3)))
x = lp(x, 0.3)
guardar('campana', x)
print('ok')
