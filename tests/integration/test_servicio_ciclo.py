from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from tarjeta_lealtad.servicio import ServicioTarjetas

Utc = Callable[[str], datetime]


def registrar_dias(servicio: Any, cliente_id: int, dias: range, utc: Utc) -> list[Any]:
    return [servicio.registrar_cita(cliente_id, utc(f"2026-11-{d:02d} 16:00")) for d in dias]


def test_ciclo_completo_de_tarjeta(servicio: Any, utc: Utc) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-10-31 16:00"))
    resultados = registrar_dias(servicio, carmen.id, range(1, 12), utc)

    novena = resultados[8]
    assert novena.flores == 9
    assert novena.es_premio is False
    assert novena.cliente.proxima_es_premio is True

    decima = resultados[9]
    assert decima.es_premio is True
    assert decima.numero_tarjeta == 1
    assert decima.flores == 9
    assert decima.cliente.citas_en_curso == 0
    assert decima.cliente.tarjetas_completadas == 1

    undecima = resultados[10]
    assert undecima.es_premio is False
    assert undecima.flores == 1
    assert undecima.cliente.citas_en_curso == 1


def test_bajar_n_cierra_la_tarjeta_en_la_siguiente_cita(
    sesiones: Any, zona: ZoneInfo, utc: Utc
) -> None:
    con_10 = ServicioTarjetas(sesiones, citas_por_tarjeta=10, zona=zona)
    carmen = con_10.crear_cliente("Carmen", 0, utc("2026-10-31 16:00"))
    registrar_dias(con_10, carmen.id, range(1, 10), utc)  # 9 en curso

    con_8 = ServicioTarjetas(sesiones, citas_por_tarjeta=8, zona=zona)
    resultado = con_8.registrar_cita(carmen.id, utc("2026-11-10 16:00"))
    assert resultado.es_premio is True
    assert resultado.numero_tarjeta == 1


def test_cambiar_n_no_altera_tarjetas_completadas(sesiones: Any, zona: ZoneInfo, utc: Utc) -> None:
    con_10 = ServicioTarjetas(sesiones, citas_por_tarjeta=10, zona=zona)
    carmen = con_10.crear_cliente("Carmen", 0, utc("2026-10-31 16:00"))
    registrar_dias(con_10, carmen.id, range(1, 11), utc)

    con_5 = ServicioTarjetas(sesiones, citas_por_tarjeta=5, zona=zona)
    resumen = con_5.resumen(carmen.id)
    assert resumen.tarjetas_completadas == 1
    assert resumen.citas_en_curso == 0
