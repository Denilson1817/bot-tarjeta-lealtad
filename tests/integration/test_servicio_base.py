from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from typing import Any

import pytest
from PIL import Image

from tarjeta_lealtad.db import Cita, Cliente
from tarjeta_lealtad.servicio import ClienteInexistente


def preparar_carmen(sesiones: Any, utc: Callable[[str], datetime]) -> int:
    """Carmen: tarjeta 1 completada (10 citas, la 10.ª de premio), 1 cita en curso y 1 anulada."""
    with sesiones.begin() as s:
        cliente = Cliente(
            nombre="Carmen", nombre_normalizado="carmen", creado_en=utc("2026-11-01 15:00")
        )
        s.add(cliente)
        s.flush()
        for dia in range(1, 12):
            s.add(
                Cita(
                    cliente_id=cliente.id,
                    origen="bot",
                    registrada_en=utc(f"2026-11-{dia:02d} 16:00"),
                    es_premio=dia == 10,
                    creada_en=utc(f"2026-11-{dia:02d} 16:00"),
                )
            )
        s.add(
            Cita(
                cliente_id=cliente.id,
                origen="bot",
                registrada_en=utc("2026-11-12 16:00"),
                anulada_en=utc("2026-11-12 16:05"),
                creada_en=utc("2026-11-12 16:00"),
            )
        )
        return cliente.id


def test_resumen_ignora_anuladas(
    servicio: Any, sesiones: Any, utc: Callable[[str], datetime]
) -> None:
    cliente_id = preparar_carmen(sesiones, utc)
    resumen = servicio.resumen(cliente_id)
    assert resumen.id == cliente_id
    assert resumen.nombre == "Carmen"
    assert resumen.citas_en_curso == 1
    assert resumen.tarjetas_completadas == 1
    assert resumen.ultima_cita == utc("2026-11-11 16:00")
    assert resumen.proxima_es_premio is False


def test_tarjeta_png(servicio: Any, sesiones: Any, utc: Callable[[str], datetime]) -> None:
    cliente_id = preparar_carmen(sesiones, utc)
    img = Image.open(BytesIO(servicio.tarjeta_png(cliente_id)))
    assert img.format == "PNG"


def test_cliente_inexistente(servicio: Any) -> None:
    with pytest.raises(ClienteInexistente):
        servicio.resumen(999)
    with pytest.raises(ClienteInexistente):
        servicio.tarjeta_png(999)
