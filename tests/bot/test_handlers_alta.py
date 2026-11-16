from collections.abc import Callable
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.filters import CommandObject

from tarjeta_lealtad.bot import handlers, textos
from tarjeta_lealtad.bot.acciones import AccionCB
from tarjeta_lealtad.render import generar_tarjeta
from tarjeta_lealtad.servicio import Encontrado

Utc = Callable[[str], datetime]
Botones = Callable[[AsyncMock], list[tuple[str, str]]]


async def alta(mensaje: MagicMock, args: str | None, servicio: Any, acciones: Any) -> None:
    comando = CommandObject(prefix="/", command="alta", args=args)
    await handlers.cmd_alta(mensaje, comando, servicio=servicio, acciones=acciones)


def test_separar_alta() -> None:
    assert handlers.separar_alta("Rosa 6") == ("Rosa", 6)
    assert handlers.separar_alta("María Fernanda Ruiz") == ("María Fernanda Ruiz", 0)
    assert handlers.separar_alta("Rosa -1") == ("Rosa", -1)
    for sin_nombre in ("6", "", "   "):
        with pytest.raises(ValueError):
            handlers.separar_alta(sin_nombre)


async def test_alta_con_previas_envia_la_tarjeta(
    mensaje_falso: Any, servicio: Any, acciones: Any
) -> None:
    mensaje = mensaje_falso("/alta Rosa 6")
    await alta(mensaje, "Rosa 6", servicio, acciones)
    rosa = servicio.buscar("rosa")
    assert isinstance(rosa, Encontrado)
    assert rosa.cliente.citas_en_curso == 6
    assert mensaje.answer_photo.call_args.args[0].data == generar_tarjeta("Rosa", 6)
    assert mensaje.answer_photo.call_args.kwargs["caption"] == (
        f"✅ Cliente nuevo: Rosa (#{rosa.cliente.id}) con 6 citas previas. "
        "Revisa que la tarjeta coincida con la que tenía."
    )


async def test_alta_sin_previas(mensaje_falso: Any, servicio: Any, acciones: Any) -> None:
    mensaje = mensaje_falso("/alta Ana")
    await alta(mensaje, "Ana", servicio, acciones)
    caption = mensaje.answer_photo.call_args.kwargs["caption"]
    assert caption.startswith("✅ Cliente nuevo: Ana (#") and "sin citas previas" in caption


async def test_alta_de_homonimo_pide_confirmacion(
    mensaje_falso: Any,
    callback_falso: Any,
    botones: Botones,
    servicio: Any,
    acciones: Any,
    utc: Utc,
) -> None:
    rosa = servicio.crear_cliente("Rosa", 0, utc("2026-11-16 15:00"))
    mensaje = mensaje_falso("/alta Rosa 2")
    await alta(mensaje, "Rosa 2", servicio, acciones)
    mensaje.answer_photo.assert_not_awaited()
    assert mensaje.answer.call_args.args[0] == (
        f"Ya existe Rosa (#{rosa.id}). ¿Crear otro cliente con el mismo nombre?"
    )
    assert [e for e, _ in botones(mensaje.answer)] == ["Crear otro", "Cancelar"]

    prompt = mensaje_falso()
    data = botones(mensaje.answer)[0][1]
    await handlers.al_pulsar(
        callback_falso(data, prompt), AccionCB.unpack(data), servicio=servicio, acciones=acciones
    )
    rosas = servicio.homonimos("rosa")
    assert len(rosas) == 2
    assert rosas[1].citas_en_curso == 2
    prompt.answer_photo.assert_awaited_once()


async def test_alta_fuera_de_rango(mensaje_falso: Any, servicio: Any, acciones: Any) -> None:
    mensaje = mensaje_falso("/alta Rosa 10")
    await alta(mensaje, "Rosa 10", servicio, acciones)
    mensaje.answer.assert_awaited_once_with("Las citas previas deben estar entre 0 y 9.")


async def test_alta_con_nombre_invalido(mensaje_falso: Any, servicio: Any, acciones: Any) -> None:
    mensaje = mensaje_falso("/alta Ana 😀")
    await alta(mensaje, "Ana 😀", servicio, acciones)
    assert "😀" in mensaje.answer.call_args.args[0]
    mensaje.answer_photo.assert_not_awaited()


@pytest.mark.parametrize("args", [None, "6"])
async def test_alta_sin_nombre_muestra_el_uso(
    mensaje_falso: Any, servicio: Any, acciones: Any, args: str | None
) -> None:
    mensaje = mensaje_falso("/alta")
    await alta(mensaje, args, servicio, acciones)
    mensaje.answer.assert_awaited_once_with(textos.uso("alta"))
