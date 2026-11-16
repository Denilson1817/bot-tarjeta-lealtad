"""Acciones pendientes detrás de los botones (research §5).

Un botón solo lleva un token corto: los datos de un botón de Telegram admiten 64 bytes como
máximo. La acción se *toma* (pop) al pulsarlo, así que un segundo toque no tiene efecto (FR-011).
Se guarda en memoria: si el bot se reinicia, los botones antiguos solo caducan.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from aiogram.filters.callback_data import CallbackData

type Comando = Literal["cita", "alta", "deshacer", "tarjeta"]
type TipoAccion = Literal[
    "elegir", "crear_y_cita", "confirmar_mismo_dia", "crear_homonimo", "confirmar_deshacer"
]

MAXIMO_PENDIENTES = 500


@dataclass(frozen=True)
class Accion:
    tipo: TipoAccion
    comando: Comando  # comando que originó la acción; decide qué hacer al elegir un cliente
    cliente_ids: tuple[int, ...] = ()
    nombre: str = ""
    fecha_comando: datetime | None = None
    citas_previas: int = 0
    cita_id: int | None = None  # la cita mostrada al confirmar un deshacer


class AccionesPendientes:
    def __init__(self) -> None:
        self._pendientes: dict[str, Accion] = {}

    def registrar(self, accion: Accion) -> str:
        token = secrets.token_urlsafe(8)
        while token in self._pendientes:
            token = secrets.token_urlsafe(8)
        if len(self._pendientes) >= MAXIMO_PENDIENTES:  # descarta la más antigua
            del self._pendientes[next(iter(self._pendientes))]
        self._pendientes[token] = accion
        return token

    def tomar(self, token: str) -> Accion | None:
        return self._pendientes.pop(token, None)


class AccionCB(CallbackData, prefix="a"):
    token: str
    opcion: str  # un ID de cliente, "nuevo", "si" o "no"
