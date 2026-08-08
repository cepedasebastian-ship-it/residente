"""TIJUANA — motor de diálogo de dos compuertas.

Uso mínimo:

    from tijuana import Motor, cargar_contenido

    motor = Motor(cargar_contenido())
    print(motor.turno("¿te acuerdas de esta chica?").respuesta)
"""

from __future__ import annotations

from .carga import Contenido, cargar_contenido, guion_demo
from .estado import Estado
from .modelos import ErrorDeContenido
from .motor import Motor, Turno
from .narradores import NarradorPlantillas, crear_narrador

__version__ = "1.0.0"

__all__ = [
    "Contenido",
    "ErrorDeContenido",
    "Estado",
    "Motor",
    "NarradorPlantillas",
    "Turno",
    "cargar_contenido",
    "crear_narrador",
    "guion_demo",
    "__version__",
]
