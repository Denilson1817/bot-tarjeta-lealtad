"""Servidor web del modo webhook (contracts/webhook-http.md), con la aplicación real y sin red."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from starlette.applications import Starlette
from telegram import Update
from telegram.ext import Application

from tarjeta_lealtad.bot.app import crear_aplicacion
from tarjeta_lealtad.bot.web import RegistroDeUpdates, crear_app_web

SECRETO = "s3cr3t0-de_prueba-0123456789abcdef"
URL = "https://cuenta.alwaysdata.net/tarjeta/telegram"
DUENO = 5221


@pytest.fixture
def sitio(servicio: Any, api_falsa: Callable[..., Any]) -> tuple[Starlette, Any]:
    api = api_falsa()
    aplicacion = crear_aplicacion(
        servicio, frozenset({DUENO}), "42:PRUEBA", request=api, con_updater=False
    )
    return crear_app_web(aplicacion, URL, SECRETO), api


@asynccontextmanager
async def cliente_de(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """Arranca el *lifespan* (registro del webhook) y da un cliente HTTP sin red."""
    transporte = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transporte, base_url="http://sitio") as cliente,
    ):
        yield cliente


async def enviar(
    cliente: httpx.AsyncClient,
    datos: Any,
    ruta: str = "/tarjeta/telegram",
    secreto: str | None = SECRETO,
) -> httpx.Response:
    cabeceras = {"X-Telegram-Bot-Api-Secret-Token": secreto} if secreto is not None else {}
    return await cliente.post(ruta, json=datos, headers=cabeceras)


def test_registro_de_updates() -> None:
    registro = RegistroDeUpdates(capacidad=3)
    assert registro.registrar(5) is True
    assert registro.registrar(5) is False
    for update_id in (6, 7, 8):
        registro.registrar(update_id)
    assert registro.registrar(5) is True  # el más antiguo ya se olvidó


async def test_al_arrancar_registra_webhook_y_comandos(sitio: tuple[Starlette, Any]) -> None:
    app, api = sitio
    async with cliente_de(app):
        pass
    (params,) = api.enviados("setWebhook")
    assert params["url"] == URL
    assert params["secret_token"] == SECRETO
    assert params["max_connections"] == 1
    assert params["allowed_updates"] == ["message", "callback_query"]
    assert params["drop_pending_updates"] is False
    assert api.metodos().index("setWebhook") < api.metodos().index("setMyCommands")
    assert "deleteWebhook" not in api.metodos()  # al apagarse no se borra


@pytest.mark.parametrize("secreto", [None, "otro-secreto-que-no-es-el-bueno"])
async def test_sin_el_token_secreto_correcto_responde_403(
    sitio: tuple[Starlette, Any],
    update_de: Callable[..., Any],
    caplog: pytest.LogCaptureFixture,
    secreto: str | None,
) -> None:
    app, api = sitio
    async with cliente_de(app) as cliente:
        caplog.set_level(logging.WARNING)
        respuesta = await enviar(cliente, update_de(1, "/ayuda", de=DUENO), secreto=secreto)
    assert respuesta.status_code == 403
    assert api.enviados("sendMessage") == []
    assert "token secreto" in caplog.text
    if secreto:
        assert secreto not in caplog.text


async def test_cuerpo_invalido_responde_400(sitio: tuple[Starlette, Any]) -> None:
    app, api = sitio
    cabeceras = {"X-Telegram-Bot-Api-Secret-Token": SECRETO}
    async with cliente_de(app) as cliente:
        assert (
            await cliente.post("/x", content=b"no es json", headers=cabeceras)
        ).status_code == 400
        assert (await enviar(cliente, {"no": "es un update"})).status_code == 400
    assert api.enviados("sendMessage") == []


async def test_update_valido_del_dueno_se_procesa(
    sitio: tuple[Starlette, Any], update_de: Callable[..., Any]
) -> None:
    app, api = sitio
    async with cliente_de(app) as cliente:
        assert (await enviar(cliente, update_de(1, "/ayuda", de=DUENO))).status_code == 200
    (respuesta,) = api.enviados("sendMessage")
    assert respuesta["text"].startswith("Comandos:")


async def test_update_repetido_se_procesa_una_sola_vez(
    sitio: tuple[Starlette, Any], update_de: Callable[..., Any]
) -> None:
    app, api = sitio
    async with cliente_de(app) as cliente:
        assert (await enviar(cliente, update_de(7, "/ayuda", de=DUENO))).status_code == 200
        assert (await enviar(cliente, update_de(7, "/ayuda", de=DUENO))).status_code == 200
    assert len(api.enviados("sendMessage")) == 1


async def test_acepta_el_webhook_en_cualquier_ruta(
    sitio: tuple[Starlette, Any], update_de: Callable[..., Any]
) -> None:
    app, api = sitio
    async with cliente_de(app) as cliente:
        assert (
            await enviar(cliente, update_de(1, "/ayuda", de=DUENO), ruta="/telegram")
        ).status_code == 200
        assert (await enviar(cliente, update_de(2, "/ayuda", de=DUENO))).status_code == 200
    assert len(api.enviados("sendMessage")) == 2


async def test_get_responde_ok_en_cualquier_ruta_y_otros_metodos_405(
    sitio: tuple[Starlette, Any],
) -> None:
    app, _ = sitio
    async with cliente_de(app) as cliente:
        for ruta in ("/", "/tarjeta", "/tarjeta/telegram"):
            respuesta = await cliente.get(ruta)
            assert (respuesta.status_code, respuesta.text) == (200, "ok")
        assert (await cliente.put("/tarjeta/telegram")).status_code == 405


async def test_otra_cuenta_no_recibe_respuesta(
    sitio: tuple[Starlette, Any], update_de: Callable[..., Any]
) -> None:
    app, api = sitio
    async with cliente_de(app) as cliente:
        assert (await enviar(cliente, update_de(1, "/ayuda", de=777))).status_code == 200
    assert api.enviados("sendMessage") == []


async def test_peticiones_simultaneas_se_procesan_en_serie(
    sitio: tuple[Starlette, Any],
    update_de: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _ = sitio
    eventos: list[tuple[str, int]] = []

    async def lento(self: Application, update: Update) -> None:  # type: ignore[type-arg]
        eventos.append(("inicio", update.update_id))
        await asyncio.sleep(0.05)
        eventos.append(("fin", update.update_id))

    monkeypatch.setattr(Application, "process_update", lento)
    cabeceras = {"X-Telegram-Bot-Api-Secret-Token": SECRETO}
    async with cliente_de(app) as cliente:
        await asyncio.gather(
            *(
                cliente.post("/t", json=update_de(i, "/ayuda", de=DUENO), headers=cabeceras)
                for i in (1, 2)
            )
        )
    assert eventos in (
        [("inicio", 1), ("fin", 1), ("inicio", 2), ("fin", 2)],
        [("inicio", 2), ("fin", 2), ("inicio", 1), ("fin", 1)],
    )
