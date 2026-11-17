"""Handlers de Telegram: capa delgada entre los comandos y el servicio (principio II).

Cada callback recibe `(update, context)`; `servicio` y `acciones` viven en `context.bot_data`.
"""

import logging
from datetime import UTC, datetime
from typing import Any, cast

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from tarjeta_lealtad.bot import textos
from tarjeta_lealtad.bot.acciones import (
    PREFIJO,
    Accion,
    AccionesPendientes,
    Comando,
    desempaquetar,
    empaquetar,
)
from tarjeta_lealtad.servicio import (
    CitasPreviasFueraDeRango,
    Encontrado,
    IdInexistente,
    NombreInvalido,
    Parecidos,
    ResumenCliente,
    ServicioTarjetas,
    SinCoincidencias,
    Varios,
)

log = logging.getLogger(__name__)

type Contexto = ContextTypes.DEFAULT_TYPE
type Aplicacion = Application[Any, Any, Any, Any, Any, Any]

COMANDOS = [
    BotCommand(comando, descripcion) for comando, (_, descripcion, _) in textos.COMANDOS.items()
]
TIPOS_DE_UPDATE = ["message", "callback_query"]


# --- utilidades --------------------------------------------------------------------------------


def _servicio(context: Contexto) -> ServicioTarjetas:
    return cast(ServicioTarjetas, context.bot_data["servicio"])


def _acciones(context: Contexto) -> AccionesPendientes:
    return cast(AccionesPendientes, context.bot_data["acciones"])


def _argumentos(context: Contexto) -> str:
    return " ".join(context.args or [])


def _teclado(token: str, opciones: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """Un botón por fila; cada uno lleva el token de la acción y su opción."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(texto, callback_data=empaquetar(token, opcion))]
            for texto, opcion in opciones
        ]
    )


def _si_no(token: str, si: str) -> InlineKeyboardMarkup:
    return _teclado(token, [(si, "si"), (textos.BOTON_CANCELAR, "no")])


async def _anotar(mensaje: Message, nota: str) -> None:
    """Quita los botones del mensaje y deja anotada la elección."""
    try:
        await mensaje.edit_text(f"{mensaje.text or ''}\n\n{nota}".strip())
    except BadRequest:
        log.debug("No se pudo editar el mensaje con botones", exc_info=True)


async def enviar_tarjeta(
    message: Message, servicio: ServicioTarjetas, cliente_id: int, flores: int | None, pie: str
) -> None:
    """Envía la tarjeta como foto. Si falla, los datos ya están guardados: se avisa y se anota."""
    try:
        png = servicio.tarjeta_png(cliente_id, flores)
        await message.reply_photo(photo=png, caption=pie)
    except Exception:
        log.exception("No se pudo enviar la tarjeta del cliente %s", cliente_id)
        await message.reply_text(textos.error_envio(cliente_id))


def _nombre_creable(servicio: ServicioTarjetas, texto: str) -> str | None:
    try:
        return servicio.validar_nombre(texto)
    except NombreInvalido:
        return None


# --- flujo común: resolver el cliente y continuar según el comando ------------------------------


async def _resolver(
    message: Message,
    texto: str,
    comando: Comando,
    fecha: datetime,
    servicio: ServicioTarjetas,
    acciones: AccionesPendientes,
) -> None:
    """Busca al cliente; si hay dudas, pregunta con botones (FR-005 – FR-007 de la 001)."""
    resultado = servicio.buscar(texto)
    match resultado:
        case Encontrado(cliente=cliente):
            await _continuar(message, comando, cliente.id, fecha, servicio, acciones)
        case Varios(opciones=opciones):
            await _ofrecer_opciones(
                message,
                textos.elegir_homonimo(texto),
                opciones,
                None,
                comando,
                fecha,
                servicio,
                acciones,
            )
        case Parecidos(opciones=opciones):
            nombre = _nombre_creable(servicio, texto) if comando == "cita" else None
            await _ofrecer_opciones(
                message,
                textos.elegir_parecido(texto),
                opciones,
                nombre,
                comando,
                fecha,
                servicio,
                acciones,
            )
        case IdInexistente(id=cliente_id):
            await message.reply_text(textos.id_inexistente(cliente_id))
        case SinCoincidencias():
            if comando != "cita":
                await message.reply_text(textos.no_encontrado(texto))
                return
            try:
                nombre = servicio.validar_nombre(texto)
            except NombreInvalido as error:
                await message.reply_text(textos.nombre_invalido(error.motivo))
                return
            token = acciones.registrar(
                Accion(tipo="crear_y_cita", comando="cita", nombre=nombre, fecha_comando=fecha)
            )
            await message.reply_text(
                textos.confirmar_crear(nombre), reply_markup=_si_no(token, textos.BOTON_CREAR)
            )


async def _ofrecer_opciones(
    message: Message,
    pregunta: str,
    opciones: tuple[ResumenCliente, ...],
    nombre_nuevo: str | None,
    comando: Comando,
    fecha: datetime,
    servicio: ServicioTarjetas,
    acciones: AccionesPendientes,
) -> None:
    """Un botón por cliente (y "Crear «X»" si se puede crear) para que el dueño elija."""
    botones = [(textos.etiqueta_cliente(o, servicio.zona), str(o.id)) for o in opciones]
    if nombre_nuevo is not None:
        botones.append((textos.boton_crear(nombre_nuevo), "nuevo"))
    botones.append((textos.BOTON_CANCELAR, "no"))
    token = acciones.registrar(
        Accion(
            tipo="elegir",
            comando=comando,
            cliente_ids=tuple(o.id for o in opciones),
            nombre=nombre_nuevo or "",
            fecha_comando=fecha,
        )
    )
    await message.reply_text(pregunta, reply_markup=_teclado(token, botones))


async def _continuar(
    message: Message,
    comando: Comando,
    cliente_id: int,
    fecha: datetime,
    servicio: ServicioTarjetas,
    acciones: AccionesPendientes,
) -> None:
    """Qué hacer con el cliente ya resuelto, según el comando que lo pidió."""
    if comando == "cita":
        hora = servicio.cita_del_dia(cliente_id, fecha)
        if hora is not None:  # probable duplicado (FR-010 de la 001)
            token = acciones.registrar(
                Accion(
                    tipo="confirmar_mismo_dia",
                    comando="cita",
                    cliente_ids=(cliente_id,),
                    fecha_comando=fecha,
                )
            )
            await message.reply_text(
                textos.confirmar_mismo_dia(servicio.resumen(cliente_id), hora, servicio.zona),
                reply_markup=_si_no(token, textos.BOTON_SI_REGISTRAR),
            )
            return
        await _registrar(message, cliente_id, fecha, servicio)
    elif comando == "tarjeta":  # solo consulta: no registra nada
        pie = textos.pie_tarjeta(servicio.resumen(cliente_id))
        await enviar_tarjeta(message, servicio, cliente_id, None, pie)
    elif comando == "deshacer":
        resumen = servicio.resumen(cliente_id)
        cita = servicio.ultima_cita_vigente(cliente_id)
        if cita is None:
            await message.reply_text(textos.nada_que_deshacer(resumen))
            return
        token = acciones.registrar(
            Accion(
                tipo="confirmar_deshacer",
                comando="deshacer",
                cliente_ids=(cliente_id,),
                cita_id=cita.id,
                fecha_comando=fecha,
            )
        )
        await message.reply_text(
            textos.confirmar_deshacer(cita, resumen, servicio.zona),
            reply_markup=_si_no(token, textos.BOTON_SI_DESHACER),
        )


async def _registrar(
    message: Message, cliente_id: int, fecha: datetime, servicio: ServicioTarjetas
) -> None:
    resultado = servicio.registrar_cita(cliente_id, fecha)
    log.info("Cita registrada: cliente=%s premio=%s", cliente_id, resultado.es_premio)
    pie = textos.pie_cita(resultado, servicio.citas_por_tarjeta)
    await enviar_tarjeta(message, servicio, cliente_id, resultado.flores, pie)


def separar_alta(args: str) -> tuple[str, int]:
    """Separa nombre y citas previas: "Rosa 6" → ("Rosa", 6); sin número, 0 previas."""
    partes = args.split()
    previas = 0
    if partes:
        try:
            previas = int(partes[-1])
        except ValueError:
            pass
        else:
            partes = partes[:-1]
    if not partes:
        raise ValueError("falta el nombre")
    return " ".join(partes), previas


async def _crear_alta(
    message: Message, nombre: str, previas: int, fecha: datetime, servicio: ServicioTarjetas
) -> None:
    try:
        cliente = servicio.crear_cliente(nombre, previas, fecha)
    except NombreInvalido as error:
        await message.reply_text(textos.nombre_invalido(error.motivo))
        return
    except CitasPreviasFueraDeRango:
        await message.reply_text(textos.previas_fuera_de_rango(servicio.citas_por_tarjeta - 1))
        return
    log.info("Alta: cliente=%s previas=%s", cliente.id, previas)
    await enviar_tarjeta(message, servicio, cliente.id, None, textos.pie_alta(cliente))


async def _crear_y_registrar(
    message: Message, nombre: str, fecha: datetime, servicio: ServicioTarjetas
) -> None:
    try:
        cliente = servicio.crear_cliente(nombre, 0, fecha)
    except NombreInvalido as error:
        await message.reply_text(textos.nombre_invalido(error.motivo))
        return
    log.info("Alta: cliente=%s previas=0", cliente.id)
    await _registrar(message, cliente.id, fecha, servicio)


# --- comandos ----------------------------------------------------------------------------------


async def cmd_ayuda(update: Update, context: Contexto) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(textos.AYUDA)


async def _comando_con_cliente(update: Update, context: Contexto, comando: Comando) -> None:
    """`/cita`, `/deshacer` y `/tarjeta`: todos reciben `<nombre o #id>`."""
    message = update.effective_message
    if message is None:
        return
    texto = _argumentos(context).strip()
    if not texto:
        await message.reply_text(textos.uso(comando))
        return
    await _resolver(message, texto, comando, message.date, _servicio(context), _acciones(context))


async def cmd_cita(update: Update, context: Contexto) -> None:
    await _comando_con_cliente(update, context, "cita")


async def cmd_deshacer(update: Update, context: Contexto) -> None:
    await _comando_con_cliente(update, context, "deshacer")


async def cmd_tarjeta(update: Update, context: Contexto) -> None:
    await _comando_con_cliente(update, context, "tarjeta")


async def cmd_alta(update: Update, context: Contexto) -> None:
    message = update.effective_message
    if message is None:
        return
    servicio = _servicio(context)
    try:
        nombre, previas = separar_alta(_argumentos(context))
    except ValueError:
        await message.reply_text(textos.uso("alta"))
        return
    maximo = servicio.citas_por_tarjeta - 1
    if not 0 <= previas <= maximo:
        await message.reply_text(textos.previas_fuera_de_rango(maximo))
        return
    try:
        nombre = servicio.validar_nombre(nombre)
    except NombreInvalido as error:
        await message.reply_text(textos.nombre_invalido(error.motivo))
        return
    existentes = servicio.homonimos(nombre)
    if existentes:  # puede ser otra persona con el mismo nombre: se confirma (FR-020 de la 001)
        token = _acciones(context).registrar(
            Accion(
                tipo="crear_homonimo",
                comando="alta",
                nombre=nombre,
                citas_previas=previas,
                fecha_comando=message.date,
            )
        )
        await message.reply_text(
            textos.confirmar_homonimo(existentes),
            reply_markup=_si_no(token, textos.BOTON_CREAR_OTRO),
        )
        return
    await _crear_alta(message, nombre, previas, message.date, servicio)


async def cmd_clientes(update: Update, context: Contexto) -> None:
    message = update.effective_message
    if message is None:
        return
    clientes = _servicio(context).listar()
    if not clientes:
        await message.reply_text(textos.SIN_CLIENTES)
        return
    for parte in textos.dividir_mensajes(textos.lista_clientes(clientes)):
        await message.reply_text(parte)


# --- botones -----------------------------------------------------------------------------------


async def al_pulsar(update: Update, context: Contexto) -> None:
    consulta = update.callback_query
    if consulta is None:
        return
    await consulta.answer()
    mensaje = consulta.message
    if not isinstance(mensaje, Message):
        return
    servicio, acciones = _servicio(context), _acciones(context)
    datos = desempaquetar(consulta.data or "")
    accion = acciones.tomar(datos[0]) if datos else None  # una sola vez (FR-011 de la 001)
    if datos is None or accion is None:
        await mensaje.reply_text(textos.ACCION_CADUCADA)
        return
    opcion = datos[1]
    if opcion == "no":
        await _anotar(mensaje, textos.CANCELADO)
        return
    fecha = accion.fecha_comando or mensaje.date  # la cita lleva la fecha del comando original

    if accion.tipo == "elegir":
        if opcion == "nuevo":
            await _anotar(mensaje, textos.elegido(textos.boton_crear(accion.nombre)))
            await _crear_y_registrar(mensaje, accion.nombre, fecha, servicio)
            return
        cliente_id = int(opcion)
        if cliente_id not in accion.cliente_ids:
            await mensaje.reply_text(textos.ACCION_CADUCADA)
            return
        resumen = servicio.resumen(cliente_id)
        await _anotar(mensaje, textos.elegido(f"{resumen.nombre} #{resumen.id}"))
        await _continuar(mensaje, accion.comando, cliente_id, fecha, servicio, acciones)
    elif accion.tipo == "crear_y_cita":
        await _anotar(mensaje, textos.elegido(textos.BOTON_CREAR))
        await _crear_y_registrar(mensaje, accion.nombre, fecha, servicio)
    elif accion.tipo == "confirmar_mismo_dia":
        await _anotar(mensaje, textos.elegido(textos.BOTON_SI_REGISTRAR))
        await _registrar(mensaje, accion.cliente_ids[0], fecha, servicio)
    elif accion.tipo == "crear_homonimo":
        await _anotar(mensaje, textos.elegido(textos.BOTON_CREAR_OTRO))
        await _crear_alta(mensaje, accion.nombre, accion.citas_previas, fecha, servicio)
    elif accion.tipo == "confirmar_deshacer":
        await _deshacer(mensaje, accion, servicio)


async def _deshacer(mensaje: Message, accion: Accion, servicio: ServicioTarjetas) -> None:
    cliente_id = accion.cliente_ids[0]
    cita = servicio.ultima_cita_vigente(cliente_id)
    if cita is None or cita.id != accion.cita_id:  # no anular una cita distinta de la mostrada
        await mensaje.reply_text(textos.cita_cambio(servicio.resumen(cliente_id)))
        return
    await _anotar(mensaje, textos.elegido(textos.BOTON_SI_DESHACER))
    resumen = servicio.deshacer_ultima(cliente_id, datetime.now(UTC))
    if resumen is None:
        await mensaje.reply_text(textos.nada_que_deshacer(servicio.resumen(cliente_id)))
        return
    log.info("Cita anulada: cliente=%s premio=%s", cliente_id, cita.es_premio)
    pie = textos.pie_deshacer(resumen, era_premio=cita.es_premio)
    await enviar_tarjeta(mensaje, servicio, cliente_id, None, pie)


# --- errores, mensajes sin comando y registro --------------------------------------------------


async def al_fallar(update: object, context: Contexto) -> None:
    log.error("Error inesperado", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message is not None:
        await update.effective_message.reply_text(textos.ERROR_INESPERADO)


async def sin_comando(update: Update, context: Contexto) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(textos.NO_ES_COMANDO)


async def registrar_comandos(aplicacion: Aplicacion) -> None:
    """El menú que aparece al escribir \"/\" en Telegram."""
    await aplicacion.bot.set_my_commands(COMANDOS)


def registrar_handlers(application: Aplicacion) -> None:
    """Comandos, botones y, al final, lo que no es un comando conocido."""
    application.add_handler(CommandHandler(["start", "ayuda"], cmd_ayuda))
    application.add_handler(CommandHandler("cita", cmd_cita))
    application.add_handler(CommandHandler("alta", cmd_alta))
    application.add_handler(CommandHandler("deshacer", cmd_deshacer))
    application.add_handler(CommandHandler("tarjeta", cmd_tarjeta))
    application.add_handler(CommandHandler("clientes", cmd_clientes))
    application.add_handler(CallbackQueryHandler(al_pulsar, pattern=rf"^{PREFIJO}:"))
    application.add_handler(MessageHandler(filters.ALL, sin_comando))  # debe ser el último
    application.add_error_handler(al_fallar)
