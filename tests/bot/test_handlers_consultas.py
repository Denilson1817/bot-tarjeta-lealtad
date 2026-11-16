from collections.abc import Callable
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.filters import CommandObject

from tarjeta_lealtad.bot import handlers, textos
from tarjeta_lealtad.bot.acciones import AccionCB
from tarjeta_lealtad.render import generar_tarjeta
from tarjeta_lealtad.servicio import ResumenCliente

Utc = Callable[[str], datetime]
Botones = Callable[[AsyncMock], list[tuple[str, str]]]


async def tarjeta(mensaje: MagicMock, args: str | None, servicio: Any, acciones: Any) -> None:
    comando = CommandObject(prefix="/", command="tarjeta", args=args)
    await handlers.cmd_tarjeta(mensaje, comando, servicio=servicio, acciones=acciones)


async def test_clientes_vacio(mensaje_falso: Any, servicio: Any) -> None:
    mensaje = mensaje_falso("/clientes")
    await handlers.cmd_clientes(mensaje, servicio=servicio)
    mensaje.answer.assert_awaited_once_with(textos.SIN_CLIENTES)


async def test_clientes_en_un_mensaje(mensaje_falso: Any, servicio: Any, utc: Utc) -> None:
    servicio.crear_cliente("Rosa", 6, utc("2026-11-16 16:00"))
    servicio.crear_cliente("Carmen", 9, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/clientes")
    await handlers.cmd_clientes(mensaje, servicio=servicio)
    mensaje.answer.assert_awaited_once_with("Clientes (2):\n#2 Carmen: 9/9 🎁\n#1 Rosa: 6/9")


async def test_clientes_en_varios_mensajes(
    mensaje_falso: Any, servicio: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    muchos = tuple(
        ResumenCliente(i, f"Cliente con nombre largo {i}", 3, 0, None, False) for i in range(200)
    )
    monkeypatch.setattr(servicio, "listar", lambda: muchos)
    mensaje = mensaje_falso("/clientes")
    await handlers.cmd_clientes(mensaje, servicio=servicio)
    partes = [llamada.args[0] for llamada in mensaje.answer.call_args_list]
    assert len(partes) > 1
    assert all(len(p) <= 4000 for p in partes)
    assert sum(p.count("\n#") + p.startswith("#") for p in partes) == 200


async def test_tarjeta_no_cambia_el_conteo(
    mensaje_falso: Any, servicio: Any, acciones: Any, utc: Utc
) -> None:
    carmen = servicio.crear_cliente("Carmen", 6, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/tarjeta Carmen")
    await tarjeta(mensaje, "Carmen", servicio, acciones)
    assert mensaje.answer_photo.call_args.args[0].data == generar_tarjeta("Carmen", 6)
    assert mensaje.answer_photo.call_args.kwargs["caption"] == (
        f"🌸 Carmen (#{carmen.id}): 6 de 9 flores."
    )
    assert servicio.resumen(carmen.id).citas_en_curso == 6


async def test_tarjeta_con_parecidos_sin_crear_y_sin_registrar(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    carmen = servicio.crear_cliente("Carmen", 6, utc("2026-11-16 16:00"))
    mensaje = mensaje_falso("/tarjeta Carmn")
    await tarjeta(mensaje, "Carmn", servicio, acciones)
    assert [e for e, _ in botones(mensaje.answer)][-1] == "Cancelar"
    assert len(botones(mensaje.answer)) == 2  # sin "Crear"

    prompt = mensaje_falso()
    data = botones(mensaje.answer)[0][1]
    await handlers.al_pulsar(
        callback_falso(data, prompt), AccionCB.unpack(data), servicio=servicio, acciones=acciones
    )
    prompt.answer_photo.assert_awaited_once()
    assert servicio.resumen(carmen.id).citas_en_curso == 6


async def test_tarjeta_sin_argumento(mensaje_falso: Any, servicio: Any, acciones: Any) -> None:
    mensaje = mensaje_falso("/tarjeta")
    await tarjeta(mensaje, None, servicio, acciones)
    mensaje.answer.assert_awaited_once_with(textos.uso("tarjeta"))
