import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from mage_maker.controller import PeopleController
from mage_maker.creation_wizard import CreationWizardDialog
from mage_maker.database import JsonDatabase
from mage_maker.person_form import PersonForm
from mage_maker.person_list import PeopleList
from mage_maker.theme import (
    APP_BACKGROUND,
    BORDER,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    DELETE_HOVER,
    DELETE_SOFT,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    PRIMARY_LIGHT,
    PRIMARY_SOFT,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
    configure_tk_fonts,
)
from mage_maker.widgets import SoftButton


class MageMakerApp(tk.Tk):
    def __init__(self, database_path=None):
        super().__init__()
        configure_tk_fonts(self)

        application_directory = Path(__file__).resolve().parent.parent
        resolved_database_path = (
            database_path or application_directory / "data" / "mage_maker.json"
        )

        self.title("Mage Maker")
        self.geometry("1320x820")
        self.minsize(1040, 680)
        self.configure(bg=APP_BACKGROUND)

        try:
            self.state("zoomed")
        except tk.TclError:
            pass

        self.database = JsonDatabase(resolved_database_path)
        self.database.load()
        self.controller = PeopleController(self.database)
        self.people = []
        self.current_record_id = None
        self.form_dirty = False

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_header()
        self.build_workspace()
        self.build_status_bar()

        self.bind("<Control-s>", self.save_shortcut)
        self.bind("<Control-n>", self.create_shortcut)
        self.bind("<Control-f>", self.search_shortcut)
        self.protocol("WM_DELETE_WINDOW", self.close_application)

        self.refresh_people()

        if self.people:
            self.load_person(self.people[0]["record_id"])

    def build_header(self):
        header = tk.Frame(self, bg=PRIMARY_DARK, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        title = tk.Label(
            header,
            text="Mage Maker",
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(19, "bold"),
            anchor="w",
            padx=24,
        )
        title.grid(row=0, column=0, sticky="nsew")

        subtitle = tk.Label(
            header,
            text="People Database",
            bg=PRIMARY_DARK,
            fg=PRIMARY_LIGHT,
            font=app_font(10),
            padx=24,
        )
        subtitle.grid(row=0, column=1, sticky="e")

    def build_workspace(self):
        workspace = tk.PanedWindow(
            self,
            orient="horizontal",
            bg=BORDER,
            borderwidth=0,
            sashwidth=6,
            sashrelief="flat",
            showhandle=False,
        )
        workspace.grid(row=1, column=0, sticky="nsew", padx=22, pady=22)

        list_card = tk.Frame(
            workspace,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        list_card.grid_rowconfigure(0, weight=1)
        list_card.grid_columnconfigure(0, weight=1)
        self.people_list = PeopleList(
            list_card,
            selection_command=self.select_person,
            create_command=self.open_creation_wizard,
        )
        self.people_list.grid(row=0, column=0, sticky="nsew")

        editor_card = tk.Frame(
            workspace,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        editor_card.grid_rowconfigure(1, weight=1)
        editor_card.grid_columnconfigure(0, weight=1)
        self.build_editor_toolbar(editor_card)
        self.person_form = PersonForm(
            editor_card,
            self.mark_form_dirty,
            self.controller.list_people,
            self.create_related_person,
            self.update_related_person,
            self.refresh_related_people,
            self.select_person,
        )
        self.person_form.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=22,
            pady=18,
        )

        workspace.add(list_card, minsize=300, width=350)
        workspace.add(editor_card, minsize=690)

    def build_editor_toolbar(self, parent):
        toolbar = tk.Frame(parent, bg=PRIMARY_DARK, height=64)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_propagate(False)
        toolbar.grid_columnconfigure(0, weight=1)

        label = tk.Label(
            toolbar,
            text="Magician Profile",
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(16, "bold"),
            anchor="w",
            padx=20,
        )
        label.grid(row=0, column=0, sticky="nsew")

        self.new_button = SoftButton(
            toolbar,
            text="New",
            command=self.open_creation_wizard,
            background=PRIMARY_DARK,
            fill=PRIMARY_SOFT,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=82,
            height=38,
        )
        self.new_button.grid(row=0, column=1, padx=4, pady=13)

        self.delete_button = SoftButton(
            toolbar,
            text="Delete",
            command=self.delete_person,
            background=PRIMARY_DARK,
            fill=DELETE_SOFT,
            hover_fill=DELETE_HOVER,
            foreground=TEXT_DARK,
            width=88,
            height=38,
        )
        self.delete_button.grid(row=0, column=2, padx=4, pady=13)

        self.revert_button = SoftButton(
            toolbar,
            text="Revert",
            command=self.revert_person,
            background=PRIMARY_DARK,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            foreground=TEXT_DARK,
            width=88,
            height=38,
        )
        self.revert_button.grid(row=0, column=3, padx=4, pady=13)

        self.save_button = SoftButton(
            toolbar,
            text="Save",
            command=self.save_person,
            background=PRIMARY_DARK,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=92,
            height=38,
        )
        self.save_button.grid(row=0, column=4, padx=(4, 16), pady=13)
        self.set_editor_state(False)

    def build_status_bar(self):
        self.status_value = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            self,
            textvariable=self.status_value,
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
            padx=12,
            pady=7,
        )
        status_bar.grid(row=2, column=0, sticky="ew")

    def refresh_people(self, selected_record_id=None):
        self.people = self.controller.list_people()
        self.people_list.set_people(self.people, selected_record_id)

    def load_person(self, record_id):
        person = self.controller.get_person(record_id)

        if person is None:
            return False

        self.current_record_id = record_id
        self.person_form.set_person(person)
        self.people_list.set_selected_record(record_id)
        self.form_dirty = False
        self.set_editor_state(True)
        self.status_value.set(f"Loaded {person.get('displayed_name', 'magician')}")

        return True

    def select_person(self, record_id):
        if record_id == self.current_record_id:
            return True

        if not self.confirm_unsaved_changes():
            self.people_list.set_selected_record(self.current_record_id)
            return False

        return self.load_person(record_id)

    def open_creation_wizard(self):
        if not self.confirm_unsaved_changes():
            return

        CreationWizardDialog(self, self.create_person)

    def create_person(self, values):
        created_person = self.controller.create_person(values)
        self.refresh_people(created_person["record_id"])
        self.load_person(created_person["record_id"])
        self.status_value.set(f"Created {created_person['displayed_name']}")

        return created_person

    def create_related_person(self, values):
        created_person = self.controller.create_person(values)
        self.refresh_people(self.current_record_id)
        self.status_value.set(f"Created {created_person['displayed_name']} as a relative")
        return created_person

    def update_related_person(self, record_id, values):
        updated_person = self.controller.update_person(record_id, values)
        self.refresh_people(self.current_record_id)
        self.status_value.set(
            f"Updated family links for {updated_person['displayed_name']}"
        )
        return updated_person

    def refresh_related_people(self):
        self.refresh_people(self.current_record_id)

    def save_person(self):
        if self.current_record_id is None:
            return False

        try:
            saved_person = self.controller.update_person(
                self.current_record_id,
                self.person_form.get_values(),
            )
        except (TypeError, ValueError) as error:
            messagebox.showerror("Cannot save magician", str(error), parent=self)
            return False

        self.refresh_people(saved_person["record_id"])
        self.load_person(saved_person["record_id"])
        self.status_value.set(f"Saved {saved_person['displayed_name']}")

        return True

    def delete_person(self):
        if self.current_record_id is None:
            return

        person = self.controller.get_person(self.current_record_id)
        person_name = person.get("displayed_name", "this magician")

        if not messagebox.askyesno(
            "Delete magician",
            f"Permanently delete {person_name}?",
            parent=self,
        ):
            return

        self.controller.delete_person(self.current_record_id)
        self.current_record_id = None
        self.form_dirty = False
        self.refresh_people()

        if self.people:
            self.load_person(self.people[0]["record_id"])
        else:
            self.set_editor_state(False)

        self.status_value.set(f"Deleted {person_name}")

    def revert_person(self):
        if self.current_record_id is None:
            return

        self.load_person(self.current_record_id)
        self.status_value.set("Changes reverted")

    def mark_form_dirty(self):
        if self.current_record_id is None:
            return

        self.form_dirty = True
        self.save_button.set_enabled(True)
        self.revert_button.set_enabled(True)
        self.status_value.set("Unsaved changes")

    def set_editor_state(self, has_person):
        self.delete_button.set_enabled(has_person)
        self.save_button.set_enabled(False)
        self.revert_button.set_enabled(False)

    def confirm_unsaved_changes(self):
        if not self.form_dirty:
            return True

        save_choice = messagebox.askyesnocancel(
            "Unsaved magician changes",
            "Save changes before continuing?",
            parent=self,
        )

        if save_choice is None:
            return False

        if save_choice:
            return self.save_person()

        self.revert_person()
        return True

    def close_application(self):
        if self.confirm_unsaved_changes():
            self.destroy()

    def save_shortcut(self, event=None):
        if self.form_dirty:
            self.save_person()

        return "break"

    def create_shortcut(self, event=None):
        self.open_creation_wizard()
        return "break"

    def search_shortcut(self, event=None):
        self.people_list.search_entry.focus_set()
        self.people_list.search_entry.selection_range(0, "end")
        return "break"
