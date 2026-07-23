import tkinter as tk
from tkinter import ttk

from mage_maker.ui.theme import SURFACE, TEXT_MUTED, app_font
from mage_maker.ui.widgets import LabeledEntry


SCHOOL_NONE = "{none}"
SCHOOL_SPECIALTY = "{specialty}"


class SchoolField(tk.Frame):
    def __init__(
        self,
        parent,
        school_names=None,
        change_command=None,
        background=SURFACE,
    ):
        super().__init__(parent, bg=background)
        self.background = background
        self.change_command = change_command
        self.loading = False
        self.school_names = self.normalize_school_names(school_names)
        self.choice_value = tk.StringVar(value=SCHOOL_NONE)
        self.specialty_value = tk.StringVar()
        self.specialty_value.trace_add("write", self.specialty_changed)
        self.grid_columnconfigure(0, weight=1)

        label = tk.Label(
            self,
            text="School",
            bg=background,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.picker = ttk.Combobox(
            self,
            textvariable=self.choice_value,
            values=(SCHOOL_NONE, SCHOOL_SPECIALTY, *self.school_names),
            state="readonly",
            font=app_font(10),
        )
        self.picker.grid(row=1, column=0, sticky="ew", ipady=7)
        self.picker.bind("<<ComboboxSelected>>", self.choice_changed)
        self.specialty_field = LabeledEntry(
            self,
            "Specialty school name",
            self.specialty_value,
            background=background,
        )
        self.specialty_field.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.specialty_field.grid_remove()

    def normalize_school_names(self, school_names):
        normalized = []

        for school_name in school_names or []:
            name = str(school_name or "").strip()

            if name and name not in normalized:
                normalized.append(name)

        return normalized

    def set_value(self, school_name):
        self.loading = True
        normalized_name = str(school_name or "").strip()

        if not normalized_name:
            self.choice_value.set(SCHOOL_NONE)
            self.specialty_value.set("")
        elif normalized_name in self.school_names:
            self.choice_value.set(normalized_name)
            self.specialty_value.set("")
        else:
            self.choice_value.set(SCHOOL_SPECIALTY)
            self.specialty_value.set(normalized_name)

        self.update_specialty_visibility()
        self.loading = False

    def get_value(self):
        choice = self.choice_value.get().strip()

        if choice == SCHOOL_NONE:
            return ""

        if choice == SCHOOL_SPECIALTY:
            return self.specialty_value.get().strip()

        return choice

    def specialty_is_blank(self):
        return (
            self.choice_value.get().strip() == SCHOOL_SPECIALTY
            and not self.specialty_value.get().strip()
        )

    def choice_changed(self, event=None):
        self.update_specialty_visibility()
        self.notify_change()

    def specialty_changed(self, *arguments):
        if self.choice_value.get().strip() == SCHOOL_SPECIALTY:
            self.notify_change()

    def update_specialty_visibility(self):
        if self.choice_value.get().strip() == SCHOOL_SPECIALTY:
            self.specialty_field.grid()
        else:
            self.specialty_field.grid_remove()

    def notify_change(self):
        if not self.loading and self.change_command is not None:
            self.change_command()
