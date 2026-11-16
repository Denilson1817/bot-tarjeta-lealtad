from collections.abc import Callable
from datetime import datetime
from typing import Any

from tarjeta_lealtad.servicio import Encontrado, IdInexistente, Varios

Utc = Callable[[str], datetime]


def test_varias_coincidencias_exactas(servicio: Any, utc: Utc) -> None:
    primera = servicio.crear_cliente("María", 0, utc("2026-11-16 15:00"))
    segunda = servicio.crear_cliente("Maria", 0, utc("2026-11-16 15:05"))
    resultado = servicio.buscar("maría")
    assert isinstance(resultado, Varios)
    assert [o.id for o in resultado.opciones] == [primera.id, segunda.id]


def test_buscar_por_id(servicio: Any, utc: Utc) -> None:
    servicio.crear_cliente("María", 0, utc("2026-11-16 15:00"))
    segunda = servicio.crear_cliente("María", 0, utc("2026-11-16 15:05"))
    for texto in (f"#{segunda.id}", str(segunda.id)):
        resultado = servicio.buscar(texto)
        assert isinstance(resultado, Encontrado)
        assert resultado.cliente.id == segunda.id


def test_id_inexistente(servicio: Any) -> None:
    assert servicio.buscar("#999") == IdInexistente(999)
