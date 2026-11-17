"""Solo el dueño puede usar el bot (FR-001, principio V)."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

log = logging.getLogger(__name__)

type Filtro = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]


def crear_filtro_dueno(owner_id: int) -> Filtro:
    """Callback para un `TypeHandler(Update, ...)` del grupo -1: corta todo lo que no sea del dueño.

    `ApplicationHandlerStop` impide que el update llegue a cualquier otro handler y no responde.
    """

    async def solo_dueno(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
        usuario = update.effective_user
        if usuario is None:
            raise ApplicationHandlerStop
        if usuario.id != owner_id:
            log.warning(
                "Mensaje ignorado de una cuenta no autorizada: id=%s usuario=%s",
                usuario.id,
                usuario.username,
            )
            raise ApplicationHandlerStop

    return solo_dueno
