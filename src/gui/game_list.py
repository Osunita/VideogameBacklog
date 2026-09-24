"""Listado de juegos por tarjetas (§4).

CTkScrollableFrame con UN CTkFrame por juego: indicador de color del estado a
la izquierda (barra, sin iconos), título en negrita, línea secundaria
"plataforma · horas", píldora de estado a la derecha y botones ✎/✕ SIEMPRE
visibles. NO accesa a datos: solo pinta las tarjetas filtradas que recibe desde
app.py; las acciones se delegan en los callbacks on_edit/on_delete que inyecta
app.py (mismo patrón que el on_submit de game_form — §4 prohíbe que esta capa
toque db.py). Muestra el placeholder "Sin resultados" cuando la lista está
vacía (§10 — no es un error). Al pasar el ratón por una tarjeta aparece una
tarjeta flotante (tooltip, solo presentación) con progress_note y/o
episode_url de ese juego.
"""

from tkinter import TclError

import customtkinter as ctk

from models import Game

# Colores SOLO de presentación: estado → (indicador, fondo píldora, texto
# píldora). El píldora usa un tinte claro del color de estado con texto en tono
# oscuro del mismo tono (legible). Los valores de config.STATUSES no cambian.
_STATUS_COLORS = {
    "pendiente": ("#9e9e9e", "#e4e4e4", "#5f5f5f"),
    "en_curso": ("#3b8ed0", "#d6e7f7", "#1f5f9e"),
    "abandonado": ("#f39c12", "#fdeecd", "#b9770e"),
    "completado": ("#2ecc71", "#d8f3e0", "#1e8449"),
}
_FALLBACK_COLORS = _STATUS_COLORS["pendiente"]  # estado fuera de catálogo
_CARD_BG = "#2b2b2b"  # la ventana (#1f1f1f) es más oscura → las tarjetas destacan


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


class GameList(ctk.CTkFrame):
    """Listado en tarjetas: scroll + placeholder + tooltip de hover (§4, §10).

    on_edit(id) / on_delete(id) los inyecta app.py al construir la lista: esta
    capa solo pinta y delega (patrón on_submit de game_form, D5).
    """

    _TOOLTIP_DELAY_MS = 250  # retardo (ms) de dwell antes de mostrar la tarjeta
    _CARD_HEIGHT = 64  # alto fijo de cada tarjeta (una sola línea de título)

    def __init__(self, master, on_edit=None, on_delete=None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._on_edit = on_edit
        self._on_delete = on_delete
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        # Placeholder "Sin resultados": se superpone al centro del listado vacío.
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
        self._tooltip.attributes("-topmost", True)  # siempre encima del listado
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

        # Juegos ya pintados y sus tarjetas, indexados por clave de juego
        # (render los repuebla): el hover lee progress_note/episode_url de
        # aquí, nunca de db.py.
        self._games: dict[str, Game] = {}
        self._cards: dict[str, ctk.CTkFrame] = {}
        self._tooltip_iid: str | None = None
        self._tooltip_after: str | None = None

    def render(self, games: list[Game]) -> None:
        """Vacía la lista y pinta solo las tarjetas recibidas (§4)."""
        self._hide_tooltip()
        self._games = {}
        for card in self._cards.values():
            card.destroy()
        self._cards = {}
        for index, game in enumerate(games, start=1):
            key = str(game.id) if game.id is not None else f"row-{index}"
            self._games[key] = game  # referencia para el tooltip y callbacks
            self._cards[key] = self._build_card(game, key, index - 1)
        self._show_placeholder(not games)

    def _build_card(self, game: Game, key: str, row: int) -> ctk.CTkFrame:
        """Construye UNA tarjeta: indicador · texto · píldora · ✎ · ✕."""
        indicator_color, pill_bg, pill_text = _STATUS_COLORS.get(
            game.status, _FALLBACK_COLORS
        )

        card = ctk.CTkFrame(
            self._scroll, fg_color=_CARD_BG, corner_radius=10, height=self._CARD_HEIGHT
        )
        card.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 8))
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(0, weight=1)

        # Indicador de estado: barra de color a la izquierda (sin iconos).
        ctk.CTkFrame(
            card, width=8, height=40, fg_color=indicator_color, corner_radius=4
        ).grid(row=0, column=0, sticky="ns", padx=(12, 12), pady=8)

        # Título en negrita + línea secundaria "plataforma · horas".
        text = ctk.CTkFrame(card, fg_color="transparent")
        text.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=(6, 6))
        ctk.CTkLabel(
            text,
            text=game.title,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ecebe4",
        ).pack(fill="x")
        ctk.CTkLabel(
            text,
            text=f"{game.platform} · {game.hours_played:g} h",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color="#9e9e9e",
        ).pack(fill="x")

        # Píldora de estado: etiqueta visible ("en curso", sin guion bajo),
        # fondo en tinte claro y texto en tono oscuro del color del estado.
        pill = ctk.CTkFrame(card, fg_color=pill_bg, corner_radius=12)
        pill.grid(row=0, column=2)
        ctk.CTkLabel(
            pill,
            text=status_label(game.status),
            fg_color="transparent",
            text_color=pill_text,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(padx=10, pady=3)

        # Acciones por tarjeta, SIEMPRE visibles (glifos Unicode, sin assets).
        ctk.CTkButton(
            card,
            text="✎",
            width=36,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color="#565656",
            hover_color="#3d3d3d",
            text_color="#ecebe4",
            command=lambda k=key: self._edit_pressed(k),
        ).grid(row=0, column=3, padx=(10, 4))
        ctk.CTkButton(
            card,
            text="✕",
            width=36,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color="#7a4444",
            hover_color="#a33333",
            text_color="#ecebe4",
            command=lambda k=key: self._delete_pressed(k),
        ).grid(row=0, column=4, padx=(0, 8))

        self._bind_hover(card, key)
        return card

    def _edit_pressed(self, key: str) -> None:
        """✎ de la tarjeta: oculta el tooltip y delega en app.py (§4)."""
        self._hide_tooltip()
        game = self._games.get(key)
        if game is not None and self._on_edit is not None:
            self._on_edit(game.id)

    def _delete_pressed(self, key: str) -> None:
        """✕ de la tarjeta: oculta el tooltip y delega en app.py (§4)."""
        self._hide_tooltip()
        game = self._games.get(key)
        if game is not None and self._on_delete is not None:
            self._on_delete(game.id)

    def _show_placeholder(self, show: bool) -> None:
        if show and not self._placeholder_visible:
            self._placeholder.place(relx=0.5, rely=0.5, anchor="center")
        elif not show and self._placeholder_visible:
            self._placeholder.place_forget()
        self._placeholder_visible = show

    # ------------------------------------------------------------- tooltip --

    def _bind_hover(self, widget, key: str) -> None:
        """Enlaza Enter/Motion/Leave en la tarjeta y TODOS sus hijos.

        Los widgets de CustomTkinter redirigen .bind() a sus canvas/labels
        internos (por eso se recorre el subárbol completo) y se usa add="+" para
        no pisar los handlers internos de hover de los botones. Enter y Motion
        comparten handler: sigue al cursor o reprograma el dwell de 250 ms
        (mismo comportamiento que el barrido de filas del Treeview).
        """
        for sequence, handler in (
            ("<Enter>", lambda e: self._on_card_hover(e, key)),
            ("<Motion>", lambda e: self._on_card_hover(e, key)),
            ("<Leave>", lambda e: self._on_card_leave(e, key)),
        ):
            try:
                widget.bind(sequence, handler, "+")
            except NotImplementedError:
                pass  # widget sin .bind() propio (no ocurre con los actuales)
        for child in widget.winfo_children():
            self._bind_hover(child, key)

    def _on_card_hover(self, event, key: str) -> None:
        """Hover sobre una tarjeta: sigue al cursor o programa la tarjeta (§ display)."""
        if key not in self._cards:
            return  # la lista se repintó y esta tarjeta ya no existe
        if key == self._tooltip_iid and self._tooltip.winfo_viewable():
            # Misma tarjeta visible: solo reposiciona, sin recrear ni parpadear.
            self._place_tooltip(event.x_root, event.y_root)
            return
        # Tarjeta nueva (o movimiento durante el dwell): oculta la anterior YA
        # (nunca datos obsoletos) y (re)programa la aparición con retardo para
        # evitar parpadeo al barrer: solo aparece si el cursor se detiene 250 ms.
        self._hide_tooltip()
        self._tooltip_iid = key
        x_root, y_root = event.x_root, event.y_root
        self._tooltip_after = self.after(
            self._TOOLTIP_DELAY_MS,
            lambda: self._show_tooltip(key, x_root, y_root),
        )

    def _on_card_leave(self, event, key: str) -> None:
        """El cursor salió de la tarjeta: la tarjeta desaparece al instante."""
        if self._tooltip_iid != key:
            return  # el hover ya apunta a otra tarjeta (o no hay hover)
        if self._pointer_inside_card(event, key):
            return  # cruzó a un widget HIJO de la misma tarjeta: no oculta nada
        self._hide_tooltip()

    def _pointer_inside_card(self, event, key: str) -> bool:
        """True si (x_root, y_root) sigue dentro del árbol de la tarjeta `key`.

        Los eventos <Leave> también saltan al entrar en un hijo de la tarjeta
        (canvas, label, botón…): se comprueba con winfo_containing + cadena de
        masters para distinguir "entró a un hijo" de "salió de la tarjeta".
        """
        card = self._cards.get(key)
        if card is None:
            return False
        widget = self.winfo_toplevel().winfo_containing(
            event.x_root, event.y_root
        )
        card_path = str(card)
        while widget is not None:
            if widget is card or str(widget) == card_path:
                return True
            widget = widget.master
        return False

    def _show_tooltip(self, iid: str, x_root: int, y_root: int) -> None:
        """Muestra la tarjeta de `iid` junto al cursor (si la tarjeta sigue ahí)."""
        self._tooltip_after = None
        game = self._games.get(iid)
        if game is None or self._tooltip_iid != iid:
            return  # la lista se repintó o el hover ya no apunta a esta tarjeta
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
