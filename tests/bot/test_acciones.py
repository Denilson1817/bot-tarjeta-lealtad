from typing import Any

from tarjeta_lealtad.bot.acciones import (
    MAXIMO_PENDIENTES,
    Accion,
    AccionesPendientes,
    desempaquetar,
    empaquetar,
)


def test_empaquetar_y_desempaquetar() -> None:
    assert empaquetar("tok", "nuevo") == "a:tok:nuevo"
    assert desempaquetar("a:tok:nuevo") == ("tok", "nuevo")


def test_desempaquetar_rechaza_otros_formatos() -> None:
    for invalido in ("x", "a:solo", "b:t:o", "", "a::si", "a:t:"):
        assert desempaquetar(invalido) is None


def test_datos_del_boton_caben_en_64_bytes(acciones: Any) -> None:
    token = acciones.registrar(Accion(tipo="elegir", comando="tarjeta"))
    for opcion in ("nuevo", "si", "no", "123456"):
        assert len(empaquetar(token, opcion).encode()) <= 64


def test_token_corto(acciones: Any) -> None:
    token = acciones.registrar(Accion(tipo="elegir", comando="cita"))
    assert 0 < len(token) <= 16
    assert ":" not in token


def test_se_toma_una_sola_vez(acciones: Any) -> None:
    accion = Accion(tipo="crear_y_cita", comando="cita", nombre="Lucía")
    token = acciones.registrar(accion)
    assert acciones.tomar(token) == accion
    assert acciones.tomar(token) is None


def test_tokens_unicos(acciones: Any) -> None:
    tokens = {acciones.registrar(Accion(tipo="elegir", comando="cita")) for _ in range(1000)}
    assert len(tokens) == 1000


def test_descarta_la_mas_antigua_al_llenarse() -> None:
    acciones = AccionesPendientes()
    primero = acciones.registrar(Accion(tipo="elegir", comando="cita"))
    for _ in range(MAXIMO_PENDIENTES):
        acciones.registrar(Accion(tipo="elegir", comando="cita"))
    assert acciones.tomar(primero) is None
