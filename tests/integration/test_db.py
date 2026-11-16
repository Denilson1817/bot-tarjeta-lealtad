from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from tarjeta_lealtad import db
from tarjeta_lealtad.db import Cita, Cliente, UTCDateTime

AHORA = datetime(2026, 11, 16, 16, 32, tzinfo=UTC)


def nuevo_cliente(sesion: Any, nombre: str = "Carmen") -> Cliente:
    cliente = Cliente(nombre=nombre, nombre_normalizado=nombre.lower(), creado_en=AHORA)
    sesion.add(cliente)
    sesion.flush()
    return cliente


def test_se_crean_las_tablas(tmp_path: Path) -> None:
    motor = db.crear_motor(tmp_path / "sub" / "t.db")
    db.inicializar(motor)
    assert set(inspect(motor).get_table_names()) == {"clientes", "citas"}
    motor.dispose()


def test_fecha_utc_ida_y_vuelta(sesiones: Any) -> None:
    with sesiones.begin() as s:
        cliente_id = nuevo_cliente(s).id
    with sesiones() as s:
        cliente = s.get(Cliente, cliente_id)
        assert cliente.creado_en == AHORA
        assert cliente.creado_en.tzinfo is not None


def test_fecha_sin_zona_se_rechaza() -> None:
    with pytest.raises(ValueError):
        UTCDateTime().process_bind_param(datetime(2026, 11, 16, 10, 32), dialect=None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("origen", "registrada_en"),
    [("bot", None), ("previa", AHORA), ("otra", AHORA)],
)
def test_restricciones_de_cita(sesiones: Any, origen: str, registrada_en: datetime | None) -> None:
    with pytest.raises(IntegrityError), sesiones.begin() as s:
        cliente = nuevo_cliente(s)
        s.add(
            Cita(cliente_id=cliente.id, origen=origen, registrada_en=registrada_en, creada_en=AHORA)
        )
        s.flush()


def test_ids_no_se_reutilizan(sesiones: Any) -> None:
    with sesiones.begin() as s:
        ultimo = nuevo_cliente(s, "Ana")
        ultimo_id = ultimo.id
        s.delete(ultimo)
    with sesiones.begin() as s:
        assert nuevo_cliente(s, "Eva").id > ultimo_id


def test_los_datos_sobreviven_a_un_reinicio(tmp_path: Path, utc: Callable[[str], datetime]) -> None:
    ruta = tmp_path / "t.db"
    motor = db.crear_motor(ruta)
    db.inicializar(motor)
    with db.crear_sesiones(motor).begin() as s:
        cliente = nuevo_cliente(s)
        s.add(Cita(cliente_id=cliente.id, origen="bot", registrada_en=AHORA, creada_en=AHORA))
        s.add(
            Cita(
                cliente_id=cliente.id,
                origen="bot",
                registrada_en=AHORA,
                anulada_en=utc("2026-11-17 10:00"),
                creada_en=AHORA,
            )
        )
    motor.dispose()

    otro = db.crear_motor(ruta)
    db.inicializar(otro)
    with db.crear_sesiones(otro)() as s:
        assert s.scalars(select(Cliente.nombre)).all() == ["Carmen"]
        citas = s.scalars(select(Cita).order_by(Cita.id)).all()
        assert [c.anulada_en for c in citas] == [None, utc("2026-11-17 10:00")]
    otro.dispose()
