import tkinter as tk

from mage_maker.ui.theme import (
    BORDER_SOFT,
    FIELD_BACKGROUND,
    LIST_ALTERNATE,
    SURFACE,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import SectionPanel


class DevelopmentView(tk.Frame):
    def __init__(self, parent, game_database=None):
        super().__init__(parent, bg=SURFACE)
        self.game_database = game_database
        self.status_value = tk.StringVar()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        database_panel = SectionPanel(
            self,
            "Development",
            "The game database is loaded once and held in memory for development workflows.",
        )
        database_panel.grid(row=0, column=0, sticky="nsew")
        database_panel.content.grid_rowconfigure(2, weight=1)
        database_panel.content.grid_columnconfigure(0, weight=1)
        status = tk.Label(
            database_panel.content,
            textvariable=self.status_value,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            justify="left",
            anchor="w",
            wraplength=760,
            padx=14,
            pady=11,
        )
        status.grid(row=0, column=0, sticky="ew")
        schools_label = tk.Label(
            database_panel.content,
            text="Schools available to mage records",
            bg=database_panel.content.cget("bg"),
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        schools_label.grid(row=1, column=0, sticky="ew", pady=(12, 6))
        list_frame = tk.Frame(database_panel.content, bg=database_panel.content.cget("bg"))
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        self.school_list = tk.Listbox(
            list_frame,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            relief="flat",
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            borderwidth=0,
            font=app_font(10),
            activestyle="none",
        )
        self.school_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(list_frame, command=self.school_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.school_list.configure(yscrollcommand=scrollbar.set)
        self.refresh_database_summary()

    def refresh_database_summary(self):
        self.school_list.delete(0, "end")

        if self.game_database is None or not self.game_database.loaded:
            error = str(getattr(self.game_database, "error", "") or "").strip()
            self.status_value.set(
                error
                or "No game database is currently loaded from data/dbm."
            )
            return

        schools = self.game_database.schools()
        counts = self.game_database.collection_counts()
        total_records = sum(counts.values())
        self.status_value.set(
            f"Loaded {self.game_database.database_path.name} into memory · "
            f"{total_records:,} records across {len(counts)} collections · "
            f"{len(schools)} schools"
        )

        for index, school in enumerate(schools):
            name = str(school.get("name", "") or "Unnamed school").strip()
            location = str(school.get("location", "") or "Unknown location").strip()
            self.school_list.insert("end", f"{name}\n{location}")
            self.school_list.itemconfigure(
                index,
                background=FIELD_BACKGROUND if index % 2 == 0 else LIST_ALTERNATE,
            )
