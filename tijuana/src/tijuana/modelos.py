"""Modelos de contenido: lo que el juego *sabe*, sin nada de lógica de turno.

Todo lo que viene de los JSON de `datos/` termina en alguno de estos objetos.
La regla es simple: acá no se decide nada, solo se representa. Las decisiones
viven en `compuertas.py`, `diales.py` y `motor.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

Idioma = str  # "es" | "en"


class ErrorDeContenido(ValueError):
    """Un JSON de datos es inválido o inconsistente."""


# ---------------------------------------------------------------------------
# Texto bilingüe
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Texto:
    """Una línea con versión en español y en inglés."""

    es: str
    en: str

    def en_idioma(self, idioma: Idioma) -> str:
        return self.en if idioma == "en" else self.es

    @classmethod
    def desde_dict(cls, datos: Mapping[str, str], ruta: str) -> "Texto":
        faltan = {"es", "en"} - set(datos)
        if faltan:
            raise ErrorDeContenido(f"{ruta}: falta el texto en {sorted(faltan)}")
        return cls(es=datos["es"], en=datos["en"])


# ---------------------------------------------------------------------------
# Condiciones de destrabe
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Condicion:
    """Un conjunto de exigencias que se cumplen todas juntas (AND)."""

    prueba: str | None = None
    confianza_min: int = 0
    presion_min: int = 0
    verdades_previas: tuple[str, ...] = ()

    CLAVES = frozenset({"prueba", "confianza_min", "presion_min", "verdades_previas"})

    @classmethod
    def desde_dict(cls, datos: Mapping[str, object], ruta: str) -> "Condicion":
        desconocidas = set(datos) - cls.CLAVES
        if desconocidas:
            raise ErrorDeContenido(
                f"{ruta}: claves de condición desconocidas: {sorted(desconocidas)}"
            )
        return cls(
            prueba=datos.get("prueba"),  # type: ignore[arg-type]
            confianza_min=int(datos.get("confianza_min", 0)),  # type: ignore[arg-type]
            presion_min=int(datos.get("presion_min", 0)),  # type: ignore[arg-type]
            verdades_previas=tuple(datos.get("verdades_previas", ())),  # type: ignore[arg-type]
        )

    @property
    def vacia(self) -> bool:
        return self == Condicion()

    def se_cumple(
        self,
        *,
        confianza: int,
        presion: int,
        sabidas: Iterable[str],
        mostrando: str | None,
    ) -> bool:
        if self.prueba is not None and self.prueba != mostrando:
            return False
        if confianza < self.confianza_min or presion < self.presion_min:
            return False
        sabidas = set(sabidas)
        return all(v in sabidas for v in self.verdades_previas)

    def describir(self) -> str:
        partes: list[str] = []
        if self.prueba:
            partes.append(f"mostrar {self.prueba}")
        if self.confianza_min:
            partes.append(f"confianza>={self.confianza_min}")
        if self.presion_min:
            partes.append(f"presión>={self.presion_min}")
        for v in self.verdades_previas:
            partes.append(f"saber '{v}'")
        return " + ".join(partes) if partes else "sin requisitos"


@dataclass(frozen=True)
class Requisito:
    """Qué hace falta para que una verdad se destrabe.

    Se cumple cuando el jugador apunta al `concepto`, se cumple la condición
    `base` (AND) y, si hay alternativas, al menos una de ellas (OR).
    """

    concepto: str
    base: Condicion = Condicion()
    cualquiera_de: tuple[Condicion, ...] = ()

    @classmethod
    def desde_dict(cls, datos: Mapping[str, object], ruta: str) -> "Requisito":
        if "concepto" not in datos:
            raise ErrorDeContenido(f"{ruta}: el requisito no declara 'concepto'")
        base_datos = {k: v for k, v in datos.items() if k in Condicion.CLAVES}
        desconocidas = set(datos) - Condicion.CLAVES - {"concepto", "cualquiera_de"}
        if desconocidas:
            raise ErrorDeContenido(
                f"{ruta}: claves de requisito desconocidas: {sorted(desconocidas)}"
            )
        alternativas = tuple(
            Condicion.desde_dict(alt, f"{ruta}.cualquiera_de[{i}]")
            for i, alt in enumerate(datos.get("cualquiera_de", ()))  # type: ignore[arg-type]
        )
        return cls(
            concepto=str(datos["concepto"]),
            base=Condicion.desde_dict(base_datos, ruta),
            cualquiera_de=alternativas,
        )

    def se_cumple(
        self,
        *,
        conceptos: Iterable[str],
        confianza: int,
        presion: int,
        sabidas: Iterable[str],
        mostrando: str | None,
    ) -> bool:
        if self.concepto not in set(conceptos):
            return False
        sabidas = set(sabidas)
        kwargs = dict(
            confianza=confianza, presion=presion, sabidas=sabidas, mostrando=mostrando
        )
        if not self.base.se_cumple(**kwargs):  # type: ignore[arg-type]
            return False
        if not self.cualquiera_de:
            return True
        return any(alt.se_cumple(**kwargs) for alt in self.cualquiera_de)  # type: ignore[arg-type]

    def describir(self) -> str:
        partes = [f"hablar de '{self.concepto}'"]
        if not self.base.vacia:
            partes.append(self.base.describir())
        if self.cualquiera_de:
            opciones = " | ".join(alt.describir() for alt in self.cualquiera_de)
            partes.append(f"({opciones})")
        return " + ".join(partes)


# ---------------------------------------------------------------------------
# Verdades y mentiras
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Verdad:
    id: str
    tablero: str
    texto: Texto
    requiere: Requisito
    contradice: str | None = None


@dataclass(frozen=True)
class Mentira:
    concepto: str
    verdad: str
    texto: Texto
    tell: str


# ---------------------------------------------------------------------------
# NPC
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModificadoresIdioma:
    """Cuánto mueve cada cosa la comprensión del NPC (compuerta 1)."""

    mostrando_prueba: float = 0.25
    diccionario: float = 0.20
    frase_corta: float = 0.10
    frase_larga: float = -0.25
    umbral_frase_corta: int = 4
    umbral_frase_larga: int = 12
    umbral_alta: float = 0.65
    umbral_media: float = 0.40

    @classmethod
    def desde_dict(cls, datos: Mapping[str, object]) -> "ModificadoresIdioma":
        campos = {f: datos[f] for f in cls.__dataclass_fields__ if f in datos}
        return cls(**campos)  # type: ignore[arg-type]


@dataclass(frozen=True)
class Npc:
    id: str
    nombre: str
    lugar: str
    presentacion: str
    persona: str
    idioma_nativo: Idioma
    nivel_ingles: float
    finge_entender: bool
    modificadores: ModificadoresIdioma
    conceptos: Mapping[str, Sequence[str]]
    patrones_conceptos: Mapping[str, re.Pattern[str]]
    verdades: Mapping[str, Verdad]
    mentiras: Mapping[str, Mentira]
    reacciones: Mapping[str, Texto]

    def reaccion(self, clave: str, idioma: Idioma) -> str:
        texto = self.reacciones.get(clave)
        return texto.en_idioma(idioma) if texto else ""

    def mentira_de(self, concepto: str) -> Mentira | None:
        return self.mentiras.get(concepto)


# ---------------------------------------------------------------------------
# Caso (el expediente del jugador)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Prueba:
    id: str
    nombre: str
    descripcion: str


@dataclass(frozen=True)
class TarjetaInicial:
    id: str
    tipo: str  # "hecho" | "creencia"
    texto: str


@dataclass(frozen=True)
class Caso:
    id: str
    titulo: str
    subtitulo: str
    protagonista: str
    pruebas: Mapping[str, Prueba]
    tablero_inicial: Sequence[TarjetaInicial]
    npcs: Sequence[str]
    npc_inicial: str

    @property
    def creencias(self) -> set[str]:
        return {t.id for t in self.tablero_inicial if t.tipo == "creencia"}


# ---------------------------------------------------------------------------
# Léxico global
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Lexico:
    """Expresiones regulares compiladas para idioma y tono."""

    marcadores_es: re.Pattern[str]
    marcadores_en: re.Pattern[str]
    amable: re.Pattern[str]
    agresivo: re.Pattern[str]
    victima: re.Pattern[str]
    palabras: Mapping[str, Sequence[str]] = field(default_factory=dict)
