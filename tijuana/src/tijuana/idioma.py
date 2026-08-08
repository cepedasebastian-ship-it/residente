"""Detección: idioma, conceptos y tono.

Todo lo de acá trabaja sobre texto *normalizado* (minúsculas, sin tildes) y
compara con **límite de palabra**. Eso último importa: buscar la subcadena
"her" encuentra "there", y buscar "back" encuentra "background". Con `\\b` no.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Sequence

from .modelos import Idioma, Lexico, Npc

# Caracteres que solo aparecen escribiendo en español y valen como pista fuerte.
_PISTAS_ES = re.compile(r"[¿¡ñáéíóúü]", re.IGNORECASE)
_PESO_PISTA_ES = 2


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para poder comparar 'quién' con 'quien'."""
    texto = texto.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def compilar_patron(palabras: Iterable[str]) -> re.Pattern[str]:
    """Un patrón que matchea cualquiera de las palabras/frases con `\\b`."""
    normalizadas = sorted({normalizar(p).strip() for p in palabras if p.strip()})
    if not normalizadas:
        # Un patrón que nunca matchea, para no tener que chequear None arriba.
        return re.compile(r"(?!x)x")
    alternativas = "|".join(re.escape(p) for p in normalizadas)
    return re.compile(rf"\b(?:{alternativas})\b")


def detectar_idioma(texto: str, lexico: Lexico) -> Idioma:
    """Heurística ES/EN. Ante la duda devuelve el español (idioma del bar)."""
    puntos_es = _PESO_PISTA_ES if _PISTAS_ES.search(texto) else 0
    normalizado = normalizar(texto)
    puntos_es += len(lexico.marcadores_es.findall(normalizado))
    puntos_en = len(lexico.marcadores_en.findall(normalizado))
    return "en" if puntos_en > puntos_es else "es"


def detectar_conceptos(texto: str, npc: Npc) -> list[str]:
    """A qué le está apuntando el jugador, sin importar cómo lo dijo.

    Devuelve los conceptos en el orden en que los declara la ficha del NPC,
    así el resultado es estable turno a turno.
    """
    normalizado = normalizar(texto)
    return [
        concepto
        for concepto, patron in npc.patrones_conceptos.items()
        if patron.search(normalizado)
    ]


def es_amable(texto: str, lexico: Lexico) -> bool:
    return bool(lexico.amable.search(normalizar(texto)))


def es_agresivo(texto: str, lexico: Lexico) -> bool:
    if lexico.agresivo.search(normalizar(texto)):
        return True
    return (texto.count("!") + texto.count("¡")) >= 2


def menciona_victima(texto: str, lexico: Lexico) -> bool:
    """El jugador habla de lo que le hicieron: eso ablanda al NPC."""
    return bool(lexico.victima.search(normalizar(texto)))


def contar_palabras(texto: str) -> int:
    return len(texto.split())


def resumir_deteccion(texto: str, lexico: Lexico, npc: Npc) -> dict[str, object]:
    """Todo lo detectado en una frase. Para el panel de debug y los tests."""
    return {
        "idioma": detectar_idioma(texto, lexico),
        "conceptos": detectar_conceptos(texto, npc),
        "amable": es_amable(texto, lexico),
        "agresivo": es_agresivo(texto, lexico),
        "victima": menciona_victima(texto, lexico),
        "palabras": contar_palabras(texto),
    }


__all__: Sequence[str] = [
    "normalizar",
    "compilar_patron",
    "detectar_idioma",
    "detectar_conceptos",
    "es_amable",
    "es_agresivo",
    "menciona_victima",
    "contar_palabras",
    "resumir_deteccion",
]
