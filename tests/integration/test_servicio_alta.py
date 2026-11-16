from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import select

from tarjeta_lealtad.db import Cita
from tarjeta_lealtad.servicio import CitasPreviasFueraDeRango, NombreInvalido, SinCoincidencias

Utc = Callable[[str], datetime]


def test_alta_con_citas_previas(servicio: Any, sesiones: Any, utc: Utc) -> None:
    rosa = servicio.crear_cliente("Rosa", 6, utc("2026-11-16 16:32"))
    assert rosa.citas_en_curso == 6
    assert rosa.ultima_cita is None
    with sesiones() as s:
        citas = s.scalars(select(Cita).where(Cita.cliente_id == rosa.id)).all()
    assert len(citas) == 6
    assert all(c.origen == "previa" and c.registrada_en is None for c in citas)
    # el alta no cuenta como cita del día
    assert servicio.cita_del_dia(rosa.id, utc("2026-11-16 16:32")) is None
    assert servicio.registrar_cita(rosa.id, utc("2026-11-16 16:40")).cliente.citas_en_curso == 7


@pytest.mark.parametrize("previas", [-1, 10])
def test_previas_fuera_de_rango(servicio: Any, utc: Utc, previas: int) -> None:
    with pytest.raises(CitasPreviasFueraDeRango):
        servicio.crear_cliente("Rosa", previas, utc("2026-11-16 16:32"))
    assert isinstance(servicio.buscar("rosa"), SinCoincidencias)


def test_con_nueve_previas_la_siguiente_es_premio(servicio: Any, utc: Utc) -> None:
    rosa = servicio.crear_cliente("Rosa", 9, utc("2026-11-16 16:32"))
    assert rosa.proxima_es_premio is True
    assert servicio.registrar_cita(rosa.id, utc("2026-11-16 16:40")).es_premio is True


def test_homonimos(servicio: Any, utc: Utc) -> None:
    rosa = servicio.crear_cliente("Rosa", 0, utc("2026-11-16 16:32"))
    assert [c.id for c in servicio.homonimos("rosa")] == [rosa.id]
    assert [c.id for c in servicio.homonimos(" Rósa ")] == [rosa.id]
    assert servicio.homonimos("Lucía") == ()


def test_alta_con_nombre_invalido(servicio: Any, utc: Utc) -> None:
    with pytest.raises(NombreInvalido):
        servicio.crear_cliente("Ana 😀", 0, utc("2026-11-16 16:32"))
