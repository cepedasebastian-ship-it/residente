"""REPL del juego. Solo entrada/salida: las reglas viven en `motor.py`."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterator, Sequence

from .carga import cargar_contenido, guion_demo, leer_guion
from .modelos import ErrorDeContenido
from .motor import Motor, Turno
from .narradores import crear_narrador

ANCHO = 66

AYUDA = """
  /mostrar <prueba>   le mostrás algo (se usa en tu próxima frase)
  /pruebas            qué tenés encima
  /dic                abrís el diccionario (te hacés entender mejor)
  /estado             confianza, presión y tablero Memento
  /pistas             qué le falta a cada verdad (spoilers)
  /debug              mostrar/ocultar el panel de compuertas
  /ayuda              esta lista
  /salir              te vas del bar

  Todo lo demás es hablarle. Podés escribir en español o en inglés.
""".rstrip()


# ---------------------------------------------------------------------------
# Presentación
# ---------------------------------------------------------------------------
def encabezado(motor: Motor, modo: str) -> str:
    caso = motor.caso
    lineas = [
        "=" * ANCHO,
        f"  {caso.titulo}",
        f"  {caso.subtitulo}",
        "",
        f"  {motor.npc.lugar.upper()} — {motor.npc.presentacion}",
        f"  Narrador: {modo}   ( /ayuda para los comandos )",
        "=" * ANCHO,
    ]
    return "\n".join(lineas)


def render_turno(turno: Turno, debug: bool) -> str:
    partes = [f"  cantinero: {turno.respuesta}"]
    for verdad, tarjeta in zip(turno.revelaciones, turno.tarjetas_nuevas):
        partes.append(f"    -> [tablero] {tarjeta.texto}")
        if verdad.contradice:
            partes.append("       CONTRADICE una tarjeta que dabas por cierta.")
    if debug:
        partes.append(panel(turno))
    return "\n".join(partes)


def panel(turno: Turno) -> str:
    campos = [
        f"comprensión={turno.comprension}",
        f"conceptos={list(turno.conceptos) or '—'}",
        f"confianza={turno.confianza}",
        f"presión={turno.presion}",
    ]
    if turno.mostrando:
        campos.append(f"mostrando={turno.mostrando}")
    if turno.uso_diccionario:
        campos.append("diccionario")
    if turno.peligro:
        campos.append("PELIGRO")
    if turno.ids_revelados:
        campos.append(f"reveló={turno.ids_revelados}")
    if turno.cambio_diales:
        campos.append(f"diales[{turno.cambio_diales}]")
    return "    [" + " | ".join(campos) + "]"


def render_estado(motor: Motor) -> str:
    estado = motor.estado
    faltan = len(motor.verdades_pendientes())
    return "\n".join(
        [
            f"  Confianza={estado.confianza}/5  Presión={estado.presion}/5  "
            f"Peligro={'sí' if estado.peligro else 'no'}",
            f"  Verdades pendientes con {motor.npc.nombre}: {faltan}",
            "  TABLERO MEMENTO:",
            estado.render_tablero(),
        ]
    )


def render_pruebas(motor: Motor) -> str:
    lineas = ["  LLEVÁS ENCIMA:"]
    for prueba in motor.caso.pruebas.values():
        lineas.append(f"  - {prueba.id}: {prueba.nombre} — {prueba.descripcion}")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Bucle
# ---------------------------------------------------------------------------
def entradas_interactivas() -> Iterator[str]:
    while True:
        try:
            yield input("\n> tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return


def entradas_de_guion(lineas: Sequence[str]) -> Iterator[str]:
    for linea in lineas:
        print(f"\n> tú: {linea}")
        yield linea


def jugar(motor: Motor, entradas: Iterator[str], debug: bool) -> int:
    for entrada in entradas:
        if not entrada:
            continue

        if entrada.startswith("/"):
            comando, _, argumento = entrada.partition(" ")
            resultado = ejecutar_comando(motor, comando, argumento.strip())
            if resultado is None:
                print("  Te vas del bar.")
                return 0
            if resultado == "__debug__":
                debug = not debug
                print(f"  [debug={'on' if debug else 'off'}]")
            elif resultado:
                print(resultado)
            continue

        turno = motor.turno(entrada)
        print(render_turno(turno, debug))

        if motor.completo():
            print("\n  * Le sacaste todo lo que sabe. El tablero quedó así:")
            print(motor.estado.render_tablero())

    return 0


def ejecutar_comando(motor: Motor, comando: str, argumento: str) -> str | None:
    """Devuelve el texto a imprimir, "" si no hay nada, o None para salir."""
    if comando in ("/salir", "/exit", "/quit"):
        return None
    if comando in ("/ayuda", "/help", "/?"):
        return AYUDA
    if comando == "/debug":
        return "__debug__"
    if comando == "/estado":
        return render_estado(motor)
    if comando == "/pruebas":
        return render_pruebas(motor)
    if comando == "/pistas":
        return "\n".join(f"  - {p}" for p in motor.pistas()) or "  (ya sabés todo)"
    if comando == "/dic":
        motor.usar_diccionario()
        return "  [abrís el diccionario y buscás la palabra. Te ayuda esta frase.]"
    if comando == "/mostrar":
        if not argumento:
            return "  uso: /mostrar " + " | ".join(sorted(motor.caso.pruebas))
        try:
            nombre = motor.mostrar(argumento)
        except ErrorDeContenido as exc:
            return f"  {exc}"
        return f"  [le vas a mostrar: {nombre} — ahora escribí qué le decís]"
    return f"  comando desconocido: {comando} (probá /ayuda)"


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------
def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tijuana",
        description="TIJUANA — prototipo de diálogo con dos compuertas.",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="genera el diálogo con Claude (requiere el extra 'llm' y credenciales)",
    )
    parser.add_argument("--modelo", help="modelo a usar con --llm")
    parser.add_argument("--npc", help="con quién hablás (por defecto, el del caso)")
    parser.add_argument("--datos", type=Path, help="directorio de datos alternativo")
    parser.add_argument("--guion", type=Path, help="reproduce un guion de entradas")
    parser.add_argument("--demo", action="store_true", help="reproduce el guion de demo")
    parser.add_argument(
        "--sin-debug", action="store_true", help="arranca con el panel oculto"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)

    try:
        contenido = cargar_contenido(args.datos)
        narrador = (
            crear_narrador("llm", modelo=args.modelo)
            if args.llm
            else crear_narrador("plantillas")
        )
        motor = Motor(contenido, npc_id=args.npc, narrador=narrador)
    except ErrorDeContenido as exc:
        print(f"Error de contenido: {exc}")
        return 2

    print(encabezado(motor, narrador.nombre))

    if args.demo or args.guion:
        lineas = guion_demo(args.datos) if args.demo else leer_guion(args.guion)
        return jugar(motor, entradas_de_guion(lineas), not args.sin_debug)

    return jugar(motor, entradas_interactivas(), not args.sin_debug)
