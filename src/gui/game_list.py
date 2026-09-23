"""Listado de juegos (§4).

Tabla con ttk.Treeview estilizado al tema oscuro (D3). NO accede a datos:
solo pinta las filas filtradas que recibe desde app.py. Muestra el
placeholder "Sin resultados" cuando la lista está vacía (§10 — no es un error).
"""

from tkinter import ttk

import customtkinter as ctk

from models import Game

_STYLE_READY = False


def status_label(status: str) -> str:
    """Etiqueta visible de un estado, SOLO para mostrar ("en_curso" → "en curso").

    El valor almacenado (config.STATUSES) y el que se pasa a db.list_games()
    NO cambian: esta función es exclusivamente de presentación y se comparte
    con app.py y game_form.py (helper aquí porque game_list no importa a los
    demás módulos del paquete → sin ciclos).
    """
    return status.replace("_", " ")


def _ensure_dark_style() -> None:
    """Configura (una sola vez) el estilo oscuro del Treeview (D3)."""
    global _STYLE_READY
    if _STYLE_READY:
        return
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Game.Treeview",
        background="#2b2b2b",
        fieldbackground="#2b2b2b",
        foreground="#ecebe4",
        borderwidth=0,
        rowheight=26,
        font=("Segoe UI", 10),
    )
    style.configure(
        "Game.Treeview.Heading",
        background="#343638",
        foreground="#ecebe4",
        relief="flat",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Game.Treeview",
        background=[("selected", "#1f538d")],
        foreground=[("selected", "#ffffff")],
    )
    _STYLE_READY = True


class GameList(ctk.CTkFrame):
    """Listado de juegos: Treeview + scrollbar + placeholder (§4, §10)."""

    _COLUMNS = (
        ("title", "Título", 320, True),
        ("platform", "Plataforma", 140, False),
        ("status", "Estado", 120, False),
        ("hours_played", "Horas", 80, False),
    )

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        _ensure_dark_style()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        columns = [name for name, _, _, _ in self._COLUMNS]
        self._tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Game.Treeview",
        )
        for name, label, width, stretch in self._COLUMNS:
            self._tree.heading(name, text=label)
            self._tree.column(name, width=width, stretch=stretch, anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Placeholder "Sin resultados": se superpone al centro de la tabla vacía.
        self._placeholder = ctk.CTkLabel(
            self,
            text="Sin resultados",
            text_color="#9e9e9e",
            font=ctk.CTkFont(size=14),
        )
        self._placeholder_visible = False
        self._show_placeholder(True)

    def render(self, games: list[Game]) -> None:
        """Vacía la tabla y pinta solo las filas recibidas (§4)."""
        self._tree.delete(*self._tree.get_children())
        for index, game in enumerate(games, start=1):
            iid = str(game.id) if game.id is not None else f"row-{index}"
            self._tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    game.title,
                    game.platform,
                    status_label(game.status),  # solo display; game.status no cambia
                    f"{game.hours_played:g}",
                ),
            )
        self._show_placeholder(not games)

    def _show_placeholder(self, show: bool) -> None:
        if show and not self._placeholder_visible:
            self._placeholder.place(relx=0.5, rely=0.5, anchor="center")
        elif not show and self._placeholder_visible:
            self._placeholder.place_forget()
        self._placeholder_visible = show

    def get_selected_id(self) -> int | None:
        """Id (int) del juego seleccionado, o None si no hay selección."""
        selection = self._tree.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except ValueError:
            return None
