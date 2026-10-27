"""Detector de momentos fuertes: volumen (gritos/discusiones) + movimiento del chat + palabras clave del chat."""
import collections, re, statistics, subprocess
import numpy as np

CHAT_FUERTE = re.compile(r'jaj|jsjs|xd|😂|🤣|😱|🔥|😳|💀|pelea|se pele|se arm|grit|nomin|elimin|beso|traici|'
                         r'se fue|lloran|llor|qué pas|que pas|wtf|noo+|alv|ptm|ufff', re.I)


def loudness_por_segundo(path):
    """Volumen percibido (LUFS momentáneo) de cada segundo del archivo."""
    p = subprocess.run(['ffmpeg', '-nostats', '-i', path, '-map', '0:a:0?', '-af', 'ebur128=metadata=0', '-f', 'null', '-'],
                       capture_output=True, text=True)
    vals = collections.defaultdict(list)
    for m in re.finditer(r't:\s*([\d.]+)\s+TARGET.*?M:\s*(-?[\d.]+|-inf)', p.stderr):
        t, v = float(m.group(1)), m.group(2)
        vals[int(t)].append(-70.0 if v == '-inf' else float(v))
    n = max(vals) + 1 if vals else 0
    return np.array([max(vals[i]) if vals.get(i) else -70.0 for i in range(n)])


class Detector:
    """Guarda una línea base de las últimas ~2 horas para saber qué es 'normal' y qué es un pico."""

    def __init__(self):
        self.base_vol = collections.deque(maxlen=7200)
        self.base_chat = collections.deque(maxlen=720)   # mensajes por cada 10 s

    def _z(self, x, base, piso):
        if len(base) < 60:
            return 0.0
        med = statistics.median(base)
        mad = statistics.median(abs(b - med) for b in base) or piso
        return (x - med) / (1.4826 * mad)

    def analizar(self, vol, chat_ts, t0):
        """vol: volumen por segundo del pedazo; chat_ts: [(hora, texto)]; t0: hora de inicio del pedazo.
        Devuelve lista de (segundo, puntaje 0-100, detalle)."""
        n = len(vol)
        if n == 0:
            return []
        # volumen suavizado (ventana 4 s) y sostenido
        k = np.ones(4) / 4
        vs = np.convolve(vol, k, mode='same')
        # chat por bloques de 10 s
        bloques = collections.Counter(int((ts - t0) // 10) for ts, _ in chat_ts if 0 <= ts - t0 < n)
        fuertes = collections.Counter(int((ts - t0) // 10) for ts, tx in chat_ts if 0 <= ts - t0 < n and CHAT_FUERTE.search(tx))
        puntos = []
        for s in range(0, n, 2):
            zv = self._z(vs[s], self.base_vol, 3.0)
            b = s // 10
            # el chat reacciona con retraso: miramos 0-30 s después
            cnt = max((bloques.get(b + d, 0) for d in range(0, 4)), default=0)
            fz = sum(fuertes.get(b + d, 0) for d in range(0, 4))
            zc = self._z(cnt, self.base_chat, 1.0)
            raw = 0.55 * max(zv, 0) + 0.35 * max(zc, 0) + 0.1 * min(fz, 10)
            score = int(100 * (1 - np.exp(-raw / 2.2)))
            puntos.append((s, score, {'vol_z': round(float(zv), 1), 'chat_z': round(float(zc), 1), 'chat_fuerte': fz}))
        # actualizar línea base después de puntuar
        self.base_vol.extend(float(v) for v in vs if v > -69)
        for b in range(0, max(1, n // 10)):
            self.base_chat.append(bloques.get(b, 0))
        return puntos


def mejores(puntos, umbral, separacion):
    """Picos por encima del umbral, separados al menos `separacion` segundos."""
    elegidos = []
    for s, sc, d in sorted(puntos, key=lambda x: -x[1]):
        if sc < umbral:
            break
        if all(abs(s - e[0]) >= separacion for e in elegidos):
            elegidos.append((s, sc, d))
    return sorted(elegidos)
