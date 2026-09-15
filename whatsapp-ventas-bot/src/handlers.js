import { parseMensaje } from './parser.js';
import {
  registrarVenta,
  totalVentas,
  corregirUltimaVenta,
  listarVentasHoy,
  corregirVentaPorId,
  registrarDeuda,
  deudasPendientes,
  crearProducto,
  agregarAliasBatch,
  agregarAlias,
  quitarAlias,
  actualizarPrecio,
  actualizarStock,
  buscarProductosPorTexto,
  registrarVentaCatalogo,
} from './db.js';

const AYUDA = `No entendí ese mensaje 🤔 Formatos disponibles:

📦 Registrar venta: "[cantidad] [producto] [monto]$"
   Ej: 1 Relay 5$

✏️ Corregir la última venta: "Corregir última venta [cantidad] [producto] [monto]$"
   Ej: Corregir última venta 1 Relay 5$

📋 Ver ventas de hoy numeradas: "Ventas hoy"

✏️ Corregir una venta de hoy por número: "Corregir venta [número] [cantidad] [producto] [monto]$"
   Ej: Corregir venta 2 1 Relay 0$

🗂️ Agregar producto al catálogo: "#AgregarProducto [stock] [nombre] [precio]$ #[código]"
   Ej: #AgregarProducto 10 Relay 5 patas 100$ #RL01

🏷️ Alias de un producto: "Alias [código] [alias]" / "Quitar alias [código] [alias]"
   Ej: Alias RL01 relay chiquito

💲 Actualizar precio: "Precio [código] [nuevo precio]$"
   Ej: Precio RL01 120$

📦 Actualizar stock: "Stock [código] [nueva cantidad]"
   Ej: Stock RL01 20

🛒 Vender del catálogo: "Venta [cantidad] [nombre, alias o código]"
   Ej: Venta relay chiquito

📊 Consultar ventas: "Total hoy", "Total semana" o "Total mes"

💰 Registrar deuda: "Debe [nombre] [monto]"
   Ej: Debe Juan 30

📋 Consultar deudas: "Quién debe"`;

function money(valor) {
  return `$${Number(valor).toFixed(2)}`;
}

// Sugiere 2-3 alias razonables a partir del nombre del producto (primera
// palabra, primeras dos palabras, todas menos la última). Es una heurística
// simple basada en el texto, no una IA que invente sinónimos.
function sugerirAlias(nombre) {
  const palabras = nombre.trim().split(/\s+/);
  const sugerencias = new Set();

  if (palabras.length > 1) {
    sugerencias.add(palabras[0]);
    sugerencias.add(palabras.slice(0, -1).join(' '));
  }
  if (palabras.length > 2) {
    sugerencias.add(palabras.slice(0, 2).join(' '));
  }

  sugerencias.delete(nombre.trim());
  return [...sugerencias].slice(0, 3);
}

function textoProducto(producto) {
  return `${producto.codigo} - ${producto.nombre} (${money(producto.precio)})`;
}

async function ejecutarVentaCatalogo(producto, cantidad) {
  const { montoTotal, stockRestante } = await registrarVentaCatalogo(producto, cantidad);
  return `✅ Venta registrada: ${cantidad} ${producto.nombre} (${producto.codigo}) - ${money(montoTotal)}\nStock restante: ${stockRestante}`;
}

// Cuando "Venta ..." coincide con más de un producto, se guarda aquí la
// consulta pendiente por chat hasta que la persona responde con el número
// de la opción correcta.
const pendientesVenta = new Map();

export async function manejarMensaje(texto, chatId) {
  if (chatId && pendientesVenta.has(chatId)) {
    const pendiente = pendientesVenta.get(chatId);
    pendientesVenta.delete(chatId);

    const seleccion = texto.trim().match(/^(\d+)$/);
    if (seleccion) {
      const producto = pendiente.candidatos[parseInt(seleccion[1], 10) - 1];
      if (producto) {
        return ejecutarVentaCatalogo(producto, pendiente.cantidad);
      }
      return '⚠️ Ese número no corresponde a ninguna opción. Escribe de nuevo la venta.';
    }
    // No fue una selección: se descarta la venta pendiente y se procesa
    // este mensaje como uno nuevo, normal.
  }

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

    case 'ventas_hoy': {
      const ventas = await listarVentasHoy();
      if (ventas.length === 0) {
        return '📋 Todavía no hay ventas registradas hoy.';
      }
      let respuesta = '📋 Ventas de hoy:';
      ventas.forEach((v, i) => {
        respuesta += `\n${i + 1}. ${v.cantidad} ${v.producto} - ${money(v.monto)}`;
      });
      respuesta += '\n\nPara corregir alguna: "Corregir venta [número] [cantidad] [producto] [monto]$"';
      return respuesta;
    }

    case 'corregir_venta_n': {
      const ventas = await listarVentasHoy();
      const venta = ventas[accion.posicion - 1];
      if (!venta) {
        return `⚠️ No encontré la venta número ${accion.posicion} de hoy. Escribe "Ventas hoy" para ver la lista.`;
      }
      const corregida = await corregirVentaPorId(venta.id, accion.producto, accion.cantidad, accion.monto);
      return `✏️ Venta #${accion.posicion} corregida: ${corregida.cantidad} ${corregida.producto} - ${money(corregida.monto)}`;
    }

    case 'agregar_producto': {
      let producto;
      try {
        producto = await crearProducto(accion.codigo, accion.nombre, accion.precio, accion.stock);
      } catch (err) {
        if (err.code === '23505') {
          return `⚠️ Ya existe un producto con el código "${accion.codigo}".`;
        }
        throw err;
      }

      const sugerencias = sugerirAlias(accion.nombre);
      if (sugerencias.length > 0) {
        await agregarAliasBatch(producto.id, sugerencias);
      }

      let respuesta = `✅ Registrado: ${producto.codigo} = "${producto.nombre}", ${money(producto.precio)}, stock ${producto.stock}.`;
      if (sugerencias.length > 0) {
        respuesta += `\nTambién lo voy a reconocer si escribes: ${sugerencias.map((s) => `"${s}"`).join(', ')}.`;
      }
      respuesta += `\nPara agregar o quitar un alias: "Alias ${producto.codigo} [alias]" o "Quitar alias ${producto.codigo} [alias]".`;
      return respuesta;
    }

    case 'agregar_alias': {
      const producto = await agregarAlias(accion.codigo, accion.alias);
      if (!producto) {
        return `⚠️ No encontré ningún producto con el código "${accion.codigo}".`;
      }
      return `✅ Alias agregado: "${accion.alias}" ahora identifica a ${textoProducto(producto)}.`;
    }

    case 'quitar_alias': {
      const resultado = await quitarAlias(accion.codigo, accion.alias);
      if (resultado === null) {
        return `⚠️ No encontré ningún producto con el código "${accion.codigo}".`;
      }
      if (!resultado) {
        return `⚠️ "${accion.alias}" no era un alias de ${accion.codigo}.`;
      }
      return `🗑️ Alias quitado: "${accion.alias}" ya no identifica a ${textoProducto(resultado)}.`;
    }

    case 'actualizar_precio': {
      const producto = await actualizarPrecio(accion.codigo, accion.precio);
      if (!producto) {
        return `⚠️ No encontré ningún producto con el código "${accion.codigo}".`;
      }
      return `✅ Precio actualizado: ${textoProducto(producto)}.`;
    }

    case 'actualizar_stock': {
      const producto = await actualizarStock(accion.codigo, accion.stock);
      if (!producto) {
        return `⚠️ No encontré ningún producto con el código "${accion.codigo}".`;
      }
      return `✅ Stock actualizado: ${producto.codigo} - ${producto.nombre}, stock ${producto.stock}.`;
    }

    case 'venta_catalogo': {
      const candidatos = await buscarProductosPorTexto(accion.texto);

      if (candidatos.length === 0) {
        return `⚠️ No encontré ningún producto que coincida con "${accion.texto}".`;
      }

      if (candidatos.length > 1) {
        if (chatId) {
          pendientesVenta.set(chatId, { candidatos, cantidad: accion.cantidad });
        }
        let respuesta = `🤔 Encontré varios productos que coinciden con "${accion.texto}", ¿cuál es? Responde con el número:`;
        candidatos.forEach((p, i) => {
          respuesta += `\n${i + 1}. ${textoProducto(p)}`;
        });
        return respuesta;
      }

      return ejecutarVentaCatalogo(candidatos[0], accion.cantidad);
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
