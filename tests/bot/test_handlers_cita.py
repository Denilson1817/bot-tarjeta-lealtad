from collections.abc import Callable
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from aiogram.filters import CommandObject
from aiogram.types import BufferedInputFile

from tarjeta_lealtad.bot import handlers, textos
from tarjeta_lealtad.bot.acciones import AccionCB
from tarjeta_lealtad.servicio import Encontrado, SinCoincidencias

Utc = Callable[[str], datetime]
Botones = Callable[[AsyncMock], list[tuple[str, str]]]


def cmd(args: str | None, comando: str = "cita") -> CommandObject:
    return CommandObject(prefix="/", command=comando, args=args)


async def cita(mensaje: MagicMock, args: str | None, servicio: Any, acciones: Any) -> None:
    await handlers.cmd_cita(mensaje, cmd(args), servicio=servicio, acciones=acciones)


async def pulsar(
    callback_falso: Any, prompt: MagicMock, data: str, servicio: Any, acciones: Any
) -> MagicMock:
    callback = callback_falso(data, prompt)
    await handlers.al_pulsar(callback, AccionCB.unpack(data), servicio=servicio, acciones=acciones)
    return callback


def boton(botones: Botones, llamada: AsyncMock, texto: str) -> str:
    return next(data for etiqueta, data in botones(llamada) if etiqueta.startswith(texto))


async def test_sin_argumento_muestra_el_uso(
    mensaje_falso: Any, servicio: Any, acciones: Any
) -> None:
    mensaje = mensaje_falso("/cita")
    await cita(mensaje, None, servicio, acciones)
    mensaje.answer.assert_awaited_once_with(textos.uso("cita"))


async def test_cliente_existente_recibe_la_foto(
    mensaje_falso: Any, servicio: Any, acciones: Any, utc: Utc
) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-01 16:00"))
    for dia in range(10, 15):
        servicio.registrar_cita(carmen.id, utc(f"2026-11-{dia} 16:00"))
    mensaje = mensaje_falso("/cita Carmen", fecha=utc("2026-11-16 16:32"))
    await cita(mensaje, "Carmen", servicio, acciones)
    mensaje.answer_photo.assert_awaited_once()
    foto = mensaje.answer_photo.call_args.args[0]
    assert isinstance(foto, BufferedInputFile)
    assert mensaje.answer_photo.call_args.kwargs["caption"] == (
        f"🌸 Carmen (#{carmen.id}): 6 de 9 flores. Faltan 4 citas para la de premio (la 10.ª)."
    )


async def test_cliente_nuevo_se_crea_al_confirmar_con_la_fecha_del_comando(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    mensaje = mensaje_falso("/cita Lucía", fecha=utc("2026-11-16 16:32"))
    await cita(mensaje, "Lucía", servicio, acciones)
    mensaje.answer.assert_awaited_once()
    assert mensaje.answer.call_args.args[0] == textos.confirmar_crear("Lucía")
    assert [e for e, _ in botones(mensaje.answer)] == ["Crear", "Cancelar"]
    assert isinstance(servicio.buscar("lucia"), SinCoincidencias)

    prompt = mensaje_falso(fecha=utc("2026-11-16 18:00"))  # el toque llega más tarde
    await pulsar(
        callback_falso, prompt, boton(botones, mensaje.answer, "Crear"), servicio, acciones
    )
    lucia = servicio.buscar("lucia")
    assert isinstance(lucia, Encontrado)
    assert lucia.cliente.citas_en_curso == 1
    assert lucia.cliente.ultima_cita == utc("2026-11-16 16:32")
    prompt.answer_photo.assert_awaited_once()


async def test_cancelar_no_cambia_nada_y_un_segundo_toque_caduca(
    mensaje_falso: Any, callback_falso: Any, botones: Botones, servicio: Any, acciones: Any
) -> None:
    mensaje = mensaje_falso("/cita Lucía")
    await cita(mensaje, "Lucía", servicio, acciones)
    prompt = mensaje_falso()
    cancelar = boton(botones, mensaje.answer, "Cancelar")
    await pulsar(callback_falso, prompt, cancelar, servicio, acciones)
    assert isinstance(servicio.buscar("lucia"), SinCoincidencias)
    assert textos.CANCELADO in prompt.edit_text.call_args.args[0]

    await pulsar(callback_falso, prompt, cancelar, servicio, acciones)
    prompt.answer.assert_awaited_with(textos.ACCION_CADUCADA)


async def test_doble_toque_en_crear_registra_una_sola_cita(
    mensaje_falso: Any, callback_falso: Any, botones: Botones, servicio: Any, acciones: Any
) -> None:
    mensaje = mensaje_falso("/cita Lucía")
    await cita(mensaje, "Lucía", servicio, acciones)
    crear = boton(botones, mensaje.answer, "Crear")
    prompt = mensaje_falso()
    await pulsar(callback_falso, prompt, crear, servicio, acciones)
    await pulsar(callback_falso, prompt, crear, servicio, acciones)
    lucia = servicio.buscar("lucia")
    assert isinstance(lucia, Encontrado)
    assert lucia.cliente.citas_en_curso == 1
    prompt.answer.assert_awaited_with(textos.ACCION_CADUCADA)


async def test_mismo_dia_pide_confirmacion(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-16 15:00"))
    servicio.registrar_cita(carmen.id, utc("2026-11-16 16:00"))  # 10:00 local
    mensaje = mensaje_falso("/cita Carmen", fecha=utc("2026-11-16 16:32"))
    await cita(mensaje, "Carmen", servicio, acciones)
    mensaje.answer_photo.assert_not_awaited()
    assert "10:00" in mensaje.answer.call_args.args[0]
    assert [e for e, _ in botones(mensaje.answer)] == ["Sí, registrar", "Cancelar"]

    prompt = mensaje_falso()
    await pulsar(callback_falso, prompt, boton(botones, mensaje.answer, "Sí"), servicio, acciones)
    assert servicio.resumen(carmen.id).citas_en_curso == 2
    prompt.answer_photo.assert_awaited_once()


async def test_errata_sugiere_parecidos_y_permite_crear(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-16 15:00"))
    mensaje = mensaje_falso("/cita Carmn")
    await cita(mensaje, "Carmn", servicio, acciones)
    etiquetas = [e for e, _ in botones(mensaje.answer)]
    assert etiquetas == [f"Carmen #{carmen.id} · 0/9 · sin citas", "Crear «Carmn»", "Cancelar"]

    prompt = mensaje_falso()
    await pulsar(
        callback_falso, prompt, boton(botones, mensaje.answer, "Carmen #"), servicio, acciones
    )
    assert servicio.resumen(carmen.id).citas_en_curso == 1
    assert isinstance(servicio.buscar("carmn"), SinCoincidencias) is False  # sigue siendo parecido


async def test_nombre_invalido_no_ofrece_crear(
    mensaje_falso: Any, botones: Botones, servicio: Any, acciones: Any, utc: Utc
) -> None:
    mensaje = mensaje_falso("/cita Ana 😀")
    await cita(mensaje, "Ana 😀", servicio, acciones)
    assert "😀" in mensaje.answer.call_args.args[0]
    assert botones(mensaje.answer) == []

    ana = servicio.crear_cliente("Ana", 0, utc("2026-11-16 15:00"))
    mensaje = mensaje_falso("/cita Ana7")
    await cita(mensaje, "Ana7", servicio, acciones)
    etiquetas = [e for e, _ in botones(mensaje.answer)]
    assert etiquetas == [f"Ana #{ana.id} · 0/9 · sin citas", "Cancelar"]


async def test_si_falla_el_envio_la_cita_queda_registrada(
    mensaje_falso: Any, servicio: Any, acciones: Any, utc: Utc
) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-15 15:00"))
    mensaje = mensaje_falso("/cita Carmen")
    mensaje.answer_photo.side_effect = RuntimeError("Telegram no responde")
    await cita(mensaje, "Carmen", servicio, acciones)
    assert servicio.resumen(carmen.id).citas_en_curso == 1
    mensaje.answer.assert_awaited_once_with(textos.error_envio(carmen.id))


async def test_cita_de_premio_envia_nueve_flores(
    mensaje_falso: Any, servicio: Any, acciones: Any, utc: Utc
) -> None:
    from tarjeta_lealtad.render import generar_tarjeta

    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-10-31 16:00"))
    for dia in range(1, 10):
        servicio.registrar_cita(carmen.id, utc(f"2026-11-{dia:02d} 16:00"))
    mensaje = mensaje_falso("/cita Carmen", fecha=utc("2026-11-16 16:32"))
    await cita(mensaje, "Carmen", servicio, acciones)
    foto = mensaje.answer_photo.call_args.args[0]
    assert foto.data == generar_tarjeta("Carmen", 9)
    assert mensaje.answer_photo.call_args.kwargs["caption"].startswith(
        f"🎁 Carmen (#{carmen.id}): ¡cita de premio! Tarjeta n.º 1 completada."
    )


async def test_homonimos_piden_elegir_y_registran_solo_en_la_elegida(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    primera = servicio.crear_cliente("María", 0, utc("2026-11-10 15:00"))
    servicio.registrar_cita(primera.id, utc("2026-11-10 18:00"))
    segunda = servicio.crear_cliente("María", 0, utc("2026-11-12 15:00"))
    mensaje = mensaje_falso("/cita maria")
    await cita(mensaje, "maria", servicio, acciones)
    assert [e for e, _ in botones(mensaje.answer)] == [
        f"María #{primera.id} · 1/9 · 10 nov",
        f"María #{segunda.id} · 0/9 · sin citas",
        "Cancelar",
    ]
    mensaje.answer_photo.assert_not_awaited()
    assert servicio.resumen(segunda.id).citas_en_curso == 0

    prompt = mensaje_falso()
    data = botones(mensaje.answer)[1][1]
    await pulsar(callback_falso, prompt, data, servicio, acciones)
    assert servicio.resumen(segunda.id).citas_en_curso == 1
    assert servicio.resumen(primera.id).citas_en_curso == 1  # la otra no cambia


async def test_cita_por_id_no_pregunta(
    mensaje_falso: Any, servicio: Any, acciones: Any, utc: Utc
) -> None:
    servicio.crear_cliente("María", 0, utc("2026-11-10 15:00"))
    segunda = servicio.crear_cliente("María", 0, utc("2026-11-12 15:00"))
    mensaje = mensaje_falso(f"/cita #{segunda.id}")
    await cita(mensaje, f"#{segunda.id}", servicio, acciones)
    mensaje.answer_photo.assert_awaited_once()
    assert servicio.resumen(segunda.id).citas_en_curso == 1


async def test_id_inexistente(mensaje_falso: Any, servicio: Any, acciones: Any) -> None:
    mensaje = mensaje_falso("/cita #999")
    await cita(mensaje, "#999", servicio, acciones)
    mensaje.answer.assert_awaited_once_with("No existe el cliente #999.")
