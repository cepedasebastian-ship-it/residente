"""Compuerta 1 (¿te entendió?) y compuerta 2 (¿te dice la verdad?)."""

from __future__ import annotations

from tijuana.compuertas import ALTA, BAJA, MEDIA, comprension, evaluar_destrabes
from tijuana.estado import Estado

LARGA_EN = (
    "do you remember this girl who was here last night with the red dress "
    "and the black bag please"
)


def _estado(contenido, **kwargs) -> Estado:
    estado = Estado.desde_caso(contenido.caso)
    for clave, valor in kwargs.items():
        setattr(estado, clave, valor)
    return estado


# --- compuerta 1 -----------------------------------------------------------
def test_su_idioma_siempre_se_entiende(contenido, npc, lexico):
    estado = _estado(contenido)
    largo = "necesito que me digas todo lo que viste anoche en este bar por favor amigo"
    assert comprension(largo, npc, estado, lexico) == ALTA


def test_ingles_largo_no_se_entiende(contenido, npc, lexico):
    estado = _estado(contenido)
    assert comprension(LARGA_EN, npc, estado, lexico) == BAJA


def test_ingles_corto_se_entiende_a_medias(contenido, npc, lexico):
    estado = _estado(contenido)
    assert comprension("remember this girl?", npc, estado, lexico) == MEDIA


def test_mostrar_algo_desbloquea_el_ingles_corto(contenido, npc, lexico):
    estado = _estado(contenido, mostrando="aro")
    assert comprension("remember this girl?", npc, estado, lexico) == ALTA


def test_el_diccionario_tambien_ayuda(contenido, npc, lexico):
    estado = _estado(contenido, diccionario=True)
    assert comprension("remember this girl?", npc, estado, lexico) == ALTA


def test_mostrar_algo_no_alcanza_si_la_frase_es_larga(contenido, npc, lexico):
    estado = _estado(contenido, mostrando="aro")
    assert comprension(LARGA_EN, npc, estado, lexico) == BAJA


# --- compuerta 2 -----------------------------------------------------------
def test_sin_llave_no_se_destraba_nada(contenido, npc):
    estado = _estado(contenido)
    assert evaluar_destrabes(npc, estado, ["la_chica"]) == []


def test_la_prueba_correcta_destraba(contenido, npc):
    estado = _estado(contenido, mostrando="aro")
    assert evaluar_destrabes(npc, estado, ["la_chica"]) == ["marisol_estaba_asustada"]


def test_la_prueba_equivocada_no_destraba(contenido, npc):
    estado = _estado(contenido, mostrando="pulsera")
    assert evaluar_destrabes(npc, estado, ["la_chica"]) == []


def test_la_presion_es_una_llave_alternativa(contenido, npc):
    estado = _estado(contenido, presion=2)
    assert evaluar_destrabes(npc, estado, ["la_chica"]) == ["marisol_estaba_asustada"]


def test_el_concepto_equivocado_no_destraba(contenido, npc):
    estado = _estado(contenido, mostrando="aro", confianza=5)
    assert evaluar_destrabes(npc, estado, ["que_dijo_marisol"]) == []


def test_una_verdad_puede_exigir_otra_previa(contenido, npc):
    estado = _estado(contenido, confianza=5)
    # Sin saber lo de la clínica, la puerta del fondo no aparece.
    assert evaluar_destrabes(npc, estado, ["a_donde_te_llevaron"]) == []
    estado.sabidas.add("vino_gente_de_la_clinica")
    assert evaluar_destrabes(npc, estado, ["a_donde_te_llevaron"]) == [
        "hay_una_puerta_atras"
    ]


def test_lo_ya_sabido_no_se_vuelve_a_destrabar(contenido, npc):
    estado = _estado(contenido, mostrando="aro")
    estado.sabidas.add("marisol_estaba_asustada")
    assert evaluar_destrabes(npc, estado, ["la_chica"]) == []
