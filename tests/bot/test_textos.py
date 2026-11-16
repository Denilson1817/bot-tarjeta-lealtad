from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from tarjeta_lealtad.bot import textos
from tarjeta_lealtad.servicio import ResultadoCita, ResumenCliente


def test_fecha_corta(utc: Callable[[str], datetime], zona: ZoneInfo) -> None:
    assert textos.fecha_corta(utc("2026-11-10 18:00"), zona) == "10 nov"


def test_fecha_hora(utc: Callable[[str], datetime], zona: ZoneInfo) -> None:
    assert textos.fecha_hora(utc("2026-11-12 16:32"), zona) == "12 nov 2026, 10:32"


def test_ayuda_menciona_los_seis_comandos_con_ejemplo() -> None:
    for comando in ("cita", "alta", "deshacer", "tarjeta", "clientes", "ayuda"):
        assert f"/{comando}" in textos.AYUDA
    assert textos.AYUDA.count("Ej.:") >= 6


def resumen(**cambios: object) -> ResumenCliente:
    base: dict[str, object] = {
        "id": 3,
        "nombre": "Carmen",
        "citas_en_curso": 6,
        "tarjetas_completadas": 0,
        "ultima_cita": None,
        "proxima_es_premio": False,
    }
    return ResumenCliente(**{**base, **cambios})  # type: ignore[arg-type]


def test_pie_cita_normal() -> None:
    resultado = ResultadoCita(cliente=resumen(), es_premio=False, numero_tarjeta=None, flores=6)
    assert textos.pie_cita(resultado, 10) == (
        "🌸 Carmen (#3): 6 de 9 flores. Faltan 4 citas para la de premio (la 10.ª)."
    )


def test_etiqueta_cliente(utc: Callable[[str], datetime], zona: ZoneInfo) -> None:
    con_cita = resumen(citas_en_curso=4, ultima_cita=utc("2026-11-10 18:00"))
    assert textos.etiqueta_cliente(con_cita, zona) == "Carmen #3 · 4/9 · 10 nov"
    assert textos.etiqueta_cliente(resumen(citas_en_curso=4), zona) == "Carmen #3 · 4/9 · sin citas"


def test_confirmaciones(utc: Callable[[str], datetime], zona: ZoneInfo) -> None:
    assert (
        textos.confirmar_crear("Lucía") == "No encontré a «Lucía». ¿Crear el cliente nuevo «Lucía»?"
    )
    assert textos.confirmar_mismo_dia(resumen(), utc("2026-11-16 16:32"), zona) == (
        "Carmen (#3) ya tiene una cita hoy a las 10:32. ¿Registrar otra?"
    )


def test_pie_cita_nueve_de_nueve() -> None:
    nueve = resumen(citas_en_curso=9, proxima_es_premio=True)
    resultado = ResultadoCita(cliente=nueve, es_premio=False, numero_tarjeta=None, flores=9)
    assert textos.pie_cita(resultado, 10) == (
        "🌸 Carmen (#3): 9 de 9 flores. 🎁 ¡La próxima cita es la de premio!"
    )


def test_pie_cita_de_premio() -> None:
    cerrada = resumen(citas_en_curso=0, tarjetas_completadas=1)
    resultado = ResultadoCita(cliente=cerrada, es_premio=True, numero_tarjeta=1, flores=9)
    assert textos.pie_cita(resultado, 10) == (
        "🎁 Carmen (#3): ¡cita de premio! Tarjeta n.º 1 completada. "
        "La próxima cita empieza una tarjeta nueva."
    )


def test_lista_clientes() -> None:
    lista = (
        resumen(id=8, citas_en_curso=9, proxima_es_premio=True),
        resumen(id=3, citas_en_curso=4, tarjetas_completadas=1),
        resumen(id=15, nombre="Rosa", citas_en_curso=6, tarjetas_completadas=2),
    )
    assert textos.lista_clientes(lista) == (
        "Clientes (3):\n"
        "#8 Carmen: 9/9 🎁\n"
        "#3 Carmen: 4/9 · 1 completada\n"
        "#15 Rosa: 6/9 · 2 completadas"
    )


def test_dividir_mensajes_parte_entre_lineas_sin_perder_ninguna() -> None:
    lineas = [f"#{i} Cliente número {i}: 3/9" for i in range(300)]
    texto = "\n".join(lineas)
    partes = textos.dividir_mensajes(texto, 4000)
    assert len(partes) > 1
    assert all(len(p) <= 4000 for p in partes)
    assert "\n".join(partes).split("\n") == lineas
    assert textos.dividir_mensajes("corto", 4000) == ["corto"]


def test_sin_clientes() -> None:
    assert textos.SIN_CLIENTES == "Todavía no hay clientes. Empieza con /cita o /alta."


def test_pie_tarjeta() -> None:
    assert textos.pie_tarjeta(resumen(tarjetas_completadas=1)) == (
        "🌸 Carmen (#3): 6 de 9 flores · 1 tarjeta completada."
    )
    assert textos.pie_tarjeta(resumen()) == "🌸 Carmen (#3): 6 de 9 flores."
    assert textos.pie_tarjeta(resumen(tarjetas_completadas=2)).endswith("· 2 tarjetas completadas.")
