"""Servidor web del modo webhook (contracts/webhook-http.md).

Starlette + uvicorn, con el mismo patrón que el bot de finanzas del dueño:
- valida el token secreto de Telegram;
- procesa cada update una sola vez y en serie, antes de responder;
- responde "ok" a cualquier GET.
Las rutas aceptan cualquier valor: alwaysdata puede recortar o no el prefijo de la dirección
(`path_trim`), y la seguridad depende del token, no de la ruta.
"""

import asyncio
import hmac
import logging
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from telegram import Update

from tarjeta_lealtad.bot.handlers import TIPOS_DE_UPDATE, Aplicacion, registrar_comandos

log = logging.getLogger(__name__)

CABECERA_SECRETO = "X-Telegram-Bot-Api-Secret-Token"


class RegistroDeUpdates:
    """IDs de los últimos updates procesados, para no repetir un reenvío de Telegram (FR-009)."""

    def __init__(self, capacidad: int = 1000) -> None:
        self._capacidad = capacidad
        self._orden: deque[int] = deque()
        self._vistos: set[int] = set()

    def registrar(self, update_id: int) -> bool:
        """True si el update es nuevo; False si ya se había procesado."""
        if update_id in self._vistos:
            return False
        self._orden.append(update_id)
        self._vistos.add(update_id)
        if len(self._orden) > self._capacidad:
            self._vistos.discard(self._orden.popleft())
        return True


def crear_app_web(aplicacion: Aplicacion, webhook_url: str, webhook_secret: str) -> Starlette:
    registro = RegistroDeUpdates()
    candado = asyncio.Lock()
    secreto = webhook_secret.encode()

    @asynccontextmanager
    async def ciclo_de_vida(_app: Starlette) -> AsyncIterator[None]:
        async with aplicacion:  # initialize() al arrancar; shutdown() al apagar
            await aplicacion.bot.set_webhook(
                url=webhook_url,
                secret_token=webhook_secret,
                max_connections=1,  # Telegram envía un update a la vez (FR-010)
                allowed_updates=TIPOS_DE_UPDATE,
                drop_pending_updates=False,  # los pendientes se procesan (FR-008)
            )
            await registrar_comandos(aplicacion)
            log.info("Webhook registrado")
            yield
        # Al apagarse no se borra el webhook: Telegram guarda los mensajes y despierta el sitio.

    async def recibir(request: Request) -> Response:
        recibido = request.headers.get(CABECERA_SECRETO, "").encode()
        if not hmac.compare_digest(recibido, secreto):
            log.warning(
                "Petición rechazada: token secreto ausente o incorrecto (ruta %s)",
                request.url.path,
            )
            return Response(status_code=403)
        try:
            update = Update.de_json(await request.json(), aplicacion.bot)
        except Exception:
            log.warning("Petición rechazada: el cuerpo no es un update de Telegram")
            return Response(status_code=400)
        if not registro.registrar(update.update_id):
            log.info("Update repetido, no se procesa: %s", update.update_id)
            return Response(status_code=200)
        async with candado:  # uno a la vez, en orden de llegada (FR-010)
            await aplicacion.process_update(update)
        return Response(status_code=200)

    async def salud(_request: Request) -> Response:
        return PlainTextResponse("ok")

    return Starlette(
        routes=[
            Route("/{ruta:path}", recibir, methods=["POST"]),
            Route("/{ruta:path}", salud, methods=["GET"]),
        ],
        lifespan=ciclo_de_vida,
    )
