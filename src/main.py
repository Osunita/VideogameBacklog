"""Punto de entrada (§4): inicializa la BD y lanza la ventana principal.

No contiene lógica de UI ni de acceso a datos directo (solo init_db(), que es
su responsabilidad de arranque). Si la BD está corrupta o bloqueada, muestra un
mensaje de error y NO continúa, sin intentar repararla (§10).
"""

import sqlite3
import sys
from tkinter import messagebox

from config import APP_NAME
import db
from gui.app import App


def main() -> None:
    try:
        db.init_db()
    except (sqlite3.Error, OSError) as exc:
        messagebox.showerror(
            APP_NAME,
            f"No se pudo abrir la base de datos:\n{exc}\n\n"
            "La aplicación no puede continuar.",
        )
        sys.exit(1)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
