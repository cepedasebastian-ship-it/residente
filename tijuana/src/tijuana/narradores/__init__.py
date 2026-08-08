"""Narradores: convierten la decisión del motor en una línea de diálogo."""

from __future__ import annotations

from .base import ContextoTurno, Narrador
from .plantillas import NarradorPlantillas


def crear_narrador(modo: str = "plantillas", **kwargs) -> Narrador:
    """Fábrica: "plantillas" (por defecto) o "llm"."""
    if modo == "plantillas":
        return NarradorPlantillas()
    if modo == "llm":
        from .llm import NarradorLLM  # import perezoso: depende de un extra

        return NarradorLLM(**kwargs)
    raise ValueError(f"narrador desconocido: {modo!r} (usá 'plantillas' o 'llm')")


__all__ = [
    "ContextoTurno",
    "Narrador",
    "NarradorPlantillas",
    "crear_narrador",
]
