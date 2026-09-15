import test from 'node:test';
import assert from 'node:assert/strict';
import { parseMensaje } from './parser.js';

test('venta: cantidad, producto y monto simples', () => {
  assert.deepEqual(parseMensaje('1 Relay 5$'), {
    tipo: 'venta',
    cantidad: 1,
    producto: 'Relay',
    monto: 5,
  });
});

test('venta: producto con varias palabras', () => {
  assert.deepEqual(parseMensaje('1 filtro de aceite 8$'), {
    tipo: 'venta',
    cantidad: 1,
    producto: 'filtro de aceite',
    monto: 8,
  });
});

test('venta: cantidad mayor a uno', () => {
  assert.deepEqual(parseMensaje('3 rulimanes 15$'), {
    tipo: 'venta',
    cantidad: 3,
    producto: 'rulimanes',
    monto: 15,
  });
});

test('venta: monto con decimales y coma', () => {
  assert.deepEqual(parseMensaje('2 bujias 12,50$'), {
    tipo: 'venta',
    cantidad: 2,
    producto: 'bujias',
    monto: 12.5,
  });
});

test('total: hoy/semana/mes, sin distinguir mayúsculas', () => {
  assert.deepEqual(parseMensaje('Total hoy'), { tipo: 'total', periodo: 'hoy' });
  assert.deepEqual(parseMensaje('total semana'), { tipo: 'total', periodo: 'semana' });
  assert.deepEqual(parseMensaje('TOTAL MES'), { tipo: 'total', periodo: 'mes' });
});

test('deuda: nombre simple y compuesto', () => {
  assert.deepEqual(parseMensaje('Debe Juan 30'), {
    tipo: 'deuda',
    cliente: 'Juan',
    monto: 30,
  });
  assert.deepEqual(parseMensaje('debe Juan Perez 30.50'), {
    tipo: 'deuda',
    cliente: 'Juan Perez',
    monto: 30.5,
  });
});

test('corregir ultima venta: con y sin tilde', () => {
  assert.deepEqual(parseMensaje('Corregir última venta 1 Relay 5$'), {
    tipo: 'corregir_venta',
    cantidad: 1,
    producto: 'Relay',
    monto: 5,
  });
  assert.deepEqual(parseMensaje('corregir la ultima venta 3 rulimanes 15$'), {
    tipo: 'corregir_venta',
    cantidad: 3,
    producto: 'rulimanes',
    monto: 15,
  });
});

test('quien debe: con y sin tilde', () => {
  assert.deepEqual(parseMensaje('Quién debe'), { tipo: 'quien_debe' });
  assert.deepEqual(parseMensaje('quien debe'), { tipo: 'quien_debe' });
});

test('agregar producto al catalogo', () => {
  assert.deepEqual(parseMensaje('#AgregarProducto 10 Relay 5 patas 100$ #RL01'), {
    tipo: 'agregar_producto',
    stock: 10,
    nombre: 'Relay 5 patas',
    precio: 100,
    codigo: 'RL01',
  });
});

test('alias: agregar y quitar', () => {
  assert.deepEqual(parseMensaje('Alias RL01 relay chiquito'), {
    tipo: 'agregar_alias',
    codigo: 'RL01',
    alias: 'relay chiquito',
  });
  assert.deepEqual(parseMensaje('Quitar alias RL01 relay chiquito'), {
    tipo: 'quitar_alias',
    codigo: 'RL01',
    alias: 'relay chiquito',
  });
});

test('ventas hoy: con y sin tilde', () => {
  assert.deepEqual(parseMensaje('Ventas hoy'), { tipo: 'ventas_hoy' });
  assert.deepEqual(parseMensaje('ventas hoy'), { tipo: 'ventas_hoy' });
});

test('corregir venta por numero', () => {
  assert.deepEqual(parseMensaje('Corregir venta 2 1 Relay 0$'), {
    tipo: 'corregir_venta_n',
    posicion: 2,
    cantidad: 1,
    producto: 'Relay',
    monto: 0,
  });
});

test('actualizar precio y stock de un producto', () => {
  assert.deepEqual(parseMensaje('Precio RL01 120$'), {
    tipo: 'actualizar_precio',
    codigo: 'RL01',
    precio: 120,
  });
  assert.deepEqual(parseMensaje('Stock RL01 20'), {
    tipo: 'actualizar_stock',
    codigo: 'RL01',
    stock: 20,
  });
});

test('venta por catalogo: con y sin cantidad', () => {
  assert.deepEqual(parseMensaje('Venta relay mini'), {
    tipo: 'venta_catalogo',
    cantidad: 1,
    texto: 'relay mini',
  });
  assert.deepEqual(parseMensaje('venta 2 relay mini'), {
    tipo: 'venta_catalogo',
    cantidad: 2,
    texto: 'relay mini',
  });
});

test('mensaje no reconocido', () => {
  assert.deepEqual(parseMensaje('hola'), { tipo: 'desconocido' });
  assert.deepEqual(parseMensaje('1 Relay'), { tipo: 'desconocido' });
});
