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


# --- export_import (cambio export-import) ------------------------------------
# Tests AÑADIDOS al final (§4 enmendada prohíbe archivos de test nuevos).
# Los 29 tests de arriba NO se modifican. La fixture bd_temporal (autouse)
# sigue aplicando: BD temporal por test bajo tmp_path.

import json

from export_import import ExportImportError, ImportResult, export_games, import_games


def _escribir_import(path, games, version=1):
    """Escribe un archivo con el envoltorio D7 a mano (casos sintéticos)."""
    payload = {
        "app": "NuncaAcaboLosJuegos",
        "version": version,
        "exported_at": "2026-09-24T12:00:00",
        "games": games,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_export_import_roundtrip_preserva_todos_los_campos_con_acentos(tmp_path,):
    # Dado: 3 juegos con texto español (tildes, ñ, ¿) y todos los campos
    db.create_game(
        "Ori y la Voluntad de las Luciérnagas",
        "PC",
        "completado",
        hours_played=12.5,
        progress_note="¡Fin del capítulo Ñ! ¿Qué tal?",
        episode_url="https://youtu.be/ejemplo",
    )
    db.create_game(
        "Celeste",
        "Switch",
        "en_curso",
        hours_played=3,
        progress_note="Capítulo 3 — punto donde lo dejé",
        episode_url="",
    )
    db.create_game("Hades", "PS5", "pendiente")
    origen = db.list_games()

    # Cuando: se exporta
    ruta = tmp_path / "backlog.json"
    assert export_games(ruta) == 3
    # UTF-8 con ensure_ascii=False: el texto español queda legible en el archivo
    assert "Luciérnagas" in ruta.read_text(encoding="utf-8")

    # ... la BD se vacía y se reimporta
    for juego in origen:
        db.delete_game(juego.id)
    assert db.list_games() == []
    result = import_games(ruta)

    # Entonces: backlog idéntico campo a campo (ids asignados por la BD)
    assert result == ImportResult(created=3, updated=0)
    destino = db.list_games()
    assert len(destino) == 3
    campos = (
        "title",
        "platform",
        "status",
        "hours_played",
        "progress_note",
        "episode_url",
    )
    for original, reimportado in zip(origen, destino):
        for campo in campos:
            assert getattr(original, campo) == getattr(reimportado, campo)


def test_import_misma_clave_sobrescribe_los_cuatro_campos(tmp_path,):
    # Dado: juego existente y archivo con la MISMA (title, platform)
    juego = db.create_game(
        "Hollow Knight",
        "PC",
        "pendiente",
        hours_played=1,
        progress_note="nota vieja",
        episode_url="https://youtu.be/viejo",
    )
    ruta = tmp_path / "merge.json"
    _escribir_import(
        ruta,
        [
            {
                "id": 999,  # id del archivo: NUNCA se usa
                "title": "Hollow Knight",
                "platform": "PC",
                "status": "completado",
                "hours_played": 40.5,
                "progress_note": "nota nueva",
                "episode_url": "https://youtu.be/nuevo",
            }
        ],
    )

    # Cuando: se importa
    result = import_games(ruta)

    # Entonces: SOBRESCRITURA — created=0, updated=1, misma fila e id local
    assert result == ImportResult(created=0, updated=1)
    assert len(db.list_games()) == 1
    refetched = db.get_game(juego.id)
    assert refetched.id == juego.id
    assert refetched.title == "Hollow Knight"
    assert refetched.platform == "PC"
    assert refetched.status == "completado"
    assert refetched.hours_played == 40.5
    assert refetched.progress_note == "nota nueva"
    assert refetched.episode_url == "https://youtu.be/nuevo"


def test_import_mismo_titulo_plataforma_distinta_crea_registro_nuevo(tmp_path,):
    # Dado: "Hollow Knight" ya existe en PC; el archivo trae la misma clave en Switch
    db.create_game("Hollow Knight", "PC", "pendiente")
    ruta = tmp_path / "plataforma.json"
    _escribir_import(
        ruta,
        [
            {
                "title": "Hollow Knight",
                "platform": "Switch",
                "status": "en_curso",
                "hours_played": 5,
            }
        ],
    )

    # Cuando: se importa
    result = import_games(ruta)

    # Entonces: fila nueva (DECISIÓN-004 intacta); el de PC no cambia
    assert result == ImportResult(created=1, updated=0)
    juegos = db.list_games()
    assert len(juegos) == 2
    assert {juego.platform for juego in juegos} == {"PC", "Switch"}
    pc = next(juego for juego in juegos if juego.platform == "PC")
    assert pc.status == "pendiente"


def test_import_registro_totalmente_nuevo_lo_crea_con_id_de_la_bd(tmp_path,):
    # Dado: BD vacía y archivo con un juego desconocido (id=42 del archivo)
    ruta = tmp_path / "nuevo.json"
    _escribir_import(
        ruta,
        [
            {
                "id": 42,
                "title": "Celeste",
                "platform": "Switch",
                "status": "en_curso",
                "hours_played": 12.5,
                "progress_note": "Capítulo 3",
                "episode_url": "https://youtu.be/ejemplo",
            }
        ],
    )

    # Cuando: se importa
    result = import_games(ruta)

    # Entonces: creado con id asignado por la BD (el 42 se ignora)
    assert result == ImportResult(created=1, updated=0)
    juegos = db.list_games()
    assert len(juegos) == 1
    assert juegos[0].id == 1
    assert juegos[0].progress_note == "Capítulo 3"


def test_import_json_malformado_lanza_error_y_no_toca_la_bd(tmp_path,):
    # Dado: backlog con datos y un archivo JSON roto
    _crear_tres_juegos()
    antes = db.list_games()
    ruta = tmp_path / "roto.json"
    ruta.write_text(
        '{"app": "NuncaAcaboLosJuegos", "version": 1, "games": [{"title": "Celeste"',
        encoding="utf-8",
    )

    # Cuando/Entonces: se rechaza con motivo y la BD queda INTACTA
    with pytest.raises(ExportImportError):
        import_games(ruta)
    assert db.list_games() == antes


def test_import_archivo_con_registros_invalidos_es_todo_o_nada(tmp_path,):
    # Dado: backlog con datos y archivos parcialmente válidos (2 válidos + 1 inválido)
    _crear_tres_juegos()
    validos = [
        {"title": "Juego válido 1", "platform": "PC", "status": "pendiente"},
        {"title": "Juego válido 2", "platform": "PC", "status": "pendiente"},
    ]
    invalidos = [
        {"title": "", "platform": "PC", "status": "pendiente"},  # título vacío
        {"title": "Mal Estado", "platform": "PC", "status": "jugando"},  # status fuera de los 4
        {  # horas negativas
            "title": "Malas Horas",
            "platform": "PC",
            "status": "pendiente",
            "hours_played": -5,
        },
        {"platform": "PC", "status": "pendiente"},  # campo requerido ausente
    ]

    for i, invalido in enumerate(invalidos):
        antes = db.list_games()
        ruta = tmp_path / f"parcial_{i}.json"
        _escribir_import(ruta, [validos[0], invalido, validos[1]])

        # Cuando/Entonces: un SOLO ExportImportError con motivo + índice del
        # registro problemático, y CERO cambios en la BD (los 2 válidos NO se aplican)
        with pytest.raises(ExportImportError) as exc_info:
            import_games(ruta)
        assert "registro 1" in str(exc_info.value)
        assert db.list_games() == antes


def test_import_duplicado_en_archivo_gana_la_primera_aparicion(tmp_path,):
    # Dado: ("Celeste", "PC") DOS veces en el archivo, con datos distintos
    ruta = tmp_path / "dup.json"
    _escribir_import(
        ruta,
        [
            {
                "title": "Celeste",
                "platform": "PC",
                "status": "en_curso",
                "hours_played": 10,
                "progress_note": "primera",
            },
            {
                "title": "Celeste",
                "platform": "PC",
                "status": "completado",
                "hours_played": 99,
                "progress_note": "segunda",
            },
        ],
    )

    # Cuando: se importa (sin match previo en la BD)
    result = import_games(ruta)

    # Entonces: FIRST-wins — 1 sola fila con los datos de la PRIMERA;
    # la repetición se descarta sin aplicar ni contar → ImportResult(1, 0)
    assert result == ImportResult(created=1, updated=0)
    juegos = db.list_games()
    assert len(juegos) == 1
    assert juegos[0].status == "en_curso"
    assert juegos[0].hours_played == 10
    assert juegos[0].progress_note == "primera"


def test_export_backlog_vacio_escribe_json_valido_y_reimporta(tmp_path,):
    # Dado: BD sin juegos
    assert db.list_games() == []
    ruta = tmp_path / "vacio.json"

    # Cuando: se exporta
    cuenta = export_games(ruta)

    # Entonces: JSON válido con games: [], cuenta 0, y reimporta limpio
    assert cuenta == 0
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["version"] == 1
    assert datos["games"] == []
    assert import_games(ruta) == ImportResult(created=0, updated=0)


# --- rechazos de envoltorio (añadidos en verify: cierran la brecha de cobertura
#     conocida — version>1 / forma errónea / no-UTF8 eran solo evidencia ad-hoc) --


def test_import_version_mayor_que_uno_se_rechaza_sin_tocar_la_bd(tmp_path,):
    # Dado: un juego en la BD y un archivo con version=2
    db.create_game("Hollow Knight", "PC", "pendiente")
    antes = db.list_games()
    ruta = tmp_path / "v2.json"
    _escribir_import(ruta, [], version=2)

    # Cuando/Entonces: se rechaza con motivo claro y la BD queda intacta
    with pytest.raises(ExportImportError) as exc_info:
        import_games(ruta)
    assert "Versión" in str(exc_info.value)
    assert "2" in str(exc_info.value)
    assert db.list_games() == antes


def test_import_archivo_sin_forma_de_exportacion_se_rechaza(tmp_path,):
    # Dado: JSON válido PERO sin la forma del envoltorio (sin lista 'games')
    db.create_game("Hollow Knight", "PC", "pendiente")
    antes = db.list_games()
    ruta = tmp_path / "nogames.json"
    ruta.write_text('{"version": 1, "otra_cosa": true}', encoding="utf-8")

    # Cuando/Entonces: rechazo con motivo 'games' y BD intacta
    with pytest.raises(ExportImportError) as exc_info:
        import_games(ruta)
    assert "games" in str(exc_info.value)
    assert db.list_games() == antes


def test_import_archivo_no_utf8_se_rechaza_sin_tocar_la_bd(tmp_path,):
    # Dado: un archivo con bytes que NO son UTF-8 (p. ej. binario/equivocado)
    db.create_game("Hollow Knight", "PC", "pendiente")
    antes = db.list_games()
    ruta = tmp_path / "binario.json"
    ruta.write_bytes(b"\xff\xfe\x00\x00garbage\x9c\x00")

    # Cuando/Entonces: rechazo de lectura y BD intacta
    with pytest.raises(ExportImportError) as exc_info:
        import_games(ruta)
    assert "leer" in str(exc_info.value)
    assert db.list_games() == antes
