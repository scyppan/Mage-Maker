import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from mage_maker.sections.organizations.controller import ORGANIZATION_TYPES
from mage_maker.ui.theme import (
    APP_BACKGROUND,
    BORDER,
    BORDER_SOFT,
    DELETE_HOVER,
    DELETE_SOFT,
    FIELD_BACKGROUND,
    LIST_ALTERNATE,
    LIST_SELECTED,
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
from mage_maker.ui.widgets import LabeledEntry, RoundedText, SoftButton


class OrganizationPage(tk.Frame):
    def __init__(self, parent, controller, status_command):
        super().__init__(parent, bg=APP_BACKGROUND)
        self.controller = controller
        self.status_command = status_command
        self.organizations = []
        self.current_organization_id = None
        self.location_ids_by_label = {}
        self.name_value = tk.StringVar()
        self.type_value = tk.StringVar(value=ORGANIZATION_TYPES[0])
        self.location_value = tk.StringVar(value="No location selected")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_toolbar()
        self.build_workspace()
        self.refresh()

    def build_toolbar(self):
        toolbar = tk.Frame(self, bg=PRIMARY_DARK, height=64)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_propagate(False)
        toolbar.grid_columnconfigure(0, weight=1)
        title = tk.Label(
            toolbar,
            text="Organizations",
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(16, "bold"),
            anchor="w",
            padx=20,
        )
        title.grid(row=0, column=0, sticky="nsew")
        new_button = SoftButton(
            toolbar,
            text="New organization",
            command=self.create_organization,
            background=PRIMARY_DARK,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=148,
            height=38,
        )
        new_button.grid(row=0, column=1, padx=4, pady=13)
        delete_button = SoftButton(
            toolbar,
            text="Delete",
            command=self.delete_organization,
            background=PRIMARY_DARK,
            fill=DELETE_SOFT,
            hover_fill=DELETE_HOVER,
            foreground=TEXT_DARK,
            width=88,
            height=38,
        )
        delete_button.grid(row=0, column=2, padx=(4, 16), pady=13)

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
        workspace.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=18,
            pady=(10, 18),
        )
        list_card = tk.Frame(
            workspace,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        list_card.grid_rowconfigure(1, weight=1)
        list_card.grid_columnconfigure(0, weight=1)
        list_title = tk.Label(
            list_card,
            text="Organizations",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(12, "bold"),
            anchor="w",
        )
        list_title.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        self.organization_list = tk.Listbox(
            list_card,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            selectbackground=LIST_SELECTED,
            selectforeground=TEXT_DARK,
            relief="flat",
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            borderwidth=0,
            font=app_font(10),
            activestyle="none",
            exportselection=False,
        )
        self.organization_list.grid(row=1, column=0, sticky="nsew")
        self.organization_list.bind(
            "<<ListboxSelect>>",
            self.organization_selected,
        )
        list_scrollbar = tk.Scrollbar(
            list_card,
            command=self.organization_list.yview,
        )
        list_scrollbar.grid(row=1, column=1, sticky="ns")
        self.organization_list.configure(yscrollcommand=list_scrollbar.set)

        editor_card = tk.Frame(
            workspace,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=20,
            pady=18,
        )
        editor_card.grid_columnconfigure(0, weight=1)
        editor_card.grid_rowconfigure(2, weight=1)
        self.build_editor(editor_card)
        workspace.add(list_card, minsize=290, width=330)
        workspace.add(editor_card, minsize=680)

    def build_editor(self, parent):
        explanation = tk.Label(
            parent,
            text=(
                "Organizations are tied to a location. Types currently include "
                "governmental, non-profit, media, school, and shop."
            ),
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(10),
            justify="left",
            anchor="w",
            wraplength=760,
            padx=14,
            pady=12,
        )
        explanation.grid(row=0, column=0, sticky="ew")
        fields = tk.Frame(parent, bg=SURFACE)
        fields.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        fields.grid_columnconfigure(0, weight=2)
        fields.grid_columnconfigure(1, weight=1)
        fields.grid_columnconfigure(2, weight=2)
        name_field = LabeledEntry(
            fields,
            "Organization name",
            self.name_value,
            background=SURFACE,
        )
        name_field.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        type_frame = tk.Frame(fields, bg=SURFACE)
        type_frame.grid(row=0, column=1, sticky="ew", padx=7)
        type_frame.grid_columnconfigure(0, weight=1)
        type_label = tk.Label(
            type_frame,
            text="Type",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        type_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.type_picker = ttk.Combobox(
            type_frame,
            textvariable=self.type_value,
            values=ORGANIZATION_TYPES,
            state="readonly",
            font=app_font(10),
        )
        self.type_picker.grid(row=1, column=0, sticky="ew", ipady=7)
        location_frame = tk.Frame(fields, bg=SURFACE)
        location_frame.grid(row=0, column=2, sticky="ew", padx=(7, 0))
        location_frame.grid_columnconfigure(0, weight=1)
        location_label = tk.Label(
            location_frame,
            text="Location",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        location_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.location_picker = ttk.Combobox(
            location_frame,
            textvariable=self.location_value,
            state="readonly",
            font=app_font(10),
        )
        self.location_picker.grid(row=1, column=0, sticky="ew", ipady=7)
        narrative = tk.Frame(parent, bg=SURFACE)
        narrative.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
        narrative.grid_rowconfigure(0, weight=1)
        narrative.grid_columnconfigure(0, weight=1)
        narrative.grid_columnconfigure(1, weight=1)
        overview_frame = tk.Frame(narrative, bg=SURFACE)
        overview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        overview_label = tk.Label(
            overview_frame,
            text="Overview",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            anchor="w",
        )
        overview_label.pack(fill="x", pady=(0, 5))
        self.overview_control = RoundedText(
            overview_frame,
            background=SURFACE,
            height=12,
        )
        self.overview_control.pack(fill="both", expand=True)
        notes_frame = tk.Frame(narrative, bg=SURFACE)
        notes_frame.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        notes_label = tk.Label(
            notes_frame,
            text="Notes",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            anchor="w",
        )
        notes_label.pack(fill="x", pady=(0, 5))
        self.notes_control = RoundedText(
            notes_frame,
            background=SURFACE,
            height=12,
        )
        self.notes_control.pack(fill="both", expand=True)
        save_button = SoftButton(
            parent,
            text="Save organization",
            command=self.save_organization,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=148,
            height=38,
        )
        save_button.grid(row=3, column=0, sticky="e", pady=(12, 0))

    def refresh(self, selected_organization_id=None):
        selected_id = selected_organization_id or self.current_organization_id
        self.organizations = self.controller.list_organizations()
        self.organization_list.delete(0, "end")

        for index, organization in enumerate(self.organizations):
            self.organization_list.insert(
                "end",
                f"{organization.get('name', 'Unnamed')}\n"
                f"{organization.get('organization_type', '')}",
            )
            self.organization_list.itemconfigure(
                index,
                background=FIELD_BACKGROUND if index % 2 == 0 else LIST_ALTERNATE,
            )

            if organization.get("record_id") == selected_id:
                self.organization_list.selection_set(index)
                self.organization_list.see(index)

        if selected_id and self.controller.get_organization(selected_id):
            self.load_organization(selected_id)
        elif self.organizations:
            self.organization_list.selection_set(0)
            self.load_organization(self.organizations[0]["record_id"])
        else:
            self.clear_form()

    def organization_selected(self, event=None):
        selected = self.organization_list.curselection()

        if selected:
            self.load_organization(self.organizations[selected[0]]["record_id"])

    def refresh_location_picker(self, selected_location_id=""):
        self.location_ids_by_label = {"No location selected": ""}

        for option in self.controller.location_options():
            self.location_ids_by_label[option["label"]] = option["record_id"]

        self.location_picker.configure(values=list(self.location_ids_by_label))
        selected_label = "No location selected"

        for label, location_id in self.location_ids_by_label.items():
            if location_id == selected_location_id:
                selected_label = label
                break

        self.location_value.set(selected_label)

    def load_organization(self, record_id):
        organization = self.controller.get_organization(record_id)

        if organization is None:
            return

        self.current_organization_id = record_id
        self.name_value.set(str(organization.get("name", "") or ""))
        self.type_value.set(
            str(organization.get("organization_type", "") or ORGANIZATION_TYPES[0])
        )
        self.refresh_location_picker(organization.get("location_id", ""))
        self.overview_control.text.delete("1.0", "end")
        self.overview_control.text.insert(
            "1.0",
            str(organization.get("overview", "") or ""),
        )
        self.notes_control.text.delete("1.0", "end")
        self.notes_control.text.insert(
            "1.0",
            str(organization.get("notes", "") or ""),
        )
        self.status_command(
            f"Loaded organization {organization.get('name', 'Unnamed')}"
        )

    def clear_form(self):
        self.current_organization_id = None
        self.name_value.set("")
        self.type_value.set(ORGANIZATION_TYPES[0])
        self.refresh_location_picker()
        self.overview_control.text.delete("1.0", "end")
        self.notes_control.text.delete("1.0", "end")

    def create_organization(self):
        name = simpledialog.askstring(
            "New organization",
            "Organization name",
            parent=self.winfo_toplevel(),
        )

        if name is None:
            return

        try:
            created = self.controller.create_organization(
                {
                    "name": name,
                    "organization_type": ORGANIZATION_TYPES[0],
                    "location_id": "",
                    "overview": "",
                    "notes": "",
                }
            )
        except (TypeError, ValueError) as error:
            messagebox.showerror(
                "Cannot create organization",
                str(error),
                parent=self,
            )
            return

        self.refresh(created["record_id"])
        self.status_command(f"Created organization {created['name']}")

    def save_organization(self):
        if not self.current_organization_id:
            return False

        values = {
            "name": self.name_value.get(),
            "organization_type": self.type_value.get(),
            "location_id": self.location_ids_by_label.get(
                self.location_value.get(),
                "",
            ),
            "overview": self.overview_control.text.get("1.0", "end-1c"),
            "notes": self.notes_control.text.get("1.0", "end-1c"),
        }

        try:
            updated = self.controller.update_organization(
                self.current_organization_id,
                values,
            )
        except (KeyError, TypeError, ValueError) as error:
            messagebox.showerror(
                "Cannot save organization",
                str(error),
                parent=self,
            )
            return False

        self.refresh(updated["record_id"])
        self.status_command(f"Saved organization {updated['name']}")
        return True

    def delete_organization(self):
        organization = self.controller.get_organization(
            self.current_organization_id
        )

        if organization is None:
            return

        if not messagebox.askyesno(
            "Delete organization",
            f"Permanently delete {organization.get('name', 'this organization')}?",
            parent=self,
        ):
            return

        self.controller.delete_organization(self.current_organization_id)
        self.current_organization_id = None
        self.refresh()
        self.status_command(
            f"Deleted organization {organization.get('name', 'Unnamed')}"
        )
