from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest

from tarjeta_lealtad.bot import handlers, textos
from tarjeta_lealtad.render import generar_tarjeta
from tarjeta_lealtad.servicio import ResumenCliente

Utc = Callable[[str], datetime]


async def test_clientes_vacio(mensaje_falso: Any, servicio: Any, tg: Any) -> None:
    mensaje = mensaje_falso("/clientes")
    await tg.comando(handlers.cmd_clientes, mensaje)
    mensaje.reply_text.assert_awaited_once_with(textos.SIN_CLIENTES)


async def test_clientes_en_un_mensaje(mensaje_falso: Any, servicio: Any, utc: Utc, tg: Any) -> None:
    servicio.crear_cliente("Rosa", 6, utc("2026-11-16 16:00"))
    servicio.crear_cliente("Carmen", 9, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/clientes")
    await tg.comando(handlers.cmd_clientes, mensaje)
    mensaje.reply_text.assert_awaited_once_with("Clientes (2):\n#2 Carmen: 9/9 🎁\n#1 Rosa: 6/9")


async def test_clientes_en_varios_mensajes(
    mensaje_falso: Any, servicio: Any, monkeypatch: pytest.MonkeyPatch, tg: Any
) -> None:
    muchos = tuple(
        ResumenCliente(i, f"Cliente con nombre largo {i}", 3, 0, None, False) for i in range(200)
    )
    monkeypatch.setattr(servicio, "listar", lambda: muchos)
    mensaje = mensaje_falso("/clientes")
    await tg.comando(handlers.cmd_clientes, mensaje)
    partes = [llamada.args[0] for llamada in mensaje.reply_text.call_args_list]
    assert len(partes) > 1
    assert all(len(p) <= 4000 for p in partes)
    assert sum(p.count("\n#") + p.startswith("#") for p in partes) == 200


async def test_tarjeta_no_cambia_el_conteo(
    mensaje_falso: Any, servicio: Any, tg: Any, utc: Utc
) -> None:
    carmen = servicio.crear_cliente("Carmen", 6, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/tarjeta Carmen")
    await tg.comando(handlers.cmd_tarjeta, mensaje, "Carmen")
    assert mensaje.reply_photo.call_args.kwargs["photo"] == generar_tarjeta("Carmen", 6)
    assert mensaje.reply_photo.call_args.kwargs["caption"] == (
        f"🌸 Carmen (#{carmen.id}): 6 de 9 flores."
    )
    assert servicio.resumen(carmen.id).citas_en_curso == 6


async def test_tarjeta_con_parecidos_sin_crear_y_sin_registrar(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    carmen = servicio.crear_cliente("Carmen", 6, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/tarjeta Carmn")
    await tg.comando(handlers.cmd_tarjeta, mensaje, "Carmn")
    assert [e for e, _ in tg.botones(mensaje.reply_text)][-1] == "Cancelar"
    assert len(tg.botones(mensaje.reply_text)) == 2  # sin "Crear"

    prompt = mensaje_falso()
    data = tg.botones(mensaje.reply_text)[0][1]
    await tg.pulsar(prompt, data)
    prompt.reply_photo.assert_awaited_once()
    assert servicio.resumen(carmen.id).citas_en_curso == 6


async def test_tarjeta_sin_argumento(mensaje_falso: Any, servicio: Any, tg: Any) -> None:
    mensaje = mensaje_falso("/tarjeta")
    await tg.comando(handlers.cmd_tarjeta, mensaje, None)
    mensaje.reply_text.assert_awaited_once_with(textos.uso("tarjeta"))
