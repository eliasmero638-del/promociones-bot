# Cómo crear una instalación nueva (otro cliente)

Este repositorio es una **plantilla reutilizable**. Un mismo código sirve
para cualquier cantidad de clientes: cada instalación es un bot de Telegram
distinto (su propio `BOT_TOKEN`), su propio servicio en Railway, y sus
propios datos (admins, grupos, cuentas bancarias, precios), controlados
100% por variables de entorno. El código nunca se toca para dar de alta un
cliente nuevo.

## 0. Qué es "el bot", en realidad

Aunque se habla de "bot de promoción" y "bot de ventas", **es un solo
proceso y un solo bot de Telegram** (`bot.py`, un único `BOT_TOKEN`). Ese
único bot:

- Publica promociones rotativas en un grupo/canal (`GROUP_ID`) — panel de
  administración vía `/panel`.
- Da la bienvenida a los nuevos miembros de ese grupo (mensaje + botón,
  editable desde `/panel`).
- Atiende el flujo de ventas completo por chat privado: prueba gratis con
  expulsión automática, venta VIP (sistema viejo, 2 grupos) y venta
  multi-grupo (sistema nuevo, 5 grupos con selección múltiple), aprobación
  de pagos, etc. — todo dentro de `ventas/`.

Los archivos sueltos en la raíz `config.py`, `handlers.py`, `keyboards.py`,
`storage.py`, `promotions_config.py`, `texts.py`, `start_keyboard.py` **no
se usan** (código muerto, una versión vieja que quedó sin borrar antes de
que se extrajera el paquete `ventas/`). No hace falta tocarlos ni copiarlos.

## 1. Qué es específico de cada cliente

Todo lo de la lista de abajo se lee de variables de entorno (ver
`.env.example` para la lista completa con comentarios). Nada de esto vive
ya en el código:

| Dato | Variable(s) |
|---|---|
| Token del bot de Telegram | `BOT_TOKEN` |
| Grupo de promociones | `GROUP_ID` |
| Administradores (IDs numéricos) | `ADMIN_USER_IDS` |
| @usuario de contacto | `DEFAULT_ADMIN_USERNAME`, `SALES_ADMIN_CONTACT_USERNAME` |
| Nombre de marca | `BRAND_NAME` |
| Precio VIP, datos bancarios, PayPal, FAQ (sistema viejo) | `SALES_*` |
| Enlaces/IDs de grupos (demo, VIP, free, prueba exclusiva) | `SALES_*_GROUP_*` |
| Los 5 grupos y sus precios (sistema nuevo) | `MULTISALE_GROUP_*`, `MULTISALE_PRICE_*` |
| Los 4 métodos de pago (sistema nuevo) | `MULTISALE_PAYMENT_*` |
| Almacenamiento (Upstash o volumen) | `UPSTASH_REDIS_REST_URL/TOKEN` o `DATA_DIR` |

**Importante:** si no defines una variable, el bot usa el valor histórico
de la cuenta original (para no romper la instalación actual). Para un
cliente nuevo, definilas TODAS con sus propios datos — de lo contrario el
bot nuevo mostrará por defecto los datos de la cuenta original.

## 2. Aislamiento de datos (muy importante)

Cada instalación necesita su **propio** backend de almacenamiento. Las
claves usadas en Upstash Redis (`promociones_bot:*`, `ventas_bot:*`,
`multisale_bot:*`) NO llevan ningún prefijo por instalación — si dos bots
comparten la misma base de Upstash o el mismo volumen (`DATA_DIR`), sus
datos se van a mezclar y pisar entre sí.

- Si usas Upstash: crea una base de Redis **nueva** en
  [upstash.com](https://upstash.com) (tienen plan gratuito) para cada
  cliente, y usa esas credenciales solo en el servicio de Railway de ese
  cliente.
- Si no usas Upstash: usa un volumen de Railway distinto (`DATA_DIR`) por
  cada servicio - Railway ya aísla los volúmenes por servicio
  automáticamente.

## 3. Pasos para dar de alta un cliente nuevo

### a) Crear el bot de Telegram
1. Hablar con [@BotFather](https://t.me/BotFather) en Telegram.
2. `/newbot`, elegir nombre y `@username` (debe terminar en `bot`).
3. BotFather entrega el token → esto va en `BOT_TOKEN`.

### b) Preparar los grupos/canales del cliente
- Grupo de promociones (`GROUP_ID`): crear el grupo, agregar el bot como
  administrador, obtener su ID numérico (ej. con `/chatid` una vez el bot
  esté corriendo, o reenviando un mensaje del grupo a
  [@userinfobot](https://t.me/userinfobot)).
- Grupos de venta (demo, VIP, free, los 5 del sistema nuevo, etc.): crear
  cada uno, generar su enlace de invitación, y agregar el bot como
  administrador en los que necesiten expulsión automática (prueba
  gratis).

### c) Elegir almacenamiento
Crear una base de Upstash Redis nueva (recomendado) o dejar `DATA_DIR`
para usar un volumen de Railway.

### d) Crear el servicio en Railway
1. Nuevo proyecto en Railway → Deploy from GitHub repo → seleccionar este
   repositorio (rama `main`, la misma que usa la instalación original -
   **nunca** se crea un fork ni una copia del código).
2. En "Variables", cargar todas las del punto 1 con los datos del cliente
   nuevo (usar `.env.example` como checklist).
3. Deploy. Revisar logs: debe decir `Starting Telegram Promotions Bot...`
   sin errores de configuración.

### e) Probar
- `/start` en el bot nuevo → debe mostrar el menú de 5 grupos con los
  datos del cliente nuevo (no los de la cuenta original).
- Publicar una promoción de prueba desde `/panel` en el grupo del cliente.
- Simular una compra (elegir grupo, método de pago, "Ya realicé el pago")
  y confirmar que el aviso llega a los `ADMIN_USER_IDS` del cliente nuevo.
- Unirse al grupo de promociones con una cuenta de prueba y confirmar el
  mensaje de bienvenida.

## 4. Repetir el proceso para el siguiente cliente

Exactamente los mismos pasos (a)-(e), un proyecto de Railway nuevo por
cliente, un bot de BotFather nuevo por cliente. El código de este
repositorio no cambia nunca para esto - solo las variables de entorno.
