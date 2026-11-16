"""Ciclo de la tarjeta derivado de las citas vigentes (principio IV, research §6). Sin E/S."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

type Origen = Literal["bot", "previa"]


@dataclass(frozen=True)
class CitaEvento:
    """Una cita vigente (no anulada)."""

    id: int
    origen: Origen
    registrada_en: datetime | None
    es_premio: bool


@dataclass(frozen=True)
class EstadoTarjetas:
    citas_en_curso: int
    completadas: tuple[datetime | None, ...]  # fecha de cada cita de premio, en orden
    ultima_cita: datetime | None  # máxima registrada_en entre las citas del bot


def estado(citas: Sequence[CitaEvento]) -> EstadoTarjetas:
    """Cada cita de premio cierra una tarjeta; la tarjeta en curso son las citas posteriores."""
    en_curso = 0
    completadas: list[datetime | None] = []
    ultima: datetime | None = None
    for cita in sorted(citas, key=lambda c: c.id):
        if cita.es_premio:
            completadas.append(cita.registrada_en)
            en_curso = 0
        else:
            en_curso += 1
        if (
            cita.origen == "bot"
            and cita.registrada_en is not None
            and (ultima is None or cita.registrada_en > ultima)
        ):
            ultima = cita.registrada_en
    return EstadoTarjetas(en_curso, tuple(completadas), ultima)


def siguiente_es_premio(citas_en_curso: int, citas_por_tarjeta: int) -> bool:
    return citas_en_curso >= citas_por_tarjeta - 1


def flores_a_dibujar(citas_en_curso: int, casillas: int) -> int:
    return min(citas_en_curso, casillas)


def faltan_para_premio(citas_en_curso: int, citas_por_tarjeta: int) -> int:
    """Citas que faltan para llegar a la de premio, contándola."""
    return max(citas_por_tarjeta - citas_en_curso, 1)
