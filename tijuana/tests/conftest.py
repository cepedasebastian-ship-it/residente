from __future__ import annotations

import pytest

from tijuana import Motor, cargar_contenido


@pytest.fixture(scope="session")
def contenido():
    return cargar_contenido()


@pytest.fixture
def motor(contenido) -> Motor:
    return Motor(contenido)


@pytest.fixture
def npc(contenido):
    return contenido.npc()


@pytest.fixture
def lexico(contenido):
    return contenido.lexico
