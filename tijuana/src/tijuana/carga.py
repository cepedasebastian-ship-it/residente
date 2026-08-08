"""Carga y validación del contenido.

Los JSON son la fuente de verdad del juego, así que se validan al cargar y no
en medio de una partida: si una mentira apunta a una verdad que no existe, o
una verdad tacha una tarjeta inexistente, queremos enterarnos acá.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

from .idioma import compilar_patron
from .modelos import (
    Caso,
    ErrorDeContenido,
    Lexico,
    Mentira,
    ModificadoresIdioma,
    Npc,
    Prueba,
    Requisito,
    TarjetaInicial,
    Texto,
    Verdad,
)


def directorio_datos() -> Path:
    """El `datos/` que viene con el paquete."""
    return Path(str(resources.files("tijuana") / "datos"))


def _leer_json(ruta: Path) -> dict[str, Any]:
    if not ruta.exists():
        raise ErrorDeContenido(f"no existe el archivo de datos: {ruta}")
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - error de tipeo en datos
        raise ErrorDeContenido(f"{ruta}: JSON inválido ({exc})") from exc


# ---------------------------------------------------------------------------
# Léxico
# ---------------------------------------------------------------------------
def cargar_lexico(datos_dir: Path | None = None) -> Lexico:
    base = datos_dir or directorio_datos()
    crudo = _leer_json(base / "lexico.json")
    marcadores = crudo.get("marcadores_idioma", {})
    tono = crudo.get("tono", {})
    for clave in ("es", "en"):
        if clave not in marcadores:
            raise ErrorDeContenido(f"lexico.json: falta marcadores_idioma.{clave}")
    for clave in ("amable", "agresivo", "victima"):
        if clave not in tono:
            raise ErrorDeContenido(f"lexico.json: falta tono.{clave}")
    return Lexico(
        marcadores_es=compilar_patron(marcadores["es"]),
        marcadores_en=compilar_patron(marcadores["en"]),
        amable=compilar_patron(tono["amable"]),
        agresivo=compilar_patron(tono["agresivo"]),
        victima=compilar_patron(tono["victima"]),
        palabras={**{f"idioma_{k}": v for k, v in marcadores.items()}, **tono},
    )


# ---------------------------------------------------------------------------
# Caso
# ---------------------------------------------------------------------------
def cargar_caso(datos_dir: Path | None = None) -> Caso:
    base = datos_dir or directorio_datos()
    crudo = _leer_json(base / "caso.json")

    pruebas = {
        pid: Prueba(id=pid, nombre=p["nombre"], descripcion=p.get("descripcion", ""))
        for pid, p in crudo.get("pruebas", {}).items()
    }

    tarjetas: list[TarjetaInicial] = []
    vistos: set[str] = set()
    for t in crudo.get("tablero_inicial", []):
        if t["id"] in vistos:
            raise ErrorDeContenido(f"caso.json: tarjeta duplicada '{t['id']}'")
        if t.get("tipo") not in {"hecho", "creencia"}:
            raise ErrorDeContenido(
                f"caso.json: tarjeta '{t['id']}' con tipo inválido {t.get('tipo')!r}"
            )
        vistos.add(t["id"])
        tarjetas.append(TarjetaInicial(id=t["id"], tipo=t["tipo"], texto=t["texto"]))

    npcs = list(crudo.get("npcs", []))
    if not npcs:
        raise ErrorDeContenido("caso.json: el caso no declara NPCs")
    npc_inicial = crudo.get("npc_inicial", npcs[0])
    if npc_inicial not in npcs:
        raise ErrorDeContenido(
            f"caso.json: npc_inicial '{npc_inicial}' no está en la lista de npcs"
        )

    return Caso(
        id=crudo.get("id", "caso"),
        titulo=crudo.get("titulo", "TIJUANA"),
        subtitulo=crudo.get("subtitulo", ""),
        protagonista=crudo.get("protagonista", ""),
        pruebas=pruebas,
        tablero_inicial=tarjetas,
        npcs=npcs,
        npc_inicial=npc_inicial,
    )


# ---------------------------------------------------------------------------
# NPC
# ---------------------------------------------------------------------------
def cargar_npc(npc_id: str, datos_dir: Path | None = None) -> Npc:
    base = datos_dir or directorio_datos()
    ruta = base / "npcs" / f"{npc_id}.json"
    crudo = _leer_json(ruta)
    etiqueta = f"npcs/{npc_id}.json"

    conceptos: dict[str, list[str]] = {}
    for nombre, listas in crudo.get("conceptos", {}).items():
        palabras = [p for idioma_palabras in listas.values() for p in idioma_palabras]
        if not palabras:
            raise ErrorDeContenido(f"{etiqueta}: el concepto '{nombre}' no tiene palabras")
        conceptos[nombre] = palabras

    verdades: dict[str, Verdad] = {}
    for vid, v in crudo.get("verdades", {}).items():
        verdades[vid] = Verdad(
            id=vid,
            tablero=v["tablero"],
            texto=Texto.desde_dict(v["texto"], f"{etiqueta}:verdades.{vid}"),
            requiere=Requisito.desde_dict(
                v.get("requiere", {}), f"{etiqueta}:verdades.{vid}.requiere"
            ),
            contradice=v.get("contradice"),
        )

    mentiras: dict[str, Mentira] = {}
    for concepto, m in crudo.get("mentiras", {}).items():
        mentiras[concepto] = Mentira(
            concepto=concepto,
            verdad=m["verdad"],
            texto=Texto.desde_dict(m["texto"], f"{etiqueta}:mentiras.{concepto}"),
            tell=m.get("tell", ""),
        )

    reacciones = {
        clave: Texto.desde_dict(valor, f"{etiqueta}:reacciones.{clave}")
        for clave, valor in crudo.get("reacciones", {}).items()
    }

    conf_idioma: Mapping[str, Any] = crudo.get("idioma", {})
    npc = Npc(
        id=crudo.get("id", npc_id),
        nombre=crudo.get("nombre", npc_id),
        lugar=crudo.get("lugar", ""),
        presentacion=crudo.get("presentacion", ""),
        persona=crudo.get("persona", ""),
        idioma_nativo=conf_idioma.get("nativo", "es"),
        nivel_ingles=float(conf_idioma.get("ingles", 0.35)),
        finge_entender=bool(conf_idioma.get("finge_entender", False)),
        modificadores=ModificadoresIdioma.desde_dict(
            conf_idioma.get("modificadores", {})
        ),
        conceptos=conceptos,
        patrones_conceptos={n: compilar_patron(p) for n, p in conceptos.items()},
        verdades=verdades,
        mentiras=mentiras,
        reacciones=reacciones,
    )
    validar_npc(npc, etiqueta)
    return npc


def validar_npc(npc: Npc, etiqueta: str) -> None:
    if not npc.verdades:
        raise ErrorDeContenido(f"{etiqueta}: el NPC no tiene verdades que revelar")

    for clave in ("incomprension", "peligro", "relleno"):
        if clave not in npc.reacciones:
            raise ErrorDeContenido(f"{etiqueta}: falta la reacción '{clave}'")

    for vid, verdad in npc.verdades.items():
        req = verdad.requiere
        if req.concepto not in npc.conceptos:
            raise ErrorDeContenido(
                f"{etiqueta}: la verdad '{vid}' exige el concepto inexistente "
                f"'{req.concepto}'"
            )
        condiciones = (req.base, *req.cualquiera_de)
        for cond in condiciones:
            for previa in cond.verdades_previas:
                if previa not in npc.verdades:
                    raise ErrorDeContenido(
                        f"{etiqueta}: la verdad '{vid}' exige la verdad inexistente "
                        f"'{previa}'"
                    )
                if previa == vid:
                    raise ErrorDeContenido(
                        f"{etiqueta}: la verdad '{vid}' se exige a sí misma"
                    )

    for concepto, mentira in npc.mentiras.items():
        if concepto not in npc.conceptos:
            raise ErrorDeContenido(
                f"{etiqueta}: hay una mentira para el concepto inexistente '{concepto}'"
            )
        if mentira.verdad not in npc.verdades:
            raise ErrorDeContenido(
                f"{etiqueta}: la mentira de '{concepto}' tapa la verdad inexistente "
                f"'{mentira.verdad}'"
            )


def validar_contra_caso(npc: Npc, caso: Caso) -> None:
    """Chequea lo que solo se puede saber con el caso y el NPC juntos."""
    creencias = caso.creencias
    for vid, verdad in npc.verdades.items():
        if verdad.contradice and verdad.contradice not in creencias:
            raise ErrorDeContenido(
                f"npc '{npc.id}': la verdad '{vid}' contradice la tarjeta "
                f"'{verdad.contradice}', que no es una creencia del caso"
            )
    for vid, verdad in npc.verdades.items():
        for cond in (verdad.requiere.base, *verdad.requiere.cualquiera_de):
            if cond.prueba and cond.prueba not in caso.pruebas:
                raise ErrorDeContenido(
                    f"npc '{npc.id}': la verdad '{vid}' pide la prueba inexistente "
                    f"'{cond.prueba}'"
                )


# ---------------------------------------------------------------------------
# Todo junto
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Contenido:
    caso: Caso
    lexico: Lexico
    npcs: Mapping[str, Npc]

    def npc(self, npc_id: str | None = None) -> Npc:
        elegido = npc_id or self.caso.npc_inicial
        if elegido not in self.npcs:
            disponibles = ", ".join(sorted(self.npcs)) or "(ninguno)"
            raise ErrorDeContenido(
                f"no existe el NPC '{elegido}'. Disponibles: {disponibles}"
            )
        return self.npcs[elegido]


def cargar_contenido(datos_dir: Path | None = None) -> Contenido:
    base = datos_dir or directorio_datos()
    caso = cargar_caso(base)
    lexico = cargar_lexico(base)
    npcs = {npc_id: cargar_npc(npc_id, base) for npc_id in caso.npcs}
    for npc in npcs.values():
        validar_contra_caso(npc, caso)
    return Contenido(caso=caso, lexico=lexico, npcs=npcs)


def leer_guion(ruta: Path) -> list[str]:
    """Lee un guion de entradas: una por línea, `#` es comentario."""
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lineas if l.strip() and not l.lstrip().startswith("#")]


def guion_demo(datos_dir: Path | None = None) -> list[str]:
    base = datos_dir or directorio_datos()
    return leer_guion(base / "guiones" / "demo.txt")
