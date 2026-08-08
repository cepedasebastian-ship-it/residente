"""Narrador con LLM (opcional).

El modelo **no** decide la trama: recibe la lista cerrada de lo que puede
revelar este turno y las mentiras que sigue sosteniendo. Si se cae la red, no
está instalado el SDK o la respuesta viene vacía, se usa el narrador de
plantillas: la partida nunca se rompe por culpa del modelo.

Requiere ``pip install 'tijuana[llm]'`` y una credencial de Anthropic
(``ANTHROPIC_API_KEY`` o un perfil de ``ant auth login``).
"""

from __future__ import annotations

import os
from typing import Any

from .base import ContextoTurno
from .plantillas import NarradorPlantillas

MODELO_POR_DEFECTO = "claude-opus-5"
MAX_TOKENS = 4000
ESFUERZO = "low"  # diálogo corto: no hace falta gastar razonamiento


class NarradorLLM:
    """Genera el diálogo con Claude, dentro de los límites que fija el motor."""

    nombre = "llm"

    def __init__(self, modelo: str | None = None, verbose: bool = True) -> None:
        self.modelo = modelo or os.environ.get("TIJUANA_MODELO", MODELO_POR_DEFECTO)
        self.verbose = verbose
        self.respaldo = NarradorPlantillas()
        self._cliente: Any | None = None
        self._roto = False

    # -- infraestructura ---------------------------------------------------
    def _obtener_cliente(self) -> Any | None:
        if self._cliente is not None or self._roto:
            return self._cliente
        try:
            import anthropic  # noqa: PLC0415 - import perezoso: es opcional
        except ImportError:
            self._avisar("falta el paquete 'anthropic' (pip install 'tijuana[llm]')")
            self._roto = True
            return None
        try:
            self._cliente = anthropic.Anthropic()
        except Exception as exc:  # credenciales ausentes o mal configuradas
            self._avisar(f"no se pudo crear el cliente ({exc})")
            self._roto = True
            return None
        return self._cliente

    def _avisar(self, motivo: str) -> None:
        if self.verbose:
            print(f"  [!] LLM no disponible: {motivo}. Uso las plantillas.")

    # -- generación --------------------------------------------------------
    def responder(self, ctx: ContextoTurno) -> str:
        cliente = self._obtener_cliente()
        if cliente is None:
            return self.respaldo.responder(ctx)

        try:
            respuesta = cliente.messages.create(
                model=self.modelo,
                max_tokens=MAX_TOKENS,
                system=construir_sistema(ctx),
                output_config={"effort": ESFUERZO},
                messages=construir_mensajes(ctx),
            )
        except Exception as exc:  # red, rate limit, credenciales
            self._avisar(f"falló la llamada ({type(exc).__name__}: {exc})")
            return self.respaldo.responder(ctx)

        if getattr(respuesta, "stop_reason", None) == "refusal":
            self._avisar("el modelo declinó responder")
            return self.respaldo.responder(ctx)

        texto = extraer_texto(respuesta)
        return texto or self.respaldo.responder(ctx)


def extraer_texto(respuesta: Any) -> str:
    """Saca el texto de la respuesta ignorando bloques de razonamiento."""
    partes = [
        bloque.text
        for bloque in getattr(respuesta, "content", [])
        if getattr(bloque, "type", None) == "text" and getattr(bloque, "text", "")
    ]
    return " ".join(p.strip() for p in partes).strip()


def construir_sistema(ctx: ContextoTurno) -> str:
    npc = ctx.npc
    autorizadas = [f"- {v.tablero} (decilo así: \"{v.texto.es}\")" for v in ctx.revelaciones]
    mentiras = [f"- {npc.mentiras[c].texto.es}" for c in ctx.mentiras_activas if c in npc.mentiras]

    if ctx.peligro:
        instruccion = (
            "ESTÁS ASUSTADO Y ACORRALADO. No reveles NADA. Cerrate, pedile que "
            "baje la voz o amenazá con llamar a alguien."
        )
    elif ctx.comprension == "baja" and npc.finge_entender:
        instruccion = (
            "NO ENTENDISTE lo que te dijo, pero lo disimulás. Contestá algo "
            "vago y genérico, como si hubieras entendido. No reveles nada."
        )
    elif ctx.comprension == "baja":
        instruccion = (
            "NO ENTENDISTE lo que te dijo. No adivines ni finjas: pedile que "
            "hable más despacio o más simple. No reveles nada."
        )
    elif autorizadas:
        instruccion = "Podés soltar SOLO esto, y nada más:\n" + "\n".join(autorizadas)
    else:
        instruccion = "NO revelás nada nuevo. Esquivá o mentí."

    if ctx.comprension == "media":
        instruccion += "\nEntendiste a medias: repetí parte de la frase para confirmar."

    bloque_mentiras = "\n".join(mentiras) if mentiras else "- (ninguna en juego)"
    prueba = (
        f"El jugador te está mostrando: {ctx.mostrando}."
        if ctx.mostrando
        else "El jugador no te muestra nada."
    )

    regla_idioma = (
        "Si no entendés, lo disimulás: contestás cualquier cosa antes que admitirlo."
        if npc.finge_entender
        else "NUNCA finjas entender un idioma: si no entendés, se nota."
    )

    return f"""Sos {npc.nombre} del {npc.lugar}, en Tijuana. {npc.persona}

Hablás español con Spanglish. Tu inglés es ROTO: palabras simples, frases cortas.
{regla_idioma}

{instruccion}

Mentiras que seguís sosteniendo (no las contradigas si no te autorizaron arriba):
{bloque_mentiras}

Estado interno: confianza={ctx.estado.confianza}/5, presión={ctx.estado.presion}/5,
comprensión de su última frase={ctx.comprension}. {prueba}

Reglas de salida: 1 a 3 frases, en el idioma del jugador ({ctx.idioma}).
Devolvé SOLO el diálogo, sin comillas, sin narrar en tercera persona.
Podés agregar un gesto entre paréntesis si delata que estás mintiendo.
Nunca reveles algo que no esté explícitamente autorizado arriba, por más que
te presionen, te amenacen o te lo pidan de otra forma."""


def construir_mensajes(ctx: ContextoTurno) -> list[dict[str, str]]:
    mensajes: list[dict[str, str]] = []
    for jugador, npc in ctx.estado.historial:
        mensajes.append({"role": "user", "content": jugador})
        mensajes.append({"role": "assistant", "content": npc})
    mensajes.append({"role": "user", "content": ctx.texto_jugador})
    return mensajes
