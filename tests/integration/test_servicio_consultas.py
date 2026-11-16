from collections.abc import Callable
from datetime import datetime
from typing import Any

Utc = Callable[[str], datetime]


def test_listar_vacio(servicio: Any) -> None:
    assert servicio.listar() == ()


def test_listar_ordena_por_nombre_y_luego_por_id(servicio: Any, utc: Utc) -> None:
    ahora = utc("2026-11-16 16:00")
    rosa = servicio.crear_cliente("Rosa", 3, ahora)
    carmen_1 = servicio.crear_cliente("carmen", 0, ahora)
    angela = servicio.crear_cliente("Ángela", 9, ahora)
    carmen_2 = servicio.crear_cliente("Carmen", 0, ahora)
    servicio.registrar_cita(rosa.id, utc("2026-11-16 16:30"))

    lista = servicio.listar()
    assert [c.id for c in lista] == [angela.id, carmen_1.id, carmen_2.id, rosa.id]
    por_id = {c.id: c for c in lista}
    assert por_id[rosa.id].citas_en_curso == 4
    assert por_id[rosa.id].ultima_cita == utc("2026-11-16 16:30")  # las previas no tienen fecha
    assert por_id[angela.id].ultima_cita is None
    assert por_id[angela.id].proxima_es_premio is True
