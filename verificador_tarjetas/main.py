"""
main.py — Programa de terminal (para usar por SSH desde Termius).

Ejecución:
    python3 main.py          -> abre el menú
    python3 main.py --demo   -> ejecuta solo el modo demostración

Por privacidad, el número NO se acepta como argumento de la línea de
comandos (quedaría guardado en el historial de la terminal). Se pide
siempre dentro del programa y no se guarda en ningún sitio.
"""

import sys

from tarjetas_prueba import NUMEROS_DEMO, NUMEROS_DEMO_INVALIDOS
from validador import resumen_texto, validar

LINEA = "-" * 60

MENU = """
==================  VERIFICADOR DE FORMATO  ==================
  1) Verificar un número de prueba
  2) Modo demostración (números oficiales de prueba de Stripe)
  3) Ayuda: ¿qué comprueba este programa?
  4) Salir
==============================================================
"""

AYUDA = """
¿Qué comprueba este programa?
  - Que solo haya dígitos (se permiten espacios y guiones).
  - Que la longitud sea correcta (12 a 19 dígitos, y la propia de cada red).
  - La red probable (Visa, Mastercard...) según los primeros dígitos.
  - El algoritmo de Luhn, que detecta errores al escribir.

¿Qué NO puede comprobar?
  - Si la tarjeta existe, está activa, bloqueada o tiene saldo.
    Solo el banco emisor lo sabe, a través de una pasarela de pagos.

Privacidad:
  - No se guarda nada: ni en archivos, ni en registros.
  - Nunca escribas fecha de caducidad ni CVV: no hacen falta.
  - Usa solo números de prueba, nunca los de una tarjeta real.
"""


def pedir_texto(mensaje: str) -> str:
    """input() que trata Ctrl+C / Ctrl+D como 'salir' sin mostrar errores."""
    try:
        return input(mensaje)
    except (KeyboardInterrupt, EOFError):
        print()
        raise SystemExit("\nPrograma cerrado. ¡Hasta luego!")


def verificar_uno() -> None:
    print("\nEscribe el número de PRUEBA (o deja vacío para volver al menú).")
    print("No escribas fecha de caducidad ni CVV.")
    texto = pedir_texto("Número: ")
    if not texto.strip():
        return
    print(LINEA)
    print(resumen_texto(validar(texto)))
    print(LINEA)
    texto = None  # no lo conservamos en memoria más de lo necesario


def modo_demo() -> None:
    print("\n### Números oficiales de prueba (deberían ser válidos) ###")
    for descripcion, numero in NUMEROS_DEMO:
        print(LINEA)
        print(f"Ejemplo: {descripcion}")
        print(f"Entrada: {numero}")
        print(resumen_texto(validar(numero)))

    print("\n### Ejemplos con errores (para ver las explicaciones) ###")
    for descripcion, numero in NUMEROS_DEMO_INVALIDOS:
        print(LINEA)
        print(f"Ejemplo: {descripcion}")
        print(f"Entrada: {numero}")
        print(resumen_texto(validar(numero)))
    print(LINEA)


def menu() -> None:
    acciones = {
        "1": verificar_uno,
        "2": modo_demo,
        "3": lambda: print(AYUDA),
    }
    while True:
        print(MENU)
        opcion = pedir_texto("Elige una opción (1-4): ").strip()
        if opcion == "4":
            print("¡Hasta luego!")
            return
        accion = acciones.get(opcion)
        if accion:
            accion()
        else:
            print("Opción no reconocida. Escribe 1, 2, 3 o 4.")


def main() -> None:
    if sys.version_info < (3, 8):
        raise SystemExit("Este programa necesita Python 3.8 o superior.")
    argumentos = sys.argv[1:]
    if argumentos == ["--demo"]:
        modo_demo()
    elif not argumentos:
        menu()
    else:
        print("Uso: python3 main.py           (menú)")
        print("     python3 main.py --demo    (modo demostración)")
        print("El número se pide dentro del programa, no como argumento,")
        print("para que no quede guardado en el historial de la terminal.")
        sys.exit(1)


if __name__ == "__main__":
    main()
