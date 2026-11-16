"""Fixtures del dominio (las de Telegram están en tests/bot/conftest.py).

Los módulos del paquete se importan dentro de cada fixture: así, mientras un módulo todavía no
existe (TDD), solo fallan las pruebas que lo usan.
"""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest


@pytest.fixture
def zona() -> ZoneInfo:
    return ZoneInfo("America/Mexico_City")


@pytest.fixture
def utc() -> Callable[[str], datetime]:
    def crear(texto: str) -> datetime:
        return datetime.strptime(texto, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)

    return crear


@pytest.fixture
def sesiones(tmp_path: Path) -> Iterator[Any]:
    from tarjeta_lealtad import db

    motor = db.crear_motor(tmp_path / "t.db")
    db.inicializar(motor)
    yield db.crear_sesiones(motor)
    motor.dispose()


@pytest.fixture
def servicio(sesiones: Any, zona: ZoneInfo) -> Any:
    from tarjeta_lealtad.servicio import ServicioTarjetas

    return ServicioTarjetas(sesiones, citas_por_tarjeta=10, zona=zona)
