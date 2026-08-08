"""Las dos compuertas del juego.

1. **¿Te entendió?** — el cantinero habla inglés roto. Si le hablás largo y en
   inglés, se pierde. Mostrarle algo o abrir el diccionario ayuda.
2. **¿Te dice la verdad?** — miente por miedo. Cada verdad tiene su llave:
   una prueba, confianza acumulada o presión.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from .estado import Estado
from .idioma import contar_palabras, detectar_idioma
from .modelos import Lexico, Npc

ALTA = "alta"
MEDIA = "media"
BAJA = "baja"


def comprension(texto: str, npc: Npc, estado: Estado, lexico: Lexico) -> str:
    """Compuerta 1. Devuelve "alta", "media" o "baja"."""
    if detectar_idioma(texto, lexico) == npc.idioma_nativo:
        return ALTA

    mod = npc.modificadores
    nivel = npc.nivel_ingles
    if estado.mostrando:
        nivel += mod.mostrando_prueba
    if estado.diccionario:
        nivel += mod.diccionario

    palabras = contar_palabras(texto)
    if palabras > mod.umbral_frase_larga:
        nivel += mod.frase_larga
    elif palabras <= mod.umbral_frase_corta:
        nivel += mod.frase_corta

    if nivel >= mod.umbral_alta:
        return ALTA
    if nivel >= mod.umbral_media:
        return MEDIA
    return BAJA


def entendio(nivel: str) -> bool:
    """Con comprensión parcial todavía se puede avanzar; con baja, no."""
    return nivel != BAJA


def evaluar_destrabes(
    npc: Npc, estado: Estado, conceptos: Sequence[str]
) -> list[str]:
    """Compuerta 2. Qué verdades se destraban este turno, en orden de ficha."""
    destrabadas: list[str] = []
    for vid, verdad in npc.verdades.items():
        if vid in estado.sabidas:
            continue
        if verdad.requiere.se_cumple(
            conceptos=conceptos,
            confianza=estado.confianza,
            presion=estado.presion,
            sabidas=estado.sabidas,
            mostrando=estado.mostrando,
        ):
            destrabadas.append(vid)
    return destrabadas


def conceptos_trabados(
    npc: Npc, estado: Estado, conceptos: Iterable[str]
) -> list[str]:
    """Conceptos sobre los que el NPC todavía tiene una mentira en pie."""
    trabados = []
    for concepto in conceptos:
        mentira = npc.mentira_de(concepto)
        if mentira and mentira.verdad not in estado.sabidas:
            trabados.append(concepto)
    return trabados


def pistas_pendientes(npc: Npc, estado: Estado) -> list[str]:
    """Qué le falta al jugador para cada verdad. Solo para el panel de debug."""
    return [
        f"{vid}: {verdad.requiere.describir()}"
        for vid, verdad in npc.verdades.items()
        if vid not in estado.sabidas
    ]
