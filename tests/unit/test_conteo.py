from datetime import UTC, datetime, timedelta

from tarjeta_lealtad.conteo import (
    CitaEvento,
    estado,
    faltan_para_premio,
    flores_a_dibujar,
    siguiente_es_premio,
)

INICIO = datetime(2026, 11, 1, 16, 0, tzinfo=UTC)


def citas_bot(cantidad: int, premios: tuple[int, ...] = (), desde: int = 1) -> list[CitaEvento]:
    """`cantidad` citas del bot, un día por cita; `premios` son las posiciones (1..n) de premio."""
    return [
        CitaEvento(
            id=desde + i,
            origen="bot",
            registrada_en=INICIO + timedelta(days=i),
            es_premio=(i + 1) in premios,
        )
        for i in range(cantidad)
    ]


def test_sin_citas() -> None:
    resultado = estado([])
    assert resultado.citas_en_curso == 0
    assert resultado.completadas == ()
    assert resultado.ultima_cita is None


def test_seis_citas_vigentes() -> None:
    assert estado(citas_bot(6)).citas_en_curso == 6


def test_premio_cierra_la_tarjeta() -> None:
    citas = citas_bot(12, premios=(10,))
    resultado = estado(citas)
    assert resultado.citas_en_curso == 2
    assert resultado.completadas == (citas[9].registrada_en,)
    assert resultado.ultima_cita == citas[11].registrada_en


def test_orden_por_id_aunque_lleguen_desordenadas() -> None:
    citas = citas_bot(12, premios=(10,))
    assert estado(list(reversed(citas))).citas_en_curso == 2


def test_previas_no_cuentan_para_ultima_cita() -> None:
    previas = [
        CitaEvento(id=i, origen="previa", registrada_en=None, es_premio=False) for i in (1, 2)
    ]
    resultado = estado(previas)
    assert resultado.citas_en_curso == 2
    assert resultado.ultima_cita is None
    con_bot = estado([*previas, *citas_bot(1, desde=3)])
    assert con_bot.citas_en_curso == 3
    assert con_bot.ultima_cita == INICIO


def test_siguiente_es_premio() -> None:
    assert not siguiente_es_premio(8, 10)
    assert siguiente_es_premio(9, 10)
    assert siguiente_es_premio(12, 10)


def test_flores_a_dibujar() -> None:
    assert flores_a_dibujar(0, 9) == 0
    assert flores_a_dibujar(6, 9) == 6
    assert flores_a_dibujar(12, 9) == 9


def test_faltan_para_premio() -> None:
    assert faltan_para_premio(6, 10) == 4
    assert faltan_para_premio(9, 10) == 1
    assert faltan_para_premio(12, 10) == 1
