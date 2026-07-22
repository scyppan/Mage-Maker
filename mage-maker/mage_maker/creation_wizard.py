import tkinter as tk
from tkinter import messagebox

from mage_maker.theme import (
    APP_BACKGROUND,
    BORDER,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.widgets import LabeledEntry, SoftButton


class CreationWizardDialog(tk.Toplevel):
    def __init__(self, parent, create_command):
        super().__init__(parent)
        self.create_command = create_command
        self.title("Create New Magician")
        self.geometry("620x470")
        self.minsize(560, 430)
        self.configure(bg=APP_BACKGROUND)
        self.transient(parent)
        self.grab_set()

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=PRIMARY_DARK, height=66)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        heading = tk.Label(
            header,
            text="Create New Magician",
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(17, "bold"),
            anchor="w",
            padx=22,
        )
        heading.grid(row=0, column=0, sticky="nsew")

        card = tk.Frame(
            self,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        card.grid(row=1, column=0, sticky="nsew", padx=22, pady=22)
        card.grid_columnconfigure(0, weight=1)

        placeholder = tk.Label(
            card,
            text=(
                "This is the first placeholder step in the creation wizard. "
                "Enter the unique displayed name and any known birth date; the full "
                "guided process will be added when its steps are defined."
            ),
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(10),
            justify="left",
            anchor="w",
            wraplength=520,
            padx=14,
            pady=12,
        )
        placeholder.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 14))

        self.displayed_name_value = tk.StringVar()
        self.birth_year_value = tk.StringVar()
        self.birth_month_value = tk.StringVar()
        self.birth_day_value = tk.StringVar()

        displayed_name_field = LabeledEntry(
            card,
            "Displayed name",
            self.displayed_name_value,
            background=SURFACE,
            font_size=12,
        )
        displayed_name_field.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=16,
            pady=(0, 14),
        )
        self.displayed_name_entry = displayed_name_field.control

        birth_frame = tk.Frame(card, bg=SURFACE)
        birth_frame.grid(row=2, column=0, sticky="ew", padx=16)
        birth_frame.grid_columnconfigure((0, 1, 2), weight=1)

        birth_year_field = LabeledEntry(
            birth_frame,
            "Birth year",
            self.birth_year_value,
            background=SURFACE,
        )
        birth_year_field.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        birth_month_field = LabeledEntry(
            birth_frame,
            "Month",
            self.birth_month_value,
            background=SURFACE,
        )
        birth_month_field.grid(row=0, column=1, sticky="ew", padx=6)

        birth_day_field = LabeledEntry(
            birth_frame,
            "Day",
            self.birth_day_value,
            background=SURFACE,
        )
        birth_day_field.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        buttons = tk.Frame(card, bg=SURFACE)
        buttons.grid(row=3, column=0, sticky="e", padx=16, pady=18)

        cancel_button = SoftButton(
            buttons,
            text="Cancel",
            command=self.destroy,
            background=SURFACE,
            width=92,
            height=38,
        )
        cancel_button.pack(side="left", padx=(0, 6))

        create_button = SoftButton(
            buttons,
            text="Create Magician",
            command=self.create_magician,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_LIGHT,
            width=142,
            height=38,
        )
        create_button.pack(side="left")

        self.bind("<Escape>", self.close_dialog)
        self.bind("<Return>", self.submit_dialog)
        self.after(50, self.focus_name)

    def create_magician(self):
        values = {
            "displayed_name": self.displayed_name_value.get(),
            "birth_year": self.birth_year_value.get(),
            "birth_month": self.birth_month_value.get(),
            "birth_day": self.birth_day_value.get(),
        }

        try:
            created_person = self.create_command(values)
        except (TypeError, ValueError) as error:
            messagebox.showerror("Cannot create magician", str(error), parent=self)
            return

        if created_person is not None:
            self.destroy()

    def close_dialog(self, event=None):
        self.destroy()

    def submit_dialog(self, event=None):
        self.create_magician()

    def focus_name(self):
        self.displayed_name_entry.focus_set()
