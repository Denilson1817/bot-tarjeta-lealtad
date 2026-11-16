from tarjeta_lealtad.busqueda import (
    caracteres_no_admitidos,
    distancia,
    limpiar_nombre,
    normalizar,
    parecido,
)


def test_normalizar() -> None:
    assert normalizar(" Cármen  LÓPEZ ") == "carmen lopez"


def test_limpiar_nombre_conserva_mayusculas_y_acentos() -> None:
    assert limpiar_nombre("  María   Fernanda ") == "María Fernanda"


def test_limpiar_nombre_unifica_el_apostrofo_del_iphone() -> None:
    assert limpiar_nombre("O\u2019Neil") == "O'Neil"


def test_caracteres_no_admitidos() -> None:
    assert caracteres_no_admitidos("Ana 😀") == ["😀"]
    assert caracteres_no_admitidos("Ana7") == ["7"]
    assert caracteres_no_admitidos("Zoë O'Neil-Peña Jr.") == []
    assert caracteres_no_admitidos("Ana × Eva") == ["×"]


def test_distancia() -> None:
    assert distancia("carmen", "carmn") == 1
    assert distancia("ab", "ba") == 1  # intercambio de dos letras
    assert distancia("ana", "eva") == 2
    assert distancia("", "abc") == 3


def test_parecido() -> None:
    assert parecido("carmn", "carmen") is not None
    assert parecido("mar", "maria lopez") is not None  # prefijo de palabra
    assert parecido("maxim", "maximiliana montoya") is not None  # prefijo, lejos en distancia
    assert parecido("lucia", "carmen") is None


def test_parecido_menor_distancia_primero() -> None:
    errata = parecido("carmn", "carmen")
    prefijo = parecido("maxim", "maximiliana montoya")
    assert errata is not None and prefijo is not None
    assert errata < prefijo


def test_interpretar_id() -> None:
    from tarjeta_lealtad.busqueda import interpretar_id

    assert interpretar_id("#12") == 12
    assert interpretar_id("12") == 12
    assert interpretar_id(" #7 ") == 7
    for no_es_id in ("12a", "#", "Carmen", "", "#-3", "\uff11\uff12"):  # ancho completo
        assert interpretar_id(no_es_id) is None
