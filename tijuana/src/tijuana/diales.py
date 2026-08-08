"""Confianza y presión: los dos diales que abren (o cierran) al NPC.

Reglas:

* Cada **fuente** de confianza suma una sola vez en la partida. Repetir la
  misma palabra mágica no sirve; hay que traer algo nuevo.
* Hablarle en su idioma vale confianza. Es la recompensa por cruzar la
  compuerta 1 en serio, en vez de gritar en inglés.
* La presión sube cuando apretás o cuando insistís sobre algo que el NPC ya
  te negó, y **baja** si aflojás. Sin ese respiro, tres frases bruscas dejaban
  la partida trabada para siempre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .estado import Estado
from .idioma import detectar_idioma, es_agresivo, es_amable, menciona_victima
from .modelos import Lexico, Npc


@dataclass
class CambioDeDiales:
    """Qué movió el turno. Se muestra en el panel de debug."""

    confianza: list[str] = field(default_factory=list)
    presion: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        partes = [f"+conf:{c}" for c in self.confianza]
        partes += [f"{p}" for p in self.presion]
        return " ".join(partes) if partes else "sin cambios"


def actualizar_diales(
    estado: Estado,
    texto: str,
    npc: Npc,
    lexico: Lexico,
    conceptos: Sequence[str],
) -> CambioDeDiales:
    cambio = CambioDeDiales()

    # --- confianza (una vez por fuente) ---------------------------------
    if estado.mostrando in ("pulsera", "cicatriz"):
        if estado.sumar_confianza(f"prueba:{estado.mostrando}"):
            cambio.confianza.append(f"prueba:{estado.mostrando}")

    if menciona_victima(texto, lexico) and estado.sumar_confianza("victima"):
        cambio.confianza.append("victima")

    if es_amable(texto, lexico) and estado.sumar_confianza("amabilidad"):
        cambio.confianza.append("amabilidad")

    hablo_su_idioma = detectar_idioma(texto, lexico) == npc.idioma_nativo
    if hablo_su_idioma and estado.sumar_confianza("idioma_nativo"):
        cambio.confianza.append("idioma_nativo")

    # --- presión ----------------------------------------------------------
    agresivo = es_agresivo(texto, lexico)
    if agresivo:
        estado.sumar_presion()
        cambio.presion.append("+pres:agresion")

    insiste = bool(conceptos) and conceptos[0] == estado.ultimo_concepto
    if insiste and conceptos[0] in _conceptos_trabados(npc, estado, conceptos):
        estado.sumar_presion()
        cambio.presion.append("+pres:insistencia")

    if not agresivo and es_amable(texto, lexico) and estado.presion > 0:
        estado.bajar_presion()
        cambio.presion.append("-pres:calma")

    return cambio


def _conceptos_trabados(npc: Npc, estado: Estado, conceptos: Sequence[str]) -> set[str]:
    return {
        c
        for c in conceptos
        if (m := npc.mentira_de(c)) is not None and m.verdad not in estado.sabidas
    }
