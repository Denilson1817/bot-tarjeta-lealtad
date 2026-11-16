"""Principio II: el dominio no depende de Telegram ni del servidor web."""

import ast
from pathlib import Path

import tarjeta_lealtad

PAQUETE = Path(tarjeta_lealtad.__file__).parent


def modulos_importados(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
    return nombres


PROHIBIDOS = {"aiogram", "telegram", "starlette", "uvicorn"}


def test_el_dominio_no_importa_librerias_de_telegram_ni_web() -> None:
    dominio = [p for p in PAQUETE.rglob("*.py") if "bot" not in p.relative_to(PAQUETE).parts]
    assert dominio, "no se encontraron módulos de dominio"
    infractores = {
        str(p.relative_to(PAQUETE)): sorted(
            m for m in modulos_importados(p) if m.split(".")[0] in PROHIBIDOS
        )
        for p in dominio
    }
    assert {k: v for k, v in infractores.items() if v} == {}
