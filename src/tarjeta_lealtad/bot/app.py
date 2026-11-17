"""Arranque del bot: configuración, verificaciones, base de datos y modo (principio VI)."""

import logging
import sys
from collections.abc import Callable, Coroutine
from typing import Any

import uvicorn
from pydantic import ValidationError
from telegram import Update
from telegram.ext import ApplicationBuilder, TypeHandler
from telegram.request import BaseRequest

from tarjeta_lealtad import db, diseno, render
from tarjeta_lealtad.bot import handlers
from tarjeta_lealtad.bot.acciones import AccionesPendientes
from tarjeta_lealtad.bot.handlers import TIPOS_DE_UPDATE, Aplicacion, registrar_comandos
from tarjeta_lealtad.bot.seguridad import crear_filtro
from tarjeta_lealtad.bot.web import crear_app_web
from tarjeta_lealtad.config import Ajustes, verificar_diseno
from tarjeta_lealtad.servicio import ServicioTarjetas

log = logging.getLogger("tarjeta_lealtad")

type AlIniciar = Callable[[Aplicacion], Coroutine[Any, Any, None]]


def crear_aplicacion(
    servicio: ServicioTarjetas,
    autorizados: frozenset[int],
    token: str,
    *,
    request: BaseRequest | None = None,
    con_updater: bool = True,
    al_iniciar: AlIniciar | None = None,
) -> Aplicacion:
    """Aplicación con el servicio inyectado, el filtro de personas autorizadas y los handlers.

    `con_updater=False` es para el modo webhook: los updates llegan por el servidor web.
    """
    constructor = ApplicationBuilder().token(token)
    if request is not None:
        constructor = constructor.request(request)
        if con_updater:
            constructor = constructor.get_updates_request(request)
    if not con_updater:
        constructor = constructor.updater(None)
    if al_iniciar is not None:
        constructor = constructor.post_init(al_iniciar)
    aplicacion = constructor.build()
    aplicacion.bot_data["servicio"] = servicio
    aplicacion.bot_data["acciones"] = AccionesPendientes()
    aplicacion.add_handler(TypeHandler(Update, crear_filtro(autorizados)), group=-1)
    handlers.registrar_handlers(aplicacion)
    return aplicacion


async def verificar_sin_webhook(aplicacion: Aplicacion) -> None:
    """Termina si el bot ya tiene un webhook activo (FR-013).

    Debe correr antes del polling: python-telegram-bot llama `delete_webhook` al empezar a
    hacer polling y le quitaría el webhook al bot de producción.
    """
    info = await aplicacion.bot.get_webhook_info()
    if info.url:
        log.error(
            "Este bot ya tiene un webhook activo (%s): ya corre en el servidor. No lo arranco "
            "aquí para no quitárselo. Usa el bot de pruebas en tu computadora.",
            info.url,
        )
        sys.exit(1)


async def al_iniciar_polling(aplicacion: Aplicacion) -> None:
    await verificar_sin_webhook(aplicacion)  # primero: antes de tocar nada en Telegram
    await registrar_comandos(aplicacion)


def _configurar_logs(nivel: str = "INFO") -> None:
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )
    # httpx registra cada petición con la URL completa, que incluye el token del bot.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _preparar() -> tuple[Ajustes, ServicioTarjetas]:
    """Configuración, diseño, assets y base de datos; termina con código 1 si algo falla."""
    _configurar_logs()
    try:
        ajustes = Ajustes()
    except ValidationError as error:
        log.error("Configuración inválida (revisa el .env):\n%s", error)
        sys.exit(1)
    _configurar_logs(ajustes.log_level.upper())
    log.info("Configuración cargada")
    log.info("Personas autorizadas: %s", len(ajustes.ids_autorizados))  # nunca los IDs
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
    return ajustes, servicio


def main() -> None:
    ajustes, servicio = _preparar()
    token = ajustes.bot_token.get_secret_value()
    if ajustes.webhook_url and ajustes.webhook_secret:  # modo webhook (validado en Ajustes)
        aplicacion = crear_aplicacion(servicio, ajustes.ids_autorizados, token, con_updater=False)
        app_web = crear_app_web(
            aplicacion, ajustes.webhook_url, ajustes.webhook_secret.get_secret_value()
        )
        log.info("Modo webhook en %s:%s", ajustes.ip, ajustes.port)
        # log_config=None: uvicorn usa la configuración de logs de este proceso.
        uvicorn.run(app_web, host=ajustes.ip, port=ajustes.port, access_log=False, log_config=None)
        return
    aplicacion = crear_aplicacion(
        servicio, ajustes.ids_autorizados, token, al_iniciar=al_iniciar_polling
    )
    log.info("Modo polling")
    # python-telegram-bot procesa los updates de uno en uno (concurrent_updates=False) y aquí no
    # se descartan los pendientes: se procesan al arrancar con su fecha original.
    aplicacion.run_polling(drop_pending_updates=False, allowed_updates=TIPOS_DE_UPDATE)
