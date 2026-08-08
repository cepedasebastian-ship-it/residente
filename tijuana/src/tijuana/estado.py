"""El estado de una partida: diales, tablero Memento y memoria de la charla."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .modelos import Caso, Verdad

CONFIANZA_MAX = 5
PRESION_MAX = 5
UMBRAL_PELIGRO = 3

#: Cada fuente de confianza suma **una sola vez** en toda la partida. Sin esto,
#: repetir "cicatriz" cinco veces alcanzaría para maximizar la confianza.
FUENTES_CONFIANZA = (
    "prueba:pulsera",
    "prueba:cicatriz",
    "victima",
    "amabilidad",
    "idioma_nativo",
)

#: Cuántos mensajes de ida y vuelta recordamos para el narrador con LLM.
MEMORIA_MAX = 8


@dataclass
class Tarjeta:
    """Una tarjeta del tablero Memento."""

    id: str
    texto: str
    tipo: str  # "hecho" | "creencia" | "revelacion"
    tachada_por: list[str] = field(default_factory=list)

    @property
    def tachada(self) -> bool:
        return bool(self.tachada_por)

    #: Cómo se ve cada tipo de tarjeta en el tablero.
    MARCAS = {"hecho": "·", "creencia": "?", "revelacion": "+"}

    def render(self) -> str:
        if self.tachada:
            return f"  [x] {self.texto}   <- CONTRADICHA"
        return f"  [{self.MARCAS.get(self.tipo, ' ')}] {self.texto}"


@dataclass
class Estado:
    """Todo lo que cambia durante la partida."""

    confianza: int = 0
    presion: int = 0
    sabidas: set[str] = field(default_factory=set)
    tablero: list[Tarjeta] = field(default_factory=list)
    fuentes_usadas: set[str] = field(default_factory=set)
    mostrando: str | None = None  # prueba pendiente para el próximo turno
    diccionario: bool = False  # usó /dic para el próximo turno
    ultimo_concepto: str | None = None
    historial: list[tuple[str, str]] = field(default_factory=list)
    turnos: int = 0

    # -- construcción --------------------------------------------------
    @classmethod
    def desde_caso(cls, caso: Caso) -> "Estado":
        return cls(
            tablero=[
                Tarjeta(id=t.id, texto=t.texto, tipo=t.tipo) for t in caso.tablero_inicial
            ]
        )

    # -- diales ----------------------------------------------------------
    @property
    def peligro(self) -> bool:
        return self.presion >= UMBRAL_PELIGRO

    def sumar_confianza(self, fuente: str) -> bool:
        """Suma +1 si esa fuente no se usó todavía. Devuelve si sumó."""
        if fuente in self.fuentes_usadas or self.confianza >= CONFIANZA_MAX:
            self.fuentes_usadas.add(fuente)
            return False
        self.fuentes_usadas.add(fuente)
        self.confianza += 1
        return True

    def sumar_presion(self, cantidad: int = 1) -> None:
        self.presion = min(PRESION_MAX, self.presion + cantidad)

    def bajar_presion(self, cantidad: int = 1) -> None:
        self.presion = max(0, self.presion - cantidad)

    # -- tablero ---------------------------------------------------------
    def tarjeta(self, tarjeta_id: str) -> Tarjeta | None:
        return next((t for t in self.tablero if t.id == tarjeta_id), None)

    def anotar_verdad(self, verdad: Verdad) -> Tarjeta:
        """Agrega la revelación al tablero y tacha lo que contradiga."""
        self.sabidas.add(verdad.id)
        nueva = Tarjeta(id=verdad.id, texto=verdad.tablero, tipo="revelacion")
        self.tablero.append(nueva)
        if verdad.contradice:
            vieja = self.tarjeta(verdad.contradice)
            if vieja is not None and verdad.id not in vieja.tachada_por:
                vieja.tachada_por.append(verdad.id)
        return nueva

    # -- memoria de la conversación --------------------------------------
    def recordar(self, jugador: str, npc: str) -> None:
        self.historial.append((jugador, npc))
        if len(self.historial) > MEMORIA_MAX:
            del self.historial[: len(self.historial) - MEMORIA_MAX]

    # -- fin de turno ------------------------------------------------------
    def limpiar_flags(self, conceptos: Sequence[str]) -> None:
        self.mostrando = None
        self.diccionario = False
        self.ultimo_concepto = conceptos[0] if conceptos else None
        self.turnos += 1

    # -- lectura -----------------------------------------------------------
    def creencias_en_pie(self) -> list[Tarjeta]:
        return [t for t in self.tablero if t.tipo == "creencia" and not t.tachada]

    def render_tablero(self) -> str:
        if not self.tablero:
            return "  (vacío)"
        return "\n".join(t.render() for t in self.tablero)

    def faltantes(self, todas: Iterable[str]) -> list[str]:
        return [v for v in todas if v not in self.sabidas]
