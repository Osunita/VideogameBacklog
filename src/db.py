"""Capa de acceso a datos: ÚNICA capa que ejecuta SQL (§3, §4, §6).

Conexión por operación (D2): helper _connect() con context manager,
row_factory=sqlite3.Row, commit al salir y cierre garantizado.
"""

import sqlite3
from contextlib import contextmanager

import config
from models import Game

_DDL_GAMES = """
CREATE TABLE IF NOT EXISTS games (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    platform      TEXT NOT NULL,
    status        TEXT NOT NULL CHECK(status IN ('pendiente','en_curso','abandonado','completado')),
    hours_played  REAL NOT NULL DEFAULT 0 CHECK(hours_played >= 0),
    progress_note TEXT NOT NULL DEFAULT '',
    episode_url   TEXT NOT NULL DEFAULT ''
)
"""

# Sin UNIQUE en title: DECISIÓN-004 confirmada (duplicados permitidos).
_UPDATABLE_FIELDS = (
    "title",
    "platform",
    "status",
    "hours_played",
    "progress_note",
    "episode_url",
)


class GameNotFoundError(Exception):
    """Se lanza al actualizar/borrar un id que no existe en la tabla games (§6, D1)."""


@contextmanager
def _connect():
    """Conexión per-call: row_factory=Row, commit al salir, cierra siempre (D2)."""
    conn = sqlite3.connect(config.DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Crea el directorio, el archivo y la tabla games si no existen (§6, AC-001).

    No repara BD corruptas/bloqueadas: la excepción sube a main.py (§10).
    """
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(_DDL_GAMES)


def _row_to_game(row: sqlite3.Row) -> Game:
    return Game(
        id=row["id"],
        title=row["title"],
        platform=row["platform"],
        status=row["status"],
        hours_played=row["hours_played"],
        progress_note=row["progress_note"],
        episode_url=row["episode_url"],
    )


def create_game(
    title: str,
    platform: str,
    status: str,
    hours_played: float = 0,
    progress_note: str = "",
    episode_url: str = "",
) -> Game:
    """Crea un juego y lo devuelve con id asignado (TEST-001, AC-002).

    Errores: ValueError si title/platform vacíos, status inválido o horas < 0
    (valida ANTES de tocar la BD, así no se persiste nada).
    """
    game = Game(
        title=title,
        platform=platform,
        status=status,
        hours_played=hours_played,
        progress_note=progress_note,
        episode_url=episode_url,
    )
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO games (title, platform, status, hours_played, progress_note, episode_url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                game.title,
                game.platform,
                game.status,
                game.hours_played,
                game.progress_note,
                game.episode_url,
            ),
        )
        game.id = cursor.lastrowid
    return game


def get_game(game_id: int) -> Game | None:
    """Devuelve el Game con ese id, o None si no existe (sin lanzar error, §6)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM games WHERE id = ?", (game_id,)
        ).fetchone()
    return _row_to_game(row) if row is not None else None


def update_game(game_id: int, **fields) -> Game:
    """Actualiza los campos indicados y devuelve el Game actualizado (AC-003).

    Errores: GameNotFoundError si el id no existe; ValueError si un campo a
    actualizar es inválido o no es actualizable (valida antes de tocar la BD).
    """
    existing = get_game(game_id)
    if existing is None:
        raise GameNotFoundError(f"No existe ningún juego con id {game_id}")

    unknown = set(fields) - set(_UPDATABLE_FIELDS)
    if unknown:
        raise ValueError(
            f"Campos no actualizables: {', '.join(sorted(unknown))}"
        )

    updated = Game(
        id=existing.id,
        title=fields.get("title", existing.title),
        platform=fields.get("platform", existing.platform),
        status=fields.get("status", existing.status),
        hours_played=fields.get("hours_played", existing.hours_played),
        progress_note=fields.get("progress_note", existing.progress_note),
        episode_url=fields.get("episode_url", existing.episode_url),
    )

    if fields:
        assignments = ", ".join(f"{name} = ?" for name in fields)
        params = [fields[name] for name in fields]
        with _connect() as conn:
            conn.execute(
                f"UPDATE games SET {assignments} WHERE id = ?", [*params, game_id]
            )
    return updated


def delete_game(game_id: int) -> None:
    """Elimina el juego con ese id (AC-004).

    Errores: GameNotFoundError si el id no existe (§6).
    """
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
        if cursor.rowcount == 0:
            raise GameNotFoundError(f"No existe ningún juego con id {game_id}")


def list_games(
    status: str | None = None,
    platform: str | None = None,
    search: str | None = None,
) -> list[Game]:
    """Lista juegos con filtros opcionales (AC-005, §6).

    - status / platform: coincidencia exacta.
    - search: coincidencia parcial case-insensitive en title (LIKE ... COLLATE NOCASE).
    - Sin filtros: devuelve todos, ordenados por id.
    """
    clauses: list[str] = []
    params: list = []

    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if platform is not None:
        clauses.append("platform = ?")
        params.append(platform)
    if search is not None:
        clauses.append("title LIKE ? COLLATE NOCASE")
        params.append(f"%{search}%")

    sql = "SELECT * FROM games"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_game(row) for row in rows]
