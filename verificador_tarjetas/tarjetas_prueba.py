"""
tarjetas_prueba.py — Números de PRUEBA publicados oficialmente por Stripe.

Fuente: https://docs.stripe.com/testing  (sección "Cards by brand")

Estos números son públicos y ficticios: Stripe los publica para que los
desarrolladores prueben sus integraciones en "modo test". No pertenecen a
ninguna persona, no tienen fondos y cualquier comercio real los rechaza.

Puedes añadir o quitar ejemplos editando la lista NUMEROS_DEMO.
"""

# (descripción, número)
NUMEROS_DEMO = [
    ("Visa (prueba Stripe)", "4242 4242 4242 4242"),
    ("Visa débito (prueba Stripe)", "4000 0566 5566 5556"),
    ("Mastercard (prueba Stripe)", "5555 5555 5555 4444"),
    ("Mastercard serie 2 (prueba Stripe)", "2223 0031 2200 3222"),
    ("American Express (prueba Stripe)", "3782 822463 10005"),
    ("Discover (prueba Stripe)", "6011 1111 1111 1117"),
    ("Diners Club 14 dígitos (prueba Stripe)", "3622 720627 1667"),
    ("JCB (prueba Stripe)", "3566 0020 2036 0505"),
    ("UnionPay (prueba Stripe)", "6200 0000 0000 0005"),
]

# Ejemplos que FALLAN a propósito, para ver las explicaciones de error.
# Son variaciones de los números anteriores, no tarjetas nuevas.
NUMEROS_DEMO_INVALIDOS = [
    ("Último dígito cambiado (falla Luhn)", "4242 4242 4242 4241"),
    ("Le falta un dígito (longitud)", "4242 4242 4242 424"),
    ("Contiene una letra", "4242 4242 4242 42A2"),
    ("Incluye fecha (no permitido)", "4242424242424242 12/30"),
]
