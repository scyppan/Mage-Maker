import tkinter as tk

from mage_maker.ui.theme import SURFACE, SURFACE_MUTED, TEXT_MUTED, app_font


class RelationshipsView(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=SURFACE)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        placeholder = tk.Label(
            self,
            text="Relationship tools will appear here.",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(11),
            anchor="center",
        )
        placeholder.grid(row=0, column=0, sticky="nsew")
