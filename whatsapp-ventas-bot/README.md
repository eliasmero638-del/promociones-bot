# Bot de WhatsApp para ventas de piezas automotrices

Bot de WhatsApp (Baileys) que registra ventas y deudas de clientes por mensaje de
texto, y responde consultas de totales de ventas y de deudas pendientes.

No usa la API oficial de Meta: se conecta como un dispositivo vinculado a un número
de WhatsApp secundario, escaneando un código QR una sola vez.

## Formatos de mensaje soportados

| Acción | Formato | Ejemplo |
|---|---|---|
| Registrar venta | `[cantidad] [producto] [monto]$` | `1 Relay 5$` |
| Total del día | `Total hoy` | |
| Total de la semana | `Total semana` | |
| Total del mes | `Total mes` | |
| Registrar deuda | `Debe [nombre] [monto]` | `Debe Juan 30` |
| Ver deudas pendientes | `Quién debe` | |

El monto de una venta es siempre el **total** de esa línea, no el precio unitario.
Un mensaje que no calce con ninguno de estos formatos recibe una respuesta de ayuda
con los formatos disponibles.

Los mensajes de grupos de WhatsApp se ignoran; el bot solo responde a chats
individuales.

## Requisitos

- Node.js 20 o superior
- Una base de datos PostgreSQL (por ejemplo, [Neon](https://neon.tech))
- Un número de WhatsApp secundario (no el número personal) para vincular el bot

## Configuración local

```bash
cd whatsapp-ventas-bot
npm install
cp .env.example .env
# editar .env con tu DATABASE_URL
npm start
```

Al iniciar por primera vez se mostrará un código QR en la terminal. Escanéalo desde
el número secundario en **WhatsApp > Dispositivos vinculados**. La sesión se guarda
en la carpeta `AUTH_DIR` (por defecto `./auth_info`) para no tener que volver a
escanear en cada reinicio.

Las tablas `ventas` y `deudas` se crean automáticamente al arrancar si no existen.

### Variables de entorno

Ver `.env.example`. La más relevante es `TIMEZONE`, usada para calcular los
límites de "hoy", "semana" y "mes" en la hora local del negocio (por defecto
`America/Guayaquil`).

`ALLOWED_SENDER` es opcional: si se define (número con código de país, sin `+`),
el bot solo responderá a mensajes de ese número. Se recomienda configurarlo, ya
que cualquiera que le escriba al número secundario puede registrar ventas o
deudas si se deja sin restricción.

## Despliegue en Railway

Este bot vive en el subdirectorio `whatsapp-ventas-bot/` de un repositorio que
también contiene otro bot (Telegram) en la raíz. Para desplegarlo como un
servicio independiente en Railway:

1. Crea un nuevo servicio en el proyecto de Railway a partir de este repositorio.
2. En la configuración del servicio, define **Root Directory** como
   `whatsapp-ventas-bot`.
3. Configura las variables de entorno (`DATABASE_URL`, `TIMEZONE`,
   `ALLOWED_SENDER`, etc.) en el servicio.
4. Despliega y revisa los logs del servicio: ahí aparecerá el código QR para
   vincular el número de WhatsApp.

### Persistencia de la sesión de WhatsApp

El sistema de archivos de Railway no es persistente entre despliegues. Para no
tener que volver a escanear el QR cada vez que se hace un nuevo deploy, monta un
[volumen de Railway](https://docs.railway.com/reference/volumes) en la ruta que
apunte `AUTH_DIR` (por ejemplo `/data/auth_info`) y ajusta esa variable de
entorno en consecuencia. Sin volumen, el QR habrá que volverlo a escanear en
cada redeploy (los reinicios simples del mismo contenedor no lo requieren).

El teléfono secundario debe conectarse a internet al menos una vez cada 1-2
semanas para mantener viva la sesión vinculada de WhatsApp multidispositivo. Si
la sesión se desvincula, basta con volver a escanear el QR desde los logs del
servicio.

## Tests

```bash
npm test
```

Corre las pruebas del parser de mensajes (`src/parser.test.js`) con el test
runner nativo de Node.

## Alcance de esta primera versión

- Conexión a WhatsApp vía Baileys y QR.
- Registro de ventas (`ventas`) y deudas (`deudas`).
- Consultas de totales de ventas por día/semana/mes, con desglose por producto.
- Consulta de deudas pendientes agrupadas por cliente.
- Mensaje de ayuda ante formatos no reconocidos.

Marcar una deuda como pagada (`pagado = true`) todavía no tiene un comando de
WhatsApp asociado en esta versión; por ahora se actualiza directamente en la
base de datos.
