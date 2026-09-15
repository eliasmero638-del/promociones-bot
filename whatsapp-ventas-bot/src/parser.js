import { normalizarTexto } from './texto.js';

function parseMonto(texto) {
  return parseFloat(texto.replace(',', '.'));
}

const RE_AGREGAR_PRODUCTO =
  /^#agregarproducto\s+(\d+)\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*\$\s*#(\S+)$/i;
const RE_VENTA = /^(\d+)\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*\$$/i;
const RE_VENTA_CATALOGO = /^venta\s+(?:(\d+)\s+)?(.+)$/i;
const RE_TOTAL = /^total\s+(hoy|semana|mes)$/i;
const RE_QUIEN_DEBE = /^quien\s+debe$/i;
const RE_VENTAS_HOY = /^ventas\s+hoy$/i;
const RE_CORREGIR_VENTA = /^corregir\s+(la\s+)?[uú]ltima\s+venta\s+(\d+)\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*\$$/i;
const RE_CORREGIR_VENTA_N = /^corregir\s+venta\s+(\d+)\s+(\d+)\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*\$$/i;
const RE_QUITAR_ALIAS = /^quitar\s+alias\s+(\S+)\s+(.+)$/i;
const RE_ALIAS = /^alias\s+(\S+)\s+(.+)$/i;
const RE_PRECIO = /^precio\s+(\S+)\s+(\d+(?:[.,]\d+)?)\s*\$$/i;
const RE_STOCK = /^stock\s+(\S+)\s+(\d+)$/i;
const RE_DEUDA = /^debe\s+(.+?)\s+(\d+(?:[.,]\d+)?)$/i;

export function parseMensaje(textoOriginal) {
  const texto = textoOriginal.trim();

  const agregarProductoMatch = texto.match(RE_AGREGAR_PRODUCTO);
  if (agregarProductoMatch) {
    const [, stock, nombre, precio, codigo] = agregarProductoMatch;
    return {
      tipo: 'agregar_producto',
      stock: parseInt(stock, 10),
      nombre: nombre.trim(),
      precio: parseMonto(precio),
      codigo: codigo.trim(),
    };
  }

  const ventaMatch = texto.match(RE_VENTA);
  if (ventaMatch) {
    const [, cantidad, producto, monto] = ventaMatch;
    return {
      tipo: 'venta',
      cantidad: parseInt(cantidad, 10),
      producto: producto.trim(),
      monto: parseMonto(monto),
    };
  }

  const totalMatch = texto.match(RE_TOTAL);
  if (totalMatch) {
    return { tipo: 'total', periodo: totalMatch[1].toLowerCase() };
  }

  if (RE_QUIEN_DEBE.test(normalizarTexto(texto))) {
    return { tipo: 'quien_debe' };
  }

  if (RE_VENTAS_HOY.test(normalizarTexto(texto))) {
    return { tipo: 'ventas_hoy' };
  }

  const corregirMatch = texto.match(RE_CORREGIR_VENTA);
  if (corregirMatch) {
    const [, , cantidad, producto, monto] = corregirMatch;
    return {
      tipo: 'corregir_venta',
      cantidad: parseInt(cantidad, 10),
      producto: producto.trim(),
      monto: parseMonto(monto),
    };
  }

  const corregirNMatch = texto.match(RE_CORREGIR_VENTA_N);
  if (corregirNMatch) {
    const [, posicion, cantidad, producto, monto] = corregirNMatch;
    return {
      tipo: 'corregir_venta_n',
      posicion: parseInt(posicion, 10),
      cantidad: parseInt(cantidad, 10),
      producto: producto.trim(),
      monto: parseMonto(monto),
    };
  }

  const quitarAliasMatch = texto.match(RE_QUITAR_ALIAS);
  if (quitarAliasMatch) {
    const [, codigo, alias] = quitarAliasMatch;
    return { tipo: 'quitar_alias', codigo: codigo.trim(), alias: alias.trim() };
  }

  const aliasMatch = texto.match(RE_ALIAS);
  if (aliasMatch) {
    const [, codigo, alias] = aliasMatch;
    return { tipo: 'agregar_alias', codigo: codigo.trim(), alias: alias.trim() };
  }

  const precioMatch = texto.match(RE_PRECIO);
  if (precioMatch) {
    const [, codigo, precio] = precioMatch;
    return { tipo: 'actualizar_precio', codigo: codigo.trim(), precio: parseMonto(precio) };
  }

  const stockMatch = texto.match(RE_STOCK);
  if (stockMatch) {
    const [, codigo, stock] = stockMatch;
    return { tipo: 'actualizar_stock', codigo: codigo.trim(), stock: parseInt(stock, 10) };
  }

  const deudaMatch = texto.match(RE_DEUDA);
  if (deudaMatch) {
    const [, cliente, monto] = deudaMatch;
    return { tipo: 'deuda', cliente: cliente.trim(), monto: parseMonto(monto) };
  }

  // Va al final: "venta <texto>" es un formato muy amplio y no debe tapar
  // ningún comando más específico de los de arriba.
  const ventaCatalogoMatch = texto.match(RE_VENTA_CATALOGO);
  if (ventaCatalogoMatch) {
    const [, cantidad, textoProducto] = ventaCatalogoMatch;
    return {
      tipo: 'venta_catalogo',
      cantidad: cantidad ? parseInt(cantidad, 10) : 1,
      texto: textoProducto.trim(),
    };
  }

  return { tipo: 'desconocido' };
}
