"""Geometría de la tarjeta, medida sobre la tarjeta de referencia (research §9).

Coordenadas en píxeles sobre el lienzo de 1050 × 600 de `assets/plantilla-vacia.png`.
"""

import math
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / "assets"
PLANTILLA = ASSETS / "plantilla-vacia.png"
FLOR = ASSETS / "flor.png"
FUENTE = ASSETS / "fuentes" / "Sacramento-Regular.ttf"

# Centros de las casillas en orden de llenado: por filas, de izquierda a derecha.
_COLUMNAS = (584.0, 769.5, 954.5)
_FILAS = (119.0, 301.0, 483.0)
CENTROS: tuple[tuple[float, float], ...] = tuple((x, y) for y in _FILAS for x in _COLUMNAS)
CASILLAS = len(CENTROS)

# flor.png mide 115 × 115 y su píxel central va en el centro de la casilla; en los centros con .5
# se redondea hacia abajo, que es como está en el diseño.
MITAD_FLOR = 57

# El nombre se centra sobre la línea (x 50–440) y su tinta termina justo encima de ella (y = 378).
CENTRO_NOMBRE_X = 245
BORDE_INFERIOR_NOMBRE = 370
TOPE_SUPERIOR_NOMBRE = 246  # el título termina en y = 234
ANCHO_MAX_NOMBRE = 390
TAMANO_MAX = 117  # con él "Carmen" mide 86 px de alto, como en la tarjeta de referencia
TAMANO_MIN = 36
ZONA_DESTELLO = (310, 274, 354, 323)  # x0, y0, x1, y1 (x1 e y1 exclusivos): ✨ + 6 px de margen
COLOR_NOMBRE = (255, 255, 255)


def esquina_flor(centro: tuple[float, float]) -> tuple[int, int]:
    """Esquina superior izquierda donde se pega la flor para la casilla con ese centro."""
    return math.floor(centro[0]) - MITAD_FLOR, math.floor(centro[1]) - MITAD_FLOR
