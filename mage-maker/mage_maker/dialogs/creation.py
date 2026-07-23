import tkinter as tk
from tkinter import messagebox, ttk

from mage_maker.ui.theme import (
    APP_BACKGROUND,
    BORDER,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import LabeledEntry, SoftButton


class CreationWizardDialog(tk.Toplevel):
    def __init__(self, parent, create_command, game_database=None):
        super().__init__(parent)
        self.create_command = create_command
        self.game_database = game_database
        self.title("Create New Magician")
        self.geometry("640x640")
        self.minsize(580, 610)
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
                "Enter the unique displayed name, any known birth date, and the "
                "person's starting location."
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
        self.starting_location_value = tk.StringVar()
        self.school_value = tk.StringVar()
        self.can_give_birth_value = tk.BooleanVar(value=False)

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

        starting_location_field = LabeledEntry(
            card,
            "Starting location",
            self.starting_location_value,
            background=SURFACE,
        )
        starting_location_field.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=16,
            pady=(14, 0),
        )

        school_frame = tk.Frame(card, bg=SURFACE)
        school_frame.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=16,
            pady=(14, 0),
        )
        school_frame.grid_columnconfigure(0, weight=1)
        school_label = tk.Label(
            school_frame,
            text="School",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        school_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        school_names = (
            self.game_database.school_names()
            if self.game_database is not None and self.game_database.loaded
            else []
        )
        self.school_picker = ttk.Combobox(
            school_frame,
            textvariable=self.school_value,
            values=school_names,
            state="readonly" if school_names else "disabled",
            font=app_font(10),
        )
        self.school_picker.grid(row=1, column=0, sticky="ew", ipady=7)

        can_give_birth_check = tk.Checkbutton(
            card,
            text="Can give birth",
            variable=self.can_give_birth_value,
            bg=SURFACE,
            fg=TEXT_DARK,
            activebackground=SURFACE,
            activeforeground=TEXT_DARK,
            selectcolor=SURFACE_MUTED,
            font=app_font(10),
            anchor="w",
            borderwidth=0,
            highlightthickness=0,
        )
        can_give_birth_check.grid(
            row=5,
            column=0,
            sticky="w",
            padx=16,
            pady=(14, 0),
        )

        buttons = tk.Frame(self, bg=APP_BACKGROUND)
        buttons.grid(row=2, column=0, sticky="e", padx=22, pady=(0, 18))

        cancel_button = SoftButton(
            buttons,
            text="Cancel",
            command=self.destroy,
            background=APP_BACKGROUND,
            width=92,
            height=38,
        )
        cancel_button.pack(side="left", padx=(0, 6))

        create_button = SoftButton(
            buttons,
            text="Okay",
            command=self.create_magician,
            background=APP_BACKGROUND,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=112,
            height=38,
        )
        create_button.pack(side="left")

        self.bind("<Escape>", self.close_dialog)
        self.bind("<Return>", self.submit_dialog)
        self.after(50, self.focus_name)

    def create_magician(self):
        starting_location = self.starting_location_value.get().strip()

        if not starting_location:
            messagebox.showerror(
                "Starting location required",
                "Enter the magician's starting location.",
                parent=self,
            )
            return

        values = {
            "displayed_name": self.displayed_name_value.get(),
            "birth_year": self.birth_year_value.get(),
            "birth_month": self.birth_month_value.get(),
            "birth_day": self.birth_day_value.get(),
            "starting_location": starting_location,
            "school": self.school_value.get(),
            "can_give_birth": self.can_give_birth_value.get(),
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
