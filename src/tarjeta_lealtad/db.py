"""Persistencia en SQLite: clientes y citas (data-model.md).

Las tarjetas no se guardan: se derivan de las citas (principio IV).
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Dialect,
    Engine,
    ForeignKey,
    String,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Guarda UTC sin zona (SQLite no la conserva) y devuelve UTC con zona.

    Rechaza fechas sin zona para que un error de zona horaria no pase inadvertido.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"fecha sin zona horaria: {value!r}")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = ({"sqlite_autoincrement": True},)  # los IDs nunca se reutilizan (FR-003)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))
    nombre_normalizado: Mapped[str] = mapped_column(String(60), index=True)
    creado_en: Mapped[datetime] = mapped_column(UTCDateTime())


class Cita(Base):
    __tablename__ = "citas"
    __table_args__ = (
        CheckConstraint("origen IN ('bot', 'previa')", name="origen_valido"),
        CheckConstraint("(origen = 'previa') = (registrada_en IS NULL)", name="fecha_segun_origen"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    origen: Mapped[str] = mapped_column(String(6))
    registrada_en: Mapped[datetime | None] = mapped_column(UTCDateTime())
    es_premio: Mapped[bool] = mapped_column(default=False)
    anulada_en: Mapped[datetime | None] = mapped_column(UTCDateTime())
    creada_en: Mapped[datetime] = mapped_column(UTCDateTime())


def crear_motor(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    motor = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(motor, "connect")
    def _activar_claves_foraneas(conexion: Any, _registro: Any) -> None:
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return motor


def inicializar(motor: Engine) -> None:
    Base.metadata.create_all(motor)


def crear_sesiones(motor: Engine) -> sessionmaker[Session]:
    return sessionmaker(motor, expire_on_commit=False)
