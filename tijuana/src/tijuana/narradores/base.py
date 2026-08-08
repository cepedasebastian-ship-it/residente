"""Contrato de los narradores.

El motor decide **qué** puede decir el NPC (qué verdades están autorizadas este
turno, qué mentiras sigue sosteniendo, si entendió, si está asustado). El
narrador solo decide **cómo** lo dice. Por eso se puede cambiar la plantilla
por un LLM sin tocar una línea de reglas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence, runtime_checkable

from ..estado import Estado
from ..modelos import Idioma, Npc, Verdad


@dataclass(frozen=True)
class ContextoTurno:
    """Todo lo que el narrador necesita, y nada más."""

    npc: Npc
    estado: Estado
    texto_jugador: str
    idioma: Idioma
    comprension: str
    conceptos: Sequence[str] = field(default_factory=tuple)
    revelaciones: Sequence[Verdad] = field(default_factory=tuple)
    mentiras_activas: Sequence[str] = field(default_factory=tuple)
    peligro: bool = False
    mostrando: str | None = None


@runtime_checkable
class Narrador(Protocol):
    nombre: str

    def responder(self, ctx: ContextoTurno) -> str:
        """Devuelve la línea de diálogo del NPC."""
        ...
