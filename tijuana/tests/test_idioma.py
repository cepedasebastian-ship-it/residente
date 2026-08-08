from __future__ import annotations

import pytest

from tijuana.idioma import (
    compilar_patron,
    detectar_conceptos,
    detectar_idioma,
    es_agresivo,
    es_amable,
    menciona_victima,
    normalizar,
)


def test_normalizar_saca_tildes_y_baja_mayusculas():
    assert normalizar("¿QUIÉN?") == "¿quien?"
    assert normalizar("bañera") == "banera"


@pytest.mark.parametrize(
    "frase",
    [
        "¿te acuerdas de la chica?",
        "hola amigo, una cerveza por favor",
        "dime quien fue",
    ],
)
def test_detecta_espanol(frase, lexico):
    assert detectar_idioma(frase, lexico) == "es"


@pytest.mark.parametrize(
    "frase",
    [
        "do you remember the girl?",
        "who did this to me",
        "please help me, I know she was here",
    ],
)
def test_detecta_ingles(frase, lexico):
    assert detectar_idioma(frase, lexico) == "en"


def test_frase_ambigua_cae_en_espanol(lexico):
    # El bar es de él: ante la duda, asumimos que le hablaron en su idioma.
    assert detectar_idioma("marisol", lexico) == "es"


def test_conceptos_por_palabra_completa_no_por_subcadena(npc):
    # "her" está dentro de "there" y "back" dentro de "background": con
    # búsqueda por subcadena (el bug del prototipo) esto daba falsos positivos.
    assert detectar_conceptos("is there something in the background", npc) == []
    assert detectar_conceptos("her dress", npc) == ["la_chica"]


def test_conceptos_en_ambos_idiomas(npc):
    assert detectar_conceptos("¿te acuerdas de la chava?", npc) == ["la_chica"]
    assert detectar_conceptos("who did this to me", npc) == [
        "quienes_te_hicieron_esto"
    ]


def test_conceptos_multiples_en_orden_de_ficha(npc):
    conceptos = detectar_conceptos("¿qué te dijo Marisol?", npc)
    assert conceptos == ["la_chica", "que_dijo_marisol"]


def test_tono(lexico):
    assert es_amable("gracias amigo, tranquilo", lexico)
    assert not es_amable("¿dónde está?", lexico)
    assert es_agresivo("dime ya, maldito", lexico)
    assert es_agresivo("¡habla! ¡habla!", lexico)
    assert not es_agresivo("¿me ayudas?", lexico)
    assert menciona_victima("mirá la cicatriz", lexico)
    assert menciona_victima("they took my kidney", lexico)


def test_patron_vacio_nunca_matchea():
    patron = compilar_patron([])
    assert patron.search("cualquier cosa") is None
