"""Solo las personas autorizadas pueden usar el bot (FR-004 de la 003, principio V)."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ApplicationHandlerStop, ContextTypes

log = logging.getLogger(__name__)

type Filtro = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]


def crear_filtro(autorizados: frozenset[int]) -> Filtro:
    """Callback para un `TypeHandler(Update, ...)` del grupo -1: corta lo que no sea autorizado.

    `ApplicationHandlerStop` impide que el update llegue a cualquier otro handler y no responde.
    """

    async def solo_autorizados(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
        usuario = update.effective_user
        if usuario is None:
            raise ApplicationHandlerStop
        if usuario.id not in autorizados:
            # Todo queda en el log, también la conversación de un grupo (principio V); el ID de
            # una persona se copia de una línea con chat=privado.
            chat = update.effective_chat
            log.warning(
                "Mensaje ignorado de una cuenta no autorizada: id=%s usuario=%s chat=%s",
                usuario.id,
                usuario.username,
                "privado" if chat is None or chat.type == ChatType.PRIVATE else "grupo",
            )
            raise ApplicationHandlerStop

    return solo_autorizados
