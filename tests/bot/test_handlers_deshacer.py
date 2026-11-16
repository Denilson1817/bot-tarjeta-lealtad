from collections.abc import Callable
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from aiogram.filters import CommandObject

from tarjeta_lealtad.bot import handlers, textos
from tarjeta_lealtad.bot.acciones import AccionCB

Utc = Callable[[str], datetime]
Botones = Callable[[AsyncMock], list[tuple[str, str]]]


async def deshacer(mensaje: MagicMock, args: str | None, servicio: Any, acciones: Any) -> None:
    comando = CommandObject(prefix="/", command="deshacer", args=args)
    await handlers.cmd_deshacer(mensaje, comando, servicio=servicio, acciones=acciones)


async def pulsar(
    callback_falso: Any, prompt: MagicMock, data: str, servicio: Any, acciones: Any
) -> None:
    await handlers.al_pulsar(
        callback_falso(data, prompt), AccionCB.unpack(data), servicio=servicio, acciones=acciones
    )


def carmen_con_premio(servicio: Any, utc: Utc) -> int:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-10-31 16:00"))
    for dia in range(1, 10):
        servicio.registrar_cita(carmen.id, utc(f"2026-11-{dia:02d} 16:00"))
    servicio.registrar_cita(carmen.id, utc("2026-11-12 16:32"))  # 10.ª: premio, 10:32 local
    return int(carmen.id)


async def test_confirma_mostrando_la_cita_y_reabre_el_premio(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmen")
    await deshacer(mensaje, "Carmen", servicio, acciones)
    assert mensaje.answer.call_args.args[0] == (
        f"¿Anular la última cita de Carmen (#{cliente_id})? 12 nov 2026, 10:32 · cita de premio"
    )
    assert [e for e, _ in botones(mensaje.answer)] == ["Sí, deshacer", "Cancelar"]
    assert servicio.resumen(cliente_id).tarjetas_completadas == 1  # aún no cambia nada

    prompt = mensaje_falso()
    await pulsar(callback_falso, prompt, botones(mensaje.answer)[0][1], servicio, acciones)
    resumen = servicio.resumen(cliente_id)
    assert (resumen.citas_en_curso, resumen.tarjetas_completadas) == (9, 0)
    assert prompt.answer_photo.call_args.kwargs["caption"] == (
        f"↩️ Cita anulada. Carmen (#{cliente_id}): 9 de 9 flores. "
        "La tarjeta n.º 1 vuelve a estar en curso."
    )


async def test_cita_previa_al_bot(
    mensaje_falso: Any, servicio: Any, acciones: Any, utc: Utc
) -> None:
    servicio.crear_cliente("Rosa", 2, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/deshacer Rosa")
    await deshacer(mensaje, "Rosa", servicio, acciones)
    assert mensaje.answer.call_args.args[0].endswith("cita previa al bot")


async def test_cancelar_y_doble_toque(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmen")
    await deshacer(mensaje, "Carmen", servicio, acciones)
    si, cancelar = (data for _, data in botones(mensaje.answer))

    prompt = mensaje_falso()
    await pulsar(callback_falso, prompt, cancelar, servicio, acciones)
    assert servicio.resumen(cliente_id).tarjetas_completadas == 1
    await pulsar(callback_falso, prompt, si, servicio, acciones)  # la acción ya se tomó
    prompt.answer.assert_awaited_with(textos.ACCION_CADUCADA)
    assert servicio.resumen(cliente_id).tarjetas_completadas == 1


async def test_doble_toque_en_si_anula_una_sola_cita(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmen")
    await deshacer(mensaje, "Carmen", servicio, acciones)
    si = botones(mensaje.answer)[0][1]
    prompt = mensaje_falso()
    await pulsar(callback_falso, prompt, si, servicio, acciones)
    await pulsar(callback_falso, prompt, si, servicio, acciones)
    assert servicio.resumen(cliente_id).citas_en_curso == 9


async def test_sin_citas(mensaje_falso: Any, servicio: Any, acciones: Any, utc: Utc) -> None:
    ana = servicio.crear_cliente("Ana", 0, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/deshacer Ana")
    await deshacer(mensaje, "Ana", servicio, acciones)
    mensaje.answer.assert_awaited_once_with(f"Ana (#{ana.id}) no tiene citas que deshacer.")


async def test_parecidos_sin_crear_y_elegir_lleva_a_la_confirmacion(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmn")
    await deshacer(mensaje, "Carmn", servicio, acciones)
    etiquetas = [e for e, _ in botones(mensaje.answer)]
    assert len(etiquetas) == 2 and etiquetas[1] == "Cancelar"  # sin "Crear"

    prompt = mensaje_falso()
    await pulsar(callback_falso, prompt, botones(mensaje.answer)[0][1], servicio, acciones)
    assert prompt.answer.call_args.args[0].startswith("¿Anular la última cita de Carmen")
    prompt.answer_photo.assert_not_awaited()
    resumen = servicio.resumen(cliente_id)
    assert (resumen.citas_en_curso, resumen.tarjetas_completadas) == (0, 1)  # no registró nada


async def test_si_la_ultima_cita_cambio_no_anula_otra(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmen")
    await deshacer(mensaje, "Carmen", servicio, acciones)
    servicio.registrar_cita(cliente_id, utc("2026-11-16 16:00"))  # llega otra cita antes del toque
    prompt = mensaje_falso()
    await pulsar(callback_falso, prompt, botones(mensaje.answer)[0][1], servicio, acciones)
    assert "cambió" in prompt.answer.call_args.args[0]
    assert servicio.resumen(cliente_id).citas_en_curso == 1


async def test_sin_argumento_muestra_el_uso(
    mensaje_falso: Any, servicio: Any, acciones: Any
) -> None:
    mensaje = mensaje_falso("/deshacer")
    await deshacer(mensaje, None, servicio, acciones)
    mensaje.answer.assert_awaited_once_with(textos.uso("deshacer"))
