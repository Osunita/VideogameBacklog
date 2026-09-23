"""Ventana principal: orquesta listado y formulario y gestiona los filtros (§4).

NO ejecuta SQL: toda consulta y persistencia pasa por db.py. Las opciones del
filtro de plataforma se derivan en memoria de list_games() sin filtros (D4:
la interfaz de db.py §6 no expone una función DISTINCT).
"""

from tkinter import messagebox

import customtkinter as ctk

import db
from config import STATUSES

from .game_form import GameForm
from .game_list import GameList, status_label

_ALL_STATUS = "Todos"
_ALL_PLATFORM = "Todas"

# Filtro de estado: el OptionMenu muestra etiquetas ("en curso") y _refresh()
# las traduce de vuelta a los valores de config.STATUSES ("en_curso") antes de
# llamar a db.list_games(). "Todos" no está en el mapa → status=None.
_STATUS_BY_LABEL = {status_label(s): s for s in STATUSES}


class App(ctk.CTk):
    """Ventana principal (§4): filtros + listado + botones CRUD."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("Nunca acabo los juegos")
        self.geometry("920x600")
        self.minsize(760, 440)

        self._platform_values = [_ALL_PLATFORM]
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Barra de filtros: estado, plataforma, búsqueda por título (§4).
        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))

        ctk.CTkLabel(filters, text="Estado").pack(side="left")
        self._status_var = ctk.StringVar(value=_ALL_STATUS)
        ctk.CTkOptionMenu(
            filters,
            variable=self._status_var,
            values=[_ALL_STATUS, *(status_label(s) for s in STATUSES)],
            command=self._on_filter_changed,
            width=150,
        ).pack(side="left", padx=(6, 18))

        ctk.CTkLabel(filters, text="Plataforma").pack(side="left")
        self._platform_var = ctk.StringVar(value=_ALL_PLATFORM)
        self._platform_menu = ctk.CTkOptionMenu(
            filters,
            variable=self._platform_var,
            values=self._platform_values,
            command=self._on_filter_changed,
            width=160,
        )
        self._platform_menu.pack(side="left", padx=(6, 18))

        self._search_var = ctk.StringVar()
        search = ctk.CTkEntry(
            filters,
            textvariable=self._search_var,
            placeholder_text="Buscar por título…",
            width=240,
        )
        search.pack(side="left")
        search.bind("<KeyRelease>", self._on_filter_changed)

        # Listado (recibe los datos ya filtrados desde aquí, §4).
        self.game_list = GameList(self)
        self.game_list.grid(row=1, column=0, sticky="nsew", padx=14, pady=6)

        # Acciones CRUD.
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 14))
        ctk.CTkButton(actions, text="Añadir", command=self._add_game).pack(side="left")
        ctk.CTkButton(
            actions, text="Editar", command=self._edit_game
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            actions,
            text="Eliminar",
            fg_color="#a33333",
            hover_color="#c33333",
            command=self._delete_game,
        ).pack(side="left")

    # --------------------------------------------------------------- filtros --

    def _on_filter_changed(self, event=None) -> None:
        """Refresca al cambiar estado/plataforma (OptionMenu) o escribir (<KeyRelease>)."""
        self._refresh()

    def _sync_platform_options(self) -> None:
        """Deriva las plataformas del filtro en memoria de list_games() (D4)."""
        platforms = sorted({g.platform for g in db.list_games()})
        values = [_ALL_PLATFORM, *platforms]
        if values == self._platform_values:
            return
        self._platform_values = values
        self._platform_menu.configure(values=values)
        # Si la plataforma seleccionada ya no existe, vuelve a "Todas".
        if self._platform_var.get() not in values:
            self._platform_var.set(_ALL_PLATFORM)

    def _refresh(self) -> None:
        """Consulta db.list_games con los filtros actuales y repinta la lista (§7)."""
        self._sync_platform_options()

        status_label_selected = self._status_var.get()
        if status_label_selected == _ALL_STATUS:
            status = None
        else:
            # Etiqueta visible → valor de config.STATUSES (AC-005: el filtro
            # debe seguir pasando "en_curso" a db.list_games).
            status = _STATUS_BY_LABEL.get(status_label_selected, status_label_selected)
        platform = self._platform_var.get()
        if platform == _ALL_PLATFORM:
            platform = None
        search = self._search_var.get().strip() or None

        games = db.list_games(status=status, platform=platform, search=search)
        self.game_list.render(games)

    # ----------------------------------------------------------------- CRUD --

    def _require_selection(self, action: str) -> int | None:
        game_id = self.game_list.get_selected_id()
        if game_id is None:
            messagebox.showwarning(
                action, "Selecciona un juego primero.", parent=self
            )
            return None
        return game_id

    def _add_game(self) -> None:
        GameForm(self, on_submit=self._create_game)

    def _create_game(self, data: dict) -> None:
        db.create_game(**data)
        self._refresh()

    def _edit_game(self) -> None:
        game_id = self._require_selection("Editar")
        if game_id is None:
            return
        game = db.get_game(game_id)
        if game is None:
            # §10: aviso + refresh ante id que ya no existe.
            messagebox.showwarning(
                "Editar",
                f"No existe ningún juego con id {game_id}.",
                parent=self,
            )
            self._refresh()
            return
        GameForm(
            self,
            on_submit=lambda data: self._update_game(game_id, data),
            game=game,
        )

    def _update_game(self, game_id: int, data: dict) -> None:
        try:
            db.update_game(game_id, **data)
        except db.GameNotFoundError as exc:
            # §10: la capa app es la única que maneja ids inexistentes (D1):
            # aviso + refresh, y se traduce a ValueError para que el formulario
            # lo muestre dentro sin cerrarse (D5).
            messagebox.showwarning("Editar", str(exc), parent=self)
            self._refresh()
            raise ValueError(str(exc)) from exc
        self._refresh()

    def _delete_game(self) -> None:
        game_id = self._require_selection("Eliminar")
        if game_id is None:
            return
        if not messagebox.askyesno(
            "Eliminar",
            "¿Seguro que quieres eliminar este juego?",
            parent=self,
        ):
            return
        try:
            db.delete_game(game_id)
        except db.GameNotFoundError as exc:
            # §10: aviso y se refresca la lista.
            messagebox.showwarning("Eliminar", str(exc), parent=self)
        self._refresh()
