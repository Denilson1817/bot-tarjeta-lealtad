"""Arranque: resguardo del polling (FR-013) y selección de modo por configuración (FR-001)."""

import inspect
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from telegram.ext import Application

from tarjeta_lealtad.bot import app as modulo_app
from tarjeta_lealtad.bot.app import crear_aplicacion, verificar_sin_webhook

URL_PRODUCCION = "https://cuenta.alwaysdata.net/tarjeta/telegram"


async def test_con_webhook_activo_no_arranca_ni_lo_borra(
    servicio: Any, api_falsa: Callable[..., Any], caplog: pytest.LogCaptureFixture
) -> None:
    api = api_falsa(webhook_url=URL_PRODUCCION)
    aplicacion = crear_aplicacion(servicio, frozenset({1}), "42:PRUEBA", request=api)
    async with aplicacion:
        with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as salida:
            await verificar_sin_webhook(aplicacion)
    assert salida.value.code == 1
    assert "ya corre en el servidor" in caplog.text
    assert "deleteWebhook" not in api.metodos()


async def test_sin_webhook_activo_continua(servicio: Any, api_falsa: Callable[..., Any]) -> None:
    api = api_falsa()
    aplicacion = crear_aplicacion(servicio, frozenset({1}), "42:PRUEBA", request=api)
    async with aplicacion:
        await verificar_sin_webhook(aplicacion)
    assert "getWebhookInfo" in api.metodos()


async def test_al_iniciar_el_polling_verifica_antes_de_registrar_comandos(
    servicio: Any, api_falsa: Callable[..., Any]
) -> None:
    api = api_falsa(webhook_url=URL_PRODUCCION)
    aplicacion = crear_aplicacion(servicio, frozenset({1}), "42:PRUEBA", request=api)
    async with aplicacion:
        with pytest.raises(SystemExit):
            await modulo_app.al_iniciar_polling(aplicacion)
    assert "setMyCommands" not in api.metodos()


@pytest.fixture
def arranques(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """Entorno mínimo sin el .env real, y `run_polling`/`uvicorn.run` sustituidos por registros."""
    monkeypatch.chdir(tmp_path)  # así no se lee el .env del repositorio
    for clave, valor in {
        "BOT_TOKEN": "42:PRUEBA",
        "OWNER_ID": "1",
        "ZONA_HORARIA": "America/Mexico_City",
        "DB_PATH": str(tmp_path / "t.db"),
    }.items():
        monkeypatch.setenv(clave, valor)
    for clave in (
        "WEBHOOK_URL",
        "WEBHOOK_SECRET",
        "IP",
        "PORT",
        "CITAS_POR_TARJETA",
        "AUTORIZADOS",
    ):
        monkeypatch.delenv(clave, raising=False)
    registro: dict[str, Any] = {}

    def run_polling(self: Application, **kwargs: Any) -> None:  # type: ignore[type-arg]
        registro["polling"] = kwargs

    def run_uvicorn(app: Any, **kwargs: Any) -> None:
        registro["uvicorn"] = kwargs

    monkeypatch.setattr(Application, "run_polling", run_polling)
    monkeypatch.setattr(modulo_app.uvicorn, "run", run_uvicorn)
    return registro


def test_sin_webhook_url_arranca_en_polling(arranques: dict[str, Any]) -> None:
    modulo_app.main()
    assert arranques["polling"]["drop_pending_updates"] is False
    assert arranques["polling"]["allowed_updates"] == ["message", "callback_query"]
    assert "uvicorn" not in arranques


def test_con_webhook_url_arranca_el_servidor_web(
    arranques: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WEBHOOK_URL", URL_PRODUCCION)
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cr3t0-de_prueba-0123456789abcdef")
    monkeypatch.setenv("IP", "::")
    monkeypatch.setenv("PORT", "8123")
    modulo_app.main()
    assert (arranques["uvicorn"]["host"], arranques["uvicorn"]["port"]) == ("::", 8123)
    assert "polling" not in arranques


@pytest.mark.parametrize("webhook", [False, True])
def test_main_usa_las_personas_autorizadas(
    arranques: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    webhook: bool,
) -> None:
    monkeypatch.setenv("OWNER_ID", "42")
    monkeypatch.setenv("AUTORIZADOS", "7")
    if webhook:
        monkeypatch.setenv("WEBHOOK_URL", URL_PRODUCCION)
        monkeypatch.setenv("WEBHOOK_SECRET", "s3cr3t0-de_prueba-0123456789abcdef")
    original = modulo_app.crear_aplicacion
    firma = inspect.signature(original)
    recibidos: list[Any] = []

    def registrar(*args: Any, **kwargs: Any) -> Any:
        recibidos.append(firma.bind(*args, **kwargs).arguments["autorizados"])
        return original(*args, **kwargs)

    monkeypatch.setattr(modulo_app, "crear_aplicacion", registrar)
    # basicConfig(force=True) quitaría el handler de caplog.
    monkeypatch.setattr(modulo_app, "_configurar_logs", lambda nivel="INFO": None)
    with caplog.at_level(logging.INFO, logger="tarjeta_lealtad"):
        modulo_app.main()
    assert recibidos == [frozenset({42, 7})]
    assert "Personas autorizadas: 2" in caplog.messages  # cuántas, nunca los IDs
