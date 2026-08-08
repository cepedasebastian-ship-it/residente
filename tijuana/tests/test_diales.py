from __future__ import annotations

from tijuana.diales import actualizar_diales
from tijuana.estado import UMBRAL_PELIGRO, Estado


def _estado(contenido) -> Estado:
    return Estado.desde_caso(contenido.caso)


def test_hablarle_en_su_idioma_suma_confianza(contenido, npc, lexico):
    estado = _estado(contenido)
    actualizar_diales(estado, "hola, ¿me ayudas?", npc, lexico, [])
    assert estado.confianza >= 1
    assert "idioma_nativo" in estado.fuentes_usadas


def test_cada_fuente_suma_una_sola_vez(contenido, npc, lexico):
    estado = _estado(contenido)
    for _ in range(5):
        actualizar_diales(estado, "mirá la cicatriz que tengo", npc, lexico, [])
    # cicatriz(victima) + hablar español = 2. Repetir la frase no farmea más.
    assert estado.confianza == 2


def test_mostrar_pruebas_distintas_suma_distinto(contenido, npc, lexico):
    estado = _estado(contenido)
    estado.fuentes_usadas.add("idioma_nativo")  # aislamos el efecto de las pruebas
    for prueba in ("pulsera", "cicatriz", "pulsera"):
        estado.mostrando = prueba
        actualizar_diales(estado, "mira esto", npc, lexico, [])
    assert estado.confianza == 2


def test_el_aro_no_da_confianza_es_una_llave(contenido, npc, lexico):
    estado = _estado(contenido)
    estado.fuentes_usadas.add("idioma_nativo")
    estado.mostrando = "aro"
    actualizar_diales(estado, "mira esto", npc, lexico, [])
    assert estado.confianza == 0


def test_la_agresion_sube_la_presion_hasta_el_peligro(contenido, npc, lexico):
    estado = _estado(contenido)
    for _ in range(UMBRAL_PELIGRO):
        actualizar_diales(estado, "dime ya, maldito", npc, lexico, [])
    assert estado.peligro


def test_insistir_sobre_algo_trabado_presiona(contenido, npc, lexico):
    estado = _estado(contenido)
    estado.ultimo_concepto = "la_chica"
    actualizar_diales(estado, "¿y la chica?", npc, lexico, ["la_chica"])
    assert estado.presion == 1


def test_insistir_sobre_algo_ya_revelado_no_presiona(contenido, npc, lexico):
    estado = _estado(contenido)
    estado.ultimo_concepto = "la_chica"
    estado.sabidas.add("marisol_estaba_asustada")
    actualizar_diales(estado, "¿y la chica?", npc, lexico, ["la_chica"])
    assert estado.presion == 0


def test_aflojar_baja_la_presion(contenido, npc, lexico):
    estado = _estado(contenido)
    estado.presion = 3
    assert estado.peligro
    actualizar_diales(estado, "tranquilo amigo, te invito un trago", npc, lexico, [])
    assert estado.presion == 2
    assert not estado.peligro


def test_una_frase_agresiva_y_amable_a_la_vez_no_baja_la_presion(
    contenido, npc, lexico
):
    estado = _estado(contenido)
    estado.presion = 2
    actualizar_diales(estado, "gracias, pero dime ya, maldito", npc, lexico, [])
    assert estado.presion == 3
