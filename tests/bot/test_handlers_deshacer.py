import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest

from tarjeta_lealtad.bot import handlers, textos

Utc = Callable[[str], datetime]


def carmen_con_premio(servicio: Any, utc: Utc) -> int:
    carmen = servicio.crear_cliente("Carmen", 0, utc("2026-10-31 16:00"))
    for dia in range(1, 10):
        servicio.registrar_cita(carmen.id, utc(f"2026-11-{dia:02d} 16:00"))
    servicio.registrar_cita(carmen.id, utc("2026-11-12 16:32"))  # 10.ª: premio, 10:32 local
    return int(carmen.id)


async def test_confirma_mostrando_la_cita_y_reabre_el_premio(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmen")
    await tg.comando(handlers.cmd_deshacer, mensaje, "Carmen")
    assert mensaje.reply_text.call_args.args[0] == (
        f"¿Anular la última cita de Carmen (#{cliente_id})? 12 nov 2026, 10:32 · cita de premio"
    )
    assert [e for e, _ in tg.botones(mensaje.reply_text)] == ["Sí, deshacer", "Cancelar"]
    assert servicio.resumen(cliente_id).tarjetas_completadas == 1  # aún no cambia nada

    prompt = mensaje_falso()
    await tg.pulsar(prompt, tg.botones(mensaje.reply_text)[0][1])
    resumen = servicio.resumen(cliente_id)
    assert (resumen.citas_en_curso, resumen.tarjetas_completadas) == (9, 0)
    assert prompt.reply_photo.call_args.kwargs["caption"] == (
        f"↩️ Cita anulada. Carmen (#{cliente_id}): 9 de 9 flores. "
        "La tarjeta n.º 1 vuelve a estar en curso."
    )


async def test_cita_previa_al_bot(mensaje_falso: Any, servicio: Any, tg: Any, utc: Utc) -> None:
    servicio.crear_cliente("Rosa", 2, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/deshacer Rosa")
    await tg.comando(handlers.cmd_deshacer, mensaje, "Rosa")
    assert mensaje.reply_text.call_args.args[0].endswith("cita previa al bot")


async def test_cancelar_y_doble_toque(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmen")
    await tg.comando(handlers.cmd_deshacer, mensaje, "Carmen")
    si, cancelar = (data for _, data in tg.botones(mensaje.reply_text))

    prompt = mensaje_falso()
    await tg.pulsar(prompt, cancelar)
    assert servicio.resumen(cliente_id).tarjetas_completadas == 1
    await tg.pulsar(prompt, si)  # la acción ya se tomó
    prompt.reply_text.assert_awaited_with(textos.ACCION_CADUCADA)
    assert servicio.resumen(cliente_id).tarjetas_completadas == 1


async def test_doble_toque_en_si_anula_una_sola_cita(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmen")
    await tg.comando(handlers.cmd_deshacer, mensaje, "Carmen")
    si = tg.botones(mensaje.reply_text)[0][1]
    prompt = mensaje_falso()
    await tg.pulsar(prompt, si)
    await tg.pulsar(prompt, si)
    assert servicio.resumen(cliente_id).citas_en_curso == 9


async def test_sin_citas(mensaje_falso: Any, servicio: Any, tg: Any, utc: Utc) -> None:
    ana = servicio.crear_cliente("Ana", 0, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/deshacer Ana")
    await tg.comando(handlers.cmd_deshacer, mensaje, "Ana")
    mensaje.reply_text.assert_awaited_once_with(f"Ana (#{ana.id}) no tiene citas que deshacer.")


async def test_parecidos_sin_crear_y_elegir_lleva_a_la_confirmacion(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmn")
    await tg.comando(handlers.cmd_deshacer, mensaje, "Carmn")
    etiquetas = [e for e, _ in tg.botones(mensaje.reply_text)]
    assert len(etiquetas) == 2 and etiquetas[1] == "Cancelar"  # sin "Crear"

    prompt = mensaje_falso()
    await tg.pulsar(prompt, tg.botones(mensaje.reply_text)[0][1])
    assert prompt.reply_text.call_args.args[0].startswith("¿Anular la última cita de Carmen")
    prompt.reply_photo.assert_not_awaited()
    resumen = servicio.resumen(cliente_id)
    assert (resumen.citas_en_curso, resumen.tarjetas_completadas) == (0, 1)  # no registró nada


async def test_si_la_ultima_cita_cambio_no_anula_otra(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmen")
    await tg.comando(handlers.cmd_deshacer, mensaje, "Carmen")
    servicio.registrar_cita(cliente_id, utc("2026-11-16 16:00"))  # llega otra cita antes del toque
    prompt = mensaje_falso()
    await tg.pulsar(prompt, tg.botones(mensaje.reply_text)[0][1])
    assert "cambió" in prompt.reply_text.call_args.args[0]
    assert servicio.resumen(cliente_id).citas_en_curso == 1


async def test_sin_argumento_muestra_el_uso(mensaje_falso: Any, servicio: Any, tg: Any) -> None:
    mensaje = mensaje_falso("/deshacer")
    await tg.comando(handlers.cmd_deshacer, mensaje, None)
    mensaje.reply_text.assert_awaited_once_with(textos.uso("deshacer"))


# --- Quién hizo cada acción (feature 003, FR-010) ----------------------------------------------


async def test_la_anulacion_anota_quien_la_confirmo(
    mensaje_falso: Any, servicio: Any, tg: Any, utc: Utc, caplog: pytest.LogCaptureFixture
) -> None:
    cliente_id = carmen_con_premio(servicio, utc)
    mensaje = mensaje_falso("/deshacer Carmen")
    await tg.comando(handlers.cmd_deshacer, mensaje, "Carmen")
    with caplog.at_level(logging.INFO):
        await tg.pulsar(mensaje_falso(), tg.botones(mensaje.reply_text)[0][1], de=7)
    assert f"Cita anulada: cliente={cliente_id} premio=True usuario=7" in caplog.messages
