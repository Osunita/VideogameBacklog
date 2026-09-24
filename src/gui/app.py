"""Ventana principal: orquesta listado y formulario y gestiona los filtros (§4).

NO ejecuta SQL: toda consulta y persistencia pasa por db.py. Las opciones del
filtro de plataforma se derivan en memoria de list_games() sin filtros (D4:
la interfaz de db.py §6 no expone una función DISTINCT).

Exportar/Importar (cambio export-import) solo abren diálogos, muestran avisos
y refrescan: la lógica JSON vive en export_import.py (cero SQL, sin GUI).
"""

from tkinter import filedialog, messagebox

import customtkinter as ctk

import db
import export_import
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
    """Ventana principal (§4): filtros + "Añadir juego"/Exportar/Importar +
    listado en tarjetas.

    Editar/Eliminar viven en CADA tarjeta (game_list llama a _edit_game /
    _delete_game con el id) → sin selección global ni avisos "selecciona un
    juego".
    """

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        # Fondo de ventana más oscuro que las tarjetas (#2b2b2b) → destacan.
        self.configure(fg_color="#1f1f1f")
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

        # Cabecera: filtros a la izquierda; a la derecha, el grupo de
        # acciones: Exportar/Importar en estilo SECUNDARIO (borde fino, sin
        # relleno, mismo corner_radius/height) y "Añadir juego" arriba a la
        # derecha con color de acento → sigue siendo el único botón acento.
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.pack(side="right", padx=(12, 0))
        # side="left" en orden de lectura: Exportar | Importar | Añadir juego.
        for texto, comando in (
            ("Exportar", self._export_games),
            ("Importar", self._import_games),
        ):
            ctk.CTkButton(
                actions,
                text=texto,
                fg_color="transparent",
                border_width=1,
                border_color="#565656",
                hover_color="#3d3d3d",
                text_color="#ecebe4",
                corner_radius=8,
                height=34,
                command=comando,
            ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Añadir juego",
            fg_color="#1f538d",
            hover_color="#1f6ebb",
            corner_radius=8,
            height=34,
            command=self._add_game,
        ).pack(side="left")

        # Barra de filtros: estado, plataforma, búsqueda por título (§4).
        # Mismo comportamiento que siempre (mismos parámetros de list_games);
        # solo cambia la estética: corner_radius y más espaciado.
        filters = ctk.CTkFrame(header, fg_color="transparent")
        filters.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(filters, text="Estado").pack(side="left")
        self._status_var = ctk.StringVar(value=_ALL_STATUS)
        ctk.CTkOptionMenu(
            filters,
            variable=self._status_var,
            values=[_ALL_STATUS, *(status_label(s) for s in STATUSES)],
            command=self._on_filter_changed,
            width=150,
            corner_radius=8,
        ).pack(side="left", padx=(8, 26))

        ctk.CTkLabel(filters, text="Plataforma").pack(side="left")
        self._platform_var = ctk.StringVar(value=_ALL_PLATFORM)
        self._platform_menu = ctk.CTkOptionMenu(
            filters,
            variable=self._platform_var,
            values=self._platform_values,
            command=self._on_filter_changed,
            width=160,
            corner_radius=8,
        )
        self._platform_menu.pack(side="left", padx=(8, 26))

        self._search_var = ctk.StringVar()
        search = ctk.CTkEntry(
            filters,
            textvariable=self._search_var,
            placeholder_text="Buscar por título…",
            width=240,
            corner_radius=8,
        )
        search.pack(side="left")
        search.bind("<KeyRelease>", self._on_filter_changed)

        # Listado (recibe los datos ya filtrados desde aquí, §4): editar y
        # eliminar se delegan en esta clase desde cada tarjeta.
        self.game_list = GameList(
            self, on_edit=self._edit_game, on_delete=self._delete_game
        )
        self.game_list.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))

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
    # Sin selección global: el id llega desde el ✎/✕ de cada tarjeta.

    def _add_game(self) -> None:
        GameForm(self, on_submit=self._create_game)

    def _create_game(self, data: dict) -> None:
        db.create_game(**data)
        self._refresh()

    def _edit_game(self, game_id: int) -> None:
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

    def _delete_game(self, game_id: int) -> None:
        # §10: confirmación siempre (viene del ✕ de una tarjeta, ya hay id).
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

    # ------------------------------------------------------- export/import --
    # Solo diálogos, avisos y refresh: la lógica JSON (leer/parsear/validar/
    # fusionar) vive en export_import.py (D7-D10, AC-008..AC-011).

    def _export_games(self) -> None:
        """Guardado .json → export_games → aviso con el nº exportados (AC-008)."""
        path = filedialog.asksaveasfilename(
            title="Exportar backlog",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="backlog.json",
            parent=self,
        )
        if not path:
            return  # diálogo cancelado → no-op, sin aviso (AC-008)
        try:
            total = export_import.export_games(path)
        except export_import.ExportImportError as exc:
            # p. ej. ruta no escribible: aviso de error, SIN aviso de éxito.
            messagebox.showerror("Exportar", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Exportar",
            f"{total} juego{'' if total == 1 else 's'} "
            f"exportado{'' if total == 1 else 's'}.",
            parent=self,
        )

    def _import_games(self) -> None:
        """Selección .json → import_games (todo-o-nada) → aviso + refresh."""
        path = filedialog.askopenfilename(
            title="Importar backlog",
            filetypes=[("JSON", "*.json")],
            parent=self,
        )
        if not path:
            return  # diálogo cancelado → no-op, sin aviso (AC-008)
        try:
            resultado = export_import.import_games(path)
        except export_import.ExportImportError as exc:
            # Rechazo total (AC-010): la BD NO se tocó → la lista se queda
            # como estaba; un único modal con TODOS los motivos ("registro i:").
            messagebox.showerror("Importar", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Importar",
            f"{resultado.created} creado{'' if resultado.created == 1 else 's'}, "
            f"{resultado.updated} actualizado{'' if resultado.updated == 1 else 's'}.",
            parent=self,
        )
        self._refresh()
