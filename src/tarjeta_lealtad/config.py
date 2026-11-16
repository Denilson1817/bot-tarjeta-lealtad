"""Configuración del bot: variables de entorno y `.env` (principio V)."""

import re
from pathlib import Path
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tarjeta_lealtad import diseno

# Lo que Telegram acepta como secret_token del webhook.
_SECRETO_VALIDO = re.compile(r"[A-Za-z0-9_-]{16,256}")
_COMO_GENERAR = 'python -c "import secrets; print(secrets.token_urlsafe(32))"'


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr
    owner_id: int
    zona_horaria: str
    citas_por_tarjeta: int = Field(default=10, ge=2)
    db_path: Path = Path("data/lealtad.db")
    log_level: str = "INFO"
    # Modo webhook (producción en alwaysdata): sin WEBHOOK_URL el bot usa polling.
    webhook_url: str | None = None
    webhook_secret: SecretStr | None = None
    ip: str = "127.0.0.1"  # alwaysdata los entrega en IP y PORT
    port: int = 8000

    @field_validator("zona_horaria")
    @classmethod
    def _zona_existente(cls, valor: str) -> str:
        try:
            ZoneInfo(valor)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"zona horaria desconocida: {valor!r}") from error
        return valor

    @model_validator(mode="after")
    def _webhook_completo(self) -> Self:
        if self.webhook_url is None:
            return self
        if not self.webhook_url.startswith("https://"):
            raise ValueError("WEBHOOK_URL debe empezar con https:// (Telegram lo exige).")
        secreto = self.webhook_secret.get_secret_value() if self.webhook_secret else ""
        if not _SECRETO_VALIDO.fullmatch(secreto):
            raise ValueError(
                "WEBHOOK_SECRET es obligatorio en modo webhook: de 16 a 256 caracteres, solo "
                f'letras, dígitos, "_" y "-". Genera uno con: {_COMO_GENERAR}'
            )
        return self

    @property
    def zona(self) -> ZoneInfo:
        return ZoneInfo(self.zona_horaria)

    @property
    def modo(self) -> Literal["polling", "webhook"]:
        return "webhook" if self.webhook_url else "polling"


def verificar_diseno(citas_por_tarjeta: int) -> None:
    """La plantilla debe tener una casilla por cada cita excepto la de premio (FR-017)."""
    esperadas = citas_por_tarjeta - 1
    if esperadas != diseno.CASILLAS:
        raise ValueError(
            f"La plantilla tiene {diseno.CASILLAS} casillas, pero con CITAS_POR_TARJETA="
            f"{citas_por_tarjeta} se esperaban {esperadas}."
        )
