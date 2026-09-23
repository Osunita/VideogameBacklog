"""Tests unitarios de models (§11): validaciones de Game, sin BD."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from models import Game


def test_crear_game_con_datos_validos():
    game = Game(title="Hollow Knight", platform="PC", status="pendiente")
    assert game.title == "Hollow Knight"
    assert game.platform == "PC"
    assert game.status == "pendiente"
    assert game.hours_played == 0
    assert game.progress_note == ""
    assert game.episode_url == ""
    assert game.id is None


def test_crear_game_con_todos_los_campos():
    game = Game(
        title="Celeste",
        platform="Switch",
        status="en_curso",
        hours_played=12.5,
        progress_note="Capítulo 3",
        episode_url="https://youtu.be/ejemplo",
        id=7,
    )
    assert game.hours_played == 12.5
    assert game.progress_note == "Capítulo 3"
    assert game.episode_url == "https://youtu.be/ejemplo"
    assert game.id == 7


def test_rechazar_titulo_vacio():
    with pytest.raises(ValueError):
        Game(title="", platform="PC", status="pendiente")


def test_rechazar_plataforma_vacia():
    with pytest.raises(ValueError):
        Game(title="Celeste", platform="", status="pendiente")


def test_rechazar_horas_negativas():
    with pytest.raises(ValueError):
        Game(title="Celeste", platform="PC", status="pendiente", hours_played=-1)


def test_rechazar_estado_no_valido():
    with pytest.raises(ValueError):
        Game(title="Celeste", platform="PC", status="jugando")


def test_horas_cero_son_validas():
    game = Game(title="Celeste", platform="PC", status="completado", hours_played=0)
    assert game.hours_played == 0


def test_estados_validos_coinciden_con_config():
    from config import STATUSES

    assert STATUSES == ("pendiente", "en_curso", "abandonado", "completado")
    for status in STATUSES:
        Game(title="Juego", platform="PC", status=status)
