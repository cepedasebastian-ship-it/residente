"""El turno completo, y la garantía de que el caso sigue siendo resoluble."""

from __future__ import annotations

from tijuana import Motor, cargar_contenido, guion_demo
from tijuana.cli import jugar

LARGA_EN = (
    "do you remember this girl who was here last night with the red dress "
    "and the black bag please"
)


def test_el_guion_de_demo_destraba_las_cuatro_verdades(motor):
    jugar(motor, iter(guion_demo()), debug=False)

    assert motor.completo(), f"quedaron pendientes: {motor.verdades_pendientes()}"
    # Las tres creencias falsas del tablero quedan tachadas.
    assert motor.estado.creencias_en_pie() == []


def test_si_no_te_entiende_no_revela_nada(motor):
    motor.mostrar("aro")
    turno = motor.turno(LARGA_EN)

    assert turno.comprension == "baja"
    assert turno.revelaciones == ()
    assert turno.respuesta == motor.npc.reaccion("incomprension", "en")


def test_ingles_corto_con_prueba_si_revela(motor):
    motor.mostrar("aro")
    turno = motor.turno("remember this girl?")

    assert turno.comprension == "alta"
    assert turno.ids_revelados == ["marisol_estaba_asustada"]
    # Contesta en el idioma del jugador.
    assert turno.respuesta == motor.npc.verdades["marisol_estaba_asustada"].texto.en


def test_mientras_esta_trabado_miente_con_su_tell(motor):
    turno = motor.turno("¿te acuerdas de la chica?")

    mentira = motor.npc.mentiras["la_chica"]
    assert turno.revelaciones == ()
    assert mentira.texto.es in turno.respuesta
    assert mentira.tell in turno.respuesta


def test_asustado_no_suelta_nada_ni_lo_anota_en_el_tablero(motor):
    motor.estado.presion = 3
    motor.mostrar("aro")
    turno = motor.turno("¿te acuerdas de la chica?")

    assert turno.peligro
    assert turno.revelaciones == ()
    assert "marisol_estaba_asustada" not in motor.estado.sabidas
    assert turno.respuesta == motor.npc.reaccion("peligro", "es")


def test_revelar_tacha_la_creencia_que_contradice(motor):
    motor.mostrar("aro")
    motor.turno("¿te acuerdas de la chica?")

    traicion = motor.estado.tarjeta("traicion")
    assert traicion is not None
    assert traicion.tachada
    assert traicion.tachada_por == ["marisol_estaba_asustada"]


def test_la_prueba_se_consume_en_un_solo_turno(motor):
    motor.mostrar("pulsera")
    primero = motor.turno("hola amigo")
    segundo = motor.turno("¿quién me hizo esto?")

    assert primero.mostrando == "pulsera"
    assert segundo.mostrando is None
    assert segundo.revelaciones == ()


def test_el_motor_recuerda_la_conversacion(motor):
    motor.turno("hola amigo")
    motor.turno("¿te acuerdas de la chica?")

    assert len(motor.estado.historial) == 2
    assert motor.estado.historial[0][0] == "hola amigo"


def test_dos_partidas_no_comparten_estado(contenido):
    uno = Motor(contenido)
    otro = Motor(contenido)
    uno.mostrar("aro")
    uno.turno("¿te acuerdas de la chica?")

    assert otro.estado.sabidas == set()
    assert otro.estado.tarjeta("traicion").tachada is False


def test_el_camino_a_presion_tambien_funciona():
    # No hay una sola forma de sacarle la primera verdad: apretar también sirve,
    # siempre que no se pase de rosca.
    motor = Motor(cargar_contenido())
    motor.estado.presion = 2
    turno = motor.turno("¿te acuerdas de la chica?")

    assert turno.ids_revelados == ["marisol_estaba_asustada"]
