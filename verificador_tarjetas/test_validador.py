"""
test_validador.py — Pruebas automáticas para comprobar que el validador
funciona. Ejecución:  python3 -m unittest -v test_validador.py
"""

import unittest

from tarjetas_prueba import NUMEROS_DEMO
from validador import (
    FORMATO_INVALIDO,
    FORMATO_VALIDO,
    NO_VERIFICABLE,
    pasa_luhn,
    validar,
)


class TestLuhn(unittest.TestCase):
    def test_numero_correcto(self):
        self.assertTrue(pasa_luhn("4242424242424242"))

    def test_numero_incorrecto(self):
        self.assertFalse(pasa_luhn("4242424242424241"))


class TestValidar(unittest.TestCase):
    def test_todos_los_numeros_demo_son_validos(self):
        for descripcion, numero in NUMEROS_DEMO:
            with self.subTest(descripcion):
                self.assertEqual(validar(numero).estado, FORMATO_VALIDO)

    def test_detecta_red(self):
        self.assertEqual(validar("4242424242424242").red, "Visa")
        self.assertEqual(validar("5555555555554444").red, "Mastercard")
        self.assertEqual(validar("378282246310005").red, "American Express")

    def test_falla_luhn(self):
        r = validar("4242424242424241")
        self.assertEqual(r.estado, FORMATO_INVALIDO)
        self.assertFalse(r.luhn_correcto)
        self.assertTrue(any("Luhn" in m for m in r.motivos))

    def test_longitud_general_incorrecta(self):
        r = validar("42424242")
        self.assertEqual(r.estado, FORMATO_INVALIDO)
        self.assertTrue(any("entre 12 y 19" in m for m in r.motivos))

    def test_longitud_de_la_red_incorrecta(self):
        # 15 dígitos empezando por 4: Visa no usa 15 dígitos.
        r = validar("424242424242424")
        self.assertEqual(r.estado, FORMATO_INVALIDO)
        self.assertTrue(any("Visa" in m for m in r.motivos))

    def test_caracteres_no_permitidos(self):
        r = validar("4242 4242 4242 42A2")
        self.assertEqual(r.estado, FORMATO_INVALIDO)
        self.assertTrue(any("no permitidos" in m for m in r.motivos))

    def test_fecha_incluida(self):
        r = validar("4242424242424242 12/30")
        self.assertEqual(r.estado, FORMATO_INVALIDO)
        self.assertTrue(any("fecha" in m for m in r.motivos))

    def test_digitos_no_ascii(self):
        # Dígitos árabes: parecen números, pero no se aceptan.
        self.assertEqual(validar("٤٢٤٢٤٢٤٢٤٢٤٢٤٢٤٢").estado, FORMATO_INVALIDO)

    def test_vacio(self):
        self.assertEqual(validar("   ").estado, NO_VERIFICABLE)

    def test_demasiado_largo(self):
        self.assertEqual(validar("4" * 100).estado, NO_VERIFICABLE)

    def test_no_es_texto(self):
        self.assertEqual(validar(None).estado, NO_VERIFICABLE)

    def test_solo_muestra_ultimos_4(self):
        r = validar("4242 4242 4242 4242")
        self.assertEqual(r.enmascarado, "•••• 4242")


if __name__ == "__main__":
    unittest.main()
