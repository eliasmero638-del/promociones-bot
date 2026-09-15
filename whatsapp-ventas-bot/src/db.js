import pg from 'pg';
import { normalizarTexto } from './texto.js';

const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
});

const TIMEZONE = process.env.TIMEZONE || 'America/Guayaquil';

const UNIDAD_POR_PERIODO = {
  hoy: 'day',
  semana: 'week',
  mes: 'month',
};

export async function initSchema() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS ventas (
      id SERIAL PRIMARY KEY,
      producto TEXT NOT NULL,
      cantidad INTEGER NOT NULL,
      monto NUMERIC(10,2) NOT NULL,
      fecha TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS deudas (
      id SERIAL PRIMARY KEY,
      cliente TEXT NOT NULL,
      monto NUMERIC(10,2) NOT NULL,
      fecha TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      pagado BOOLEAN NOT NULL DEFAULT FALSE
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS productos (
      id SERIAL PRIMARY KEY,
      codigo TEXT NOT NULL UNIQUE,
      nombre TEXT NOT NULL,
      precio NUMERIC(10,2) NOT NULL,
      stock INTEGER NOT NULL DEFAULT 0
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS producto_alias (
      id SERIAL PRIMARY KEY,
      producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
      alias TEXT NOT NULL
    );
  `);
}

export async function registrarVenta(producto, cantidad, monto) {
  await pool.query(
    'INSERT INTO ventas (producto, cantidad, monto) VALUES ($1, $2, $3)',
    [producto, cantidad, monto],
  );
}

// Los límites del período se calculan en hora local (TIMEZONE) y se
// comparan contra `fecha`, que se guarda en UTC (TIMESTAMPTZ).
const RANGO_WHERE = `
  fecha >= date_trunc($1, now() AT TIME ZONE $2) AT TIME ZONE $2
  AND fecha < (date_trunc($1, now() AT TIME ZONE $2) + ('1 ' || $1)::interval) AT TIME ZONE $2
`;

export async function totalVentas(periodo) {
  const unidad = UNIDAD_POR_PERIODO[periodo];

  const { rows: totalRows } = await pool.query(
    `SELECT COALESCE(SUM(monto), 0) AS total FROM ventas WHERE ${RANGO_WHERE}`,
    [unidad, TIMEZONE],
  );

  const { rows: desglose } = await pool.query(
    `SELECT producto, SUM(cantidad) AS cantidad, SUM(monto) AS monto
     FROM ventas
     WHERE ${RANGO_WHERE}
     GROUP BY producto
     ORDER BY monto DESC`,
    [unidad, TIMEZONE],
  );

  return {
    total: Number(totalRows[0].total),
    desglose: desglose.map((d) => ({
      producto: d.producto,
      cantidad: Number(d.cantidad),
      monto: Number(d.monto),
    })),
  };
}

export async function corregirUltimaVenta(producto, cantidad, monto) {
  const { rows } = await pool.query(
    `UPDATE ventas
     SET producto = $1, cantidad = $2, monto = $3
     WHERE id = (SELECT id FROM ventas ORDER BY id DESC LIMIT 1)
     RETURNING producto, cantidad, monto`,
    [producto, cantidad, monto],
  );

  if (rows.length === 0) return null;
  return {
    producto: rows[0].producto,
    cantidad: Number(rows[0].cantidad),
    monto: Number(rows[0].monto),
  };
}

// Ventas de hoy en orden cronológico, para poder mostrarlas numeradas y
// corregir cualquiera (no solo la última) por esa posición.
export async function listarVentasHoy() {
  const { rows } = await pool.query(
    `SELECT id, producto, cantidad, monto
     FROM ventas
     WHERE ${RANGO_WHERE}
     ORDER BY id ASC`,
    ['day', TIMEZONE],
  );

  return rows.map((r) => ({
    id: r.id,
    producto: r.producto,
    cantidad: Number(r.cantidad),
    monto: Number(r.monto),
  }));
}

export async function corregirVentaPorId(id, producto, cantidad, monto) {
  const { rows } = await pool.query(
    `UPDATE ventas SET producto = $1, cantidad = $2, monto = $3
     WHERE id = $4
     RETURNING producto, cantidad, monto`,
    [producto, cantidad, monto, id],
  );

  if (rows.length === 0) return null;
  return {
    producto: rows[0].producto,
    cantidad: Number(rows[0].cantidad),
    monto: Number(rows[0].monto),
  };
}

export async function registrarDeuda(cliente, monto) {
  await pool.query(
    'INSERT INTO deudas (cliente, monto) VALUES ($1, $2)',
    [cliente, monto],
  );
}

export async function deudasPendientes() {
  const { rows } = await pool.query(`
    SELECT cliente, SUM(monto) AS monto
    FROM deudas
    WHERE pagado = FALSE
    GROUP BY cliente
    HAVING SUM(monto) > 0
    ORDER BY cliente ASC
  `);

  return rows.map((r) => ({ cliente: r.cliente, monto: Number(r.monto) }));
}

export async function crearProducto(codigo, nombre, precio, stock) {
  const { rows } = await pool.query(
    `INSERT INTO productos (codigo, nombre, precio, stock)
     VALUES ($1, $2, $3, $4)
     RETURNING id, codigo, nombre, precio, stock`,
    [codigo, nombre, precio, stock],
  );
  return mapProducto(rows[0]);
}

export async function actualizarPrecio(codigo, precio) {
  const { rows } = await pool.query(
    `UPDATE productos SET precio = $1
     WHERE LOWER(codigo) = LOWER($2)
     RETURNING id, codigo, nombre, precio, stock`,
    [precio, codigo],
  );
  return rows.length === 0 ? null : mapProducto(rows[0]);
}

export async function actualizarStock(codigo, stock) {
  const { rows } = await pool.query(
    `UPDATE productos SET stock = $1
     WHERE LOWER(codigo) = LOWER($2)
     RETURNING id, codigo, nombre, precio, stock`,
    [stock, codigo],
  );
  return rows.length === 0 ? null : mapProducto(rows[0]);
}

function mapProducto(row) {
  return {
    id: row.id,
    codigo: row.codigo,
    nombre: row.nombre,
    precio: Number(row.precio),
    stock: Number(row.stock),
  };
}

async function buscarProductoPorCodigo(codigo) {
  const { rows } = await pool.query(
    'SELECT id, codigo, nombre, precio, stock FROM productos WHERE LOWER(codigo) = LOWER($1)',
    [codigo],
  );
  return rows.length === 0 ? null : mapProducto(rows[0]);
}

export async function agregarAliasBatch(productoId, aliases) {
  for (const alias of aliases) {
    await pool.query(
      'INSERT INTO producto_alias (producto_id, alias) VALUES ($1, $2)',
      [productoId, alias],
    );
  }
}

// Devuelve el producto si se agregó, o null si el código no existe.
export async function agregarAlias(codigo, alias) {
  const producto = await buscarProductoPorCodigo(codigo);
  if (!producto) return null;

  await pool.query(
    'INSERT INTO producto_alias (producto_id, alias) VALUES ($1, $2)',
    [producto.id, alias],
  );
  return producto;
}

// Devuelve: null si el código no existe, false si el alias no estaba
// asociado a ese producto, o el producto si se quitó correctamente.
export async function quitarAlias(codigo, alias) {
  const producto = await buscarProductoPorCodigo(codigo);
  if (!producto) return null;

  const normalizado = normalizarTexto(alias);
  const { rows } = await pool.query(
    'SELECT id, alias FROM producto_alias WHERE producto_id = $1',
    [producto.id],
  );
  const coincidencia = rows.find((r) => normalizarTexto(r.alias) === normalizado);
  if (!coincidencia) return false;

  await pool.query('DELETE FROM producto_alias WHERE id = $1', [coincidencia.id]);
  return producto;
}

// Busca productos cuyo nombre, código o algún alias coincida exactamente
// (sin distinguir mayúsculas ni acentos) con el texto dado.
export async function buscarProductosPorTexto(texto) {
  const normalizado = normalizarTexto(texto);
  const { rows } = await pool.query(`
    SELECT p.id, p.codigo, p.nombre, p.precio, p.stock,
           COALESCE(array_agg(pa.alias) FILTER (WHERE pa.alias IS NOT NULL), '{}') AS aliases
    FROM productos p
    LEFT JOIN producto_alias pa ON pa.producto_id = p.id
    GROUP BY p.id
  `);

  return rows
    .filter((p) => [p.nombre, p.codigo, ...p.aliases].some((c) => normalizarTexto(c) === normalizado))
    .map(mapProducto);
}

// Descuenta el stock, registra la venta en la tabla `ventas` (para que
// entre en los totales) y devuelve el monto cobrado y el stock restante.
export async function registrarVentaCatalogo(producto, cantidad) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const montoTotal = producto.precio * cantidad;

    await client.query('UPDATE productos SET stock = stock - $1 WHERE id = $2', [
      cantidad,
      producto.id,
    ]);
    await client.query(
      'INSERT INTO ventas (producto, cantidad, monto) VALUES ($1, $2, $3)',
      [producto.nombre, cantidad, montoTotal],
    );
    const { rows } = await client.query('SELECT stock FROM productos WHERE id = $1', [
      producto.id,
    ]);

    await client.query('COMMIT');
    return { montoTotal, stockRestante: Number(rows[0].stock) };
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}

export default pool;
