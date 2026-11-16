"""Handlers de Telegram: capa delgada entre los comandos y el servicio (principio II).

`servicio` y `acciones` llegan por inyección desde los datos del Dispatcher.
"""

import logging
from datetime import UTC, datetime

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from tarjeta_lealtad.bot import textos
from tarjeta_lealtad.bot.acciones import Accion, AccionCB, AccionesPendientes, Comando
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

router = Router(name="tarjeta_lealtad")


# --- utilidades --------------------------------------------------------------------------------


def _teclado(token: str, opciones: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """Un botón por fila; cada uno lleva el token de la acción y su opción."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texto, callback_data=AccionCB(token=token, opcion=opcion).pack()
                )
            ]
            for texto, opcion in opciones
        ]
    )


def _si_no(token: str, si: str) -> InlineKeyboardMarkup:
    return _teclado(token, [(si, "si"), (textos.BOTON_CANCELAR, "no")])


async def _anotar(mensaje: Message, nota: str) -> None:
    """Quita los botones del mensaje y deja anotada la elección."""
    try:
        await mensaje.edit_text(f"{mensaje.text or ''}\n\n{nota}".strip())
    except TelegramBadRequest:
        log.debug("No se pudo editar el mensaje con botones", exc_info=True)


async def enviar_tarjeta(
    message: Message, servicio: ServicioTarjetas, cliente_id: int, flores: int | None, pie: str
) -> None:
    """Envía la tarjeta como foto. Si falla, los datos ya están guardados: se avisa y se anota."""
    try:
        png = servicio.tarjeta_png(cliente_id, flores)
        await message.answer_photo(BufferedInputFile(png, "tarjeta.png"), caption=pie)
    except Exception:
        log.exception("No se pudo enviar la tarjeta del cliente %s", cliente_id)
        await message.answer(textos.error_envio(cliente_id))


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
    """Busca al cliente; si hay dudas, pregunta con botones (FR-005 – FR-007)."""
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
            await message.answer(textos.id_inexistente(cliente_id))
        case SinCoincidencias():
            if comando != "cita":
                await message.answer(textos.no_encontrado(texto))
                return
            try:
                nombre = servicio.validar_nombre(texto)
            except NombreInvalido as error:
                await message.answer(textos.nombre_invalido(error.motivo))
                return
            token = acciones.registrar(
                Accion(tipo="crear_y_cita", comando="cita", nombre=nombre, fecha_comando=fecha)
            )
            await message.answer(
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
    await message.answer(pregunta, reply_markup=_teclado(token, botones))


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
        if hora is not None:  # probable duplicado (FR-010)
            token = acciones.registrar(
                Accion(
                    tipo="confirmar_mismo_dia",
                    comando="cita",
                    cliente_ids=(cliente_id,),
                    fecha_comando=fecha,
                )
            )
            await message.answer(
                textos.confirmar_mismo_dia(servicio.resumen(cliente_id), hora, servicio.zona),
                reply_markup=_si_no(token, textos.BOTON_SI_REGISTRAR),
            )
            return
        await _registrar(message, cliente_id, fecha, servicio)
    elif comando == "tarjeta":  # solo consulta: no registra nada (FR-032)
        pie = textos.pie_tarjeta(servicio.resumen(cliente_id))
        await enviar_tarjeta(message, servicio, cliente_id, None, pie)
    elif comando == "deshacer":
        resumen = servicio.resumen(cliente_id)
        cita = servicio.ultima_cita_vigente(cliente_id)
        if cita is None:
            await message.answer(textos.nada_que_deshacer(resumen))
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
        await message.answer(
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
        await message.answer(textos.nombre_invalido(error.motivo))
        return
    except CitasPreviasFueraDeRango:
        await message.answer(textos.previas_fuera_de_rango(servicio.citas_por_tarjeta - 1))
        return
    log.info("Alta: cliente=%s previas=%s", cliente.id, previas)
    await enviar_tarjeta(message, servicio, cliente.id, None, textos.pie_alta(cliente))


async def _crear_y_registrar(
    message: Message, nombre: str, fecha: datetime, servicio: ServicioTarjetas
) -> None:
    try:
        cliente = servicio.crear_cliente(nombre, 0, fecha)
    except NombreInvalido as error:
        await message.answer(textos.nombre_invalido(error.motivo))
        return
    log.info("Alta: cliente=%s previas=0", cliente.id)
    await _registrar(message, cliente.id, fecha, servicio)


# --- comandos ----------------------------------------------------------------------------------


@router.message(CommandStart())
@router.message(Command("ayuda"))
async def cmd_ayuda(message: Message) -> None:
    await message.answer(textos.AYUDA)


@router.message(Command("cita"))
async def cmd_cita(
    message: Message,
    command: CommandObject,
    servicio: ServicioTarjetas,
    acciones: AccionesPendientes,
) -> None:
    texto = (command.args or "").strip()
    if not texto:
        await message.answer(textos.uso("cita"))
        return
    await _resolver(message, texto, "cita", message.date, servicio, acciones)


@router.message(Command("alta"))
async def cmd_alta(
    message: Message,
    command: CommandObject,
    servicio: ServicioTarjetas,
    acciones: AccionesPendientes,
) -> None:
    try:
        nombre, previas = separar_alta(command.args or "")
    except ValueError:
        await message.answer(textos.uso("alta"))
        return
    maximo = servicio.citas_por_tarjeta - 1
    if not 0 <= previas <= maximo:
        await message.answer(textos.previas_fuera_de_rango(maximo))
        return
    try:
        nombre = servicio.validar_nombre(nombre)
    except NombreInvalido as error:
        await message.answer(textos.nombre_invalido(error.motivo))
        return
    existentes = servicio.homonimos(nombre)
    if existentes:  # puede ser otra persona con el mismo nombre: se confirma (FR-020)
        token = acciones.registrar(
            Accion(
                tipo="crear_homonimo",
                comando="alta",
                nombre=nombre,
                citas_previas=previas,
                fecha_comando=message.date,
            )
        )
        await message.answer(
            textos.confirmar_homonimo(existentes),
            reply_markup=_si_no(token, textos.BOTON_CREAR_OTRO),
        )
        return
    await _crear_alta(message, nombre, previas, message.date, servicio)


@router.message(Command("deshacer"))
async def cmd_deshacer(
    message: Message,
    command: CommandObject,
    servicio: ServicioTarjetas,
    acciones: AccionesPendientes,
) -> None:
    texto = (command.args or "").strip()
    if not texto:
        await message.answer(textos.uso("deshacer"))
        return
    await _resolver(message, texto, "deshacer", message.date, servicio, acciones)


@router.message(Command("tarjeta"))
async def cmd_tarjeta(
    message: Message,
    command: CommandObject,
    servicio: ServicioTarjetas,
    acciones: AccionesPendientes,
) -> None:
    texto = (command.args or "").strip()
    if not texto:
        await message.answer(textos.uso("tarjeta"))
        return
    await _resolver(message, texto, "tarjeta", message.date, servicio, acciones)


@router.message(Command("clientes"))
async def cmd_clientes(message: Message, servicio: ServicioTarjetas) -> None:
    clientes = servicio.listar()
    if not clientes:
        await message.answer(textos.SIN_CLIENTES)
        return
    for parte in textos.dividir_mensajes(textos.lista_clientes(clientes)):
        await message.answer(parte)


# --- botones -----------------------------------------------------------------------------------


@router.callback_query(AccionCB.filter())
async def al_pulsar(
    callback: CallbackQuery,
    callback_data: AccionCB,
    servicio: ServicioTarjetas,
    acciones: AccionesPendientes,
) -> None:
    await callback.answer()
    mensaje = callback.message
    if not isinstance(mensaje, Message):
        return
    accion = acciones.tomar(callback_data.token)  # una sola vez (FR-011)
    if accion is None:
        await mensaje.answer(textos.ACCION_CADUCADA)
        return
    opcion = callback_data.opcion
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
            await mensaje.answer(textos.ACCION_CADUCADA)
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
        await mensaje.answer(textos.cita_cambio(servicio.resumen(cliente_id)))
        return
    await _anotar(mensaje, textos.elegido(textos.BOTON_SI_DESHACER))
    resumen = servicio.deshacer_ultima(cliente_id, datetime.now(UTC))
    if resumen is None:
        await mensaje.answer(textos.nada_que_deshacer(servicio.resumen(cliente_id)))
        return
    log.info("Cita anulada: cliente=%s premio=%s", cliente_id, cita.es_premio)
    pie = textos.pie_deshacer(resumen, era_premio=cita.es_premio)
    await enviar_tarjeta(mensaje, servicio, cliente_id, None, pie)


# --- errores y mensajes sin comando ------------------------------------------------------------


@router.errors()
async def al_fallar(evento: ErrorEvent) -> bool:
    log.error("Error inesperado", exc_info=evento.exception)
    actualizacion = evento.update
    mensaje = actualizacion.message
    if mensaje is None and actualizacion.callback_query is not None:
        posible = actualizacion.callback_query.message
        mensaje = posible if isinstance(posible, Message) else None
    if mensaje is not None:
        await mensaje.answer(textos.ERROR_INESPERADO)
    return True


# Debe ser el último handler de mensajes: atrapa todo lo que no es un comando conocido.
@router.message()
async def sin_comando(message: Message) -> None:
    await message.answer(textos.NO_ES_COMANDO)
