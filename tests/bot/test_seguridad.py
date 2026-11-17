import logging
from unittest.mock import MagicMock

import pytest
from telegram.ext import ApplicationHandlerStop

from tarjeta_lealtad.bot.seguridad import crear_filtro_dueno

DUENO = 42


def update_de(usuario: MagicMock | None) -> MagicMock:
    update = MagicMock()
    update.effective_user = usuario
    return update


async def test_el_dueno_pasa() -> None:
    filtro = crear_filtro_dueno(DUENO)
    await filtro(update_de(MagicMock(id=DUENO, username="dueno")), MagicMock())


async def test_otra_cuenta_se_detiene_y_se_registra(caplog: pytest.LogCaptureFixture) -> None:
    filtro = crear_filtro_dueno(DUENO)
    with caplog.at_level(logging.WARNING), pytest.raises(ApplicationHandlerStop):
        await filtro(update_de(MagicMock(id=7, username="intruso")), MagicMock())
    assert "7" in caplog.text and "intruso" in caplog.text


async def test_update_sin_usuario_se_detiene() -> None:
    with pytest.raises(ApplicationHandlerStop):
        await crear_filtro_dueno(DUENO)(update_de(None), MagicMock())
