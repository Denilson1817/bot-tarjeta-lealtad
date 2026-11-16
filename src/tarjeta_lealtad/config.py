"""Configuración del bot: variables de entorno y `.env` (principio V)."""

from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tarjeta_lealtad import diseno


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr
    owner_id: int
    zona_horaria: str
    citas_por_tarjeta: int = Field(default=10, ge=2)
    db_path: Path = Path("data/lealtad.db")
    log_level: str = "INFO"

    @field_validator("zona_horaria")
    @classmethod
    def _zona_existente(cls, valor: str) -> str:
        try:
            ZoneInfo(valor)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"zona horaria desconocida: {valor!r}") from error
        return valor

    @property
    def zona(self) -> ZoneInfo:
        return ZoneInfo(self.zona_horaria)


def verificar_diseno(citas_por_tarjeta: int) -> None:
    """La plantilla debe tener una casilla por cada cita excepto la de premio (FR-017)."""
    esperadas = citas_por_tarjeta - 1
    if esperadas != diseno.CASILLAS:
        raise ValueError(
            f"La plantilla tiene {diseno.CASILLAS} casillas, pero con CITAS_POR_TARJETA="
            f"{citas_por_tarjeta} se esperaban {esperadas}."
        )
