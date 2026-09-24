"""Exportación e importación del backlog a JSON (cambio export-import).

Un único módulo nuevo (§4 enmendada) entre GUI y db.py: CERO SQL — solo
contratos §6 de db.py (list_games, create_game, update_game) y las
validaciones de models.Game (D9). db.py permanece SQLite-only. No importa GUI.

Formato de archivo (D7): envoltorio JSON versionado, UTF-8 con
ensure_ascii=False (texto español legible):
    {"app", "version": 1, "exported_at", "games": [...]}

Importación (D8): se parsean y validan TODOS los registros ANTES de aplicar
cualquiera; cualquier error se acumula en un ÚNICO ExportImportError y la BD
queda intacta (todo-o-nada).

Regla de fusión por (title, platform) — SPEC manda (AC-009):
- Match exacto → update_game SOBRESCRIBE status/hours_played/progress_note/
  episode_url. El id del archivo NUNCA se usa; si la clave está duplicada en
  la BD, se actualiza el registro de MENOR id.
- Sin match → create_game (id asignado por la BD).
- Duplicado (title, platform) DENTRO del archivo → gana la PRIMERA aparición
  (first-occurrence-wins); las repeticiones se descartan sin aplicar ni
  contar. (El design decía "último gana"; el spec prevalece.)
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import db
from config import APP_NAME
from models import Game

# Versión del formato (D7): > 1 se rechaza al importar (AC-011).
FORMAT_VERSION = 1


class ExportImportError(Exception):
    """Único tipo de error del módulo (D10). El mensaje va en español."""


@dataclass(frozen=True)
class ImportResult:
    """Conteos de una importación aplicada correctamente."""

    created: int
    updated: int


def export_games(path: str | Path) -> int:
    """Exporta el backlog COMPLETO a JSON UTF-8 (list_games() SIN filtros).

    Devuelve el nº de juegos exportados (0 si el backlog está vacío).
    Errores de escritura → ExportImportError.
    """
    juegos = db.list_games()
    payload = {
        "app": APP_NAME,
        "version": FORMAT_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "games": [_game_to_dict(juego) for juego in juegos],
    }
    try:
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ExportImportError(f"No se pudo escribir el archivo: {exc}") from exc
    return len(juegos)


def import_games(path: str | Path) -> ImportResult:
    """Lee, valida TODOS los registros y aplica la fusión (todo-o-nada).

    Cualquier error de lectura, forma, versión o registro lanza
    ExportImportError con el motivo (y el índice del registro problemático)
    SIN tocar la BD.
    """
    juegos_validos = _leer_y_validar(path)
    return _aplicar(juegos_validos)


def _game_to_dict(juego: Game) -> dict:
    """Serializa TODOS los campos del Game (§5) para el archivo."""
    return {
        "id": juego.id,
        "title": juego.title,
        "platform": juego.platform,
        "status": juego.status,
        "hours_played": juego.hours_played,
        "progress_note": juego.progress_note,
        "episode_url": juego.episode_url,
    }


def _leer_y_validar(path: str | Path) -> list[Game]:
    """Fases de lectura/parseo/validación (D8): sin efectos sobre la BD."""
    # 1. Leer (archivo ilegible o codificación no UTF-8 → error).
    try:
        texto = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ExportImportError(f"No se pudo leer el archivo: {exc}") from exc

    # 2. Parsear (JSON malformado/vacío → error).
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ExportImportError(f"El archivo no es JSON válido: {exc}") from exc

    # 3. Forma y versión del envoltorio D7 (campos extra desconocidos → ignorados).
    if not isinstance(datos, dict):
        raise ExportImportError(
            "El archivo no tiene la forma de una exportación "
            "(se esperaba un objeto JSON con 'games')"
        )
    if datos.get("version") != FORMAT_VERSION:
        raise ExportImportError(
            f"Versión de archivo no soportada: {datos.get('version')!r} "
            f"(esta app solo importa la versión {FORMAT_VERSION})"
        )
    registros = datos.get("games")
    if not isinstance(registros, list):
        raise ExportImportError(
            "El archivo no tiene la forma de una exportación "
            "(falta la lista 'games')"
        )

    # 4. Validar TODOS los registros, acumulando TODOS los errores en un solo aviso.
    errores: list[str] = []
    validos: list[Game] = []
    for i, registro in enumerate(registros):
        try:
            validos.append(_validar_registro(registro))
        except ValueError as exc:
            errores.append(f"registro {i}: {exc}")
    if errores:
        raise ExportImportError(
            "El archivo tiene registros inválidos "
            "(no se aplicó ningún cambio):\n" + "\n".join(errores)
        )
    return validos


def _validar_registro(registro: object) -> Game:
    """Construye un Game (reutiliza las validaciones de models, AC-006)."""
    if not isinstance(registro, dict):
        raise ValueError("se esperaba un objeto JSON")
    requeridos = ("title", "platform", "status")
    faltantes = [campo for campo in requeridos if campo not in registro]
    if faltantes:
        raise ValueError(f"faltan campos requeridos: {', '.join(faltantes)}")
    return Game(
        title=registro["title"],
        platform=registro["platform"],
        status=registro["status"],
        # hours_played ausente → 0 (opcional en §5); note/url ausentes o null → "".
        hours_played=registro.get("hours_played", 0),
        progress_note=_texto_opcional(registro, "progress_note"),
        episode_url=_texto_opcional(registro, "episode_url"),
    )


def _texto_opcional(registro: dict, campo: str) -> str:
    """Campo de texto opcional: ausente o null → ''; si no, debe ser str.

    (models no valida el tipo de estos campos, pero la BD es NOT NULL:
    se valida aquí para no fallar a mitad de aplicación.)
    """
    valor = registro.get(campo, "")
    if valor is None:
        return ""
    if not isinstance(valor, str):
        raise ValueError(f"{campo} debe ser texto")
    return valor


def _aplicar(juegos: list[Game]) -> ImportResult:
    """Fusión (title, platform): SOLO se ejecuta tras validar todo el archivo.

    El índice se construye en memoria desde db.list_games() (D9): la lista
    viene ordenada por id, así que con setdefault la clave duplicada en la BD
    conserva el id MENOR.
    """
    indice: dict[tuple[str, str], int] = {}
    for existente in db.list_games():
        indice.setdefault((existente.title, existente.platform), existente.id)

    aplicadas: set[tuple[str, str]] = set()
    created = 0
    updated = 0
    for juego in juegos:
        clave = (juego.title, juego.platform)
        if clave in aplicadas:
            # Duplicado DENTRO del archivo: gana la PRIMERA aparición;
            # esta repetición se descarta sin aplicar ni contar (spec, AC-009).
            continue
        aplicadas.add(clave)

        if clave in indice:
            # Match → SOBRESCRIBE los 4 campos (title/platform son la clave);
            # el id del archivo nunca determina el destino.
            db.update_game(
                indice[clave],
                status=juego.status,
                hours_played=juego.hours_played,
                progress_note=juego.progress_note,
                episode_url=juego.episode_url,
            )
            updated += 1
        else:
            creado = db.create_game(
                title=juego.title,
                platform=juego.platform,
                status=juego.status,
                hours_played=juego.hours_played,
                progress_note=juego.progress_note,
                episode_url=juego.episode_url,
            )
            indice[clave] = creado.id
            created += 1
    return ImportResult(created=created, updated=updated)
