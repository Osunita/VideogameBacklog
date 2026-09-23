"""Rutas y constantes de la aplicación (§4).

Solo importa librería estándar. No accede a datos ni a la UI.
"""

import os
from pathlib import Path

APP_NAME = "NuncaAcaboLosJuegos"

# §9: %APPDATA%\NuncaAcaboLosJuegos\backlog.db (casing exacto).
# El directorio NO se crea aquí: lo crea init_db() en db.py.
DB_DIR = Path(os.environ["APPDATA"]) / APP_NAME
DB_PATH = DB_DIR / "backlog.db"

# Estados válidos de un juego (§5 / DECISIÓN-003 de la especificación).
STATUSES = ("pendiente", "en_curso", "abandonado", "completado")
