"""18-nov: genera narración con la voz clonada del dueño (Chatterbox Multilingual, CPU). Corre en /opt/vozclon.
Uso: voz_gen.py REFERENCIA.wav TEXTO.txt SALIDA.wav [EMOCION 0-1] [CFG 0-1]"""
import re, sys, torch, torchaudio as ta
_load = torch.load
torch.load = lambda *a, **k: _load(*a, **{**k, 'map_location': 'cpu'})     # los pesos vienen guardados para GPU
import perth
if getattr(perth, 'PerthImplicitWatermarker', None) is None:        # 18-nov: en el servidor la marca de agua no carga; se usa la vacía
    perth.PerthImplicitWatermarker = perth.DummyWatermarker
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

torch.set_num_threads(max(1, torch.get_num_threads()))
ref, txt, out = sys.argv[1:4]
EX = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
CF = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
texto = open(txt, encoding='utf-8').read().strip()
frases, act = [], ''
for f in re.split(r'(?<=[.!?…])\s+', texto):           # trozos cortos: suena más natural y no se traba
    if len(act) + len(f) < 220:
        act = (act + ' ' + f).strip()
    else:
        if act: frases.append(act)
        act = f
if act: frases.append(act)
m = ChatterboxMultilingualTTS.from_pretrained(device='cpu')
partes = []
for i, f in enumerate(frases):
    w = m.generate(f, language_id='es', audio_prompt_path=ref, exaggeration=EX, cfg_weight=CF, temperature=0.75)
    partes += [w, torch.zeros(1, int(m.sr * 0.35))]
    print(f'frase {i + 1}/{len(frases)} lista', flush=True)
ta.save(out, torch.cat(partes, dim=1), m.sr)
