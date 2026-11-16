"""Aplicación real de python-telegram-bot, sin red: filtro del dueño, handlers e inyección.

Las pruebas de handlers los llaman directamente; estas pasan updates en JSON por
`Application.process_update`, como llegarían de Telegram, y revisan qué habría enviado el bot.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from telegram import Update
from telegram.ext import Application

from tarjeta_lealtad.bot.app import crear_aplicacion
from tarjeta_lealtad.servicio import Encontrado

DUENO = 5221
INTRUSO = 777


def aplicacion_con(servicio: Any, api: Any) -> Application:  # type: ignore[type-arg]
    return crear_aplicacion(
        servicio, owner_id=DUENO, token="42:PRUEBA", request=api, con_updater=False
    )


async def procesar(aplicacion: Application, *updates: dict[str, Any]) -> None:  # type: ignore[type-arg]
    for datos in updates:
        await aplicacion.process_update(Update.de_json(datos, aplicacion.bot))


def botones(params: dict[str, Any]) -> dict[str, str]:
    teclado = params["reply_markup"]
    if isinstance(teclado, str):
        teclado = json.loads(teclado)
    return {b["text"]: b["callback_data"] for fila in teclado["inline_keyboard"] for b in fila}


async def test_el_intruso_no_recibe_nada(
    servicio: Any, api_falsa: Callable[..., Any], update_de: Callable[..., Any]
) -> None:
    api = api_falsa()
    aplicacion = aplicacion_con(servicio, api)
    async with aplicacion:
        await procesar(aplicacion, update_de(1, "/ayuda", de=INTRUSO))
    assert [m for m in api.metodos() if m.startswith("send")] == []


async def test_ayuda_y_texto_libre(
    servicio: Any, api_falsa: Callable[..., Any], update_de: Callable[..., Any]
) -> None:
    api = api_falsa()
    aplicacion = aplicacion_con(servicio, api)
    async with aplicacion:
        await procesar(aplicacion, update_de(1, "/ayuda", de=DUENO), update_de(2, "hola", de=DUENO))
    textos = [p["text"] for p in api.enviados("sendMessage")]
    assert textos[0].startswith("Comandos:")
    assert textos[1] == "Usa /ayuda para ver los comandos."


async def test_flujo_de_cita_con_botones(
    servicio: Any, api_falsa: Callable[..., Any], update_de: Callable[..., Any]
) -> None:
    api = api_falsa()
    aplicacion = aplicacion_con(servicio, api)
    async with aplicacion:
        await procesar(aplicacion, update_de(1, "/cita Lucía", de=DUENO))
        crear = botones(api.enviados("sendMessage")[-1])["Crear"]

        await procesar(aplicacion, update_de(2, data=crear, de=DUENO))
        metodos = api.metodos()
        assert metodos[-3:] == ["answerCallbackQuery", "editMessageText", "sendPhoto"]
        (foto,) = api.enviados("sendPhoto")
        assert foto["caption"].startswith("🌸 Lucía (#1): 1 de 9 flores.")

        await procesar(aplicacion, update_de(3, data=crear, de=DUENO))  # segundo toque
        assert "ya se aplicó o caducó" in api.enviados("sendMessage")[-1]["text"]

    lucia = servicio.buscar("lucia")
    assert isinstance(lucia, Encontrado)
    assert lucia.cliente.citas_en_curso == 1
    assert lucia.cliente.ultima_cita == datetime(2026, 11, 16, 16, 32, tzinfo=UTC)


async def test_los_comandos_reciben_sus_argumentos(
    servicio: Any, api_falsa: Callable[..., Any], update_de: Callable[..., Any]
) -> None:
    api = api_falsa()
    aplicacion = aplicacion_con(servicio, api)
    async with aplicacion:
        await procesar(
            aplicacion,
            update_de(1, "/alta Rosa 6", de=DUENO),
            update_de(2, "/tarjeta #1", de=DUENO),
            update_de(3, "/clientes", de=DUENO),
            update_de(4, "/deshacer rosa", de=DUENO),
        )
    pies = [p["caption"] for p in api.enviados("sendPhoto")]
    assert pies[0].startswith("✅ Cliente nuevo: Rosa (#1) con 6 citas previas.")
    assert pies[1] == "🌸 Rosa (#1): 6 de 9 flores."
    textos = [p["text"] for p in api.enviados("sendMessage")]
    assert "Clientes (1):\n#1 Rosa: 6/9" in textos
    assert textos[-1] == "¿Anular la última cita de Rosa (#1)? cita previa al bot"
