"""Tests unitarios de db (§11) con una BD SQLite TEMPORAL por test (D6).

Cada test fija config.DB_PATH a tmp_path mediante monkeypatch: NUNCA se toca
la BD real de %APPDATA%. Sin conftest.py (estructura cerrada §4).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

import config
import db
from models import Game


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    """BD temporal bajo tmp_path y init_db() antes de cada test.

    Usa una subcarpeta ("data/") para demostrar que init_db crea el
    directorio con parents=True si falta (AC-001).
    """
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "data" / "backlog.db")
    db.init_db()


def _crear_tres_juegos():
    db.create_game("Hollow Knight", "PC", "pendiente")
    db.create_game("Celeste", "Switch", "en_curso")
    db.create_game("Hades", "PS5", "completado")


# --- init_db -----------------------------------------------------------------


def test_init_db_crea_carpeta_archivo_y_tabla():
    assert config.DB_PATH.parent.is_dir()
    assert config.DB_PATH.exists()
    assert db.list_games() == []


# --- create_game (TEST-001) --------------------------------------------------


def test_test_001_create_game_devuelve_game_con_id():
    # Dado: una base de datos vacía
    # Cuando: se llama a create_game("Hollow Knight", "PC", "pendiente")
    game = db.create_game("Hollow Knight", "PC", "pendiente")
    # Entonces: Game con id asignado y status="pendiente"
    assert isinstance(game, Game)
    assert game.id is not None
    assert game.status == "pendiente"


def test_create_game_con_datos_completos():
    game = db.create_game(
        "Celeste",
        "Switch",
        "en_curso",
        hours_played=12.5,
        progress_note="Capítulo 3",
        episode_url="https://youtu.be/ejemplo",
    )
    assert game.hours_played == 12.5
    assert game.progress_note == "Capítulo 3"
    assert game.episode_url == "https://youtu.be/ejemplo"
    assert db.get_game(game.id) == game


def test_create_game_titulo_vacio_lanza_value_error_y_no_persiste():
    with pytest.raises(ValueError):
        db.create_game("", "PC", "pendiente")
    assert db.list_games() == []


def test_create_game_horas_negativas_lanza_value_error():
    with pytest.raises(ValueError):
        db.create_game("Celeste", "PC", "pendiente", hours_played=-5)
    assert db.list_games() == []


def test_create_game_estado_invalido_lanza_value_error():
    with pytest.raises(ValueError):
        db.create_game("Celeste", "PC", "jugando")
    assert db.list_games() == []


def test_titulos_duplicados_permitidos():
    # DECISIÓN-004: mismo título en dos plataformas debe permitirse
    db.create_game("Hades", "PC", "pendiente")
    db.create_game("Hades", "Switch", "completado")
    assert len(db.list_games()) == 2


# --- get_game ----------------------------------------------------------------


def test_get_game_inexistente_devuelve_none():
    assert db.get_game(999) is None


def test_get_game_devuelve_el_juego_persistido():
    created = db.create_game("Hollow Knight", "PC", "pendiente")
    fetched = db.get_game(created.id)
    assert fetched == created


# --- list_games (TEST-002) ---------------------------------------------------


def test_list_games_sin_filtros_devuelve_todos():
    _crear_tres_juegos()
    assert len(db.list_games()) == 3


def test_test_002_list_games_filtra_por_estado():
    # Dado: 3 juegos con estados distintos
    _crear_tres_juegos()
    # Cuando: list_games(status="pendiente")
    result = db.list_games(status="pendiente")
    # Entonces: solo los de ese estado
    assert len(result) == 1
    assert result[0].title == "Hollow Knight"
    assert result[0].status == "pendiente"


def test_list_games_filtra_por_plataforma():
    _crear_tres_juegos()
    result = db.list_games(platform="Switch")
    assert len(result) == 1
    assert result[0].title == "Celeste"


def test_list_games_busqueda_parcial_case_insensitive():
    _crear_tres_juegos()
    result = db.list_games(search="hollow")
    assert len(result) == 1
    assert result[0].title == "Hollow Knight"


def test_list_games_busqueda_sin_resultados():
    _crear_tres_juegos()
    assert db.list_games(search="portal") == []


def test_list_games_filtros_combinados():
    _crear_tres_juegos()
    assert db.list_games(status="pendiente", platform="Switch") == []
    assert len(db.list_games(status="en_curso", platform="Switch")) == 1


# --- update_game -------------------------------------------------------------


def test_update_game_modifica_los_campos_indicados():
    game = db.create_game("Hades", "PC", "pendiente", hours_played=1)
    updated = db.update_game(
        game.id, hours_played=10.5, status="en_curso", progress_note="Asíto 3"
    )
    assert updated.hours_played == 10.5
    assert updated.status == "en_curso"
    assert updated.progress_note == "Asíto 3"
    # Los campos no indicados no cambian
    assert updated.title == "Hades"
    # Persiste en la BD
    refetched = db.get_game(game.id)
    assert refetched.hours_played == 10.5
    assert refetched.status == "en_curso"


def test_update_game_con_datos_invalidos_lanza_value_error():
    game = db.create_game("Hades", "PC", "pendiente")
    with pytest.raises(ValueError):
        db.update_game(game.id, hours_played=-5)
    with pytest.raises(ValueError):
        db.update_game(game.id, status="jugando")
    with pytest.raises(ValueError):
        db.update_game(game.id, title="")
    # No se persistió nada
    assert db.get_game(game.id) == game


def test_update_game_campo_desconocido_lanza_value_error():
    game = db.create_game("Hades", "PC", "pendiente")
    with pytest.raises(ValueError):
        db.update_game(game.id, id=99)


def test_update_game_id_inexistente_lanza_game_not_found_error():
    with pytest.raises(db.GameNotFoundError):
        db.update_game(999, status="en_curso")


# --- delete_game (TEST-003) --------------------------------------------------


def test_test_003_delete_luego_get_devuelve_none():
    # Dado: un juego con id=1
    game = db.create_game("Hollow Knight", "PC", "pendiente")
    assert game.id == 1
    # Cuando: delete_game(1) y después get_game(1)
    db.delete_game(1)
    # Entonces: get_game devuelve None
    assert db.get_game(1) is None
    assert db.list_games() == []


def test_delete_game_id_inexistente_lanza_game_not_found_error():
    with pytest.raises(db.GameNotFoundError):
        db.delete_game(999)
