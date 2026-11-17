import logging
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from telegram import Update
from telegram.ext import ApplicationHandlerStop

from tarjeta_lealtad.bot.seguridad import crear_filtro

DUENO = 42
OTRA = 43
AUTORIZADOS = frozenset({DUENO, OTRA})


def update_de(usuario: MagicMock | None) -> MagicMock:
    update = MagicMock()
    update.effective_user = usuario
    return update


@pytest.mark.parametrize("cuenta", [DUENO, OTRA])
async def test_las_personas_autorizadas_pasan(cuenta: int) -> None:
    await crear_filtro(AUTORIZADOS)(update_de(MagicMock(id=cuenta, username="u")), MagicMock())


async def test_otra_cuenta_se_detiene_y_se_registra(caplog: pytest.LogCaptureFixture) -> None:
    filtro = crear_filtro(AUTORIZADOS)
    with caplog.at_level(logging.WARNING), pytest.raises(ApplicationHandlerStop):
        await filtro(update_de(MagicMock(id=7, username="intruso")), MagicMock())
    assert "id=7" in caplog.text and "intruso" in caplog.text


async def test_update_sin_usuario_se_detiene() -> None:
    with pytest.raises(ApplicationHandlerStop):
        await crear_filtro(AUTORIZADOS)(update_de(None), MagicMock())


# --- Tipo de chat en el registro (feature 003, US2) --------------------------------------------

GRUPO = -1001
CASOS = [
    pytest.param({"texto": "hola"}, "privado", id="privado"),
    pytest.param({"texto": "/cita Carmen", "chat": GRUPO}, "grupo", id="comando-en-grupo"),
    pytest.param({"texto": "hola", "chat": GRUPO}, "grupo", id="conversacion-en-grupo"),
    pytest.param({"aviso": True, "chat": GRUPO}, "grupo", id="aviso-del-grupo"),
    pytest.param({"data": "a:tok:si", "chat": GRUPO}, "grupo", id="boton-en-grupo"),
]


@pytest.mark.parametrize(("datos", "chat"), CASOS)
async def test_lo_que_envia_una_cuenta_no_autorizada_queda_con_el_tipo_de_chat(
    update_de: Callable[..., dict[str, Any]],
    caplog: pytest.LogCaptureFixture,
    datos: dict[str, Any],
    chat: str,
) -> None:
    update = Update.de_json(update_de(1, de=7, **datos), None)
    with caplog.at_level(logging.WARNING), pytest.raises(ApplicationHandlerStop):
        await crear_filtro(AUTORIZADOS)(update, MagicMock())
    assert f"id=7 usuario=u7 chat={chat}" in caplog.text


@pytest.mark.parametrize(("datos", "chat"), CASOS)
async def test_una_cuenta_autorizada_no_deja_avisos(
    update_de: Callable[..., dict[str, Any]],
    caplog: pytest.LogCaptureFixture,
    datos: dict[str, Any],
    chat: str,
) -> None:
    update = Update.de_json(update_de(1, de=OTRA, **datos), None)
    with caplog.at_level(logging.WARNING):
        await crear_filtro(AUTORIZADOS)(update, MagicMock())
    assert caplog.records == []
