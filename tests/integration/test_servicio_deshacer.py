from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import select

from tarjeta_lealtad.db import Cita

Utc = Callable[[str], datetime]


def carmen_con_citas(servicio: Any, utc: Utc, cantidad: int) -> int:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-10-31 16:00"))
    for dia in range(1, cantidad + 1):
        servicio.registrar_cita(carmen.id, utc(f"2026-11-{dia:02d} 16:00"))
    return int(carmen.id)


def test_deshacer_anula_sin_borrar(servicio: Any, sesiones: Any, utc: Utc) -> None:
    cliente_id = carmen_con_citas(servicio, utc, 4)
    resumen = servicio.deshacer_ultima(cliente_id, utc("2026-11-16 17:00"))
    assert resumen.citas_en_curso == 3
    with sesiones() as s:
        citas = s.scalars(select(Cita).order_by(Cita.id)).all()
    assert len(citas) == 4
    assert [c.anulada_en for c in citas] == [None, None, None, utc("2026-11-16 17:00")]


def test_deshacer_el_premio_reabre_la_tarjeta(servicio: Any, utc: Utc) -> None:
    cliente_id = carmen_con_citas(servicio, utc, 10)
    assert servicio.resumen(cliente_id).tarjetas_completadas == 1
    resumen = servicio.deshacer_ultima(cliente_id, utc("2026-11-16 17:00"))
    assert resumen.citas_en_curso == 9
    assert resumen.tarjetas_completadas == 0
    assert resumen.proxima_es_premio is True


def test_deshacer_cita_previa(servicio: Any, utc: Utc) -> None:
    rosa = servicio.crear_cliente("Rosa", 2, utc("2026-11-16 16:00"))
    assert servicio.deshacer_ultima(rosa.id, utc("2026-11-16 17:00")).citas_en_curso == 1


def test_sin_citas_vigentes(servicio: Any, utc: Utc) -> None:
    ana = servicio.crear_cliente("Ana", 0, utc("2026-11-16 16:00"))
    assert servicio.ultima_cita_vigente(ana.id) is None
    assert servicio.deshacer_ultima(ana.id, utc("2026-11-16 17:00")) is None


def test_ultima_cita_vigente_y_dos_deshacer_seguidos(servicio: Any, utc: Utc) -> None:
    cliente_id = carmen_con_citas(servicio, utc, 3)
    ultima = servicio.ultima_cita_vigente(cliente_id)
    assert ultima.origen == "bot"
    assert ultima.registrada_en == utc("2026-11-03 16:00")
    servicio.deshacer_ultima(cliente_id, utc("2026-11-16 17:00"))
    assert servicio.ultima_cita_vigente(cliente_id).registrada_en == utc("2026-11-02 16:00")
    assert servicio.deshacer_ultima(cliente_id, utc("2026-11-16 17:01")).citas_en_curso == 1
