import tkinter as tk
from tkinter import messagebox

from mage_maker.sections.events.editor import (
    NEW_EVENT_DRAFT_ID,
    EventEditor,
)
from mage_maker.sections.events.types import event_type_label
from mage_maker.sections.locations.location_hierarchy import (
    LocationHierarchyTree,
    WORLD_LOCATION_LABEL,
    location_id_is_in_scope,
    location_ids_in_scope,
)
from mage_maker.sections.locations.models import descendant_ids
from mage_maker.ui.theme import (
    APP_BACKGROUND,
    BORDER,
    BORDER_SOFT,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    DELETE_HOVER,
    DELETE_SOFT,
    FIELD_BACKGROUND,
    LIST_SELECTED,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    PRIMARY_SOFT,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import (
    LabeledEntry,
    RoundedEntry,
    RoundedText,
    SoftButton,
)


LOCAL_EVENT_COLORS = ("#FFFFFF", "#F1F1F1")
PROPAGATED_EVENT_COLORS = (
    "#E6D8F0",
    "#D9E7F3",
    "#DCEBDD",
    "#F1E7CF",
    "#E6DFD8",
)


def location_scope_after_parent_change(
    scope_location_id,
    previous_parent_location_id,
    next_parent_location_id,
):
    previous_parent_id = str(
        previous_parent_location_id or ""
    ).strip()
    next_parent_id = str(next_parent_location_id or "").strip()

    if previous_parent_id != next_parent_id:
        return ""

    return str(scope_location_id or "").strip()


class LocationPage(tk.Frame):
    def __init__(
        self,
        parent,
        controller,
        status_command,
        navigate_person_command,
        scope_change_command=None,
        event_controller=None,
        navigate_event_command=None,
        events_changed_command=None,
    ):
        super().__init__(parent, bg=APP_BACKGROUND)
        self.controller = controller
        self.status_command = status_command
        self.navigate_person_command = navigate_person_command
        self.scope_change_command = scope_change_command
        self.event_controller = event_controller
        self.navigate_event_command = navigate_event_command
        self.events_changed_command = events_changed_command
        self.locations = []
        self.visible_events = []
        self.draft_event = None
        self.selected_timeline_event_id = ""
        self.event_editor_visible = False
        self.remove_armed_event_id = ""
        self.current_location_id = None
        self.creating_location = False
        self.region_lock_id = ""
        self.selected_parent_location_id = ""
        self.loaded_parent_location_id = ""
        self.content = None
        self.editor_heading_value = tk.StringVar(value="Location details")
        self.parent_path_value = tk.StringVar(value=WORLD_LOCATION_LABEL)
        self.name_value = tk.StringVar()
        self.extinct_value = tk.BooleanVar(value=False)
        self.extinction_year_value = tk.StringVar()
        self.timeline_type_value = tk.StringVar(
            value="No event selected"
        )
        self.timeline_date_value = tk.StringVar(value="Date: nd.")
        self.timeline_people_value = tk.StringVar(value="None")
        self.timeline_periods_value = tk.StringVar(value="None")
        self.timeline_locations_value = tk.StringVar(value="None")
        self.timeline_source_value = tk.StringVar(
            value="Select an event to view its details."
        )
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_toolbar()
        self.build_content()
        self.refresh()

    def build_toolbar(self):
        toolbar = tk.Frame(self, bg=PRIMARY_DARK, height=64)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_propagate(False)
        toolbar.grid_columnconfigure(0, weight=1)
        title = tk.Label(
            toolbar,
            text="Locations",
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(16, "bold"),
            anchor="w",
            padx=20,
        )
        title.grid(row=0, column=0, sticky="nsew")
        self.new_location_button = SoftButton(
            toolbar,
            text="New location",
            command=self.create_location,
            background=PRIMARY_DARK,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=126,
            height=38,
        )
        self.new_location_button.grid(row=0, column=1, padx=4, pady=13)
        self.delete_location_button = SoftButton(
            toolbar,
            text="Delete",
            command=self.delete_location,
            background=PRIMARY_DARK,
            fill=DELETE_SOFT,
            hover_fill=DELETE_HOVER,
            foreground=TEXT_DARK,
            width=88,
            height=38,
        )
        self.delete_location_button.grid(
            row=0,
            column=2,
            padx=(4, 16),
            pady=13,
        )

    def build_content(self):
        self.content = tk.Frame(self, bg=APP_BACKGROUND)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.build_workspace(self.content)

    def build_workspace(self, parent):
        workspace = tk.PanedWindow(
            parent,
            orient="horizontal",
            bg=BORDER,
            borderwidth=0,
            sashwidth=6,
            sashrelief="flat",
            showhandle=False,
        )
        workspace.grid(
            row=0,
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
            text="Location hierarchy",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(12, "bold"),
            anchor="w",
        )
        list_title.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        self.location_tree = LocationHierarchyTree(
            list_card,
            self.location_selected,
            background=SURFACE,
            scope_change_command=self.region_lock_changed,
        )
        self.location_tree.grid(row=1, column=0, sticky="nsew")

        editor_card = tk.Frame(
            workspace,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=18,
            pady=16,
        )
        editor_card.grid_rowconfigure(2, weight=1)
        editor_card.grid_columnconfigure(0, weight=1)
        self.build_location_fields(editor_card)
        self.build_timeline(editor_card)

        workspace.add(list_card, minsize=290, width=330)
        workspace.add(editor_card, minsize=680)

    def save_shortcut(self):
        return self.save_location()

    def create_shortcut(self):
        self.create_location()
        return True

    def build_location_fields(self, parent):
        identity = tk.Frame(parent, bg=SURFACE_MUTED, padx=14, pady=10)
        identity.grid(row=0, column=0, sticky="ew")
        identity.grid_columnconfigure(0, weight=3)
        identity.grid_columnconfigure(1, weight=2)
        editor_heading = tk.Label(
            identity,
            textvariable=self.editor_heading_value,
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        editor_heading.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )
        self.save_location_button = SoftButton(
            identity,
            text="Save location",
            command=self.save_location,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=126,
            height=34,
        )
        self.save_location_button.grid(
            row=0,
            column=1,
            sticky="e",
            pady=(0, 8),
        )
        self.name_field = LabeledEntry(
            identity,
            "Location name",
            self.name_value,
            background=SURFACE_MUTED,
        )
        self.name_field.grid(row=1, column=0, sticky="ew", padx=(0, 7))
        parent_frame = tk.Frame(identity, bg=SURFACE_MUTED)
        parent_frame.grid(row=1, column=1, sticky="ew", padx=(7, 0))
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_label = tk.Label(
            parent_frame,
            text="Within region",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        parent_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        parent_display = tk.Frame(
            parent_frame,
            bg=FIELD_BACKGROUND,
            highlightbackground=BORDER,
            highlightthickness=1,
            height=40,
        )
        parent_display.grid(row=1, column=0, sticky="ew")
        parent_display.grid_propagate(False)
        parent_display.grid_columnconfigure(0, weight=1)
        parent_path = tk.Label(
            parent_display,
            textvariable=self.parent_path_value,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            font=app_font(9),
            anchor="w",
            padx=10,
        )
        parent_path.grid(row=0, column=0, sticky="nsew")
        self.change_parent_button = SoftButton(
            parent_display,
            text="Change",
            command=self.choose_parent_location,
            background=FIELD_BACKGROUND,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            foreground=TEXT_DARK,
            width=78,
            height=32,
            font=app_font(9, "bold"),
        )
        self.change_parent_button.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(4, 4),
            pady=4,
        )
        extinction_options = tk.Frame(identity, bg=SURFACE_MUTED)
        extinction_options.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(11, 0),
        )
        extinction_checkbox = tk.Checkbutton(
            extinction_options,
            text="This location is extinct",
            variable=self.extinct_value,
            command=self.toggle_extinction_fields,
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            activebackground=SURFACE_MUTED,
            activeforeground=TEXT_DARK,
            selectcolor=FIELD_BACKGROUND,
            font=app_font(9),
            anchor="w",
            padx=0,
            pady=0,
        )
        extinction_checkbox.pack(side="left")
        self.extinction_year_label = tk.Label(
            extinction_options,
            text="Year extinct",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        self.extinction_year_control = RoundedEntry(
            extinction_options,
            textvariable=self.extinction_year_value,
            background=SURFACE_MUTED,
            width=170,
            height=36,
            font=app_font(10),
        )
        self.toggle_extinction_fields()

        narrative = tk.Frame(parent, bg=SURFACE)
        narrative.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        narrative.grid_columnconfigure(0, weight=1)
        narrative.grid_columnconfigure(1, weight=1)
        demographics_frame = tk.Frame(narrative, bg=SURFACE)
        demographics_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        demographics_label = tk.Label(
            demographics_frame,
            text="Broad demographics",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            anchor="w",
        )
        demographics_label.pack(fill="x", pady=(0, 5))
        self.demographics_control = RoundedText(
            demographics_frame,
            background=SURFACE,
            height=3,
        )
        self.demographics_control.pack(fill="both", expand=True)
        notes_frame = tk.Frame(narrative, bg=SURFACE)
        notes_frame.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        notes_label = tk.Label(
            notes_frame,
            text="Location notes",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            anchor="w",
        )
        notes_label.pack(fill="x", pady=(0, 5))
        self.notes_control = RoundedText(
            notes_frame,
            background=SURFACE,
            height=3,
        )
        self.notes_control.pack(fill="both", expand=True)

    def toggle_extinction_fields(self):
        if self.extinct_value.get():
            self.extinction_year_label.pack(
                side="left",
                padx=(22, 8),
            )
            self.extinction_year_control.pack(side="left")
        else:
            self.extinction_year_label.pack_forget()
            self.extinction_year_control.pack_forget()

    def set_parent_location(self, location_id=""):
        requested_id = str(location_id or "").strip()
        available_ids = {
            str(location.get("record_id", "") or "")
            for location in self.locations
        }

        if requested_id not in available_ids:
            requested_id = ""

        if (
            self.region_lock_id
            and not location_id_is_in_scope(
                requested_id,
                self.locations,
                self.region_lock_id,
            )
            and not (
                self.current_location_id == self.region_lock_id
                and not self.creating_location
            )
        ):
            requested_id = self.region_lock_id

        self.selected_parent_location_id = requested_id
        self.refresh_parent_display()

    def refresh_parent_display(self):
        parent = self.controller.get_location(
            self.selected_parent_location_id
        )
        parent_name = (
            str(parent.get("name", "") or "Unnamed region").strip()
            if parent is not None
            else WORLD_LOCATION_LABEL
        )
        self.parent_path_value.set(parent_name)
        change_allowed = not (
            self.region_lock_id
            and self.current_location_id == self.region_lock_id
            and not self.creating_location
        )
        self.change_parent_button.set_enabled(change_allowed)

    def choose_parent_location(self):
        if (
            self.region_lock_id
            and self.current_location_id == self.region_lock_id
            and not self.creating_location
        ):
            messagebox.showinfo(
                "Region is locked",
                "Unlock this region before moving the region itself.",
                parent=self,
            )
            return

        unavailable_ids = descendant_ids(
            self.current_location_id,
            self.locations,
        )
        unavailable_ids.add(str(self.current_location_id or ""))
        scoped_ids = location_ids_in_scope(
            self.locations,
            self.region_lock_id,
        )
        available_locations = [
            location
            for location in self.locations
            if (
                str(location.get("record_id", "") or "") not in unavailable_ids
                and (
                    not self.region_lock_id
                    or str(location.get("record_id", "") or "") in scoped_ids
                )
            )
        ]
        LocationParentDialog(
            self,
            available_locations,
            self.selected_parent_location_id,
            self.parent_location_chosen,
            self.region_lock_id,
        )

    def parent_location_chosen(self, location_id):
        self.set_parent_location(location_id)
        parent_name = self.parent_path_value.get()
        self.status_command(f"Location will be placed within {parent_name}")

    def build_timeline(self, parent):
        timeline_panel = tk.Frame(
            parent,
            bg=SURFACE_MUTED,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        timeline_panel.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        timeline_panel.grid_rowconfigure(2, weight=1)
        timeline_panel.grid_columnconfigure(0, weight=1)
        timeline_heading = tk.Label(
            timeline_panel,
            text="Location timeline",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(12, "bold"),
            anchor="w",
        )
        timeline_heading.grid(row=0, column=0, sticky="ew")
        event_buttons = tk.Frame(timeline_panel, bg=SURFACE_MUTED)
        event_buttons.grid(row=0, column=1, sticky="e")
        self.timeline_add_button = SoftButton(
            event_buttons,
            text="Add event",
            command=self.add_event,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=104,
            height=32,
        )
        self.timeline_add_button.pack(side="left", padx=(0, 6))
        self.timeline_edit_button = SoftButton(
            event_buttons,
            text="Edit",
            command=self.edit_event,
            background=SURFACE_MUTED,
            fill=PRIMARY_SOFT,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=82,
            height=32,
        )
        self.timeline_edit_button.pack(side="left", padx=(0, 6))
        self.timeline_remove_button = SoftButton(
            event_buttons,
            text="Remove",
            command=self.remove_event,
            background=SURFACE_MUTED,
            fill=DELETE_SOFT,
            hover_fill=DELETE_HOVER,
            foreground=TEXT_DARK,
            width=92,
            height=32,
        )
        self.timeline_remove_button.pack(side="left")
        legend = tk.Label(
            timeline_panel,
            text=(
                "White/gray: this location  ·  Colored: inherited from an "
                "ancestor level  ·  Mage births and marriages are included automatically"
            ),
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(8),
            anchor="w",
            justify="left",
            wraplength=760,
        )
        legend.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(2, 6),
        )
        self.timeline_workspace = tk.Frame(
            timeline_panel,
            bg=SURFACE_MUTED,
        )
        self.timeline_workspace.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="nsew",
        )
        self.timeline_workspace.grid_rowconfigure(0, weight=1)
        self.timeline_workspace.grid_columnconfigure(
            0,
            weight=5,
            uniform="location_events",
        )
        self.timeline_workspace.grid_columnconfigure(
            1,
            weight=4,
            uniform="location_events",
        )
        self.timeline_list_panel = tk.Frame(
            self.timeline_workspace,
            bg=SURFACE_MUTED,
        )
        self.timeline_list_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
        )
        self.timeline_list_panel.grid_rowconfigure(0, weight=1)
        self.timeline_list_panel.grid_columnconfigure(0, weight=1)
        list_frame = tk.Frame(
            self.timeline_list_panel,
            bg=SURFACE_MUTED,
        )
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        self.timeline_list = tk.Listbox(
            list_frame,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            selectbackground=LIST_SELECTED,
            selectforeground=TEXT_DARK,
            relief="flat",
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            borderwidth=0,
            font=app_font(9),
            activestyle="none",
            exportselection=False,
        )
        self.timeline_list.grid(row=0, column=0, sticky="nsew")
        self.timeline_list.bind(
            "<<ListboxSelect>>",
            self.timeline_event_selected,
        )
        self.timeline_list.bind("<Double-Button-1>", self.edit_event)
        timeline_scrollbar = tk.Scrollbar(list_frame, command=self.timeline_list.yview)
        timeline_scrollbar.grid(row=0, column=1, sticky="ns")
        self.timeline_list.configure(yscrollcommand=timeline_scrollbar.set)
        self.event_editor = EventEditor(
            self.timeline_workspace,
            self.event_controller,
            self.save_event_editor,
            self.cancel_event_editor,
            context="location",
            background=SURFACE_MUTED,
        )
        self.event_editor.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
        )
        self.hide_event_editor()
        self.update_timeline_details()

    def show_event_editor(self):
        if self.event_editor_visible:
            return

        self.timeline_workspace.grid_columnconfigure(
            0,
            weight=5,
            uniform="location_events",
        )
        self.timeline_workspace.grid_columnconfigure(
            1,
            weight=4,
            uniform="location_events",
        )
        self.timeline_list_panel.grid(
            row=0,
            column=0,
            columnspan=1,
            sticky="nsew",
            padx=(0, 7),
        )
        self.event_editor.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
        )
        self.event_editor_visible = True

    def hide_event_editor(self):
        self.event_editor.grid_remove()
        self.timeline_workspace.grid_columnconfigure(
            0,
            weight=1,
            uniform="",
        )
        self.timeline_workspace.grid_columnconfigure(
            1,
            weight=0,
            uniform="",
        )
        self.timeline_list_panel.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=0,
        )
        self.event_editor_visible = False

    def build_timeline_association_detail(
        self,
        parent,
        row,
        title,
        variable,
    ):
        heading = tk.Label(
            parent,
            text=title,
            bg=FIELD_BACKGROUND,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        heading.grid(row=row, column=0, sticky="ew", pady=(9, 2))
        value = tk.Label(
            parent,
            textvariable=variable,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            font=app_font(9),
            anchor="w",
            justify="left",
            wraplength=390,
        )
        value.grid(row=row + 1, column=0, sticky="ew")

    def refresh(self, selected_location_id=None):
        selected_id = selected_location_id or self.current_location_id
        self.locations = self.controller.list_locations()
        available_ids = {
            str(location.get("record_id", "") or "")
            for location in self.locations
        }

        if self.region_lock_id not in available_ids:
            self.region_lock_id = ""

        self.location_tree.set_locations(self.locations, selected_id or "")
        self.location_tree.set_scope(self.region_lock_id)
        scoped_ids = location_ids_in_scope(
            self.locations,
            self.region_lock_id,
        )

        if (
            selected_id
            and selected_id in scoped_ids
            and self.controller.get_location(selected_id)
        ):
            self.location_tree.select_location(selected_id)
            self.load_location(selected_id)
        elif (
            self.region_lock_id
            and self.region_lock_id in scoped_ids
            and self.controller.get_location(self.region_lock_id)
        ):
            self.location_tree.select_location(self.region_lock_id)
            self.load_location(self.region_lock_id)
        elif self.locations:
            scoped_locations = [
                location
                for location in self.locations
                if str(location.get("record_id", "") or "") in scoped_ids
            ]
            first_location_id = (
                str(scoped_locations[0].get("record_id", "") or "")
                if scoped_locations
                else ""
            )
            self.location_tree.select_location(first_location_id)

            if first_location_id:
                self.load_location(first_location_id)
            else:
                self.clear_form()
        else:
            self.location_tree.select_location("")
            self.clear_form()

    def refresh_person_data(self):
        self.refresh(self.current_location_id)

    def location_selected(self, location_id):
        requested_id = str(location_id or "").strip()

        if not requested_id and self.region_lock_id:
            requested_id = self.region_lock_id
            self.location_tree.select_location(requested_id)

        self.controller.remember_location_interaction(requested_id)

        if requested_id:
            self.load_location(requested_id)
        else:
            self.clear_form()
            self.status_command(f"Selected {WORLD_LOCATION_LABEL}")

    def load_location(self, record_id):
        location = self.controller.get_location(record_id)

        if location is None:
            return

        if record_id != self.current_location_id:
            self.draft_event = None
            self.selected_timeline_event_id = ""

        self.current_location_id = record_id
        self.creating_location = False
        self.editor_heading_value.set("Location details")
        self.name_value.set(str(location.get("name", "") or ""))
        self.loaded_parent_location_id = str(
            location.get("parent_location_id", "") or ""
        ).strip()
        self.set_parent_location(location.get("parent_location_id", ""))
        self.extinct_value.set(bool(location.get("extinct")))
        self.extinction_year_value.set(
            str(location.get("extinction_year", "") or "")
        )
        self.toggle_extinction_fields()
        self.demographics_control.text.delete("1.0", "end")
        self.demographics_control.text.insert(
            "1.0",
            str(location.get("demographics", "") or ""),
        )
        self.notes_control.text.delete("1.0", "end")
        self.notes_control.text.insert(
            "1.0",
            str(location.get("notes", "") or ""),
        )
        self.save_location_button.set_enabled(True)
        self.timeline_add_button.set_enabled(True)
        self.refresh_timeline()
        self.status_command(f"Loaded location {location.get('name', 'Unnamed')}")

    def set_region_lock(self, location_id="", notify=False):
        requested_id = str(location_id or "").strip()
        available_ids = {
            str(location.get("record_id", "") or "")
            for location in self.locations
        }

        if requested_id not in available_ids:
            requested_id = ""

        self.region_lock_id = requested_id
        self.location_tree.set_scope(requested_id, notify=False)

        if (
            self.current_location_id
            and not location_id_is_in_scope(
                self.current_location_id,
                self.locations,
                self.region_lock_id,
            )
        ):
            self.current_location_id = None

        if (
            self.selected_parent_location_id
            and not location_id_is_in_scope(
                self.selected_parent_location_id,
                self.locations,
                self.region_lock_id,
            )
            and self.current_location_id != self.region_lock_id
        ):
            self.set_parent_location(self.region_lock_id)

        if self.creating_location:
            self.set_parent_location(
                self.selected_parent_location_id or self.region_lock_id
            )
            self.location_tree.select_location(
                self.selected_parent_location_id
            )
        elif self.current_location_id:
            self.location_tree.select_location(self.current_location_id)
            self.load_location(self.current_location_id)
        elif self.region_lock_id:
            self.location_tree.select_location(self.region_lock_id)
            self.load_location(self.region_lock_id)
        else:
            self.location_tree.select_location("")
            self.clear_form()

        if self.region_lock_id:
            location = self.controller.get_location(self.region_lock_id)
            location_name = str(
                (location or {}).get("name", "") or "selected region"
            )
            self.status_command(f"Locked location work to {location_name}")
        else:
            self.status_command("Showing all location regions")

        if notify and self.scope_change_command is not None:
            self.scope_change_command(self.region_lock_id)

        return self.region_lock_id

    def region_lock_changed(self, location_id):
        return self.set_region_lock(location_id, notify=True)

    def open_location(self, location_id):
        requested_id = str(location_id or "").strip()

        if not location_id_is_in_scope(
            requested_id,
            self.locations,
            self.region_lock_id,
        ):
            self.status_command(
                "Unlock the current region to open that source location"
            )
            return False

        self.location_tree.select_location(requested_id)
        self.controller.remember_location_interaction(requested_id)
        self.load_location(requested_id)
        return True

    def refresh_timeline(self):
        self.timeline_list.delete(0, "end")

        if not self.current_location_id:
            self.visible_events = []
            self.selected_timeline_event_id = ""
            self.update_timeline_details()
            return

        self.visible_events = self.controller.timeline_for(self.current_location_id)

        if (
            self.draft_event is not None
            and self.draft_event.get("_location_id")
            == self.current_location_id
        ):
            self.visible_events.append(self.draft_event)

        visible_event_ids = {
            str(event.get("event_id", "") or "")
            for event in self.visible_events
        }

        if self.selected_timeline_event_id not in visible_event_ids:
            self.selected_timeline_event_id = ""

        for index, event in enumerate(self.visible_events):
            if event.get("_draft_event"):
                self.timeline_list.insert("end", "New event (unsaved)")
                self.timeline_list.itemconfigure(
                    index,
                    background=PRIMARY_SOFT,
                )

                if (
                    str(event.get("event_id", "") or "")
                    == self.selected_timeline_event_id
                ):
                    self.timeline_list.selection_set(index)
                    self.timeline_list.see(index)

                continue

            date_text = str(event.get("date", "") or "nd.")
            source_text = ""

            if event.get("propagation_distance", 0):
                source_text = (
                    f"  ·  from {event.get('origin_location_name', 'ancestor')} "
                    f"(level {event.get('source_level', 0)})"
                )

            self.timeline_list.insert(
                "end",
                (
                    f"{date_text}  ·  {event_type_label(event)}  ·  "
                    f"{event.get('title', 'Event')}{source_text}"
                ),
            )

            if event.get("propagation_distance", 0):
                level = int(event.get("source_level", 0) or 0)
                color = PROPAGATED_EVENT_COLORS[
                    min(level, len(PROPAGATED_EVENT_COLORS) - 1)
                ]
            else:
                color = LOCAL_EVENT_COLORS[index % 2]

            self.timeline_list.itemconfigure(index, background=color)

            if (
                str(event.get("event_id", "") or "")
                == self.selected_timeline_event_id
            ):
                self.timeline_list.selection_set(index)
                self.timeline_list.see(index)

        self.update_timeline_details()

    def timeline_event_selected(self, event=None):
        selected = self.timeline_list.curselection()

        if not selected:
            return

        self.selected_timeline_event_id = str(
            self.visible_events[selected[0]].get("event_id", "") or ""
        )
        self.reset_event_remove_confirmation()
        self.update_timeline_details()

    def update_timeline_details(self):
        event = self.selected_timeline_event()

        if event is None:
            if self.event_editor.is_new_event():
                self.show_event_editor()
                self.event_editor.ensure_new_event_editable()
                self.timeline_edit_button.set_enabled(False)
                self.timeline_remove_button.set_enabled(False)
                return

            self.event_editor.clear(
                "Select an event to view it, or click Add event."
            )
            self.hide_event_editor()
            self.timeline_edit_button.set_enabled(False)
            self.timeline_remove_button.set_enabled(False)
            return

        if event.get("_draft_event"):
            self.show_event_editor()

            if not self.event_editor.is_new_event():
                self.event_editor.start_new(
                    context="location",
                    default_location_ids=(self.current_location_id,),
                    locked_location_ids=(self.current_location_id,),
                    hide_locations=True,
                )

            self.event_editor.ensure_new_event_editable()
            self.timeline_edit_button.set_enabled(False)
            self.timeline_remove_button.set_enabled(False)
            return

        self.show_event_editor()
        can_edit = bool(
            event.get("event_kind") in ("global", "location")
            and not event.get("propagation_distance", 0)
        )
        self.timeline_edit_button.set_enabled(can_edit)
        self.timeline_remove_button.set_enabled(can_edit)
        location_id = str(
            event.get("origin_location_id", "")
            or self.current_location_id
            or ""
        )

        if event.get("event_kind") == "global":
            stored_event = (
                self.event_controller.get_event(
                    event.get("record_id", "")
                )
                if self.event_controller is not None
                else None
            )

            if stored_event is None:
                self.event_editor.clear("This event no longer exists.")
                return

            inherited = bool(event.get("propagation_distance", 0))
            self.event_editor.load_event(
                stored_event,
                storage_kind="shared",
                context="location",
                location_ids=(location_id,),
                locked_location_ids=(location_id,),
                hide_locations=True,
                read_only=inherited,
                explanation=(
                    "This event is inherited from an enclosing location."
                    if inherited
                    else (
                        "The source location is fixed to this location. "
                        "Saving updates the event everywhere it appears."
                    )
                ),
            )
            return

        if event.get("event_kind") == "location":
            inherited = bool(event.get("propagation_distance", 0))
            self.event_editor.load_event(
                event,
                storage_kind="location",
                context="location",
                location_ids=(location_id,),
                locked_location_ids=(location_id,),
                hide_locations=True,
                read_only=inherited,
                explanation=(
                    "This event is inherited from an enclosing location."
                    if inherited
                    else "This event is stored on this location."
                ),
            )
            return

        person_ids = event.get("person_ids", [])

        if not person_ids and event.get("related_person_id"):
            person_ids = [event.get("related_person_id")]

        self.event_editor.load_event(
            event,
            storage_kind="timeline",
            context="person",
            person_ids=person_ids,
            location_ids=(location_id,),
            locked_location_ids=(location_id,),
            hide_locations=True,
            read_only=True,
            explanation=(
                "This individual event is shown here because it happened "
                "at this location."
            )
        )

    def timeline_event_type_text(self, event):
        return event_type_label(event)

    def timeline_event_association_labels(self, event):
        if (
            event.get("event_kind") == "global"
            and self.event_controller is not None
        ):
            return self.event_controller.association_labels(event)

        people_labels = {}
        location_labels = {}

        if self.event_controller is not None:
            people_labels = {
                option["value"]: option["label"]
                for option in self.event_controller.people_options()
            }
            location_labels = {
                option["value"]: option["label"]
                for option in self.event_controller.location_options()
            }

        person_id = str(event.get("related_person_id", "") or "")
        location_id = str(event.get("origin_location_id", "") or "")
        period_names = (
            self.event_controller.period_names_for_date(
                event.get("date", "")
            )
            if self.event_controller is not None
            else []
        )
        return {
            "people": (
                [people_labels.get(person_id, "Missing person")]
                if person_id
                else []
            ),
            "periods": period_names,
            "locations": (
                [
                    location_labels.get(
                        location_id,
                        event.get("origin_location_name", "Missing location"),
                    )
                ]
                if location_id
                else []
            ),
        }

    def timeline_event_source_text(self, event):
        if event.get("event_kind") == "global":
            return "Linked event · visible from every associated record"

        if event.get("event_kind") == "mage":
            return "Individual event · edit from the linked person"

        origin_name = str(
            event.get("origin_location_name", "") or "this location"
        )

        if event.get("propagation_distance", 0):
            return f"Inherited from {origin_name}"

        return f"Saved directly to {origin_name}"

    def clear_form(self, parent_location_id="", creating=False):
        self.current_location_id = None
        self.draft_event = None
        self.creating_location = bool(creating)
        self.loaded_parent_location_id = ""
        self.editor_heading_value.set(
            "New location"
            if self.creating_location
            else "Select a location"
        )
        self.name_value.set("")
        self.set_parent_location(parent_location_id)
        self.extinct_value.set(False)
        self.extinction_year_value.set("")
        self.toggle_extinction_fields()
        self.demographics_control.text.delete("1.0", "end")
        self.notes_control.text.delete("1.0", "end")
        self.timeline_list.delete(0, "end")
        self.visible_events = []
        self.selected_timeline_event_id = ""
        self.reset_event_remove_confirmation()
        self.update_timeline_details()
        self.save_location_button.set_enabled(self.creating_location)
        self.timeline_add_button.set_enabled(False)

    def create_location(self):
        parent_id = (
            self.current_location_id
            if location_id_is_in_scope(
                self.current_location_id,
                self.locations,
                self.region_lock_id,
            )
            else self.region_lock_id
        )
        self.clear_form(parent_id, creating=True)
        self.location_tree.select_location(parent_id)
        self.name_field.control.focus_set()
        parent_name = self.parent_path_value.get()
        self.status_command(
            f"Creating a new location within {parent_name}"
        )

    def save_location(self):
        values = {
            "name": self.name_value.get(),
            "parent_location_id": self.selected_parent_location_id,
            "demographics": self.demographics_control.text.get("1.0", "end-1c"),
            "notes": self.notes_control.text.get("1.0", "end-1c"),
            "extinct": self.extinct_value.get(),
            "extinction_year": self.extinction_year_value.get(),
        }

        parent_changed = bool(
            self.current_location_id
            and self.loaded_parent_location_id
            != str(self.selected_parent_location_id or "").strip()
        )

        try:
            if self.current_location_id:
                saved_location = self.controller.update_location(
                    self.current_location_id,
                    values,
                )
                action = "Saved"
            else:
                saved_location = self.controller.create_location(values)
                action = "Created"
        except (KeyError, TypeError, ValueError) as error:
            messagebox.showerror("Cannot save location", str(error), parent=self)
            return False

        self.creating_location = False
        next_scope_id = location_scope_after_parent_change(
            self.region_lock_id,
            self.loaded_parent_location_id,
            saved_location.get("parent_location_id", ""),
        )

        if next_scope_id != self.region_lock_id:
            self.region_lock_id = next_scope_id
            self.location_tree.set_scope(next_scope_id, notify=False)

            if self.scope_change_command is not None:
                self.scope_change_command(next_scope_id)

        self.refresh(saved_location["record_id"])

        if parent_changed:
            parent_name = self.parent_path_value.get()
            self.status_command(
                f"Moved {saved_location['name']} within {parent_name} "
                "and restored the full location hierarchy"
            )
        else:
            self.status_command(
                f"{action} location {saved_location['name']}"
            )

        return True

    def delete_location(self):
        location = self.controller.get_location(self.current_location_id)

        if location is None:
            return

        if not messagebox.askyesno(
            "Delete location",
            f"Permanently delete {location.get('name', 'this location')}?",
            parent=self,
        ):
            return

        try:
            self.controller.delete_location(self.current_location_id)
        except (KeyError, ValueError) as error:
            messagebox.showerror("Cannot delete location", str(error), parent=self)
            return

        self.current_location_id = None
        self.refresh()
        self.status_command(f"Deleted location {location.get('name', 'Unnamed')}")

    def add_event(self):
        if not self.current_location_id:
            self.status_command(
                "Save the location before adding an event."
            )
            return

        if self.event_controller is None:
            self.status_command("The event collection is unavailable.")
            return

        self.draft_event = {
            "event_id": NEW_EVENT_DRAFT_ID,
            "event_type": "other",
            "title": "New event",
            "date": "",
            "note": "",
            "event_kind": "global",
            "origin_location_id": self.current_location_id,
            "_location_id": self.current_location_id,
            "_draft_event": True,
        }
        self.selected_timeline_event_id = NEW_EVENT_DRAFT_ID
        self.reset_event_remove_confirmation()
        self.refresh_timeline()
        self.event_editor.ensure_new_event_editable()

    def shared_event_saved(self, event):
        self.draft_event = None
        self.selected_timeline_event_id = str(
            event.get("record_id", "") or ""
        )
        self.refresh_timeline()
        self.status_command(
            f"Saved event {event.get('title', 'Event')}"
        )

        if self.events_changed_command is not None:
            self.events_changed_command()

    def save_new_event(self, values):
        try:
            self.controller.add_event(self.current_location_id, values)
        except (KeyError, TypeError, ValueError) as error:
            messagebox.showerror("Cannot add event", str(error), parent=self)
            return False

        self.refresh_timeline()
        self.status_command("Added location event")
        return True

    def selected_timeline_event(self):
        for event in self.visible_events:
            if (
                str(event.get("event_id", "") or "")
                == self.selected_timeline_event_id
            ):
                return event

        selected = self.timeline_list.curselection()

        if selected and selected[0] < len(self.visible_events):
            selected_event = self.visible_events[selected[0]]
            self.selected_timeline_event_id = str(
                selected_event.get("event_id", "") or ""
            )
            return selected_event

        return None

    def edit_event(self, event=None):
        event = self.selected_timeline_event()

        if event is None:
            return

        if event.get("_draft_event"):
            self.show_event_editor()
            self.event_editor.ensure_new_event_editable()
            return

        can_edit = bool(
            event.get("event_kind") in ("global", "location")
            and not event.get("propagation_distance", 0)
        )

        if not can_edit:
            return

        self.update_timeline_details()
        self.event_editor.begin_edit()
        self.event_editor.canvas.yview_moveto(0)

    def save_event_editor(self, values, storage_kind, original_event):
        if storage_kind == "shared":
            if self.event_controller is None:
                raise ValueError("The event collection is unavailable.")

            source_location_id = str(
                self.current_location_id or ""
            ).strip()
            location_ids = list(values.get("location_ids", []))
            locked_location_ids = list(
                values.get("locked_location_ids", [])
            )

            if source_location_id not in location_ids:
                location_ids.append(source_location_id)

            if source_location_id not in locked_location_ids:
                locked_location_ids.append(source_location_id)

            values["location_ids"] = location_ids
            values["locked_location_ids"] = locked_location_ids
            record_id = str(
                original_event.get("record_id", "") or ""
            ).strip()

            if record_id:
                saved = self.event_controller.update_event(
                    record_id,
                    values,
                )
            else:
                saved = self.event_controller.create_event(values)

            self.shared_event_saved(saved)
            return saved

        if storage_kind != "location":
            raise ValueError(
                "This event is generated from an individual record."
            )

        event_id = str(
            original_event.get("event_id", "") or ""
        ).strip()
        location_id = str(
            original_event.get("origin_location_id", "")
            or self.current_location_id
            or ""
        ).strip()
        location_values = {
            "event_id": event_id,
            "event_type": values["event_type"],
            "title": values["title"],
            "date": values["date"],
            "note": values["description"],
        }
        updated_location, saved_event = self.controller.update_event(
            location_id,
            event_id,
            location_values,
        )
        self.selected_timeline_event_id = event_id
        self.refresh_timeline()
        self.status_command(
            f"Saved event {saved_event.get('title', 'Event')}"
        )

        if self.events_changed_command is not None:
            self.events_changed_command()

        return saved_event

    def cancel_event_editor(self):
        if (
            self.draft_event is not None
            or self.event_editor.is_new_event()
        ):
            self.draft_event = None
            self.selected_timeline_event_id = ""
            self.timeline_list.selection_clear(0, "end")
            self.refresh_timeline()
            return

        self.update_timeline_details()

    def save_edited_event(self, values):
        event_id = str(values.get("event_id", "") or "")

        try:
            self.controller.update_event(
                self.current_location_id,
                event_id,
                values,
            )
        except (KeyError, TypeError, ValueError) as error:
            messagebox.showerror("Cannot edit event", str(error), parent=self)
            return False

        self.selected_timeline_event_id = event_id
        self.refresh_timeline()
        self.status_command("Updated location event")
        return True

    def remove_event(self):
        event = self.selected_timeline_event()

        if event and event.get("_draft_event"):
            self.cancel_event_editor()
            return

        if event is None:
            return

        removable = bool(
            event.get("event_kind") == "global"
            or (
                event.get("event_kind") == "location"
                and not event.get("propagation_distance", 0)
            )
        )

        if not removable:
            self.event_editor.show_error(
                "This event is generated or inherited from another record."
            )
            return

        event_id = str(event.get("event_id", "") or "")

        if self.remove_armed_event_id != event_id:
            self.remove_armed_event_id = event_id
            self.timeline_remove_button.set_text("Confirm remove")
            self.event_editor.show_error(
                "Click Confirm remove again to delete this event."
            )
            return

        if event.get("event_kind") == "global":
            if self.event_controller is None:
                return

            deleted = self.event_controller.delete_event(
                event.get("record_id", "")
            )
            removed_title = deleted.get("title", "Event")

            if self.events_changed_command is not None:
                self.events_changed_command()
        else:
            self.controller.delete_event(
                self.current_location_id,
                event.get("event_id", ""),
            )
            removed_title = event.get("title", "Event")

        self.selected_timeline_event_id = ""
        self.reset_event_remove_confirmation()
        self.refresh_timeline()
        self.status_command(f"Removed event {removed_title}")

    def reset_event_remove_confirmation(self):
        self.remove_armed_event_id = ""

        if hasattr(self, "timeline_remove_button"):
            self.timeline_remove_button.set_text("Remove")

    def open_timeline_selection(self, event=None):
        self.timeline_event_selected(event)
        return "break"


class LocationParentDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        locations,
        selected_location_id,
        save_command,
        region_lock_id="",
    ):
        super().__init__(parent)
        self.locations = list(locations)
        self.selected_location_id = str(selected_location_id or "").strip()
        self.save_command = save_command
        self.region_lock_id = str(region_lock_id or "").strip()
        self.title("Choose containing region")
        self.geometry("560x640")
        self.minsize(460, 500)
        self.configure(bg=APP_BACKGROUND)
        self.transient(parent.winfo_toplevel())
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_dialog()
        self.location_tree.set_locations(
            self.locations,
            self.selected_location_id,
        )
        self.location_tree.set_scope(self.region_lock_id)
        self.selected_location_id = self.location_tree.selected_location_id
        self.bind("<Escape>", self.close_dialog)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def build_dialog(self):
        card = tk.Frame(
            self,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=18,
            pady=16,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        card.grid_rowconfigure(2, weight=1)
        card.grid_columnconfigure(0, weight=1)
        heading = tk.Label(
            card,
            text="Place this location within",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(14, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")
        explanation = tk.Label(
            card,
            text=(
                "Choose a region from the hierarchy. Search keeps matching "
                "branches together, and The World makes the location top level."
            ),
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
            justify="left",
            wraplength=470,
        )
        explanation.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        self.location_tree = LocationHierarchyTree(
            card,
            self.location_selected,
            background=SURFACE,
            show_scope_controls=False,
            initial_scope_location_id=self.region_lock_id,
        )
        self.location_tree.grid(row=2, column=0, sticky="nsew")
        footer = tk.Frame(card, bg=SURFACE)
        footer.grid(row=3, column=0, sticky="e", pady=(14, 0))
        cancel_button = SoftButton(
            footer,
            text="Cancel",
            command=self.destroy,
            background=SURFACE,
            width=88,
            height=36,
        )
        cancel_button.pack(side="left", padx=(0, 6))
        choose_button = SoftButton(
            footer,
            text="Use this region",
            command=self.choose_location,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=134,
            height=36,
        )
        choose_button.pack(side="left")

    def location_selected(self, location_id):
        self.selected_location_id = str(location_id or "").strip()

    def choose_location(self):
        self.save_command(self.selected_location_id)
        self.destroy()

    def close_dialog(self, event=None):
        self.destroy()
        return "break"
