"""Solo el dueño puede usar el bot (FR-001, principio V)."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

log = logging.getLogger(__name__)


class SoloDueno(BaseMiddleware):
    """*Outer middleware* de `dp.update`: descarta, sin responder, lo que no venga del dueño."""

    def __init__(self, owner_id: int) -> None:
        self._owner_id = owner_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        usuario = data.get("event_from_user")
        if usuario is None:
            return None
        if usuario.id != self._owner_id:
            log.warning(
                "Mensaje ignorado de una cuenta no autorizada: id=%s usuario=%s",
                usuario.id,
                usuario.username,
            )
            return None
        return await handler(event, data)
