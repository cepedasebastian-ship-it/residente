"""El motor: un turno de conversación de punta a punta.

Orden de un turno:

1. Detectar a qué apunta el jugador (conceptos) y en qué idioma.
2. **Compuerta 1**: ¿el NPC entendió?
3. Mover los diales (confianza / presión).
4. **Compuerta 2**: ¿se destraba alguna verdad? (nunca si no entendió o si
   está asustado).
5. El narrador arma la línea de diálogo.
6. Anotar lo revelado en el tablero Memento.

El motor no imprime nada: devuelve un `Turno`. Quien quiera mostrarlo —la CLI,
un test, un front web— decide cómo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from . import compuertas, diales
from .carga import Contenido
from .estado import Estado, Tarjeta
from .idioma import detectar_conceptos, detectar_idioma
from .modelos import Caso, ErrorDeContenido, Lexico, Npc, Verdad
from .narradores import ContextoTurno, Narrador, NarradorPlantillas


@dataclass(frozen=True)
class Turno:
    """El resultado completo de un turno. Lo que se muestra y lo que se testea."""

    entrada: str
    idioma: str
    comprension: str
    conceptos: Sequence[str]
    respuesta: str
    revelaciones: Sequence[Verdad] = field(default_factory=tuple)
    tarjetas_nuevas: Sequence[Tarjeta] = field(default_factory=tuple)
    mostrando: str | None = None
    uso_diccionario: bool = False
    peligro: bool = False
    confianza: int = 0
    presion: int = 0
    cambio_diales: str = ""

    @property
    def entendio(self) -> bool:
        return compuertas.entendio(self.comprension)

    @property
    def ids_revelados(self) -> list[str]:
        return [v.id for v in self.revelaciones]


class Motor:
    def __init__(
        self,
        contenido: Contenido,
        npc_id: str | None = None,
        narrador: Narrador | None = None,
        estado: Estado | None = None,
    ) -> None:
        self.contenido = contenido
        self.npc: Npc = contenido.npc(npc_id)
        self.narrador: Narrador = narrador or NarradorPlantillas()
        self.estado = estado or Estado.desde_caso(contenido.caso)

    # -- atajos -------------------------------------------------------------
    @property
    def caso(self) -> Caso:
        return self.contenido.caso

    @property
    def lexico(self) -> Lexico:
        return self.contenido.lexico

    # -- acciones del jugador -----------------------------------------------
    def mostrar(self, prueba_id: str) -> str:
        """Deja una prueba lista para el próximo turno de conversación."""
        if prueba_id not in self.caso.pruebas:
            disponibles = " | ".join(sorted(self.caso.pruebas))
            raise ErrorDeContenido(f"no tenés esa prueba. Tenés: {disponibles}")
        self.estado.mostrando = prueba_id
        return self.caso.pruebas[prueba_id].nombre

    def usar_diccionario(self) -> None:
        self.estado.diccionario = True

    def cambiar_npc(self, npc_id: str) -> Npc:
        """Cambia de interlocutor conservando el tablero y los diales."""
        self.npc = self.contenido.npc(npc_id)
        self.estado.ultimo_concepto = None
        self.estado.historial.clear()
        return self.npc

    # -- el turno -------------------------------------------------------------
    def turno(self, texto: str) -> Turno:
        estado, npc, lexico = self.estado, self.npc, self.lexico
        mostrando = estado.mostrando
        uso_diccionario = estado.diccionario

        idioma = detectar_idioma(texto, lexico)
        conceptos = detectar_conceptos(texto, npc)
        nivel = compuertas.comprension(texto, npc, estado, lexico)

        cambio = diales.actualizar_diales(estado, texto, npc, lexico, conceptos)

        # Si no te entendió no puede soltar nada, y si está asustado no quiere.
        puede_hablar = compuertas.entendio(nivel) and not estado.peligro
        ids = compuertas.evaluar_destrabes(npc, estado, conceptos) if puede_hablar else []
        revelaciones = tuple(npc.verdades[i] for i in ids)

        ctx = ContextoTurno(
            npc=npc,
            estado=estado,
            texto_jugador=texto,
            idioma=idioma,
            comprension=nivel,
            conceptos=tuple(conceptos),
            revelaciones=revelaciones,
            mentiras_activas=tuple(
                compuertas.conceptos_trabados(npc, estado, conceptos)
            ),
            peligro=estado.peligro,
            mostrando=mostrando,
        )
        respuesta = self.narrador.responder(ctx)

        # Recién ahora se anota: si el NPC se cerró, no hay tarjeta.
        tarjetas = tuple(estado.anotar_verdad(v) for v in revelaciones)

        turno = Turno(
            entrada=texto,
            idioma=idioma,
            comprension=nivel,
            conceptos=tuple(conceptos),
            respuesta=respuesta,
            revelaciones=revelaciones,
            tarjetas_nuevas=tarjetas,
            mostrando=mostrando,
            uso_diccionario=uso_diccionario,
            peligro=estado.peligro,
            confianza=estado.confianza,
            presion=estado.presion,
            cambio_diales=cambio.resumen(),
        )

        estado.recordar(texto, respuesta)
        estado.limpiar_flags(conceptos)
        return turno

    # -- lectura ---------------------------------------------------------------
    def verdades_pendientes(self) -> list[str]:
        return self.estado.faltantes(self.npc.verdades)

    def completo(self) -> bool:
        return not self.verdades_pendientes()

    def pistas(self) -> list[str]:
        return compuertas.pistas_pendientes(self.npc, self.estado)
