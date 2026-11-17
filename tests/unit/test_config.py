from pathlib import Path

import pytest
from pydantic import ValidationError

from tarjeta_lealtad.config import Ajustes, verificar_diseno

VARIABLES = (
    "BOT_TOKEN",
    "OWNER_ID",
    "ZONA_HORARIA",
    "CITAS_POR_TARJETA",
    "DB_PATH",
    "LOG_LEVEL",
    "WEBHOOK_URL",
    "WEBHOOK_SECRET",
    "IP",
    "PORT",
)
SECRETO = "s3cr3t0-de_prueba-0123456789abcdef"


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in VARIABLES:
        monkeypatch.delenv(variable, raising=False)


def definir(monkeypatch: pytest.MonkeyPatch, **valores: str) -> None:
    base = {"BOT_TOKEN": "123:abc", "OWNER_ID": "42", "ZONA_HORARIA": "America/Mexico_City"}
    for clave, valor in {**base, **valores}.items():
        monkeypatch.setenv(clave, valor)


def test_carga_correcta_y_valores_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    definir(monkeypatch)
    ajustes = Ajustes(_env_file=None)
    assert ajustes.bot_token.get_secret_value() == "123:abc"
    assert ajustes.owner_id == 42
    assert ajustes.zona_horaria == "America/Mexico_City"
    assert ajustes.citas_por_tarjeta == 10
    assert ajustes.db_path == Path("data/lealtad.db")
    assert ajustes.log_level == "INFO"


@pytest.mark.parametrize("falta", ["BOT_TOKEN", "OWNER_ID"])
def test_faltan_obligatorios(monkeypatch: pytest.MonkeyPatch, falta: str) -> None:
    definir(monkeypatch)
    monkeypatch.delenv(falta)
    with pytest.raises(ValidationError):
        Ajustes(_env_file=None)


def test_zona_horaria_mal_escrita(monkeypatch: pytest.MonkeyPatch) -> None:
    definir(monkeypatch, ZONA_HORARIA="America/Mexico_city")
    with pytest.raises(ValidationError):
        Ajustes(_env_file=None)


def test_citas_por_tarjeta_minimo(monkeypatch: pytest.MonkeyPatch) -> None:
    definir(monkeypatch, CITAS_POR_TARJETA="1")
    with pytest.raises(ValidationError):
        Ajustes(_env_file=None)


def test_diseno_coherente_con_10_citas() -> None:
    verificar_diseno(10)


def test_diseno_incoherente_con_8_citas() -> None:
    with pytest.raises(ValueError, match=r"9 casillas.*7"):
        verificar_diseno(8)


# --- Modo webhook (feature 002) ----------------------------------------------------------------


def test_sin_webhook_url_el_modo_es_polling(monkeypatch: pytest.MonkeyPatch) -> None:
    definir(monkeypatch)
    ajustes = Ajustes(_env_file=None)
    assert ajustes.modo == "polling"
    assert ajustes.webhook_url is None


def test_con_webhook_url_y_secreto_el_modo_es_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    definir(
        monkeypatch,
        WEBHOOK_URL="https://cuenta.alwaysdata.net/tarjeta/telegram",
        WEBHOOK_SECRET=SECRETO,
    )
    ajustes = Ajustes(_env_file=None)
    assert ajustes.modo == "webhook"
    assert ajustes.webhook_secret is not None
    assert ajustes.webhook_secret.get_secret_value() == SECRETO


def test_webhook_url_debe_ser_https(monkeypatch: pytest.MonkeyPatch) -> None:
    definir(monkeypatch, WEBHOOK_URL="http://cuenta.alwaysdata.net/x", WEBHOOK_SECRET=SECRETO)
    with pytest.raises(ValidationError, match="https://"):
        Ajustes(_env_file=None)


@pytest.mark.parametrize(
    "secreto",
    [None, "corto-15-caract", "con espacios no vale nada", "con/barra/0123456789"],
)
def test_secreto_obligatorio_y_con_formato(
    monkeypatch: pytest.MonkeyPatch, secreto: str | None
) -> None:
    definir(monkeypatch, WEBHOOK_URL="https://cuenta.alwaysdata.net/tarjeta/telegram")
    if secreto is not None:
        monkeypatch.setenv("WEBHOOK_SECRET", secreto)
    with pytest.raises(ValidationError, match=r"secrets\.token_urlsafe"):
        Ajustes(_env_file=None)


def test_ip_y_puerto(monkeypatch: pytest.MonkeyPatch) -> None:
    definir(monkeypatch)
    ajustes = Ajustes(_env_file=None)
    assert (ajustes.ip, ajustes.port) == ("127.0.0.1", 8000)
    monkeypatch.setenv("IP", "::1")
    monkeypatch.setenv("PORT", "8100")
    ajustes = Ajustes(_env_file=None)
    assert (ajustes.ip, ajustes.port) == ("::1", 8100)
