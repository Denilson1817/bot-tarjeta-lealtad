from collections.abc import Callable
from datetime import datetime
from typing import Any

from tarjeta_lealtad.bot import handlers, textos
from tarjeta_lealtad.servicio import Encontrado, SinCoincidencias

Utc = Callable[[str], datetime]


async def test_sin_argumento_muestra_el_uso(mensaje_falso: Any, servicio: Any, tg: Any) -> None:
    mensaje = mensaje_falso("/cita")
    await tg.comando(handlers.cmd_cita, mensaje, None)
    mensaje.reply_text.assert_awaited_once_with(textos.uso("cita"))


async def test_cliente_existente_recibe_la_foto(
    mensaje_falso: Any, servicio: Any, tg: Any, utc: Utc
) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-01 16:00"))
    for dia in range(10, 15):
        servicio.registrar_cita(carmen.id, utc(f"2026-11-{dia} 16:00"))
    mensaje = mensaje_falso("/cita Carmen", fecha=utc("2026-11-16 16:32"))
    await tg.comando(handlers.cmd_cita, mensaje, "Carmen")
    mensaje.reply_photo.assert_awaited_once()
    foto = mensaje.reply_photo.call_args.kwargs["photo"]
    assert isinstance(foto, bytes)
    assert mensaje.reply_photo.call_args.kwargs["caption"] == (
        f"🌸 Carmen (#{carmen.id}): 6 de 9 flores. Faltan 4 citas para la de premio (la 10.ª)."
    )


async def test_cliente_nuevo_se_crea_al_confirmar_con_la_fecha_del_comando(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    mensaje = mensaje_falso("/cita Lucía", fecha=utc("2026-11-16 16:32"))
    await tg.comando(handlers.cmd_cita, mensaje, "Lucía")
    mensaje.reply_text.assert_awaited_once()
    assert mensaje.reply_text.call_args.args[0] == textos.confirmar_crear("Lucía")
    assert [e for e, _ in tg.botones(mensaje.reply_text)] == ["Crear", "Cancelar"]
    assert isinstance(servicio.buscar("lucia"), SinCoincidencias)

    prompt = mensaje_falso(fecha=utc("2026-11-16 18:00"))  # el toque llega más tarde
    await tg.pulsar(prompt, tg.boton(mensaje.reply_text, "Crear"))
    lucia = servicio.buscar("lucia")
    assert isinstance(lucia, Encontrado)
    assert lucia.cliente.citas_en_curso == 1
    assert lucia.cliente.ultima_cita == utc("2026-11-16 16:32")
    prompt.reply_photo.assert_awaited_once()


async def test_cancelar_no_cambia_nada_y_un_segundo_toque_caduca(
    mensaje_falso: Any, servicio: Any, tg: Any
) -> None:
    mensaje = mensaje_falso("/cita Lucía")
    await tg.comando(handlers.cmd_cita, mensaje, "Lucía")
    prompt = mensaje_falso()
    cancelar = tg.boton(mensaje.reply_text, "Cancelar")
    await tg.pulsar(prompt, cancelar)
    assert isinstance(servicio.buscar("lucia"), SinCoincidencias)
    assert textos.CANCELADO in prompt.edit_text.call_args.args[0]

    await tg.pulsar(prompt, cancelar)
    prompt.reply_text.assert_awaited_with(textos.ACCION_CADUCADA)


async def test_doble_toque_en_crear_registra_una_sola_cita(
    mensaje_falso: Any, servicio: Any, tg: Any
) -> None:
    mensaje = mensaje_falso("/cita Lucía")
    await tg.comando(handlers.cmd_cita, mensaje, "Lucía")
    crear = tg.boton(mensaje.reply_text, "Crear")
    prompt = mensaje_falso()
    await tg.pulsar(prompt, crear)
    await tg.pulsar(prompt, crear)
    lucia = servicio.buscar("lucia")
    assert isinstance(lucia, Encontrado)
    assert lucia.cliente.citas_en_curso == 1
    prompt.reply_text.assert_awaited_with(textos.ACCION_CADUCADA)


async def test_mismo_dia_pide_confirmacion(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-16 15:00"))
    servicio.registrar_cita(carmen.id, utc("2026-11-16 16:00"))  # 10:00 local
    mensaje = mensaje_falso("/cita Carmen", fecha=utc("2026-11-16 16:32"))
    await tg.comando(handlers.cmd_cita, mensaje, "Carmen")
    mensaje.reply_photo.assert_not_awaited()
    assert "10:00" in mensaje.reply_text.call_args.args[0]
    assert [e for e, _ in tg.botones(mensaje.reply_text)] == ["Sí, registrar", "Cancelar"]

    prompt = mensaje_falso()
    await tg.pulsar(prompt, tg.boton(mensaje.reply_text, "Sí"))
    assert servicio.resumen(carmen.id).citas_en_curso == 2
    prompt.reply_photo.assert_awaited_once()


async def test_errata_sugiere_parecidos_y_permite_crear(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-16 15:00"))
    mensaje = mensaje_falso("/cita Carmn")
    await tg.comando(handlers.cmd_cita, mensaje, "Carmn")
    etiquetas = [e for e, _ in tg.botones(mensaje.reply_text)]
    assert etiquetas == [f"Carmen #{carmen.id} · 0/9 · sin citas", "Crear «Carmn»", "Cancelar"]

    prompt = mensaje_falso()
    await tg.pulsar(prompt, tg.boton(mensaje.reply_text, "Carmen #"))
    assert servicio.resumen(carmen.id).citas_en_curso == 1
    assert isinstance(servicio.buscar("carmn"), SinCoincidencias) is False  # sigue siendo parecido


async def test_nombre_invalido_no_ofrece_crear(
    mensaje_falso: Any, servicio: Any, tg: Any, utc: Utc
) -> None:
    mensaje = mensaje_falso("/cita Ana 😀")
    await tg.comando(handlers.cmd_cita, mensaje, "Ana 😀")
    assert "😀" in mensaje.reply_text.call_args.args[0]
    assert tg.botones(mensaje.reply_text) == []

    ana = servicio.crear_cliente("Ana", 0, utc("2026-11-16 15:00"))
    mensaje = mensaje_falso("/cita Ana7")
    await tg.comando(handlers.cmd_cita, mensaje, "Ana7")
    etiquetas = [e for e, _ in tg.botones(mensaje.reply_text)]
    assert etiquetas == [f"Ana #{ana.id} · 0/9 · sin citas", "Cancelar"]


async def test_si_falla_el_envio_la_cita_queda_registrada(
    mensaje_falso: Any, servicio: Any, tg: Any, utc: Utc
) -> None:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-11-15 15:00"))
    mensaje = mensaje_falso("/cita Carmen")
    mensaje.reply_photo.side_effect = RuntimeError("Telegram no responde")
    await tg.comando(handlers.cmd_cita, mensaje, "Carmen")
    assert servicio.resumen(carmen.id).citas_en_curso == 1
    mensaje.reply_text.assert_awaited_once_with(textos.error_envio(carmen.id))


async def test_cita_de_premio_envia_nueve_flores(
    mensaje_falso: Any, servicio: Any, tg: Any, utc: Utc
) -> None:
    from tarjeta_lealtad.render import generar_tarjeta

    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-10-31 16:00"))
    for dia in range(1, 10):
        servicio.registrar_cita(carmen.id, utc(f"2026-11-{dia:02d} 16:00"))
    mensaje = mensaje_falso("/cita Carmen", fecha=utc("2026-11-16 16:32"))
    await tg.comando(handlers.cmd_cita, mensaje, "Carmen")
    foto = mensaje.reply_photo.call_args.kwargs["photo"]
    assert foto == generar_tarjeta("Carmen", 9)
    assert mensaje.reply_photo.call_args.kwargs["caption"].startswith(
        f"🎁 Carmen (#{carmen.id}): ¡cita de premio! Tarjeta n.º 1 completada."
    )


async def test_homonimos_piden_elegir_y_registran_solo_en_la_elegida(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    primera = servicio.crear_cliente("María", 0, utc("2026-11-10 15:00"))
    servicio.registrar_cita(primera.id, utc("2026-11-10 18:00"))
    segunda = servicio.crear_cliente("María", 0, utc("2026-11-12 15:00"))
    mensaje = mensaje_falso("/cita maria")
    await tg.comando(handlers.cmd_cita, mensaje, "maria")
    assert [e for e, _ in tg.botones(mensaje.reply_text)] == [
        f"María #{primera.id} · 1/9 · 10 nov",
        f"María #{segunda.id} · 0/9 · sin citas",
        "Cancelar",
    ]
    mensaje.reply_photo.assert_not_awaited()
    assert servicio.resumen(segunda.id).citas_en_curso == 0

    prompt = mensaje_falso()
    data = tg.botones(mensaje.reply_text)[1][1]
    await tg.pulsar(prompt, data)
    assert servicio.resumen(segunda.id).citas_en_curso == 1
    assert servicio.resumen(primera.id).citas_en_curso == 1  # la otra no cambia


async def test_cita_por_id_no_pregunta(
    mensaje_falso: Any, servicio: Any, tg: Any, utc: Utc
) -> None:
    servicio.crear_cliente("María", 0, utc("2026-11-10 15:00"))
    segunda = servicio.crear_cliente("María", 0, utc("2026-11-12 15:00"))
    mensaje = mensaje_falso(f"/cita #{segunda.id}")
    await tg.comando(handlers.cmd_cita, mensaje, f"#{segunda.id}")
    mensaje.reply_photo.assert_awaited_once()
    assert servicio.resumen(segunda.id).citas_en_curso == 1


async def test_id_inexistente(mensaje_falso: Any, servicio: Any, tg: Any) -> None:
    mensaje = mensaje_falso("/cita #999")
    await tg.comando(handlers.cmd_cita, mensaje, "#999")
    mensaje.reply_text.assert_awaited_once_with("No existe el cliente #999.")
