"""Entidad Game y validaciones de datos (§4, §5).

No accede a datos ni a la UI. Todas las validaciones lanzan ValueError (§6).
DECISIÓN-004 confirmada: los títulos DUPLICADOS están permitidos (sin unicidad).
"""

from dataclasses import dataclass

from config import STATUSES


@dataclass
class Game:
    """Modelo de un juego del backlog (§5).

    - id: autogenerado por SQLite; None antes de persistir.
    - title / platform: obligatorios, no vacíos.
    - status: uno de config.STATUSES.
    - hours_played: >= 0, por defecto 0.
    - progress_note / episode_url: opcionales, texto libre.
    """

    title: str
    platform: str
    status: str
    hours_played: float = 0
    progress_note: str = ""
    episode_url: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Valida todos los campos; lanza ValueError si alguno es inválido (AC-006)."""
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("El título no puede estar vacío")
        if not isinstance(self.platform, str) or not self.platform.strip():
            raise ValueError("La plataforma no puede estar vacía")
        if self.status not in STATUSES:
            raise ValueError(
                f"Estado no válido: {self.status!r} (válidos: {', '.join(STATUSES)})"
            )
        if isinstance(self.hours_played, bool) or not isinstance(
            self.hours_played, (int, float)
        ):
            raise ValueError("Las horas jugadas deben ser un número")
        if self.hours_played < 0:
            raise ValueError("Las horas jugadas no pueden ser negativas")
