"""
validador.py — Lógica de validación de FORMATO de números de tarjeta.

IMPORTANTE:
    - Este módulo solo comprueba el formato (caracteres, longitud, red y
      algoritmo de Luhn). NO puede saber si una tarjeta existe, está activa
      o tiene fondos. Eso solo lo sabe el banco emisor.
    - No guarda nada: no escribe en disco, no usa red y no registra logs.
    - Nunca pide ni procesa fechas de caducidad ni códigos CVV.

Se puede usar desde la terminal (main.py) o desde el bot (bot_telegram.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# --- Resultados posibles (textos que verá el usuario) ----------------------
FORMATO_VALIDO = "Formato válido"
FORMATO_INVALIDO = "Formato inválido"
NO_VERIFICABLE = "No se pudo verificar"

# Aviso que se muestra SIEMPRE junto al resultado.
AVISO = (
    "Esto solo comprueba el formato. No indica si la tarjeta existe, "
    "está activa ni si tiene fondos."
)

# Separadores que aceptamos y simplemente ignoramos (p. ej. "4242 4242-...").
SEPARADORES_PERMITIDOS = {" ", "-"}

# Límite de seguridad para no procesar textos enormes.
MAX_CARACTERES_ENTRADA = 40

# Longitud general de un número de tarjeta (norma ISO/IEC 7812).
LONGITUD_MIN = 12
LONGITUD_MAX = 19


@dataclass
class Red:
    """Describe una red de tarjetas y las reglas de formato que usa."""

    nombre: str
    longitudes: tuple
    prefijos: tuple  # cada prefijo es un texto ("4") o un rango (2221, 2720)


# Reglas públicas de prefijos (IIN) y longitudes. El orden importa: se
# comprueban de arriba a abajo y gana la primera coincidencia.
REDES: List[Red] = [
    Red("American Express", (15,), ("34", "37")),
    Red("Diners Club", (14, 15, 16, 17, 18, 19), ("36", "38", "39", (300, 305))),
    Red("JCB", (16, 17, 18, 19), ((3528, 3589),)),
    Red("Discover", (16, 17, 18, 19), ("6011", "65", (644, 649))),
    Red("UnionPay", (16, 17, 18, 19), ("62",)),
    Red("Mastercard", (16,), ((51, 55), (2221, 2720))),
    Red("Maestro", tuple(range(12, 20)), ("50", (56, 58), "6")),
    Red("Visa", (13, 16, 19), ("4",)),
]


@dataclass
class Resultado:
    """Todo lo que el programa sabe tras revisar un número."""

    estado: str  # FORMATO_VALIDO, FORMATO_INVALIDO o NO_VERIFICABLE
    motivos: List[str] = field(default_factory=list)  # por qué falla
    red: Optional[str] = None
    longitud: int = 0
    luhn_correcto: Optional[bool] = None
    enmascarado: str = ""  # solo los últimos 4 dígitos, p. ej. "•••• 4242"

    @property
    def es_valido(self) -> bool:
        return self.estado == FORMATO_VALIDO


# --- Funciones auxiliares ---------------------------------------------------

def limpiar(texto: str) -> str:
    """Quita espacios y guiones. No toca ningún otro carácter."""
    return "".join(c for c in texto if c not in SEPARADORES_PERMITIDOS)


def enmascarar(digitos: str) -> str:
    """Devuelve el número oculto, mostrando solo los últimos 4 dígitos."""
    if len(digitos) < 4:
        return "••••"
    return "•••• " + digitos[-4:]


def pasa_luhn(digitos: str) -> bool:
    """
    Algoritmo de Luhn (también llamado "módulo 10").

    1. Empezando por la DERECHA, se duplica uno de cada dos dígitos
       (el segundo, el cuarto, el sexto...).
    2. Si al duplicar sale un número mayor que 9, se le resta 9.
    3. Se suman todos los dígitos.
    4. Si la suma termina en 0 (es múltiplo de 10), el número es válido.

    El algoritmo solo detecta errores de escritura (un dígito cambiado,
    dos dígitos intercambiados...). No dice nada sobre si la tarjeta existe.
    """
    total = 0
    for posicion, caracter in enumerate(reversed(digitos)):
        valor = int(caracter)
        if posicion % 2 == 1:  # uno de cada dos, empezando por la derecha
            valor *= 2
            if valor > 9:
                valor -= 9
        total += valor
    return total % 10 == 0


def _coincide_prefijo(digitos: str, prefijo) -> bool:
    if isinstance(prefijo, str):
        return digitos.startswith(prefijo)
    inicio, fin = prefijo  # rango numérico, p. ej. (51, 55)
    tamano = len(str(inicio))
    if len(digitos) < tamano:
        return False
    return inicio <= int(digitos[:tamano]) <= fin


def detectar_red(digitos: str) -> Optional[Red]:
    """Identifica la red por los primeros dígitos. None si no se reconoce."""
    for red in REDES:
        if any(_coincide_prefijo(digitos, p) for p in red.prefijos):
            return red
    return None


# --- Función principal -------------------------------------------------------

def validar(texto) -> Resultado:
    """
    Revisa el texto introducido y devuelve un Resultado con la explicación.

    Nunca lanza excepciones: si algo inesperado ocurre, devuelve
    "No se pudo verificar" con un mensaje comprensible.
    """
    try:
        return _validar(texto)
    except Exception:  # red de seguridad: no mostrar errores técnicos
        return Resultado(
            estado=NO_VERIFICABLE,
            motivos=["Ocurrió un error inesperado al revisar el número."],
        )


def _validar(texto) -> Resultado:
    # 1) ¿Hay algo que revisar?
    if not isinstance(texto, str):
        return Resultado(NO_VERIFICABLE, ["La entrada no es texto."])
    texto = texto.strip()
    if not texto:
        return Resultado(NO_VERIFICABLE, ["No escribiste ningún número."])
    if len(texto) > MAX_CARACTERES_ENTRADA:
        return Resultado(
            NO_VERIFICABLE,
            [f"El texto es demasiado largo (máximo {MAX_CARACTERES_ENTRADA} caracteres)."],
        )

    motivos: List[str] = []

    # 2) ¿Hay caracteres no permitidos?
    digitos = limpiar(texto)
    no_permitidos = sorted({c for c in digitos if not c.isdigit() or not c.isascii()})
    if no_permitidos:
        mostrados = " ".join(repr(c) for c in no_permitidos)
        motivos.append(
            f"Contiene caracteres no permitidos: {mostrados}. "
            "Solo se aceptan dígitos (0-9), espacios y guiones."
        )
        if "/" in no_permitidos:
            motivos.append(
                "Parece que incluiste una fecha. Escribe SOLO el número, "
                "sin fecha de caducidad ni CVV."
            )
        # Sin dígitos limpios no tiene sentido seguir con el resto de pruebas.
        return Resultado(FORMATO_INVALIDO, motivos)

    resultado = Resultado(
        estado=FORMATO_INVALIDO,
        longitud=len(digitos),
        enmascarado=enmascarar(digitos),
    )

    # 3) ¿Longitud general correcta?
    if not LONGITUD_MIN <= len(digitos) <= LONGITUD_MAX:
        motivos.append(
            f"Tiene {len(digitos)} dígitos; un número de tarjeta tiene entre "
            f"{LONGITUD_MIN} y {LONGITUD_MAX}."
        )

    # 4) ¿De qué red es y encaja su longitud?
    red = detectar_red(digitos)
    if red:
        resultado.red = red.nombre
        if LONGITUD_MIN <= len(digitos) <= LONGITUD_MAX and len(digitos) not in red.longitudes:
            esperadas = ", ".join(str(n) for n in red.longitudes)
            motivos.append(
                f"Parece {red.nombre}, que usa {esperadas} dígitos, "
                f"pero este tiene {len(digitos)}."
            )

    # 5) ¿Pasa el algoritmo de Luhn?
    resultado.luhn_correcto = pasa_luhn(digitos)
    if not resultado.luhn_correcto:
        motivos.append(
            "No supera el algoritmo de Luhn: el último dígito (dígito de "
            "control) no cuadra con los demás. Suele indicar un error al escribir."
        )

    resultado.motivos = motivos
    if not motivos:
        resultado.estado = FORMATO_VALIDO
        if red is None:
            resultado.red = "No identificada"
    return resultado


def resumen_texto(resultado: Resultado) -> str:
    """Convierte un Resultado en un texto listo para mostrar al usuario."""
    lineas = [f"Resultado: {resultado.estado}"]
    if resultado.enmascarado:
        lineas.append(f"Número:    {resultado.enmascarado}")
    if resultado.red:
        lineas.append(f"Red:       {resultado.red}")
    if resultado.longitud:
        lineas.append(f"Longitud:  {resultado.longitud} dígitos")
    if resultado.luhn_correcto is not None:
        lineas.append(f"Luhn:      {'correcto' if resultado.luhn_correcto else 'incorrecto'}")
    if resultado.motivos:
        lineas.append("Motivos:")
        lineas.extend(f"  - {m}" for m in resultado.motivos)
    lineas.append("")
    lineas.append(f"Aviso: {AVISO}")
    return "\n".join(lineas)
