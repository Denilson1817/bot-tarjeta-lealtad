"""Normalización, búsqueda tolerante y validación de nombres (research §7–§8). Sin E/S."""

import unicodedata

# Letras Latin-1 (À–ÿ) sin "×" ni "÷": todas existen en la fuente del nombre.
_LATIN1 = frozenset(chr(c) for c in range(0xC0, 0x100)) - {"×", "÷"}
_ASCII = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
_SIGNOS = frozenset(" '-.")
_APOSTROFOS = str.maketrans({"\u2018": "'", "\u2019": "'"})  # el iPhone los escribe "curvos"

DISTANCIA_MAXIMA = 2
PUNTUACION_PREFIJO = DISTANCIA_MAXIMA + 1  # después de cualquier errata


def normalizar(texto: str) -> str:
    """Sin mayúsculas, acentos ni espacios sobrantes: "Cármen  LÓPEZ" → "carmen lopez"."""
    sin_marcas = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sin_marcas.casefold().split())


def limpiar_nombre(nombre: str) -> str:
    """Recorta y colapsa espacios; conserva mayúsculas y acentos tal como los escribió el dueño."""
    return " ".join(nombre.translate(_APOSTROFOS).split())


def caracteres_no_admitidos(nombre: str) -> list[str]:
    """Caracteres que no pueden ir en un nombre, sin repetir y en orden de aparición."""
    malos: list[str] = []
    for caracter in nombre:
        admitido = caracter in _ASCII or caracter in _LATIN1 or caracter in _SIGNOS
        if not admitido and caracter not in malos:
            malos.append(caracter)
    return malos


def distancia(a: str, b: str) -> int:
    """Damerau-Levenshtein (OSA): falta, sobra, cambia o se intercambia una letra."""
    anterior2: list[int] = []
    anterior = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        actual = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            costo = 0 if a[i - 1] == b[j - 1] else 1
            actual[j] = min(anterior[j] + 1, actual[j - 1] + 1, anterior[j - 1] + costo)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                actual[j] = min(actual[j], anterior2[j - 2] + 1)
        anterior2, anterior = anterior, actual
    return anterior[len(b)]


def parecido(consulta: str, nombre: str) -> int | None:
    """Puntuación (menor = más parecido) o None. Ambos textos ya normalizados.

    Es parecido si está a distancia ≤ 2 del nombre o de alguna de sus palabras, o si la consulta
    es el inicio del nombre o de alguna de sus palabras.
    """
    if not consulta:
        return None
    candidatos = [nombre, *nombre.split()]
    mejor = min(distancia(consulta, candidato) for candidato in candidatos)
    if mejor <= DISTANCIA_MAXIMA:
        return mejor
    if any(candidato.startswith(consulta) for candidato in candidatos):
        return PUNTUACION_PREFIJO
    return None


def interpretar_id(texto: str) -> int | None:
    """Identificador de cliente escrito como "#12" o "12" (solo dígitos ASCII)."""
    limpio = texto.strip().removeprefix("#")
    if limpio.isascii() and limpio.isdigit():
        return int(limpio)
    return None
