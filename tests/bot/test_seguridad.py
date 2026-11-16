import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from tarjeta_lealtad.bot.seguridad import SoloDueno

DUENO = 42


async def test_el_dueno_pasa() -> None:
    handler = AsyncMock(return_value="ok")
    datos = {"event_from_user": MagicMock(id=DUENO, username="dueno")}
    assert await SoloDueno(DUENO)(handler, MagicMock(), datos) == "ok"
    handler.assert_awaited_once()


async def test_otra_cuenta_se_ignora_y_se_registra(caplog: pytest.LogCaptureFixture) -> None:
    handler = AsyncMock()
    evento = MagicMock()
    datos = {"event_from_user": MagicMock(id=7, username="intruso")}
    with caplog.at_level(logging.WARNING):
        assert await SoloDueno(DUENO)(handler, evento, datos) is None
    handler.assert_not_awaited()
    evento.answer.assert_not_called()
    assert "7" in caplog.text and "intruso" in caplog.text


async def test_evento_sin_usuario_se_ignora() -> None:
    handler = AsyncMock()
    assert await SoloDueno(DUENO)(handler, MagicMock(), {}) is None
    handler.assert_not_awaited()
