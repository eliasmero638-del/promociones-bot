import { parseMensaje } from './parser.js';
import {
  registrarVenta,
  totalVentas,
  corregirUltimaVenta,
  registrarDeuda,
  deudasPendientes,
} from './db.js';

const AYUDA = `No entendí ese mensaje 🤔 Formatos disponibles:

📦 Registrar venta: "[cantidad] [producto] [monto]$"
   Ej: 1 Relay 5$

✏️ Corregir la última venta: "Corregir última venta [cantidad] [producto] [monto]$"
   Ej: Corregir última venta 1 Relay 5$

📊 Consultar ventas: "Total hoy", "Total semana" o "Total mes"

💰 Registrar deuda: "Debe [nombre] [monto]"
   Ej: Debe Juan 30

📋 Consultar deudas: "Quién debe"`;

function money(valor) {
  return `$${Number(valor).toFixed(2)}`;
}

export async function manejarMensaje(texto) {
  const accion = parseMensaje(texto);

  switch (accion.tipo) {
    case 'venta': {
      await registrarVenta(accion.producto, accion.cantidad, accion.monto);
      return `✅ Venta registrada: ${accion.cantidad} ${accion.producto} - ${money(accion.monto)}`;
    }

    case 'total': {
      const { total, desglose } = await totalVentas(accion.periodo);
      let respuesta = `📊 Total ${accion.periodo}: ${money(total)}`;
      if (desglose.length > 0) {
        respuesta += '\n\nDesglose:';
        for (const item of desglose) {
          respuesta += `\n- ${item.producto}: ${item.cantidad} u. - ${money(item.monto)}`;
        }
      }
      return respuesta;
    }

    case 'corregir_venta': {
      const corregida = await corregirUltimaVenta(accion.producto, accion.cantidad, accion.monto);
      if (!corregida) {
        return '⚠️ No hay ninguna venta registrada para corregir.';
      }
      return `✏️ Última venta corregida: ${corregida.cantidad} ${corregida.producto} - ${money(corregida.monto)}`;
    }

    case 'deuda': {
      await registrarDeuda(accion.cliente, accion.monto);
      return `✅ Deuda registrada: ${accion.cliente} debe ${money(accion.monto)}`;
    }

    case 'quien_debe': {
      const deudas = await deudasPendientes();
      if (deudas.length === 0) {
        return '✅ Nadie tiene deudas pendientes.';
      }
      let respuesta = '📋 Deudas pendientes:';
      for (const d of deudas) {
        respuesta += `\n- ${d.cliente}: ${money(d.monto)}`;
      }
      return respuesta;
    }

    default:
      return AYUDA;
  }
}

export async function cierreDeCajaTexto() {
  const { total, desglose } = await totalVentas('hoy');
  let respuesta = `🌙 Cierre de caja: ${money(total)}`;
  if (desglose.length > 0) {
    respuesta += '\n\nDesglose:';
    for (const item of desglose) {
      respuesta += `\n- ${item.producto}: ${item.cantidad} u. - ${money(item.monto)}`;
    }
  }
  return respuesta;
}
