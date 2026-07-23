import tkinter as tk

from mage_maker.ui.theme import SURFACE


class DevelopmentView(tk.Frame):
    def __init__(self, parent, game_database=None):
        super().__init__(parent, bg=SURFACE)
        self.game_database = game_database
