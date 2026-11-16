"""Imagen de la tarjeta: plantilla + nombre + una flor por cita (research §9).

Se genera siempre desde cero, en memoria, sin modificar imágenes anteriores (principio IV).
"""

import math
from dataclasses import dataclass
from functools import cache, lru_cache
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from tarjeta_lealtad import diseno


class NombreNoCabe(Exception):
    """El nombre no cabe en su área de la tarjeta ni con el tamaño mínimo."""


@dataclass(frozen=True)
class AjusteNombre:
    tamano: int  # tamaño de fuente elegido
    origen: tuple[int, int]  # esquina superior izquierda de la tinta en la tarjeta


@cache
def _plantilla() -> Image.Image:
    with Image.open(diseno.PLANTILLA) as imagen:
        return imagen.convert("RGB")


@cache
def _flor() -> Image.Image:
    with Image.open(diseno.FLOR) as imagen:
        return imagen.convert("RGBA")


@cache
def _fuente(tamano: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(diseno.FUENTE), tamano)


@lru_cache(maxsize=512)
def _tinta(nombre: str, tamano: int) -> Image.Image:
    """Máscara (modo L) del nombre recortada a sus píxeles de tinta.

    Se comparte desde la caché: quien la use no debe modificarla.
    """
    fuente = _fuente(tamano)
    izquierda, arriba, derecha, abajo = fuente.getbbox(nombre)
    margen = tamano  # los trazos manuscritos pueden salirse de la caja tipográfica
    lienzo = Image.new(
        "L",
        (math.ceil(derecha - izquierda) + 2 * margen, math.ceil(abajo - arriba) + 2 * margen),
        0,
    )
    ImageDraw.Draw(lienzo).text(
        (margen - izquierda, margen - arriba), nombre, font=fuente, fill=255
    )
    caja = lienzo.getbbox()
    if caja is None:
        raise NombreNoCabe(f"{nombre!r} no tiene tinta")
    return lienzo.crop(caja)


def _origen(tinta: Image.Image) -> tuple[int, int]:
    """Tinta centrada en la línea y apoyada justo encima de ella."""
    return round(
        diseno.CENTRO_NOMBRE_X - tinta.width / 2
    ), diseno.BORDE_INFERIOR_NOMBRE - tinta.height


def _cabe_en_el_area(tinta: Image.Image) -> bool:
    return (
        tinta.width <= diseno.ANCHO_MAX_NOMBRE
        and diseno.BORDE_INFERIOR_NOMBRE - tinta.height >= diseno.TOPE_SUPERIOR_NOMBRE
    )


def _toca_destello(tinta: Image.Image, origen: tuple[int, int]) -> bool:
    """Se compara la máscara real: las minúsculas pueden pasar por debajo del ✨ sin tocarlo."""
    x0, y0, x1, y1 = diseno.ZONA_DESTELLO
    ox, oy = origen
    izquierda, arriba = max(x0 - ox, 0), max(y0 - oy, 0)
    derecha, abajo = min(x1 - ox, tinta.width), min(y1 - oy, tinta.height)
    if izquierda >= derecha or arriba >= abajo:
        return False
    return tinta.crop((izquierda, arriba, derecha, abajo)).getbbox() is not None


@lru_cache(maxsize=512)
def ajustar_nombre(nombre: str) -> AjusteNombre:
    """Mayor tamaño con el que el nombre cabe en su área sin tocar el ✨ (FR-027)."""
    menor, mayor = diseno.TAMANO_MIN, diseno.TAMANO_MAX
    if not _cabe_en_el_area(_tinta(nombre, menor)):
        raise NombreNoCabe(nombre)
    # Ancho y alto crecen con el tamaño: búsqueda binaria del mayor que cabe en el área.
    while menor < mayor:
        medio = (menor + mayor + 1) // 2
        if _cabe_en_el_area(_tinta(nombre, medio)):
            menor = medio
        else:
            mayor = medio - 1
    # El choque con el ✨ no es monótono: se baja de uno en uno hasta que deja de tocarlo.
    for tamano in range(menor, diseno.TAMANO_MIN - 1, -1):
        tinta = _tinta(nombre, tamano)
        origen = _origen(tinta)
        if not _toca_destello(tinta, origen):
            return AjusteNombre(tamano, origen)
    raise NombreNoCabe(nombre)


def generar_tarjeta(nombre: str, flores: int) -> bytes:
    """PNG de 1050 × 600 con el nombre y `flores` flores en las primeras casillas."""
    if not 0 <= flores <= diseno.CASILLAS:
        raise ValueError(f"flores debe estar entre 0 y {diseno.CASILLAS}, no {flores}")
    ajuste = ajustar_nombre(nombre)
    tarjeta = _plantilla().copy()
    flor = _flor()
    for centro in diseno.CENTROS[:flores]:
        tarjeta.paste(flor, diseno.esquina_flor(centro), flor)
    tinta = _tinta(nombre, ajuste.tamano)
    x, y = ajuste.origen
    tarjeta.paste(diseno.COLOR_NOMBRE, (x, y, x + tinta.width, y + tinta.height), tinta)
    salida = BytesIO()
    tarjeta.save(salida, format="PNG")
    return salida.getvalue()
