from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest

from tarjeta_lealtad.bot import handlers, textos
from tarjeta_lealtad.render import generar_tarjeta
from tarjeta_lealtad.servicio import Encontrado

Utc = Callable[[str], datetime]


def test_separar_alta() -> None:
    assert handlers.separar_alta("Rosa 6") == ("Rosa", 6)
    assert handlers.separar_alta("María Fernanda Ruiz") == ("María Fernanda Ruiz", 0)
    assert handlers.separar_alta("Rosa -1") == ("Rosa", -1)
    for sin_nombre in ("6", "", "   "):
        with pytest.raises(ValueError):
            handlers.separar_alta(sin_nombre)


async def test_alta_con_previas_envia_la_tarjeta(
    mensaje_falso: Any, servicio: Any, tg: Any
) -> None:
    mensaje = mensaje_falso("/alta Rosa 6")
    await tg.comando(handlers.cmd_alta, mensaje, "Rosa 6")
    rosa = servicio.buscar("rosa")
    assert isinstance(rosa, Encontrado)
    assert rosa.cliente.citas_en_curso == 6
    assert mensaje.reply_photo.call_args.kwargs["photo"] == generar_tarjeta("Rosa", 6)
    assert mensaje.reply_photo.call_args.kwargs["caption"] == (
        f"✅ Cliente nuevo: Rosa (#{rosa.cliente.id}) con 6 citas previas. "
        "Revisa que la tarjeta coincida con la que tenía."
    )


async def test_alta_sin_previas(mensaje_falso: Any, servicio: Any, tg: Any) -> None:
    mensaje = mensaje_falso("/alta Ana")
    await tg.comando(handlers.cmd_alta, mensaje, "Ana")
    caption = mensaje.reply_photo.call_args.kwargs["caption"]
    assert caption.startswith("✅ Cliente nuevo: Ana (#") and "sin citas previas" in caption


async def test_alta_de_homonimo_pide_confirmacion(
    mensaje_falso: Any,
    servicio: Any,
    tg: Any,
    utc: Utc,
) -> None:
    rosa = servicio.crear_cliente("Rosa", 0, utc("2026-11-16 15:00"))
    mensaje = mensaje_falso("/alta Rosa 2")
    await tg.comando(handlers.cmd_alta, mensaje, "Rosa 2")
    mensaje.reply_photo.assert_not_awaited()
    assert mensaje.reply_text.call_args.args[0] == (
        f"Ya existe Rosa (#{rosa.id}). ¿Crear otro cliente con el mismo nombre?"
    )
    assert [e for e, _ in tg.botones(mensaje.reply_text)] == ["Crear otro", "Cancelar"]

    prompt = mensaje_falso()
    data = tg.botones(mensaje.reply_text)[0][1]
    await tg.pulsar(prompt, data)
    rosas = servicio.homonimos("rosa")
    assert len(rosas) == 2
    assert rosas[1].citas_en_curso == 2
    prompt.reply_photo.assert_awaited_once()


async def test_alta_fuera_de_rango(mensaje_falso: Any, servicio: Any, tg: Any) -> None:
    mensaje = mensaje_falso("/alta Rosa 10")
    await tg.comando(handlers.cmd_alta, mensaje, "Rosa 10")
    mensaje.reply_text.assert_awaited_once_with("Las citas previas deben estar entre 0 y 9.")


async def test_alta_con_nombre_invalido(mensaje_falso: Any, servicio: Any, tg: Any) -> None:
    mensaje = mensaje_falso("/alta Ana 😀")
    await tg.comando(handlers.cmd_alta, mensaje, "Ana 😀")
    assert "😀" in mensaje.reply_text.call_args.args[0]
    mensaje.reply_photo.assert_not_awaited()


@pytest.mark.parametrize("args", [None, "6"])
async def test_alta_sin_nombre_muestra_el_uso(
    mensaje_falso: Any, servicio: Any, tg: Any, args: str | None
) -> None:
    mensaje = mensaje_falso("/alta")
    await tg.comando(handlers.cmd_alta, mensaje, args)
    mensaje.reply_text.assert_awaited_once_with(textos.uso("alta"))
