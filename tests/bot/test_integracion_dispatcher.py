"""Cableado real de aiogram (sin red): middleware, filtros, inyección de dependencias y router.

Las demás pruebas de handlers los llaman directamente; estas alimentan *updates* al Dispatcher
con una sesión falsa de Telegram que registra lo que el bot habría enviado.
"""

from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageText,
    SendMessage,
    SendPhoto,
    TelegramMethod,
)
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from tarjeta_lealtad.bot.acciones import AccionesPendientes
from tarjeta_lealtad.bot.app import crear_dispatcher
from tarjeta_lealtad.servicio import Encontrado

DUENO = 5221
INTRUSO = 777
AHORA = datetime(2026, 11, 16, 16, 32, tzinfo=UTC)


class SesionFalsa(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.enviados: list[TelegramMethod[Any]] = []

    async def make_request(
        self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None
    ) -> Any:
        self.enviados.append(method)
        if isinstance(method, SendMessage | SendPhoto | EditMessageText):
            return Message(
                message_id=len(self.enviados),
                date=AHORA,
                chat=Chat(id=DUENO, type="private"),
                text=getattr(method, "text", None),
            )
        return True

    async def stream_content(self, *args: Any, **kwargs: Any) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError
        yield b""

    async def close(self) -> None:
        pass


@pytest.fixture(scope="module")
def dp() -> Dispatcher:
    # El router de handlers solo puede pertenecer a un Dispatcher: uno por módulo de pruebas.
    return crear_dispatcher(servicio=None, owner_id=DUENO)  # type: ignore[arg-type]


@pytest.fixture
def entorno(dp: Dispatcher, servicio: Any) -> Iterator[tuple[Bot, SesionFalsa]]:
    dp["servicio"] = servicio
    dp["acciones"] = AccionesPendientes()
    sesion = SesionFalsa()
    yield Bot("42:PRUEBA", session=sesion), sesion


def mensaje(texto: str, de: int = DUENO, update_id: int = 1) -> Update:
    return Update(
        update_id=update_id,
        message=Message(
            message_id=update_id,
            date=AHORA,
            chat=Chat(id=de, type="private"),
            from_user=User(id=de, is_bot=False, first_name="Persona"),
            text=texto,
        ),
    )


def toque(data: str, update_id: int) -> Update:
    return Update(
        update_id=update_id,
        callback_query=CallbackQuery(
            id=str(update_id),
            from_user=User(id=DUENO, is_bot=False, first_name="Dueño"),
            chat_instance="chat",
            data=data,
            message=Message(
                message_id=99, date=AHORA, chat=Chat(id=DUENO, type="private"), text="¿…?"
            ),
        ),
    )


def botones(metodo: TelegramMethod[Any]) -> list[tuple[str, str]]:
    teclado = metodo.reply_markup  # type: ignore[attr-defined]
    return [(b.text, b.callback_data) for fila in teclado.inline_keyboard for b in fila]


async def test_el_intruso_no_recibe_nada(dp: Dispatcher, entorno: tuple[Bot, SesionFalsa]) -> None:
    bot, sesion = entorno
    await dp.feed_update(bot, mensaje("/ayuda", de=INTRUSO))
    assert sesion.enviados == []


async def test_ayuda_y_texto_libre(dp: Dispatcher, entorno: tuple[Bot, SesionFalsa]) -> None:
    bot, sesion = entorno
    await dp.feed_update(bot, mensaje("/ayuda"))
    await dp.feed_update(bot, mensaje("hola", update_id=2))
    textos = [m.text for m in sesion.enviados if isinstance(m, SendMessage)]
    assert textos[0].startswith("Comandos:")
    assert textos[1] == "Usa /ayuda para ver los comandos."


async def test_flujo_completo_de_cita_con_botones(
    dp: Dispatcher, entorno: tuple[Bot, SesionFalsa], servicio: Any
) -> None:
    bot, sesion = entorno
    await dp.feed_update(bot, mensaje("/cita Lucía"))
    pregunta = sesion.enviados[-1]
    assert isinstance(pregunta, SendMessage)
    crear = dict(botones(pregunta))["Crear"]

    await dp.feed_update(bot, toque(crear, update_id=2))
    tipos = [type(m) for m in sesion.enviados[1:]]
    assert tipos == [AnswerCallbackQuery, EditMessageText, SendPhoto]
    foto = sesion.enviados[-1]
    assert isinstance(foto, SendPhoto)
    assert foto.caption is not None and foto.caption.startswith("🌸 Lucía (#1): 1 de 9 flores.")

    lucia = servicio.buscar("lucia")
    assert isinstance(lucia, Encontrado)
    assert lucia.cliente.ultima_cita == AHORA

    await dp.feed_update(bot, toque(crear, update_id=3))  # segundo toque
    assert isinstance(sesion.enviados[-1], SendMessage)
    assert "ya se aplicó o caducó" in (sesion.enviados[-1].text or "")
    assert servicio.resumen(lucia.cliente.id).citas_en_curso == 1


async def test_comandos_con_argumentos_por_inyeccion(
    dp: Dispatcher, entorno: tuple[Bot, SesionFalsa], servicio: Any
) -> None:
    bot, sesion = entorno
    await dp.feed_update(bot, mensaje("/alta Rosa 6"))
    await dp.feed_update(bot, mensaje("/tarjeta #1", update_id=2))
    await dp.feed_update(bot, mensaje("/clientes", update_id=3))
    await dp.feed_update(bot, mensaje("/deshacer rosa", update_id=4))
    fotos = [m for m in sesion.enviados if isinstance(m, SendPhoto)]
    assert [f.caption for f in fotos][1] == "🌸 Rosa (#1): 6 de 9 flores."
    textos = [m.text for m in sesion.enviados if isinstance(m, SendMessage)]
    assert "Clientes (1):\n#1 Rosa: 6/9" in textos
    assert textos[-1] == "¿Anular la última cita de Rosa (#1)? cita previa al bot"
