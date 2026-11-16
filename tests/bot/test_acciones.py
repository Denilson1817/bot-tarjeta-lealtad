from typing import Any

from tarjeta_lealtad.bot.acciones import Accion, AccionCB


def test_token_corto(acciones: Any) -> None:
    token = acciones.registrar(Accion(tipo="elegir", comando="cita"))
    assert 0 < len(token) <= 16


def test_se_toma_una_sola_vez(acciones: Any) -> None:
    accion = Accion(tipo="crear_y_cita", comando="cita", nombre="Lucía")
    token = acciones.registrar(accion)
    assert acciones.tomar(token) == accion
    assert acciones.tomar(token) is None


def test_tokens_unicos(acciones: Any) -> None:
    tokens = {acciones.registrar(Accion(tipo="elegir", comando="cita")) for _ in range(1000)}
    assert len(tokens) == 1000


def test_datos_del_boton_caben_en_64_bytes(acciones: Any) -> None:
    token = acciones.registrar(Accion(tipo="elegir", comando="tarjeta"))
    for opcion in ("nuevo", "si", "no", "123456"):
        assert len(AccionCB(token=token, opcion=opcion).pack().encode()) <= 64
