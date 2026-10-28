# CONTEXTO — Clipero + Fábrica Ridmer (para continuar en otra sesión de Claude)

El dueño no programa: explicarle todo paso a paso, en español sencillo, con un comando a la vez para copiar y pegar.
**Nunca subir secretos a GitHub** (este repo es público). Los secretos viven solo en el servidor:
`/var/lib/clipero/secrets/config.json`.

## ⚠️ Antes de nada
- El plan del dueño está en `docs/Plan_Definitivo_v2.txt` (y PDF). Manda sobre este archivo.
- **Cualquier push a la rama `clipero` se despliega solo en ~5 min.** Trabaja en `clipero-dev` y fusiona solo con
  autorización explícita del dueño.
- v20-categorias (en `clipero-dev`): categorías más allá de peleas, supervisor con reglas (decision, normal, explicación,
  contexto, certeza ≥60, evidencia que aparezca en la transcripción), prefiltro con Groq, extensión del clip si "sigue"
  (hasta +6 min), sin tope fijo (clip_max 900), control de calidad del archivo (audio + duración), motivos de rechazo en
  Telegram. NO toca el temporizador de 20 min.
- v23-gratis: Ridmer saca temas de Wikipedia (`app/fuentes.py`, sin cuota) y urgentes de Google Noticias RSS; el guion
  lo escribe Groq (o Gemini sin búsqueda) SOLO con el texto fuente; fotos del propio artículo como respaldo; la fuente
  (URL) va en la descripción. Gemini con Google queda como último recurso. Clipero usa primero los modelos lite de Gemini.
- Pendiente del plan: cola persistente con estados/reintentos, métricas por categoría, fuentes con URL/fecha en Ridmer,
  YouTube API, Ridmer TV en Meta.

## Cómo se despliega
- Rama `clipero` de `eliasmero638-del/promociones-bot`. El servidor hace `git pull` cada 5 min
  (`clipero-update.timer` → `server/update.sh`). Si cambió algo, corre `server/install.sh`, que instala lo de
  `app/requirements.txt` y reinicia `clipero.service`.
- Al arrancar, el bot de Telegram manda "🟢 Clipero vXX encendido". Hay que subir `VERSION` en `app/main.py` en cada cambio.
- **Pedidos desde el repo:** `pedidos.json` en la raíz (lista de `{id, formato: short|largo, tema, resumen}`). El
  servidor hace cada `id` una sola vez. Sirve para que Claude mande a hacer videos sin acceso SSH.
- Claude NO tiene SSH al servidor. El usuario usa Termius (host "clipero"). Comandos útiles: `clipero estado`,
  `clipero log`, `clipero reiniciar`, `clipero gemini`, `clipero facebook`, `clipero avisos`, `clipero voces`,
  `clipero ridmer short "tema"`.
- Para forzar la actualización:
  `cd /opt/clipero && git fetch -q origin clipero && git reset -q --hard origin/clipero && bash server/install.sh`

## Infraestructura
- **Servidor:** Contabo Cloud VPS, IP 173.249.44.95, Ubuntu 24.04. La app está en /opt/clipero y los datos en
  /var/lib/clipero. SSH por el puerto 22 (y el 443 redirigido al 22 con iptables). Hay una web en el puerto 80
  (`app/web.py`).
- **Grabación:** un Infinix Note 12 con Termux (`termux/grabar.sh`) graba el en vivo de YouTube de La Casa 593 con
  yt-dlp y cookies de una cuenta descartable. YouTube bloquea las IPs de servidores, por eso graba el teléfono.
  Sube pedazos .ts de 2 minutos por rsync a `/var/lib/clipero/rec`.
- **IA:** Gemini, con la clave en config, cuenta gratuita. `ia.modelos()` elige automáticamente entre flash y lite;
  cuando un modelo da 429 se pausa 1 hora (`_agotado`).
- **Avisos:** la app ntfy (tema secreto en config), el bot de Telegram @cliperoyt_bot y una página web privada
  `/c/<token>` (clips) y `/r/<token>` (Ridmer). CallMeBot para WhatsApp está programado, pero el servicio estaba
  lleno; falta la apikey.
- **Facebook:** app de Meta "Clipero" en modo desarrollo, con los permisos pages_show_list, pages_read_engagement
  y pages_manage_posts. `clipero facebook` guarda los tokens de todas las páginas del token (`fb_paginas`). Hoy solo
  está conectada **Pasión por los Realities**. **FALTA conectar Ridmer TV**: repetir el token marcando las dos
  páginas.

## Clipero (clips de realities → página "Pasión por los Realities")
`analyzer.py` detecta picos de volumen y de chat. `editor.hacer_clip` corta una ventana de 60 s antes y 150 s
después del pico. Gemini (`ia.analizar`) ve 8 fotos, el audio y el chat, y devuelve el interés, el título, los
personajes, la evidencia y el inicio y fin del momento. El clip queda vertical 720x1280 con subtítulos.
Reglas aprendidas con el usuario:
- **Mínimo de interés 85.** Nunca mandar un clip si la IA falló (`solo_ia`). Descartar clips de menos de 55 s.
- Solo es "pelea" si hay confrontación real; tiene que haber una "evidencia" (la frase exacta), si no, el interés
  baja a 55 como máximo.
- **Nombres:** solo si la IA está 100% segura. Quien habla tiene que ser un participante actual. A los
  exparticipantes se los puede mencionar, pero nunca confundirlos con quien habla. Se manejan con `/participantes`,
  `/salio Nombre` y `/entro Nombre, apodos`.
- Aprende de los botones ❌ y ✅ (`ia.aprender` → `aprendizaje.json`, que se agrega al prompt).
- Publica en Facebook con el botón 📤 o solo si nadie responde en 20 min y el clip tiene 85 o más. Lo explícito
  nunca se publica solo.

## Fábrica Ridmer (canal de YouTube "Ridmer", página de Facebook Ridmer TV)
`app/fabrica.py` + `app/montaje.py` + `app/voz.py`. Shorts a las 8, 12, 16 y 20 h; video largo a las 18 h;
revisión de noticias urgentes cada 2 h. Pasos: tema con Google Search de Gemini → guion verificado y **clickbait**
→ voz de Gemini TTS **Algenib** (respaldo: Microsoft Edge) → Whisper para los tiempos → fotos de Wikimedia Commons
o satelitales de Esri → video con zoom lento, subtítulos, música de suspenso, golpe y riser, **intro de Ridmer
después del gancho** (`assets/intro_ridmer.mp4`) → miniatura → se manda a Telegram con los botones
"✅ Publicar en Ridmer TV" y "❌ No publicar" → si nadie responde en 20 min, se publica solo. El usuario sube a
YouTube a mano.
Preferencias: Shorts SIEMPRE de menos de 60 s; nada de efectos de comedia; imágenes reales; títulos clickbait pero
verdaderos.

## Estado al 27-oct-2026 22:30 y pendientes
1. La cuota gratis de Gemini se agotó el 27-oct (429). YA HECHO (v18-filtro): prefiltro local con Whisper en
   `editor.prefiltro()` antes de llamar a Gemini; los modelos agotados se pausan 1 h. Falta ver si alcanza la cuota
   gratis. YA HECHO (v19-groq): si Gemini no tiene cuota, el clip lo juzga Groq con la transcripción local (`ia.analizar_groq`). Falta que el usuario ponga su clave con `clipero groq`.
2. Short de prueba de Robert Hansen: hay un reintento en `pedidos.json` (id `prueba-hansen-2`, el 28-oct a las 7:30 EC).
3. Conectar Ridmer TV en Facebook (nuevo token con las dos páginas).
4. Pendiente opcional: WhatsApp (CallMeBot sin cupo; o el número de prueba de WhatsApp Cloud de Meta), reconocimiento
   de caras, La Mansión VIP 2 (desde el 8 de noviembre).
