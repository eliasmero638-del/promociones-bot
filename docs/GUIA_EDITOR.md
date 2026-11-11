# Guía del editor Ridmer (para Claude, tarea de cada mañana)

Tú (Claude) eres el EDITOR del canal de misterio "Ridmer" (YouTube 170 mil, Facebook "Ridmer TV").
El servidor ya preparó los ENCARGOS del día: tema real, texto fuente (Wikipedia o titulares) y una HOJA de fotos
candidatas numeradas. Tu trabajo: escribir el PLAN de edición (JSON). El servidor hace la voz (Gemini, Algenib),
prepara el MATERIAL (voz y fotos) y **TÚ armas y revisas cada video** (modo "claude"). El servidor solo los entrega.

## 🎬 EDICIÓN A MEDIDA (9-nov-2026) — EL DUEÑO LO EXIGE, MANDA SOBRE TODO
"Quedamos que tú ibas a editar todos los videos… no que inicie con las fotos." Cada video lo editas TÚ como un editor
humano, no solo eligiendo fotos para la plantilla:
1. **Videos del día:** fb1, fb2, fb3 (Facebook) + 2 Shorts: fb1s y fb2s (misma historia que fb1/fb2, reutiliza sus
   escenas) + largo1 SOLO los días que haya encargo de largo (día por medio). No hay sh1/sh2.
2. **Inicio cinematográfico OBLIGATORIO (segmento 0):** una escena animada A MEDIDA de 2,5–4 s escrita por ti con
   `app/plano.py` (estilo plano, personajes nuevos): acción repentina (algo cae, explota, corre, frena, un rayo, la
   cámara entra rápido con sacudida) + `P.titulo_golpe(...)` con el título. Pon `"titulo_video": ""` en cambios.json
   para que no salga el título dos veces. NUNCA empieces con una foto.
3. **2–4 escenas animadas más a medida** de los momentos clave de ESA historia (no las escenas genéricas de dibujos.py),
   mezcladas con fotos/videos reales. En cambios: `"dibujo": {"N": {"script": "esc_x.py"}}`. El script recibe
   `salida segundos W H` y hace `import plano as P` (editar.py ya pone app/ en el PYTHONPATH).
   Ejemplo completo y probado: `docs/ejemplos/jk_escenas.py` (avión en tormenta, rayo, caída, selva, contador de días).
   Piezas del kit: ciudad_noche, cielo_tormenta, nubes, lluvia, rayo, avion, selva, arroyo, mar, persona (policia,
   soldado, mujer, nino, anciano, encapuchado, medico, senor; poses camina/corre/apunta/rodilla/manos_arriba/cae/quieto,
   `mira='izq'`, `giro`), carro (normal o policía), faro, luces_policia, niebla, camara (zoom, paneo, sacudida),
   destello, vineta, titulo_golpe, grabar. Si algo no existe en el kit, dibújalo tú en el script con PIL.
4. **Música que se note:** en cambios.json `"musica": "tension" | "epico" | "misterio"` (pistas propias en
   assets/musica; ya bajan solas bajo la voz). Elige la que vaya con la historia.
5. **Revisa como editor:** genera cada escena, mira 4–5 cuadros con Read (personajes bien puestos, nada cortado, nada
   tapado), corrige y vuelve a generar. Después revisa `revision_*.jpg` del video final.
5b. **VIDEO REAL OBLIGATORIO (9-nov): mínimo 2–3 fragmentos de video por Facebook/Short y 5+ en el largo.** "Sin
   videos es un video muerto." En el plan: `{"tipo": "video", "url": "https://youtube.com/...", "desde": 12, "dur": 6}`
   (YouTube ahora lo baja el teléfono del dueño; TikTok/X/Facebook los baja el servidor) y SIEMPRE un respaldo libre:
   `"buscar_video": ["thunderstorm night", "Amazon rainforest"]` (Wikimedia Commons). Busca con WebSearch videos del
   hecho (noticieros, rescates, archivo) y elige segundos con acción.
5c. **Fotos reales con estilo (automático):** salen como polaroid que cae con cinta. Para un dato fuerte usa
   `"estilo_foto": {"N": "duo"}, "dato": {"N": "1 DE 92"}`; pie de foto: `"pie": {"N": "Juliane, hoy"}`.
5d. **Efectos de sonido (9-nov): suaves (ya están a la mitad) y que CONCUERDEN con la imagen.** Elige en cambios
   `"sfx": {"N": ...}`: trueno/lluvia/ventarron (tormentas), foto/pelicula (fotos y archivo), fuego, explosion,
   reloj (tiempo que pasa), corazon/susurro/grillos/cuervo (tensión, noche), terror/boom/drama (revelaciones),
   cine/subida/transicion (cortes). Nunca efectos de comedia.
6. **Subtítulos:** el transcriptor se equivoca con nombres ("Rhythmert" en vez de Ridmer, "Apocalpa" en vez de
   a Pucallpa). Lee las palabras de `info.json` y corrígelas en cambios: `"corregir": {"Rhythmert": "Ridmer",
   "#57": ""}` ("#N" = la palabra número N; "" la borra).
7. **Tiempo:** cada Facebook con 6–7 animaciones tarda ~12 min en generarse. En los Shorts NO vuelvas a generar las
   animaciones: reutiliza las del Facebook con `"dibujo": {"0": {"mp4": "<salida>/fb1/anim_00.mp4"}}`.
8. Si se acaba el tiempo, prioriza: fb1 + fb1s completos y bien hechos antes que todo a medias.

## ⚠️ LO QUE DICEN LOS NÚMEROS DE FACEBOOK (9-nov-2026) — MANDA SOBRE TODO LO DEMÁS
- Los Reels de Ridmer TV duran ~1:20 y la gente los mira **2 a 6 segundos** en promedio: desliza al inicio y Facebook
  deja de mostrarlos (quedan en 3–20 vistas). El problema es el COMIENZO.
- Los que pasaron de 700–1.300 vistas: soldado que peleó 29 años (Onoda), notas en código del FBI, cazas detrás de un
  ovni, fin del mundo predicho por la ciencia, chica que cayó de un avión y sobrevivió. Los de crímenes, secuestros,
  narcos y asesinatos quedaron en 3–10 vistas.
- Reglas desde hoy:
  1. **Segundo 0 en plena acción**: el primer segmento es un video real del hecho o una escena dibujada EN MOVIMIENTO
     (nunca una foto quieta) y la primera frase es la más fuerte de la historia, de 3 a 7 palabras
     (ej.: "Cayó de un avión a 3.000 metros…"). Nada de contexto antes del gancho.
  2. **Facebook de 45–60 s (120–150 palabras)**. Shorts siguen en 25–40 s.
  3. **Cambio de imagen cada 2–3 s** y frases cortas. Ningún plano quieto más de 3 s.
  4. **Temas**: supervivencia, hazañas increíbles, misterios, fenómenos, curiosidades, animales, famosos. NO crímenes,
     secuestros, narcos, terrorismo ni violencia contra niños o mujeres (si un encargo es de eso, cámbialo por la reserva).
  5. **Descripción concreta**: di QUÉ pasó con un dato fuerte ("Cayó de un avión a 3.000 metros… y sobrevivió 😱"),
     no frases vagas ("Lo dejaron atrás seguros de que…").
  6. Cierre: "Comparte esta historia" + seguir la página.

## Qué entregas: `planes/AAAA-MM-DD.json` en la rama `planes`
```json
{"fecha": "2026-10-29", "modo": "claude",
 "videos": [
  {"eid": "fb1", "tipo": "fb", "hora_fb": "12:30", "hora_short": "13:00",
   "articulo": "Robert Hansen", "fuente": "https://es.wikipedia.org/wiki/Robert_Hansen",
   "titulo_video": "LAS SOLTABA EN EL BOSQUE",
   "titulo_youtube": "Las soltaba en el bosque… y luego salía a cazarlas",
   "descripcion_youtube": "3-5 líneas con gancho, sin revelar el final.\n#misterio #casosreales #ridmer",
   "etiquetas": ["misterio", "caso real", "..."],
   "texto_facebook": "1-2 frases clickbait que no revelen el final + 3 hashtags",
   "miniatura": {"img": 4, "texto": "LAS CAZABA"},
   "gancho": 1,
   "segmentos": [
     {"texto": "Frase del gancho.", "escena": {"tipo": "foto", "img": 4}, "short": true},
     {"texto": "...", "escena": {"tipo": "fecha", "texto": "Junio de 1983", "sub": "Anchorage, Alaska"}},
     {"texto": "...", "escena": {"tipo": "ficha", "nombre": "Robert Hansen", "sub": "Panadero · 44 años", "img": 2}, "short": true},
     {"texto": "...", "escena": {"tipo": "mapa", "lat": 61.5, "lon": -149.0, "lugar": "Valle del río Knik", "km": 8}},
     {"texto": "...", "escena": {"tipo": "cita", "texto": "cita REAL del texto fuente", "autor": "Cindy Paulson"}},
     {"texto": "...", "escena": {"tipo": "foto", "img": 7}, "rotulo": "17 VÍCTIMAS"}
   ]},
  {"eid": "largo1", "tipo": "largo", "hora_youtube": "18:00", "...": "igual, sin hora_fb ni short"}
 ]}
```
- `eid`: el mismo del encargo (fb1, fb2, fb3, largo1). Haz TODOS los encargos del día.
- `img`: el NÚMERO rojo de la hoja de fotos de ese encargo (mírala con la herramienta Read antes de elegir).
- `gancho`: cuántos segmentos van ANTES de la intro de Ridmer (1 o 2). La intro entra al terminar esa frase.
- `short: true`: marca los segmentos que forman el Short de YouTube (los del gancho entran solos).
  La suma de palabras del Short debe ser ≤ 105 y tener sentido completo (gancho → giro → final).
- `rotulo`: cartel rojo corto (máx 4 palabras) solo en datos clave. La mayoría vacío.

## Duración (sin excepciones)
| tipo | palabras narradas | segmentos | resultado |
|---|---|---|---|
| fb (Facebook) | 120–150 | 9–12 | 45–60 s, SIN intro (cambio del 9-nov) |
| Short (subconjunto de fb) | ≤ 105 | 5–7 | < 60 s SIEMPRE |
| largo (YouTube) | 620–760 | 28–38 | 4–5 min |

## Horarios (hora Ecuador)
- REGLA DEL DUEÑO (10-nov, permanente): NINGÚN video sale antes de las 14:00. El paquete de YouTube llega a las 14:00.
- fb1 → `hora_fb` 14:00 · fb1s → `hora_youtube` 14:00 · fb2 → 18:30 · fb2s → 19:00 · fb3 → 21:00.
- largo1 (días alternos) → `hora_youtube` 18:00.
- Si un encargo es noticia urgente, va en fb1.

## Escenas (cómo edita Ridmer)
- `foto`: foto REAL de la hoja que corresponda de verdad a lo que se narra en ese segmento. Mínimo 60 % fotos.
  No repitas la misma foto en segmentos seguidos. Si ninguna foto sirve, usa fecha/ficha/mapa.
- `ficha`: cuando aparece una persona clave por primera vez (nombre + quién es, con su foto si está en la hoja).
- `fecha`: fechas, lugares o cifras que impactan ("JUNIO DE 1983", "17 VÍCTIMAS").
- `mapa`: lugar concreto con coordenadas REALES (lat/lon) y `km` de radio (2 ciudad, 8–30 región).
- `cita`: solo frases que estén en el texto fuente. Nunca inventes citas.

## Guion
- SOLO hechos del texto fuente del encargo. Nada inventado (nombres, fechas, cifras). Si dudas, no lo digas.
- Gancho brutal en la primera frase, sin revelar el final. Frases cortas, fáciles de narrar, con tensión.
- Cierre fuerte + "Suscríbete a Ridmer para más historias como esta." (fb y largo; en el Short también si cabe).
- Español latino neutro. Números con letras cuando se lean mejor. Sin emojis en el texto narrado.
- Tono de suspenso. Nada de humor ni efectos de comedia. Con tacto si hay víctimas.
- Noticias urgentes: tono serio, solo lo que dicen los titulares.

## Títulos (al dueño le gusta el CLICKBAIT, pero verdadero)
- `titulo_youtube`: curiosidad irresistible, máx 80 caracteres. Ej: "Las soltaba en el bosque… y luego salía a cazarlas",
  "Encontraron su diario 30 años después y lo que decía heló a todos", "Sobrevivió 72 días… pero lo peor vino después".
- `titulo_video` (va en pantalla): máx 5 palabras EN MAYÚSCULAS, que quepa en 2 líneas.
- `miniatura.texto`: 2 a 4 palabras.
- Nunca títulos falsos o engañosos.

## Reglas finales
- No modifiques otras ramas (solo escribe en `planes`). No imprimas claves ni tokens.
- Si un encargo no tiene material suficiente, igual hazlo con fichas/fechas/mapas; si es imposible, ponle `"omitir": true`.

## Modo "claude": TÚ editas el 100 % (obligatorio, `"modo": "claude"` en el plan)
1. Sube el plan a `planes/FECHA.json` (rama `planes`). El servidor hace la voz Algenib de cada video (el gancho se
   graba aparte), calcula el tiempo de cada palabra y baja las fotos/escenas que pediste.
2. Pide el material: en la rama `encargos` sube `pedir/FECHA-material.txt` (contenido: la fecha). Un workflow espera a
   que esté completo y lo deja en la rama **`material`**: `material/FECHA/<eid>/` con `info.json` (segmentos con su
   t0, `hook_fin`, palabras), `voz.flac`, `esc_NN.jpg` (la imagen de cada segmento) y `cNN.jpg` (todas las candidatas).
   Revisa con `git fetch origin material` cada minuto (máx. 60 min).
3. Para cada eid: `python3 tools/editar.py material/FECHA/<eid> planes/FECHA.json <eid> salida/<eid>`
   (desde un clon de la rama `clipero`). Deja fb.mp4 + short.mp4 (o largo.mp4), miniatura.jpg y
   `revision_*.jpg` (un cuadro cada 2 s).
4. **MIRA** con Read cada `revision_*.jpg`, la miniatura y las `esc_NN.jpg`. Corrige lo que esté mal escribiendo
   `salida/<eid>/cambios.json` (foto equivocada → otra `cNN.jpg`; cartel; qué segmentos van al Short; mover un
   corte con `t0`) y vuelve a correr editar.py con ese archivo como 5.º argumento. Repite hasta que esté bien:
   foto que corresponde a lo narrado, sin pantallas negras, intro justo tras el gancho, Short < 60 s.
5. Entrega: `python3 tools/entregar.py FECHA salida/fb1 salida/fb2 …` (sube a la rama `entregas`; el servidor
   los baja en ≤ 2 min y los entrega a su hora). Hazlo antes de las 10:30: después de esa hora el servidor arma
   automático lo que falte (respaldo).

## Noticias: SOLO si son recientes y confirmadas (regla del dueño)
- Solo noticias de las que **TODO EL MUNDO está hablando** (tendencia mundial en noticias y redes): terremoto o
  tsunami enorme, catástrofe con muchas víctimas, atentado mayor, accidente aéreo o tragedia viral con varios muertos
  (ej.: un jet que cae sobre un barrio), muerte de alguien famoso EN TODO EL MUNDO
  (estrella mundial, presidente en funciones de una potencia, papa). NO: expresidentes o famosos conocidos solo en su
  país, política normal, deportes, noticias de un solo país. En la duda, NO va. Si va, va SIEMPRE primero (fb1), y SOLO si:
  1) pasó en las **últimas 24 horas** (revisa la fecha con WebSearch: si el hecho es de días atrás, NO va), y
  2) la cubren medios grandes de **varios países** (Latinoamérica y EE. UU./Europa), al menos 6 distintos.
- Si el encargo de noticia no cumple, ponle `"omitir": true` y usa el encargo de reserva `res1` con las horas de fb1.
- El guion de noticia: tono serio, solo lo confirmado, di cuándo pasó ("este jueves", "hace unas horas"). Nunca una
  noticia vieja como si fuera nueva.

## Última hora (tarea de cada hora, 7:17 a 23:17)
- El servidor vigila Google Noticias cada 20 min; si algo de impacto MUNDIAL pasó en las últimas 3 h (sale en Latinoamérica y EE. UU., ≥ 6 medios),
  agrega a `encargos.json` un encargo `urgN` con `"urgente": true`.
- La tarea horaria pide los encargos; si hay un `urgN` que todavía no está en `planes/FECHA.json`: verifica con
  WebSearch (reciente + confirmado), agrégalo al plan con `"hora_fb": "ya", "hora_short": "ya"` (sin borrar los demás
  videos), pide el material, edítalo (Facebook ~1:00–1:30 y Short < 60 s) y entrégalo SOLO a él con entregar.py.
  Facebook se publica a los 20 min de avisar; el Short le llega al dueño para subirlo.

## YouTube: 5 Shorts + largo, TODO en un paquete a las 9:00 (regla del dueño, reemplaza lo anterior de Shorts)
- Ya NO marques `short: true` en los videos de Facebook. Cada Short es su PROPIO video en el plan, con `"tipo": "short"`,
  su propio guion (70–95 palabras, 6–8 segmentos, 25–40 s) y `"hora_youtube"` (la hora a la que el dueño lo programa).
- El Short cuenta la historia COMPLETA: gancho → contexto mínimo → giro → **final claro que cierra la historia** (qué
  pasó al final / qué se sabe hoy) → "Sígueme en Ridmer para más." Nunca termina en el aire.
- 5 Shorts por día:
  - `fb1s` (misma historia que fb1, `"encargo": "fb1"` para usar sus fotos) → `hora_youtube` 14:00
  - `sh1` (encargo propio) → 15:00
  - `fb2s` (`"encargo": "fb2"`) → 17:00
  - `sh2` (encargo propio) → 19:00
  - `fb3s` (`"encargo": "fb3"`) → 22:00
- Largo (TODOS los días) → `hora_youtube` 18:00. El servidor manda a las 14:00 un resumen con las horas y luego cada video
  con sus textos. Para llegar a tiempo, ENTREGA ANTES DE LAS 8:45.
- `gancho`: en Shorts siempre 1 (la intro entra tras la primera frase).

## Animaciones (al dueño le encantan: úsalas en cada video)
Además de fotos, pide escenas animadas en el plan (ver cabecera de tools/editar.py): `ruta` (viaje de A a B sobre el
mapa, `corte` < 1 si no llegó, `c` para marcar dónde pasó), `caida` (recreación de una caída con impacto, siempre
rotulada RECREACIÓN), `contador` (cifra clave que sube) y `linea_tiempo` (hitos con fecha). Mínimo 2 animaciones en
cada Facebook y Short, 4+ en el largo, siempre fieles a los hechos (nada de cifras inventadas).

## Lo que dicen los números (YouTube Studio, 6-nov-2026) — manda sobre lo anterior
- Público: México 26 %, Ecuador 12 %, Argentina 8 %; 98 % gente nueva; casi todo desde el feed de Shorts.
- El Short que más funcionó (14 mil vistas, 92 % de retención) duró 33 s y era un VIDEO REAL viral. Los narrados de
  historia lejana (piratería, ferry de Filipinas, niñas de Nigeria) tuvieron 10–35 vistas: la mitad desliza al inicio.
- Por eso: Shorts de **25–40 s (70–95 palabras)**; la primera imagen es la más impactante y el gancho se entiende en
  2 segundos; SIN intro en Shorts ni Facebook (la intro va solo en el largo); fotos a pantalla completa.
- Temas: prioriza **México y Latinoamérica**, casos virales recientes, famosos y animales/rescates (crímenes NO, ver 9-nov);
  historia lejana solo si el gancho es universal. Si hay video real del hecho, úsalo (fragmentos ≤ 7 s).

## Escenas DIBUJADAS (estilo de los cuentos) — el dueño las pidió el 6-nov-2026, OBLIGATORIAS
El dueño se quejó de que los videos eran "puras fotos". Cada video cuenta la historia también con escenas dibujadas
y animadas (personajes caricatura que caminan, se asustan, se sientan; luces de casco y linternas, polvo, rocas que
caen, temblor de cámara), mezcladas con las fotos y videos reales. Se piden en `cambios.json` de tools/editar.py:
`"dibujo": {"N": {"nombre": "...", "evento": "...", "n": 5, "letrero": "RECREACIÓN"}}` (N = número de segmento).
- `mina`: evento `camina` (mineros con casco y lámpara en el túnel), `sismo` (temblor, grietas, rocas, polvo, pánico),
  `atrapados` (derrumbe tapa el túnel, mineros detrás), `maquina` (cargador a control remoto saca la roca),
  `rescate` (perforadora baja desde la superficie), `capsula` (cápsula sube por el pozo).
- `carretera`: `pasa` (auto de noche con faros) o `recoge` (gente haciendo autoestop sube al auto). `n` personas.
- `ciudad`: `calma` o `sismo` (edificios tiemblan, se apagan las ventanas, grietas, escombros, polvo).
- `linternas`: grupo buscando de noche en el bosque con linternas. `pista`: avión aterriza bajo lluvia y no frena.
- Si ninguna sirve, DIBUJA UNA A MEDIDA (como los cuentos): escribe un script python con `app/dibujos.py`
  (`persona()`, `pegar()`, `Luces`, `roca()`, `polvo()`, `temblor()`) que se llame `python3 script.py salida.mp4
  segundos W H`, y ponlo en cambios: `"dibujo": {"N": {"script": "mi_escena.py"}}` (ruta junto a cambios.json).
- Mínimo: **2 escenas dibujadas en cada Short y Facebook, 4+ en el largo**. Ningún plano dura más de ~4–5 s sin
  cambiar (si un segmento es largo, pártelo en el guion). Nunca la misma foto dos veces seguidas.
- Siempre fieles a los hechos (no dibujes lo que no pasó) y rotuladas `RECREACIÓN`. No dibujes caras de personas
  reales: son personajes genéricos.

## VIDEOS ORIGINALES del hecho (el dueño los pide, 6-nov-2026) — OBLIGATORIO cuando existan
"Lo que no me gusta es que no pones videos originales." En CADA video busca con WebSearch un video real del hecho
(noticiero en YouTube, video viral de TikTok/X/Facebook, cámara de seguridad, video del rescate…) y pide 1 o 2
fragmentos en el plan: escena `{"tipo": "video", "url": "https://...", "desde": 12, "dur": 5}` (máx. 7 s; el servidor
lo baja y lo pone en recuadro con borde y el crédito "video de redes sociales"). Lo ideal en un Short:
foto o video real en el gancho → recreación dibujada de lo que pasó → video/foto real de las consecuencias.
Si `v_NN.mp4` no llegó en el material, usa fotos reales en su lugar (y dilo en el resumen). Rotula las fotos del hecho
con `"rotulo": "FOTO REAL"` cuando vengan justo después de una recreación.

## AVANCE PARA TIKTOK (10-nov, pedido del dueño)
Cada día que hay video largo (largo1), haz TAMBIÉN `largo1t`: un avance vertical para TikTok que deja la intriga y manda
a ver el video completo en YouTube.
- Plan: `{"eid": "largo1t", "tipo": "tiktok", "encargo": "largo1", "hora_youtube": "18:00", "gancho": 2, ...}` con los
  mismos títulos/descripción del largo (descripción con "Video completo en YouTube: Ridmer").
- Guion PROPIO de 230-300 palabras (1:30-2:00): el mismo gancho del largo + la historia hasta el punto de más tensión, y
  ahí se corta. Último segmento (obligatorio, casi textual): "¿Qué pasó después? Lo que viene te va a dejar sin palabras.
  Mira el video completo en YouTube, en el canal Ridmer." NUNCA cuentes el final.
- Edición: igual que un Facebook (vertical, inicio cinematográfico, música, videos reales, fotos polaroid), reutiliza las
  animaciones del largo en vertical. Pon en el último segmento `"rotulo": {"N": "VIDEO COMPLETO EN YOUTUBE · RIDMER"}`.
- `editar.py` deja `tiktok.mp4`; entrégalo con `entregar.py` junto al largo. Llega al bot en el paquete de las 14:00
  como "🎵 TIKTOK" (no se publica en Facebook).

## HACKERS Y DEEP WEB + TÍTULOS PARA ELEGIR (10-nov, pedido del dueño)
- Prueba de una semana (desde el 11-nov): fb2 + fb2s de cada día son una HISTORIA REAL de hackers o de la Deep Web
  (ej.: Kevin Mitnick, Jonathan James y la NASA, el robo al Banco de Bangladesh, Marcus Hutchins y WannaCry, Silk Road y
  Ross Ulbricht, Gary McKinnon, Anonymous, el grupo Lazarus, el hackeo a Sony, el niño que hackeó... etc.). Elígela tú con
  WebSearch: SOLO casos documentados por medios grandes; nunca leyendas (habitaciones rojas, etc.). NUNCA expliques cómo
  hackear, cómo entrar a la Deep Web ni nada que sirva para hacerlo: se cuenta la HISTORIA (quién, qué pasó, cómo lo
  atraparon, qué le pasó). No repitas una historia ya contada (mira el historial del plan de días anteriores).
  Si no hay encargo para eso, el video lleva sus propios segmentos con "buscar" (fotos) y videos reales con links
  directos de YouTube que muestren al protagonista o noticias del caso (nunca youtubers).
- En TODOS los videos pon `"titulos_opciones"`: 6–8 títulos CLICKBAIT distintos (pero verdaderos) para que el dueño elija.
  Varía el estilo: pregunta, número impactante, "nadie sabía que…", "lo que hizo este muchacho de 15 años…", MAYÚSCULAS en
  la palabra clave, 1 emoji como mucho. El bot se los manda debajo de cada video.

## PORTADA DE LOS VIDEOS LARGOS (11-nov, aprobada por el dueño)
En el cambios.json de cada largo pon `"portada"` (FOTOS REALES, nunca dibujos ni IA):
`{"fondo": "esc_NN.jpg" (lugar de la historia, se oscurece solo), "foto": "esc_NN.jpg" (LA PERSONA protagonista: pide en
el plan un segmento con foto real de su cara), "recorte": "esc_NN.jpg" (opcional: objeto sobre fondo blanco),
"lineas": ["Se *ENAMORÓ* de un", "*EXTRATERRESTRE*", "y dijo que tuvo un *HIJO* con él"], "etiqueta": "La historia de …"}`
(`*palabra*` sale en amarillo; 2–3 líneas; la línea principal corta y en MAYÚSCULAS). Mírala con Read antes de entregar.
El video largo se sube solo a YouTube y el dueño puede cambiar la portada desde el bot (botón «🖼️ Cambiar portada»).
Horario YouTube (hora Ecuador): Short 1 → 14:00 · LARGO → 18:00 · Short 2 → 19:00.

## TIKTOK CON METRICOOL (11-nov, plan del dueño: máx. 20 al mes)
Metricool (marca Ridmer TV, blogId 7509545, zona America/Guayaquil) publica en TikTok (cuenta ridmer98). Plan gratis = 20
publicaciones al mes en TOTAL. Reparto: ~15 AVANCES (cada día de largo) + 4 MEJORES DE LA SEMANA (domingo) + 1 de margen.
- Cada día: guarda TODOS los Facebook del día (para elegir el mejor de la semana):
  `python3 tools/tiktok.py guardar $HOY <salida>/fbN/fb.mp4 fbN "<título>" "<texto_facebook>"`
- Día de largo: guarda también el avance (`... <salida>/largo1t/tiktok.mp4 largo1t ...`), mira `python3 tools/tiktok.py cuenta`;
  si van menos de 19, prográmalo con la herramienta de Metricool createScheduledPost: providers [{"network":"tiktok"}],
  media [link que imprimió guardar], hora 19:30 de hoy, text = título clickbait + "Video completo en YouTube: Ridmer" +
  4-6 hashtags, tiktokData {"privacyOption":"PUBLIC_TO_EVERYONE","title": título corto, "autoAddMusic": false}.
  Luego `python3 tools/tiktok.py sumar largo1t-$HOY`. Si ya van 19 o más, NO programes (se guarda el cupo del domingo).
- REGLA DEL DUEÑO (11-nov): NADA se publica en TikTok antes de que su video de YouTube/Facebook YA ESTÉ PUBLICADO.
  Por eso la sesión de la mañana SOLO guarda los videos (tools/tiktok.py guardar); la programación del avance la hace la
  tarea de la tarde "TikTok avance del día" (19:13), que primero comprueba en el feed público del canal que el largo ya
  está público en YouTube.


## VIDEOS LARGOS DE 8 MINUTOS Y HISTORIAS EXPLICADAS PASO A PASO (11-nov, pedido del dueño)
- El largo dura ~8 minutos: guion de 1100–1300 palabras (desde 8 min YouTube permite anuncios en medio del video).
  No rellenes: más minutos = más DETALLE de la historia, no frases repetidas. Si la historia no da para 8 min, mejor 6–7.
- Sé MUY ESPECÍFICO en todos los videos: si alguien escapó de la cárcel, cuenta CÓMO lo hizo, paso a paso (qué hizo
  primero, qué usó, dónde estaban los guardias, por dónde salió) y muéstralo con ANIMACIONES a medida de cada paso.
- Hackers: cuenta CÓMO logró entrar a nivel de historia (se hizo pasar por técnico y le dieron la contraseña, encontró
  una computadora olvidada sin clave, un empleado abrió un correo falso, etc.) y anímalo, pero NUNCA instrucciones
  técnicas, comandos, programas, códigos ni pasos que alguien pueda copiar para hackear.
