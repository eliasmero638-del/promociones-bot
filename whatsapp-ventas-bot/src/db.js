import pg from 'pg';

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

export default pool;
