"""Fakes de python-telegram-bot para las pruebas de la capa de Telegram.

- `mensaje_falso`: un `Message` simulado con `reply_text`, `reply_photo` y `edit_text`.
- `tg`: ejecuta comandos y toques de botón como lo haría python-telegram-bot.
- `api_falsa`: simula la API de Telegram al nivel HTTP (`BaseRequest`), para usar el bot y la
  aplicación reales sin red (mismo patrón que el bot de finanzas).
- `update_de`: updates en JSON, en privado o en un grupo (IDs de chat negativos).
"""

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from itertools import count
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Message
from telegram.request import BaseRequest, RequestData

FECHA_POR_DEFECTO = datetime(2026, 11, 16, 16, 32, tzinfo=UTC)  # 10:32 en Mexico City
_update_ids = count(1)


@pytest.fixture
def acciones() -> Any:
    from tarjeta_lealtad.bot.acciones import AccionesPendientes

    return AccionesPendientes()


@pytest.fixture
def mensaje_falso() -> Callable[..., MagicMock]:
    def crear(texto: str = "", fecha: datetime = FECHA_POR_DEFECTO, user_id: int = 1) -> MagicMock:
        mensaje = MagicMock(spec=Message)
        mensaje.text = texto
        mensaje.date = fecha
        mensaje.chat_id = user_id
        mensaje.from_user = MagicMock(id=user_id, username="dueno")
        mensaje.reply_text = AsyncMock()
        mensaje.reply_photo = AsyncMock()
        mensaje.edit_text = AsyncMock()
        return mensaje

    return crear


class Telegram:
    """Invoca los handlers con `update` y `context` simulados, como python-telegram-bot."""

    def __init__(self, servicio: Any, acciones: Any) -> None:
        self.servicio = servicio
        self.acciones = acciones

    def contexto(self, args: str | None = None) -> MagicMock:
        contexto = MagicMock()
        contexto.args = args.split() if args else []
        contexto.bot_data = {"servicio": self.servicio, "acciones": self.acciones}
        contexto.error = None
        return contexto

    @staticmethod
    def update(mensaje: MagicMock) -> MagicMock:
        update = MagicMock()
        update.update_id = next(_update_ids)
        update.message = mensaje
        update.effective_message = mensaje
        update.effective_user = mensaje.from_user
        update.callback_query = None
        return update

    async def comando(
        self,
        handler: Callable[[Any, Any], Awaitable[None]],
        mensaje: MagicMock,
        args: str | None = None,
    ) -> None:
        await handler(self.update(mensaje), self.contexto(args))

    async def pulsar(self, prompt: MagicMock, data: str, de: int | None = None) -> MagicMock:
        """Toca un botón del mensaje `prompt`; devuelve la consulta (para revisar `answer`).

        Con `de`, el toque lo hace esa cuenta y no la que envió el mensaje original.
        """
        from tarjeta_lealtad.bot import handlers

        consulta = MagicMock()
        consulta.data = data
        consulta.message = prompt
        consulta.answer = AsyncMock()
        update = self.update(prompt)
        update.message = None
        update.callback_query = consulta
        if de is not None:
            update.effective_user = MagicMock(id=de, username=f"u{de}")
        await handlers.al_pulsar(update, self.contexto())
        return consulta

    @staticmethod
    def botones(llamada: AsyncMock) -> list[tuple[str, str]]:
        """(texto, callback_data) de cada botón del teclado enviado en la última llamada."""
        teclado = llamada.call_args.kwargs.get("reply_markup")
        if teclado is None:
            return []
        return [
            (boton.text, str(boton.callback_data))
            for fila in teclado.inline_keyboard
            for boton in fila
        ]

    def boton(self, llamada: AsyncMock, prefijo: str) -> str:
        return next(data for texto, data in self.botones(llamada) if texto.startswith(prefijo))


@pytest.fixture
def tg(servicio: Any, acciones: Any) -> Telegram:
    return Telegram(servicio, acciones)


class FakeTelegramAPI(BaseRequest):
    """La API de Telegram al nivel HTTP: el bot real de python-telegram-bot habla con esto."""

    def __init__(self, webhook_url: str = "") -> None:
        self.webhook_url = webhook_url
        self.llamadas: list[tuple[str, dict[str, Any]]] = []
        self._ids = count(100)

    @property
    def read_timeout(self) -> float:
        return 5.0

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def _mensaje(self, params: dict[str, Any], **extra: Any) -> dict[str, Any]:
        chat_id = int(params.get("chat_id", 1))
        return {
            "message_id": next(self._ids),
            "date": int(FECHA_POR_DEFECTO.timestamp()),
            "chat": {"id": chat_id, "type": "private" if chat_id > 0 else "group"},
            **extra,
        }

    async def do_request(
        self,
        url: str,
        method: str,
        request_data: RequestData | None = None,
        **_tiempos: Any,
    ) -> tuple[int, bytes]:
        metodo = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        self.llamadas.append((metodo, dict(params)))
        resultado: Any = True
        if metodo == "getMe":
            resultado = {"id": 42, "is_bot": True, "first_name": "Bot", "username": "tarjeta_bot"}
        elif metodo in ("sendMessage", "editMessageText"):
            resultado = self._mensaje(params, text=params.get("text", ""))
        elif metodo == "sendPhoto":
            foto = {"file_id": "f", "file_unique_id": "u", "width": 1050, "height": 600}
            resultado = self._mensaje(params, photo=[foto], caption=params.get("caption"))
        elif metodo == "getWebhookInfo":
            resultado = {
                "url": self.webhook_url,
                "has_custom_certificate": False,
                "pending_update_count": 0,
            }
        return 200, json.dumps({"ok": True, "result": resultado}).encode()

    def metodos(self) -> list[str]:
        return [metodo for metodo, _ in self.llamadas]

    def enviados(self, metodo: str) -> list[dict[str, Any]]:
        return [params for m, params in self.llamadas if m == metodo]


@pytest.fixture
def api_falsa() -> Callable[..., FakeTelegramAPI]:
    return FakeTelegramAPI


def update_json(
    update_id: int,
    texto: str | None = None,
    *,
    de: int = 1,
    data: str | None = None,
    chat: int | None = None,
    aviso: bool = False,
) -> dict[str, Any]:
    """Update de Telegram en JSON: un mensaje de texto o, con `data`, un toque de botón.

    Sin `chat`, el chat es el privado con `de`; con `chat` (negativo), es un grupo. Con `aviso`,
    el mensaje es un aviso del grupo (miembro nuevo) y no lleva texto.
    """
    usuario = {"id": de, "is_bot": False, "first_name": "Persona", "username": f"u{de}"}
    datos_chat = (
        {"id": de, "type": "private"}
        if chat is None
        else {"id": chat, "type": "group", "title": "Grupo"}
    )
    mensaje: dict[str, Any] = {
        "message_id": update_id,
        "date": int(FECHA_POR_DEFECTO.timestamp()),
        "chat": datos_chat,
        "from": usuario,
    }
    if aviso:
        mensaje["new_chat_members"] = [usuario]
    else:
        mensaje["text"] = texto or ""
    if texto and texto.startswith("/"):
        comando = texto.split()[0]
        mensaje["entities"] = [{"type": "bot_command", "offset": 0, "length": len(comando)}]
    if data is None:
        return {"update_id": update_id, "message": mensaje}
    del mensaje["from"]
    mensaje["from"] = {"id": 42, "is_bot": True, "first_name": "Bot"}
    return {
        "update_id": update_id,
        "callback_query": {
            "id": str(update_id),
            "from": usuario,
            "chat_instance": "chat",
            "data": data,
            "message": mensaje,
        },
    }


@pytest.fixture
def update_de() -> Callable[..., dict[str, Any]]:
    return update_json
