"""El narrador con LLM: nunca inventa trama y nunca rompe la partida.

No se llama a la API: se inyecta un cliente falso.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import pytest

from tijuana.estado import Estado
from tijuana.narradores import ContextoTurno, NarradorPlantillas
from tijuana.narradores.llm import (
    NarradorLLM,
    construir_mensajes,
    construir_sistema,
    extraer_texto,
)


# --- dobles de prueba -------------------------------------------------------
@dataclass
class BloqueFalso:
    type: str
    text: str = ""


@dataclass
class RespuestaFalsa:
    content: list[BloqueFalso]
    stop_reason: str = "end_turn"


class ClienteFalso:
    def __init__(self, respuesta: Any = None, error: Exception | None = None):
        self.respuesta = respuesta
        self.error = error
        self.llamadas: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> Any:
        self.llamadas.append(kwargs)
        if self.error:
            raise self.error
        return self.respuesta


@pytest.fixture
def ctx(contenido) -> ContextoTurno:
    npc = contenido.npc()
    return ContextoTurno(
        npc=npc,
        estado=Estado.desde_caso(contenido.caso),
        texto_jugador="¿te acuerdas de la chica?",
        idioma="es",
        comprension="alta",
        conceptos=("la_chica",),
        revelaciones=(npc.verdades["marisol_estaba_asustada"],),
        mentiras_activas=("quienes_te_hicieron_esto",),
    )


def _narrador(cliente: Any) -> NarradorLLM:
    narrador = NarradorLLM(verbose=False)
    narrador._cliente = cliente
    return narrador


# --- prompt -----------------------------------------------------------------
def test_el_sistema_autoriza_solo_lo_revelado(ctx):
    sistema = construir_sistema(ctx)
    assert "Marisol estaba ASUSTADA" in sistema
    # Lo que el motor no autorizó no aparece como revelable.
    assert "puerta en el fondo" not in sistema
    assert "Esto es un bar" in sistema  # la mentira que sigue sosteniendo


def test_sin_revelaciones_el_sistema_lo_dice(ctx):
    sistema = construir_sistema(replace(ctx, revelaciones=()))
    assert "NO revelás nada nuevo" in sistema


def test_el_peligro_pisa_cualquier_autorizacion(ctx):
    sistema = construir_sistema(replace(ctx, peligro=True))
    assert "No reveles NADA" in sistema
    assert "Podés soltar SOLO esto" not in sistema


def test_la_incomprension_pisa_cualquier_autorizacion(ctx):
    sistema = construir_sistema(replace(ctx, comprension="baja"))
    assert "NO ENTENDISTE" in sistema
    assert "Podés soltar SOLO esto" not in sistema


def test_los_mensajes_incluyen_el_historial(ctx):
    ctx.estado.recordar("hola amigo", "¿vas a pedir algo?")
    mensajes = construir_mensajes(ctx)
    assert [m["role"] for m in mensajes] == ["user", "assistant", "user"]
    assert mensajes[-1]["content"] == ctx.texto_jugador


# --- respuesta ---------------------------------------------------------------
def test_ignora_los_bloques_de_razonamiento():
    respuesta = RespuestaFalsa(
        content=[BloqueFalso("thinking", "no mostrar"), BloqueFalso("text", " Órale. ")]
    )
    assert extraer_texto(respuesta) == "Órale."


def test_usa_la_respuesta_del_modelo(ctx):
    narrador = _narrador(
        ClienteFalso(RespuestaFalsa([BloqueFalso("text", "Sí... estaba asustada.")]))
    )
    assert narrador.responder(ctx) == "Sí... estaba asustada."


def test_si_el_modelo_declina_usa_las_plantillas(ctx):
    narrador = _narrador(
        ClienteFalso(RespuestaFalsa([], stop_reason="refusal"))
    )
    assert narrador.responder(ctx) == NarradorPlantillas().responder(ctx)


def test_si_la_llamada_falla_usa_las_plantillas(ctx):
    narrador = _narrador(ClienteFalso(error=RuntimeError("sin red")))
    assert narrador.responder(ctx) == NarradorPlantillas().responder(ctx)


def test_si_la_respuesta_viene_vacia_usa_las_plantillas(ctx):
    narrador = _narrador(ClienteFalso(RespuestaFalsa([BloqueFalso("text", "   ")])))
    assert narrador.responder(ctx) == NarradorPlantillas().responder(ctx)


def test_la_llamada_usa_el_modelo_configurado(ctx):
    cliente = ClienteFalso(RespuestaFalsa([BloqueFalso("text", "ok")]))
    narrador = _narrador(cliente)
    narrador.modelo = "claude-opus-5"
    narrador.responder(ctx)

    (kwargs,) = cliente.llamadas
    assert kwargs["model"] == "claude-opus-5"
    assert kwargs["max_tokens"] >= 1000  # deja aire para el razonamiento
    assert "temperature" not in kwargs  # no está soportado en los modelos actuales


def test_un_npc_que_finge_entender_no_admite_que_no_entendio(contenido):
    """`finge_entender` cambia la línea, nunca lo que se revela."""
    npc = replace(contenido.npc(), finge_entender=True)
    base = ContextoTurno(
        npc=npc,
        estado=Estado.desde_caso(contenido.caso),
        texto_jugador="do you remember the girl in the red dress from last night",
        idioma="en",
        comprension="baja",
        conceptos=("la_chica",),
    )

    respuesta = NarradorPlantillas().responder(base)
    assert respuesta != npc.reaccion("incomprension", "en")
    assert npc.mentiras["la_chica"].texto.en in respuesta
    assert "NO ENTENDISTE" in construir_sistema(base)
    assert "disimulás" in construir_sistema(base)
