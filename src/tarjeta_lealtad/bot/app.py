"""Arranque del bot: configuración, verificaciones, base de datos y long polling (principio VI)."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from pydantic import ValidationError

from tarjeta_lealtad import db, diseno, render
from tarjeta_lealtad.bot import handlers, textos
from tarjeta_lealtad.bot.acciones import AccionesPendientes
from tarjeta_lealtad.bot.seguridad import SoloDueno
from tarjeta_lealtad.config import Ajustes, verificar_diseno
from tarjeta_lealtad.servicio import ServicioTarjetas

log = logging.getLogger("tarjeta_lealtad")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    try:
        ajustes = Ajustes()
    except ValidationError as error:
        log.error("Configuración inválida (revisa el .env):\n%s", error)
        sys.exit(1)
    logging.getLogger().setLevel(ajustes.log_level.upper())
    log.info("Configuración cargada")

    try:
        verificar_diseno(ajustes.citas_por_tarjeta)
        render.ajustar_nombre("Prueba")  # comprueba que plantilla, flor y fuente cargan
    except (ValueError, OSError) as error:
        log.error("No se puede arrancar: %s", error)
        sys.exit(1)
    log.info(
        "Diseño verificado: %s casillas para %s citas por tarjeta",
        diseno.CASILLAS,
        ajustes.citas_por_tarjeta,
    )

    motor = db.crear_motor(ajustes.db_path)
    db.inicializar(motor)
    log.info("Base de datos lista en %s", ajustes.db_path)
    servicio = ServicioTarjetas(db.crear_sesiones(motor), ajustes.citas_por_tarjeta, ajustes.zona)
    asyncio.run(_ejecutar(ajustes, servicio))


def crear_dispatcher(servicio: ServicioTarjetas, owner_id: int) -> Dispatcher:
    """Dispatcher con el servicio inyectado, el filtro del dueño y los handlers.

    El router de `handlers` solo puede pertenecer a un Dispatcher: se llama una vez por proceso.
    """
    dp = Dispatcher(servicio=servicio, acciones=AccionesPendientes())
    dp.update.outer_middleware(SoloDueno(owner_id))
    dp.include_router(handlers.router)
    return dp


async def _ejecutar(ajustes: Ajustes, servicio: ServicioTarjetas) -> None:
    bot = Bot(ajustes.bot_token.get_secret_value())
    dp = crear_dispatcher(servicio, ajustes.owner_id)
    await bot.set_my_commands(
        [
            BotCommand(command=comando, description=descripcion)
            for comando, (_, descripcion, _) in textos.COMANDOS.items()
        ]
    )
    log.info("Comandos registrados; polling iniciado")
    # En serie: con un solo usuario no se pierde nada y un doble toque no puede competir consigo
    # mismo. No se descartan los mensajes pendientes: se procesan al arrancar (research §3).
    await dp.start_polling(bot, handle_as_tasks=False)
