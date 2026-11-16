"""Render de la tarjeta: verificación determinista por píxeles (principio III)."""

import math
import string
import time
from io import BytesIO

import pytest
from PIL import Image, ImageChops, ImageDraw, ImageFont

from tarjeta_lealtad import diseno
from tarjeta_lealtad.render import NombreNoCabe, ajustar_nombre, generar_tarjeta

BLANCO = (255, 255, 255)
RECTANGULO_NOMBRE = (40, 240, 451, 377)  # x0, y0, x1, y1 (exclusivos)
NOMBRES_SC006 = [
    "María Fernanda Ruiz",
    "Guadalupe Hernández",
    "Wendy Montserrat Paz",
    "Maximiliana Montoya",
    "Ximena Guadalupe Mtz",
    "Marisol Del Castillo",
    "Itzel Bethel Ballard",
    "Wilhelmina Whitfield",
]


def abrir(png: bytes) -> Image.Image:
    return Image.open(BytesIO(png)).convert("RGB")


def plantilla() -> Image.Image:
    return Image.open(diseno.PLANTILLA).convert("RGB")


def disco(radio: int) -> Image.Image:
    mascara = Image.new("L", (2 * radio + 1, 2 * radio + 1), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, 2 * radio, 2 * radio), fill=255)
    return mascara


def no_blancos_en_disco(img: Image.Image, centro: tuple[float, float], radio: int) -> int:
    cx, cy = math.floor(centro[0]), math.floor(centro[1])
    recorte = img.crop((cx - radio, cy - radio, cx + radio + 1, cy + radio + 1))
    diferencia = ImageChops.difference(recorte, Image.new("RGB", recorte.size, BLANCO))
    distintos = diferencia.convert("L").point(lambda v: 255 if v else 0)
    distintos = ImageChops.multiply(distintos, disco(radio))
    return sum(distintos.histogram()[1:])


def tinta_del_nombre(img: Image.Image) -> Image.Image:
    """Máscara (modo L) de lo que difiere de la plantilla dentro del rectángulo del nombre."""
    diferencia = ImageChops.difference(img, plantilla()).convert("L")
    solo_rectangulo = Image.new("L", img.size, 0)
    solo_rectangulo.paste(diferencia.crop(RECTANGULO_NOMBRE), RECTANGULO_NOMBRE[:2])
    return solo_rectangulo.point(lambda v: 255 if v else 0)


def test_salida_es_png_1050x600() -> None:
    img = Image.open(BytesIO(generar_tarjeta("Carmen", 3)))
    assert img.format == "PNG"
    assert img.size == (1050, 600)


@pytest.mark.parametrize("flores", range(diseno.CASILLAS + 1))
def test_flores_en_las_casillas_correctas(flores: int) -> None:
    img = abrir(generar_tarjeta("Carmen", flores))
    for indice, centro in enumerate(diseno.CENTROS):
        if indice < flores:
            area = math.pi * 50**2
            assert no_blancos_en_disco(img, centro, 50) >= 0.2 * area, f"casilla {indice + 1}"
        else:
            # radio 54: a partir de ~56,5 empieza el borde suavizado del círculo de la plantilla
            assert no_blancos_en_disco(img, centro, 54) == 0, f"casilla {indice + 1}"


def test_fuera_de_casillas_y_nombre_igual_a_la_plantilla() -> None:
    img = abrir(generar_tarjeta("Maximiliana Montoya", 9))
    diferencia = ImageChops.difference(img, plantilla()).convert("L")
    tapar = ImageDraw.Draw(diferencia)
    for cx, cy in diseno.CENTROS:
        x, y = math.floor(cx), math.floor(cy)
        tapar.ellipse((x - 58, y - 58, x + 58, y + 58), fill=0)
    tapar.rectangle(
        (
            RECTANGULO_NOMBRE[0],
            RECTANGULO_NOMBRE[1],
            RECTANGULO_NOMBRE[2] - 1,
            RECTANGULO_NOMBRE[3] - 1,
        ),
        fill=0,
    )
    assert diferencia.getbbox() is None


@pytest.mark.parametrize("nombre", ["Carmen", "Isabel", "Ángela", "Íñigo", *NOMBRES_SC006])
def test_tinta_del_nombre_dentro_del_area_y_fuera_del_destello(nombre: str) -> None:
    tinta = tinta_del_nombre(abrir(generar_tarjeta(nombre, 0)))
    caja = tinta.getbbox()
    assert caja is not None, "el nombre no se dibujó"
    x0, y0, x1, y1 = caja
    assert x0 >= 50 and x1 <= 440, f"ancho fuera de la línea: {caja}"
    assert y1 - 1 <= 370, f"la tinta baja hasta y={y1 - 1}"
    assert y0 >= diseno.TOPE_SUPERIOR_NOMBRE, f"la tinta sube hasta y={y0} (toca el título)"
    assert tinta.crop(diseno.ZONA_DESTELLO).getbbox() is None, "la tinta toca el destello"


def test_tamanos_de_referencia() -> None:
    assert ajustar_nombre("Carmen").tamano == 117
    assert ajustar_nombre("Isabel").tamano < 117


@pytest.mark.parametrize("nombre", NOMBRES_SC006)
def test_nombres_largos_caben(nombre: str) -> None:
    assert ajustar_nombre(nombre).tamano >= 36


def test_nombre_demasiado_largo() -> None:
    with pytest.raises(NombreNoCabe):
        ajustar_nombre("Maximiliana Guadalupe Montoya Ruiz")


def test_determinismo() -> None:
    assert generar_tarjeta("Guadalupe Hernández", 5) == generar_tarjeta("Guadalupe Hernández", 5)


@pytest.mark.parametrize("flores", [-1, diseno.CASILLAS + 1])
def test_flores_fuera_de_rango(flores: int) -> None:
    with pytest.raises(ValueError):
        generar_tarjeta("Carmen", flores)


def test_la_fuente_tiene_todos_los_caracteres_permitidos() -> None:
    latin1 = [chr(c) for c in range(0xC0, 0x100) if c not in (0xD7, 0xF7)]
    permitidos = [*string.ascii_letters, *latin1, "'", "-", "."]
    fuente = ImageFont.truetype(str(diseno.FUENTE), 60)

    def huella(caracter: str) -> tuple[tuple[int, int], bytes]:
        mascara = fuente.getmask(caracter)
        return mascara.size, bytes(mascara)

    no_definido = huella("")
    faltantes = [c for c in permitidos if huella(c) == no_definido]
    assert faltantes == []


@pytest.mark.parametrize("nombre", NOMBRES_SC006)
def test_rendimiento(nombre: str) -> None:
    inicio = time.perf_counter()
    generar_tarjeta(nombre + " ", 9)  # espacio final: evita la caché de ajustar_nombre
    assert time.perf_counter() - inicio < 1.0
