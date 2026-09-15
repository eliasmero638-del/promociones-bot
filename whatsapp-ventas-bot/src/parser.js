function quitarAcentos(texto) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function parseMonto(texto) {
  return parseFloat(texto.replace(',', '.'));
}

const RE_VENTA = /^(\d+)\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*\$$/i;
const RE_TOTAL = /^total\s+(hoy|semana|mes)$/i;
const RE_QUIEN_DEBE = /^quien\s+debe$/i;
const RE_CORREGIR_VENTA = /^corregir\s+(la\s+)?[uú]ltima\s+venta\s+(\d+)\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*\$$/i;
const RE_DEUDA = /^debe\s+(.+?)\s+(\d+(?:[.,]\d+)?)$/i;

export function parseMensaje(textoOriginal) {
  const texto = textoOriginal.trim();

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

  if (RE_QUIEN_DEBE.test(quitarAcentos(texto))) {
    return { tipo: 'quien_debe' };
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

  const deudaMatch = texto.match(RE_DEUDA);
  if (deudaMatch) {
    const [, cliente, monto] = deudaMatch;
    return { tipo: 'deuda', cliente: cliente.trim(), monto: parseMonto(monto) };
  }

  return { tipo: 'desconocido' };
}
