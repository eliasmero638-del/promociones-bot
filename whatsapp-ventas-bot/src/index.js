import 'dotenv/config';

// La dependencia libsignal (usada internamente por Baileys) imprime por
// console.info/console.warn el estado completo de cada sesión de cifrado al
// abrirla o cerrarla -- incluyendo llaves privadas -- sin pasar por el
// logger que se le configura a Baileys. Nuestro propio código nunca usa
// console.info/console.warn, así que se silencian por completo para no
// filtrar material criptográfico a los logs. console.log y console.error
// quedan intactos.
console.info = () => {};
console.warn = () => {};

import makeWASocket, { useMultiFileAuthState, DisconnectReason } from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import pino from 'pino';
import { initSchema } from './db.js';
import { manejarMensaje, cierreDeCajaTexto } from './handlers.js';

const AUTH_DIR = process.env.AUTH_DIR || './auth_info';
const ALLOWED_SENDER = process.env.ALLOWED_SENDER
  ? process.env.ALLOWED_SENDER.replace(/\D/g, '')
  : null;
const PROFILE_NAME = process.env.PROFILE_NAME || null;
const TIMEZONE = process.env.TIMEZONE || 'America/Guayaquil';
const CIERRE_HORA = process.env.CIERRE_HORA || null; // formato "HH:MM", 24h

let sockActivo = null;
let ultimaFechaCierreEnviado = null;

function horaLocalActual() {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date());
}

function fechaLocalActual() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TIMEZONE }).format(new Date());
}

// Revisa cada minuto si ya es la hora configurada de cierre de caja (hora
// local del negocio) y, si no se ha enviado hoy, manda el resumen del día
// al número autorizado sin que nadie tenga que pedirlo.
function iniciarSchedulerCierreDeCaja() {
  if (!CIERRE_HORA || !ALLOWED_SENDER) return;

  setInterval(async () => {
    if (!sockActivo) return;

    const fechaActual = fechaLocalActual();
    if (horaLocalActual() !== CIERRE_HORA || ultimaFechaCierreEnviado === fechaActual) return;

    ultimaFechaCierreEnviado = fechaActual;
    try {
      const texto = await cierreDeCajaTexto();
      await sockActivo.sendMessage(`${ALLOWED_SENDER}@s.whatsapp.net`, { text: texto });
    } catch (err) {
      console.error('Error enviando el cierre de caja:', err);
    }
  }, 60 * 1000);
}

// Justo después de conectar, las claves de app-state (necesarias para
// updateProfileName) todavía pueden no estar sincronizadas, así que se
// reintenta con espera en vez de fallar directo.
async function actualizarNombrePerfil(sock, nombre, intentos = 5, esperaMs = 4000) {
  for (let i = 0; i < intentos; i++) {
    try {
      await sock.updateProfileName(nombre);
      return;
    } catch (err) {
      if (i === intentos - 1) {
        console.error('No se pudo actualizar el nombre de perfil tras varios intentos:', err);
      } else {
        await new Promise((resolve) => setTimeout(resolve, esperaMs));
      }
    }
  }
}

async function iniciarBot() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  const sock = makeWASocket({
    auth: state,
    logger: pino({ level: 'silent' }),
    printQRInTerminal: false,
  });

  sockActivo = sock;

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('Escanea este código QR desde WhatsApp > Dispositivos vinculados:');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const sesionCerrada = statusCode === DisconnectReason.loggedOut;
      console.log(
        sesionCerrada
          ? 'Sesión cerrada desde el teléfono. Escanea el QR nuevamente para reconectar.'
          : 'Conexión perdida, reconectando...',
      );
      if (!sesionCerrada) {
        iniciarBot();
      }
    } else if (connection === 'open') {
      console.log('✅ Bot de WhatsApp conectado.');
      if (PROFILE_NAME) {
        actualizarNombrePerfil(sock, PROFILE_NAME);
      }
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const msg of messages) {
      if (!msg.message || msg.key.fromMe) continue;

      const remoteJid = msg.key.remoteJid;
      if (!remoteJid || remoteJid.endsWith('@g.us')) continue; // ignorar grupos

      // Con el sistema LID de WhatsApp, remoteJid puede ser un ID interno
      // en vez del número de teléfono; senderPn trae el número real en
      // ese caso.
      const senderJid = msg.key.senderPn || remoteJid;
      const senderNumber = senderJid.split('@')[0];
      if (ALLOWED_SENDER && senderNumber !== ALLOWED_SENDER) continue;

      const texto =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        '';

      if (!texto.trim()) continue;

      try {
        const respuesta = await manejarMensaje(texto, remoteJid);
        await sock.sendMessage(remoteJid, { text: respuesta });
      } catch (err) {
        console.error('Error procesando mensaje:', err);
        await sock.sendMessage(remoteJid, {
          text: '⚠️ Ocurrió un error al procesar tu mensaje. Intenta de nuevo.',
        });
      }
    }
  });
}

async function main() {
  await initSchema();
  await iniciarBot();
  iniciarSchedulerCierreDeCaja();
}

main().catch((err) => {
  console.error('Error iniciando el bot:', err);
  process.exit(1);
});
