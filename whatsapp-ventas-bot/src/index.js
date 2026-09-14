import 'dotenv/config';
import makeWASocket, { useMultiFileAuthState, DisconnectReason } from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import pino from 'pino';
import { initSchema } from './db.js';
import { manejarMensaje } from './handlers.js';

const AUTH_DIR = process.env.AUTH_DIR || './auth_info';
const ALLOWED_SENDER = process.env.ALLOWED_SENDER
  ? process.env.ALLOWED_SENDER.replace(/\D/g, '')
  : null;
const PROFILE_NAME = process.env.PROFILE_NAME || null;

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

      const senderNumber = remoteJid.split('@')[0];
      if (ALLOWED_SENDER && senderNumber !== ALLOWED_SENDER) continue;

      const texto =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        '';

      if (!texto.trim()) continue;

      try {
        const respuesta = await manejarMensaje(texto);
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
}

main().catch((err) => {
  console.error('Error iniciando el bot:', err);
  process.exit(1);
});
