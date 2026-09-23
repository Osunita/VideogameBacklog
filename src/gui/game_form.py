"""Formulario modal de alta/edición de un juego (§4, §7).

- Modal: transient() + grab_set().
- Valida con models (Game) ANTES de persistir (D5).
- NO importa db: la persistencia entra por el callback inyectado on_submit(datos)
  que app.py conecta a db.py (D5 — §4 prohíbe que game_form importe db).
- Si la validación falla (o el callback lanza ValueError) muestra el error
  DENTRO del formulario, marca el campo y NO cierra el modal (§7, §10, AC-006).
- Sin unicidad de título: los duplicados están permitidos (DECISIÓN-004).
"""

import customtkinter as ctk

from config import STATUSES
from models import Game

from .game_list import status_label

_ERROR_COLOR = "#e74c3c"

# Estado <-> etiqueta visible: el OptionMenu muestra la etiqueta ("en curso"),
# pero _collect() devuelve SIEMPRE el valor de config.STATUSES ("en_curso").
_STATUS_LABELS = [status_label(s) for s in STATUSES]
_STATUS_BY_LABEL = {status_label(s): s for s in STATUSES}


class GameForm(ctk.CTkToplevel):
    """Modal de alta (game=None) o edición (game precargado).

    on_submit(datos) recibe un dict con las claves de Game (sin id) y debe
    persistirlo (app.py → db.py). Si lanza ValueError, el formulario muestra el
    mensaje y permanece abierto.
    """

    def __init__(self, master, on_submit, game: Game | None = None) -> None:
        super().__init__(master)
        self._on_submit = on_submit
        self._game = game

        self.title("Editar juego" if game is not None else "Añadir juego")
        self.geometry("500x600")
        self.resizable(True, True)
        self.transient(master)

        self._build()
        if game is not None:
            self._prefill(game)

        self.after(75, self._focus_first_field)
        self.grab_set()

    # ------------------------------------------------------------------ UI --

    def _build(self) -> None:
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=14)
        content.grid_columnconfigure(1, weight=1)

        self._title = ctk.CTkEntry(content, placeholder_text="Ej. Hollow Knight")
        self._platform = ctk.CTkEntry(content, placeholder_text="Ej. PC")
        self._status_var = ctk.StringVar(value=_STATUS_LABELS[0])
        self._status = ctk.CTkOptionMenu(
            content, variable=self._status_var, values=list(_STATUS_LABELS), width=180
        )
        self._hours = ctk.CTkEntry(content, placeholder_text="0")
        self._note = ctk.CTkTextbox(content, height=90)
        self._url = ctk.CTkEntry(content, placeholder_text="https://…")
        # Campos de texto plano marcables en rojo (§10: "muestra el campo con error").
        self._text_inputs = (self._title, self._platform, self._hours, self._url)

        fields = (
            ("Título *", self._title, "w"),
            ("Plataforma *", self._platform, "w"),
            ("Estado", self._status, "w"),
            ("Horas jugadas", self._hours, "w"),
            ("Nota de progreso", self._note, "n"),
            ("URL del episodio", self._url, "w"),
        )
        for row, (label, widget, sticky) in enumerate(fields):
            ctk.CTkLabel(content, text=label, anchor="e").grid(
                row=row, column=0, padx=(0, 12), pady=6, sticky=sticky
            )
            widget.grid(row=row, column=1, sticky="ew", pady=6)

        self._error = ctk.CTkLabel(
            content, text="", text_color=_ERROR_COLOR, justify="left", anchor="w"
        )
        self._error.grid(
            row=len(fields), column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        buttons = ctk.CTkFrame(content, fg_color="transparent")
        buttons.grid(
            row=len(fields) + 1, column=0, columnspan=2, pady=(16, 0), sticky="e"
        )
        ctk.CTkButton(
            buttons, text="Cancelar", fg_color="transparent", border_width=1,
            command=self.destroy,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(buttons, text="Guardar", command=self._submit).pack(side="left")

    def _prefill(self, game: Game) -> None:
        self._title.insert(0, game.title)
        self._platform.insert(0, game.platform)
        self._status_var.set(status_label(game.status))
        self._hours.insert(0, f"{game.hours_played:g}")
        self._note.insert("1.0", game.progress_note)
        self._url.insert(0, game.episode_url)

    def _focus_first_field(self) -> None:
        if self.winfo_exists():
            self._title.focus_set()

    # ---------------------------------------------------------- validación --

    def _collect(self) -> dict:
        """Lee y convierte los campos; lanza ValueError si las horas no son número."""
        raw_hours = self._hours.get().strip().replace(",", ".")
        if raw_hours == "":
            hours = 0.0
        else:
            try:
                hours = float(raw_hours)
            except ValueError:
                raise ValueError("Las horas jugadas deben ser un número") from None
        selected_label = self._status_var.get()
        return {
            "title": self._title.get().strip(),
            "platform": self._platform.get().strip(),
            # Etiqueta visible → valor de config.STATUSES (fallback: ya era valor).
            "status": _STATUS_BY_LABEL.get(selected_label, selected_label),
            "hours_played": hours,
            "progress_note": self._note.get("1.0", "end").strip(),
            "episode_url": self._url.get().strip(),
        }

    def _submit(self) -> None:
        """Valida con models, delega en on_submit y cierra SOLO si no hay error."""
        self._clear_error()
        try:
            data = self._collect()  # conversión de tipos (horas)
            Game(**data)  # validación con models (D5) → ValueError
            self._on_submit(data)  # callback inyectado (app → db)
        except ValueError as exc:
            # §7 / AC-006: error DENTRO del formulario; NO se cierra el modal.
            self._show_error(str(exc))
            return
        self.destroy()

    def _show_error(self, message: str) -> None:
        self._error.configure(text=message)
        lowered = message.lower()
        field = None
        if "título" in lowered:
            field = self._title
        elif "plataforma" in lowered:
            field = self._platform
        elif "horas" in lowered:
            field = self._hours
        if field is not None:
            field.configure(border_width=2, border_color=_ERROR_COLOR)
            field.focus_set()

    def _clear_error(self) -> None:
        self._error.configure(text="")
        for widget in self._text_inputs:
            widget.configure(border_width=0)
