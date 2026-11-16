"""Fixtures compartidas.

Los módulos del paquete se importan dentro de cada fixture: así, mientras un módulo todavía no
existe (TDD), solo fallan las pruebas que lo usan.
"""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

FECHA_POR_DEFECTO = datetime(2026, 11, 16, 16, 32, tzinfo=UTC)  # 10:32 en Mexico City


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


@pytest.fixture
def acciones() -> Any:
    from tarjeta_lealtad.bot.acciones import AccionesPendientes

    return AccionesPendientes()


@pytest.fixture
def mensaje_falso() -> Callable[..., MagicMock]:
    def crear(texto: str = "", fecha: datetime = FECHA_POR_DEFECTO, user_id: int = 1) -> MagicMock:
        from aiogram.types import Message

        mensaje = MagicMock(spec=Message)
        mensaje.text = texto
        mensaje.date = fecha
        mensaje.from_user = MagicMock(id=user_id, username="dueno")
        mensaje.chat = MagicMock(id=user_id)
        mensaje.answer = AsyncMock()
        mensaje.answer_photo = AsyncMock()
        mensaje.edit_text = AsyncMock()
        mensaje.edit_reply_markup = AsyncMock()
        return mensaje

    return crear


@pytest.fixture
def callback_falso() -> Callable[[str, MagicMock], MagicMock]:
    def crear(data: str, mensaje: MagicMock) -> MagicMock:
        from aiogram.types import CallbackQuery

        callback = MagicMock(spec=CallbackQuery)
        callback.data = data
        callback.message = mensaje
        callback.answer = AsyncMock()
        return callback

    return crear


@pytest.fixture
def botones() -> Callable[[AsyncMock], list[tuple[str, str]]]:
    """(texto, callback_data) de cada botón del teclado enviado en la última llamada."""

    def extraer(llamada: AsyncMock) -> list[tuple[str, str]]:
        teclado = llamada.call_args.kwargs.get("reply_markup")
        if teclado is None:
            return []
        return [
            (boton.text, boton.callback_data or "")
            for fila in teclado.inline_keyboard
            for boton in fila
        ]

    return extraer
