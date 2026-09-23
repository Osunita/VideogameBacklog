"""Listado de juegos (§4).

Tabla con ttk.Treeview estilizado al tema oscuro (D3). NO accede a datos:
solo pinta las filas filtradas que recibe desde app.py. Muestra el
placeholder "Sin resultados" cuando la lista está vacía (§10 — no es un error).
Al pasar el ratón por una fila aparece una tarjeta flotante (tooltip, solo
presentación) con progress_note y/o episode_url de ese juego.
"""

from tkinter import TclError, ttk

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


def _tooltip_text(game: Game) -> str:
    """Texto de la tarjeta de hover: nota y/o episodio, o "No hay info".

    Solo presentación: un string de solo espacios cuenta como vacío y un
    campo ausente NO pinta línea alguna (sin huecos ni placeholders).
    episode_url se muestra como texto informativo, NO como enlace clicable.
    """
    lines = []
    if (game.progress_note or "").strip():
        lines.append(f"Nota: {game.progress_note}")
    if (game.episode_url or "").strip():
        lines.append(f"Episodio: {game.episode_url}")
    return "\n".join(lines) if lines else "No hay info"


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
    """Listado de juegos: Treeview + scrollbar + placeholder + tooltip de hover (§4, §10)."""

    _COLUMNS = (
        ("title", "Título", 320, True),
        ("platform", "Plataforma", 140, False),
        ("status", "Estado", 120, False),
        ("hours_played", "Horas", 80, False),
    )

    _TOOLTIP_DELAY_MS = 250  # retardo (ms) de dwell antes de mostrar la tarjeta

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

        # Tarjeta flotante de hover (solo display): UN único Toplevel
        # reutilizado en todos los hovers (nace oculta) → sin fugas de
        # ventanas ni foco robado (overrideredirect + topmost, sin grab).
        self._tooltip = ctk.CTkToplevel(self, fg_color="#2b2b2b")
        self._tooltip.withdraw()
        self._tooltip.overrideredirect(True)  # sin barra de título ni marco
        self._tooltip.attributes("-topmost", True)  # siempre encima de la tabla
        self._tooltip_label = ctk.CTkLabel(
            self._tooltip,
            anchor="w",
            justify="left",
            wraplength=360,
            padx=10,
            pady=8,
            text_color="#ecebe4",
            font=ctk.CTkFont(size=12),
        )
        self._tooltip_label.pack()

        # Juegos ya pintados, indexados por iid de la fila (render los repuebla):
        # el hover lee progress_note/episode_url de aquí, nunca de db.py.
        self._games: dict[str, Game] = {}
        self._tooltip_iid: str | None = None
        self._tooltip_after: str | None = None
        self._tree.bind("<Motion>", self._on_row_motion)
        self._tree.bind("<Leave>", self._on_tree_leave)

    def render(self, games: list[Game]) -> None:
        """Vacía la tabla y pinta solo las filas recibidas (§4)."""
        self._hide_tooltip()
        self._games = {}
        self._tree.delete(*self._tree.get_children())
        for index, game in enumerate(games, start=1):
            iid = str(game.id) if game.id is not None else f"row-{index}"
            self._games[iid] = game  # referencia para el tooltip de hover
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

    # ------------------------------------------------------------- tooltip --

    def _on_row_motion(self, event) -> None:
        """Hover sobre una fila: sigue al cursor o programa la tarjeta (§ display)."""
        iid = self._tree.identify_row(event.y)
        if not iid or iid not in self._games:
            self._hide_tooltip()  # hueco sin fila o cabecera → nada que mostrar
            return
        if iid == self._tooltip_iid and self._tooltip.winfo_viewable():
            # Misma fila: solo reposiciona, sin recrear ni parpadear.
            self._place_tooltip(event.x_root, event.y_root)
            return
        # Fila nueva: oculta la anterior YA (nunca datos obsoletos) y
        # programa la aparición con retardo para evitar parpadeo al barrer.
        self._hide_tooltip()
        self._tooltip_iid = iid
        x_root, y_root = event.x_root, event.y_root
        self._tooltip_after = self.after(
            self._TOOLTIP_DELAY_MS,
            lambda: self._show_tooltip(iid, x_root, y_root),
        )

    def _on_tree_leave(self, event=None) -> None:
        """El cursor salió de la tabla: la tarjeta desaparece al instante."""
        self._hide_tooltip()

    def _show_tooltip(self, iid: str, x_root: int, y_root: int) -> None:
        """Muestra la tarjeta de `iid` junto al cursor (si la fila sigue ahí)."""
        self._tooltip_after = None
        game = self._games.get(iid)
        if game is None or self._tooltip_iid != iid:
            return  # la lista se repintó o el hover ya no apunta a esta fila
        self._tooltip_label.configure(text=_tooltip_text(game))
        self._place_tooltip(x_root, y_root)
        self._tooltip.deiconify()

    def _place_tooltip(self, x_root: int, y_root: int) -> None:
        """Posiciona la tarjeta junto al cursor sin que se salga de la pantalla."""
        self._tooltip.update_idletasks()
        width = self._tooltip.winfo_reqwidth()
        height = self._tooltip.winfo_reqheight()
        x = x_root + 14
        y = y_root + 16
        if x + width > self._tooltip.winfo_screenwidth():
            x = x_root - width - 14
        if y + height > self._tooltip.winfo_screenheight():
            y = y_root - height - 16
        self._tooltip.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _hide_tooltip(self) -> None:
        """Oculta la tarjeta al instante y cancela cualquier aparición pendiente."""
        if self._tooltip_after is not None:
            try:
                self.after_cancel(self._tooltip_after)
            except TclError:
                pass  # callback ya ejecutado
            self._tooltip_after = None
        self._tooltip.withdraw()
        self._tooltip_iid = None

    def get_selected_id(self) -> int | None:
        """Id (int) del juego seleccionado, o None si no hay selección."""
        selection = self._tree.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except ValueError:
            return None
