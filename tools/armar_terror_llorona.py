"""Arma el Short de prueba del canal de terror: La Llorona (escenas dibujadas + voz Gemini + lamento + susto)."""
import json, os, subprocess, sys
APP = '/tmp/claude-0/-home-claude/892f978d-49cb-5753-ad70-2df73d3cf53c/scratchpad/clipero/repo/app'
sys.path.insert(0, APP)
import dibujos, terror, montaje  # noqa: E401

M = sys.argv[1]            # material/2026-11-06
O = os.path.abspath(sys.argv[2])
os.makedirs(O, exist_ok=True)
W, H = 1080, 1920
SFX = montaje.SFX


def sh(c):
    subprocess.run(c, check=True)


EID = sys.argv[3] if len(sys.argv) > 3 else 'ter2'
info = json.load(open(f'{M}/{EID}/info.json'))
segs = info['segmentos']
dur_voz = info['duracion_voz']
sh(['ffmpeg', '-v', 'error', '-y', '-i', f'{M}/{EID}/voz.flac', '-ar', '48000', '-ac', '1', f'{O}/voz.wav'])
hb = json.load(open(f'{M}/ter1b/info.json'))['hook_fin']
sh(['ffmpeg', '-v', 'error', '-y', '-i', f'{M}/ter1b/voz.flac', '-t', f'{hb:.2f}', '-af', 'afade=t=out:st=%.2f:d=0.4' % max(0, hb - 0.4), '-ar', '48000', '-ac', '1', f'{O}/llanto.wav'])
d_llanto = montaje.dur(f'{O}/llanto.wav')

# hueco para el lamento: después del segmento 5 ("...gritando entre los árboles")
corte = segs[6]['t0']
HUECO = d_llanto + 0.4
pal = []
for a, b, w in info['palabras']:
    if a >= corte - 0.05:
        a, b = a + HUECO, b + HUECO
    w = {'busquéis.': 'busques.', 'busquéis': 'busques'}.get(w, w)
    pal.append((a, b, w))
t0 = [s['t0'] if s['t0'] < corte - 0.05 else s['t0'] + HUECO for s in segs]
COLA = 2.6                                                   # el susto va después de la última frase
fin_voz = dur_voz + HUECO
total = fin_voz + COLA

# voz con el hueco + un poco de eco
sh(['ffmpeg', '-v', 'error', '-y', '-i', f'{O}/voz.wav', '-filter_complex',
    f"[0:a]atrim=0:{corte:.3f},asetpts=PTS-STARTPTS[a];[0:a]atrim={corte:.3f},asetpts=PTS-STARTPTS[b];"
    f"anullsrc=r=48000:cl=mono,atrim=0:{HUECO:.3f}[s];[a][s][b]concat=n=3:v=0:a=1,aecho=0.8:0.6:60|120:0.25|0.12[v]",
    '-map', '[v]', f'{O}/voz_h.wav'])

# escenas (cada una cubre su segmento + 0.5 s de transición)
plan = [('rio', 'llorona'), ('pueblo', 'noche'), ('pueblo', 'abandono'), ('rio', 'orilla'), ('rio', 'salpica'),
        ('rio', 'cerca'), ('bosque', 'lejos'), ('bosque', 'oscuro'), ('bosque', 'oscuro')]
inicios = list(t0)
inicios[6] = corte + 0.0                                     # durante el lamento ya se ve el bosque? no: la mujer cerca
inicios[6] = t0[6]
fines = inicios[1:] + [fin_voz]
fines[5] = t0[6]                                             # la mujer de cerca dura hasta que vuelve la voz (cubre el lamento)
clips = []
for k, ((nom, ev), a, b) in enumerate(zip(plan, inicios, fines)):
    d = b - a + 0.5
    sal = f'{O}/anim_{k:02d}.mp4'
    if not os.path.exists(sal):
        dibujos.escena(nom, sal, d, W, H, evento=ev)
    clips.append((sal, b - a))
dibujos.escena('susto', f'{O}/anim_99.mp4', COLA + 0.2, W, H) if not os.path.exists(f'{O}/anim_99.mp4') else None
clips.append((f'{O}/anim_99.mp4', COLA))

# unir: fundidos a negro suaves; el susto entra de golpe
ins, fc, prev, off = [], '', '[0:v]', 0.0
for c, _ in clips:
    ins += ['-i', c]
for i in range(1, len(clips)):
    off += clips[i - 1][1]
    if i == len(clips) - 1:
        fc += f"{prev}[{i}:v]xfade=transition=fade:duration=0.04:offset={off - 0.04:.3f}[x{i}];"
    else:
        tr = 'fadeblack' if i in (1, 3, 6, 7) else 'fade'
        fc += f"{prev}[{i}:v]xfade=transition={tr}:duration=0.45:offset={off:.3f}[x{i}];"
    prev = f'[x{i}]'
sh(['ffmpeg', '-v', 'error', '-y'] + ins + ['-filter_complex', fc.rstrip(';') + f";{prev}eq=saturation=0.85,vignette=PI/4,"
    f"noise=alls=9:allf=t,fps=30,format=yuv420p[v]", '-map', '[v]', '-t', f'{total:.3f}', '-c:v', 'libx264', '-preset',
    'veryfast', '-crf', '19', f'{O}/cuerpo.mp4'])

# audio: voz + música + viento + lamento con eco + latido + subida + golpe del susto
t_llanto = corte + 0.15
t_lat = t0[7]
t_susto = fin_voz + 0.18
fa = (f"[0:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={total:.2f},volume=1.25[v];"
      f"[1:a]atrim=0:{total:.2f},volume=0.16,afade=t=in:d=2,volume='if(gt(t,{t_lat - 0.5:.2f}),0.5,1)':eval=frame[m];"
      f"anoisesrc=color=brown:a=0.5:r=48000,lowpass=f=380,atrim=0:{total:.2f},volume=0.10,aformat=channel_layouts=stereo[w];"
      f"[2:a]aecho=0.8:0.85:300|600:0.45|0.3,volume=1.1,adelay={int(t_llanto * 1000)}|{int(t_llanto * 1000)}[ll];"
      f"[3:a]volume=0.9,atrim=0:{fin_voz - t_lat + 0.2:.2f},adelay={int(t_lat * 1000)}|{int(t_lat * 1000)}[lat];"
      f"[4:a]volume=0.5,adelay={int((t_susto - 2.0) * 1000)}|{int((t_susto - 2.0) * 1000)}[ris];"
      f"[5:a]volume=1.0,adelay={int(t_susto * 1000)}|{int(t_susto * 1000)}[g1];"
      f"[6:a]volume=0.9,adelay={int(t_susto * 1000)}|{int(t_susto * 1000)}[g2];"
      f"[v][m][w][ll][lat][ris][g1][g2]amix=inputs=8:normalize=0:duration=first,atrim=0:{total:.2f},"
      f"loudnorm=I=-14:TP=-1.0:LRA=11[a]")
sh(['ffmpeg', '-v', 'error', '-y', '-i', f'{O}/voz_h.wav', '-stream_loop', '-1', '-i', montaje.MUSICA, '-i', f'{O}/llanto.wav',
    '-stream_loop', '-1', '-i', os.path.join(SFX, 'heart_slow.mp3'), '-i', os.path.join(SFX, 'riser2.mp3'),
    '-i', os.path.join(SFX, 'golpe_terror.mp3'), '-i', os.path.join(SFX, 'susp_impact.mp3'),
    '-filter_complex', fa, '-map', '[a]', '-ar', '48000', '-ac', '2', f'{O}/mezcla.wav'])

# subtítulos (palabra por palabra) + título los primeros segundos
ass = f'{O}/subs.ass'
montaje._ass(pal, W, H, 'LA LLORONA', ass, rotulos=[(a, b, '') for a, b in zip(inicios, fines)])
open(ass, 'w').write(''.join(l for l in open(ass) if not l.rstrip().endswith(',RIDMER')))   # sin la marca de Ridmer
sh(['ffmpeg', '-v', 'error', '-y', '-i', f'{O}/cuerpo.mp4', '-i', f'{O}/mezcla.wav', '-filter_complex',
    f"[0:v]subtitles='{ass}':fontsdir='{os.path.dirname(montaje.FUENTE)}',format=yuv420p[v]", '-map', '[v]', '-map', '1:a',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
    '-t', f'{total:.3f}', f'{O}/La_Llorona_prueba.mp4'])
print('listo', round(total, 1), 's')
