"""El contenido se valida al cargar, no en medio de una partida."""

from __future__ import annotations

from dataclasses import replace

import pytest

from tijuana import cargar_contenido
from tijuana.carga import validar_npc, cargar_npc, validar_contra_caso
from tijuana.modelos import Condicion, ErrorDeContenido, Requisito, Texto, Verdad


def test_todo_el_contenido_del_caso_carga(contenido):
    assert contenido.caso.npcs
    for npc_id in contenido.caso.npcs:
        npc = contenido.npc(npc_id)
        assert npc.verdades and npc.conceptos


def test_cada_mentira_tapa_una_verdad_alcanzable(contenido):
    for npc in contenido.npcs.values():
        for concepto, mentira in npc.mentiras.items():
            verdad = npc.verdades[mentira.verdad]
            assert verdad.requiere.concepto == concepto, (
                f"la mentira de '{concepto}' tapa una verdad que se destraba "
                f"hablando de '{verdad.requiere.concepto}': el jugador nunca "
                "podría llegar a ella"
            )


def test_cada_concepto_tiene_su_mentira(contenido):
    for npc in contenido.npcs.values():
        assert set(npc.conceptos) == set(npc.mentiras)


def test_las_verdades_no_forman_ciclos(contenido):
    for npc in contenido.npcs.values():
        resueltas: set[str] = set()
        for _ in range(len(npc.verdades)):
            for vid, verdad in npc.verdades.items():
                previas = {
                    p
                    for cond in (verdad.requiere.base, *verdad.requiere.cualquiera_de)
                    for p in cond.verdades_previas
                }
                if previas <= resueltas:
                    resueltas.add(vid)
        assert resueltas == set(npc.verdades), "hay verdades inalcanzables"


def test_npc_inexistente_da_error_claro(contenido):
    with pytest.raises(ErrorDeContenido, match="no existe el NPC"):
        contenido.npc("la_mesera")


def test_mentira_hacia_una_verdad_inexistente_se_rechaza(contenido):
    npc = contenido.npc()
    rota = replace(npc, mentiras={"la_chica": replace(npc.mentiras["la_chica"], verdad="no_existe")})
    with pytest.raises(ErrorDeContenido, match="verdad inexistente"):
        validar_npc(rota, "npc de prueba")


def test_verdad_sobre_un_concepto_inexistente_se_rechaza(contenido):
    npc = contenido.npc()
    inventada = Verdad(
        id="inventada",
        tablero="...",
        texto=Texto(es="...", en="..."),
        requiere=Requisito(concepto="el_perro"),
    )
    rota = replace(npc, verdades={**npc.verdades, "inventada": inventada})
    with pytest.raises(ErrorDeContenido, match="concepto inexistente"):
        validar_npc(rota, "npc de prueba")


def test_contradecir_una_tarjeta_inexistente_se_rechaza(contenido):
    npc = contenido.npc()
    verdad = replace(npc.verdades["marisol_estaba_asustada"], contradice="fantasma")
    rota = replace(npc, verdades={**npc.verdades, "marisol_estaba_asustada": verdad})
    with pytest.raises(ErrorDeContenido, match="no es una creencia del caso"):
        validar_contra_caso(rota, contenido.caso)


def test_pedir_una_prueba_inexistente_se_rechaza(contenido):
    npc = contenido.npc()
    original = npc.verdades["marisol_estaba_asustada"]
    requiere = replace(original.requiere, cualquiera_de=(Condicion(prueba="navaja"),))
    rota = replace(
        npc,
        verdades={**npc.verdades, "marisol_estaba_asustada": replace(original, requiere=requiere)},
    )
    with pytest.raises(ErrorDeContenido, match="prueba inexistente"):
        validar_contra_caso(rota, contenido.caso)


def test_claves_desconocidas_en_una_condicion_se_rechazan():
    with pytest.raises(ErrorDeContenido, match="desconocidas"):
        Condicion.desde_dict({"confianza_minima": 2}, "prueba")


def test_datos_alternativos(tmp_path, contenido):
    # El motor no está atado al `datos/` del paquete: se puede apuntar a otro.
    import shutil

    from tijuana.carga import directorio_datos

    destino = tmp_path / "datos"
    shutil.copytree(directorio_datos(), destino)
    otro = cargar_contenido(destino)
    assert set(otro.npcs) == set(contenido.npcs)


def test_cargar_npc_inexistente_da_error(tmp_path):
    with pytest.raises(ErrorDeContenido, match="no existe el archivo"):
        cargar_npc("nadie", tmp_path)
