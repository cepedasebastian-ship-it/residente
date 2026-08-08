"""Narrador determinista: usa los textos escritos en la ficha del NPC.

Es el modo por defecto. No necesita red ni API key, y como es determinista
sirve de oráculo en los tests: si el motor está bien, la línea es predecible.
"""

from __future__ import annotations

from .base import ContextoTurno


class NarradorPlantillas:
    nombre = "plantillas"

    def responder(self, ctx: ContextoTurno) -> str:
        npc, idioma = ctx.npc, ctx.idioma

        if ctx.comprension == "baja":
            # Un NPC que finge entender no lo admite: contesta cualquier cosa.
            # El motor ya se encargó de que no revele nada.
            if not npc.finge_entender:
                return npc.reaccion("incomprension", idioma)
            return self._mentira_o_relleno(ctx)

        if ctx.peligro:
            return npc.reaccion("peligro", idioma)

        if ctx.revelaciones:
            linea = " ".join(v.texto.en_idioma(idioma) for v in ctx.revelaciones)
            return self._con_duda(ctx, linea)

        return self._con_duda(ctx, self._mentira_o_relleno(ctx))

    def _mentira_o_relleno(self, ctx: ContextoTurno) -> str:
        """La mentira que corresponde al tema, o el latiguillo de siempre."""
        for concepto in ctx.conceptos:
            mentira = ctx.npc.mentira_de(concepto)
            if mentira and mentira.verdad not in ctx.estado.sabidas:
                linea = mentira.texto.en_idioma(ctx.idioma)
                return f"{linea} {mentira.tell}".strip() if mentira.tell else linea
        return ctx.npc.reaccion("relleno", ctx.idioma)

    def _con_duda(self, ctx: ContextoTurno, linea: str) -> str:
        """Con comprensión parcial el NPC contesta, pero titubeando."""
        if ctx.comprension != "media":
            return linea
        duda = ctx.npc.reaccion("comprension_parcial", ctx.idioma)
        return f"{duda} {linea}".strip()
