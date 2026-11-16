from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import select

from tarjeta_lealtad.db import Cita, Cliente
from tarjeta_lealtad.servicio import Encontrado, NombreInvalido, Parecidos, SinCoincidencias

Utc = Callable[[str], datetime]


def test_buscar_ignora_mayusculas_acentos_y_espacios(servicio: Any, utc: Utc) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-16 16:00"))
    for texto in ("carmen", "Cármen", "  CARMEN "):
        resultado = servicio.buscar(texto)
        assert isinstance(resultado, Encontrado)
        assert resultado.cliente.id == carmen.id


def test_sin_coincidencias(servicio: Any, utc: Utc) -> None:
    servicio.crear_cliente("Carmen", 0, utc("2026-11-16 16:00"))
    assert isinstance(servicio.buscar("Lucía"), SinCoincidencias)


def test_parecidos_por_errata(servicio: Any, utc: Utc) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-16 16:00"))
    resultado = servicio.buscar("Carmn")
    assert isinstance(resultado, Parecidos)
    assert carmen.id in [opcion.id for opcion in resultado.opciones]


def test_parecidos_maximo_seis_ordenados(servicio: Any, utc: Utc) -> None:
    nombres = ["Carmen", "Carmela", "Carmín", "Carla", "Carina", "Carola", "Carmina", "Carmona"]
    for nombre in nombres:
        servicio.crear_cliente(nombre, 0, utc("2026-11-16 16:00"))
    resultado = servicio.buscar("Car")
    assert isinstance(resultado, Parecidos)
    # "Carla" está a distancia 2; los demás solo coinciden por prefijo y van por nombre.
    assert [o.nombre for o in resultado.opciones] == [
        "Carla",
        "Carina",
        "Carmela",
        "Carmen",
        "Carmín",
        "Carmina",
    ]


def test_validar_nombre(servicio: Any) -> None:
    assert servicio.validar_nombre("  Lucía ") == "Lucía"
    with pytest.raises(NombreInvalido, match="😀"):
        servicio.validar_nombre("Ana 😀")
    with pytest.raises(NombreInvalido, match="7"):
        servicio.validar_nombre("Ana7")
    with pytest.raises(NombreInvalido, match="demasiado largo"):
        servicio.validar_nombre("Maximiliana Guadalupe Montoya Ruiz")
    with pytest.raises(NombreInvalido, match="letra"):
        servicio.validar_nombre(" .. ")


def test_crear_cliente(servicio: Any, sesiones: Any, utc: Utc) -> None:
    resumen = servicio.crear_cliente("  María   López ", 0, utc("2026-11-16 16:00"))
    assert resumen.nombre == "María López"
    assert resumen.citas_en_curso == 0
    with sesiones() as s:
        cliente = s.get(Cliente, resumen.id)
        assert cliente.nombre_normalizado == "maria lopez"
        assert cliente.creado_en == utc("2026-11-16 16:00")


def test_registrar_cita(servicio: Any, sesiones: Any, utc: Utc) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-15 16:00"))
    primera = servicio.registrar_cita(carmen.id, utc("2026-11-15 16:32"))
    assert primera.cliente.citas_en_curso == 1
    assert primera.flores == 1
    assert primera.es_premio is False
    segunda = servicio.registrar_cita(carmen.id, utc("2026-11-16 16:32"))
    assert segunda.cliente.citas_en_curso == 2
    assert segunda.cliente.ultima_cita == utc("2026-11-16 16:32")
    with sesiones() as s:
        citas = s.scalars(select(Cita).order_by(Cita.id)).all()
        assert [(c.origen, c.registrada_en) for c in citas] == [
            ("bot", utc("2026-11-15 16:32")),
            ("bot", utc("2026-11-16 16:32")),
        ]


def test_cita_del_dia_en_la_zona_del_negocio(servicio: Any, utc: Utc) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-16 16:00"))
    # 05:30 UTC del 17 = 23:30 del 16 en Mexico City
    servicio.registrar_cita(carmen.id, utc("2026-11-17 05:30"))
    # 02:00 UTC del 17 = 20:00 del 16: mismo día local
    assert servicio.cita_del_dia(carmen.id, utc("2026-11-17 02:00")) == utc("2026-11-17 05:30")
    # 15:00 UTC del 17 = 09:00 del 17: otro día local
    assert servicio.cita_del_dia(carmen.id, utc("2026-11-17 15:00")) is None
