import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from mage_maker.core.dates import split_partial_date
from mage_maker.sections.locations.models import location_path
from mage_maker.sections.locations.periods_page import PeriodsPage
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
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import LabeledEntry, RoundedText, SoftButton


LOCAL_EVENT_COLORS = ("#FFFFFF", "#F1F1F1")
PROPAGATED_EVENT_COLORS = (
    "#E6D8F0",
    "#D9E7F3",
    "#DCEBDD",
    "#F1E7CF",
    "#E6DFD8",
)


class LocationPage(tk.Frame):
    def __init__(self, parent, controller, status_command, navigate_person_command):
        super().__init__(parent, bg=APP_BACKGROUND)
        self.controller = controller
        self.status_command = status_command
        self.navigate_person_command = navigate_person_command
        self.locations = []
        self.visible_events = []
        self.current_location_id = None
        self.active_section_name = "overview"
        self.section_pages = {}
        self.section_buttons = {}
        self.parent_ids_by_label = {}
        self.name_value = tk.StringVar()
        self.parent_value = tk.StringVar()
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_toolbar()
        self.build_navigation()
        self.build_content()
        self.refresh()
        self.show_section("overview")

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
        new_button = SoftButton(
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
        new_button.grid(row=0, column=1, padx=4, pady=13)
        delete_button = SoftButton(
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
        delete_button.grid(row=0, column=2, padx=(4, 16), pady=13)

    def build_navigation(self):
        navigation = tk.Frame(self, bg=APP_BACKGROUND)
        navigation.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=18,
            pady=(10, 0),
        )

        for section_name, label, width in (
            ("overview", "Overview", 104),
            ("periods", "Periods", 96),
        ):
            button = SoftButton(
                navigation,
                text=label,
                command=LocationSectionCommand(self, section_name),
                background=APP_BACKGROUND,
                fill=BUTTON_SOFT,
                hover_fill=BUTTON_SOFT_HOVER,
                foreground=TEXT_DARK,
                width=width,
                height=36,
            )
            button.pack(side="left", padx=(0, 6))
            self.section_buttons[section_name] = button

    def build_content(self):
        content = tk.Frame(self, bg=APP_BACKGROUND)
        content.grid(row=2, column=0, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        self.build_workspace(content)
        self.periods_page = PeriodsPage(
            content,
            self.controller,
            self.status_command,
            self.navigate_person_command,
        )
        self.periods_page.grid(row=0, column=0, sticky="nsew")
        self.section_pages["periods"] = self.periods_page

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
        self.section_pages["overview"] = workspace

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
            text="Nested locations",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(12, "bold"),
            anchor="w",
        )
        list_title.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        self.location_list = tk.Listbox(
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
        self.location_list.grid(row=1, column=0, sticky="nsew")
        self.location_list.bind("<<ListboxSelect>>", self.location_selected)
        list_scrollbar = tk.Scrollbar(list_card, command=self.location_list.yview)
        list_scrollbar.grid(row=1, column=1, sticky="ns")
        self.location_list.configure(yscrollcommand=list_scrollbar.set)

        editor_card = tk.Frame(
            workspace,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=18,
            pady=16,
        )
        editor_card.grid_rowconfigure(3, weight=1)
        editor_card.grid_columnconfigure(0, weight=1)
        self.build_location_fields(editor_card)
        self.build_timeline(editor_card)

        workspace.add(list_card, minsize=290, width=330)
        workspace.add(editor_card, minsize=680)

    def show_section(self, section_name):
        if section_name not in self.section_pages:
            return False

        self.active_section_name = section_name

        if section_name == "periods":
            self.periods_page.refresh()

        self.section_pages[section_name].tkraise()

        for name, button in self.section_buttons.items():
            if name == section_name:
                button.set_colors(PRIMARY, PRIMARY_HOVER, TEXT_DARK)
            else:
                button.set_colors(BUTTON_SOFT, BUTTON_SOFT_HOVER, TEXT_DARK)

        return True

    def build_location_fields(self, parent):
        identity = tk.Frame(parent, bg=SURFACE_MUTED, padx=14, pady=12)
        identity.grid(row=0, column=0, sticky="ew")
        identity.grid_columnconfigure(0, weight=1)
        identity.grid_columnconfigure(1, weight=1)
        name_field = LabeledEntry(
            identity,
            "Location name",
            self.name_value,
            background=SURFACE_MUTED,
        )
        name_field.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        parent_frame = tk.Frame(identity, bg=SURFACE_MUTED)
        parent_frame.grid(row=0, column=1, sticky="ew", padx=(7, 0))
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_label = tk.Label(
            parent_frame,
            text="Nested within",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        parent_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.parent_picker = ttk.Combobox(
            parent_frame,
            textvariable=self.parent_value,
            state="readonly",
            font=app_font(10),
        )
        self.parent_picker.grid(row=1, column=0, sticky="ew", ipady=7)

        narrative = tk.Frame(parent, bg=SURFACE)
        narrative.grid(row=1, column=0, sticky="ew", pady=(14, 0))
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
            height=4,
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
            height=4,
        )
        self.notes_control.pack(fill="both", expand=True)
        save_button = SoftButton(
            parent,
            text="Save location",
            command=self.save_location,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=126,
            height=38,
        )
        save_button.grid(row=2, column=0, sticky="e", pady=(10, 0))

    def build_timeline(self, parent):
        timeline_panel = tk.Frame(
            parent,
            bg=SURFACE_MUTED,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        timeline_panel.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
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
        legend.grid(row=1, column=0, sticky="ew", pady=(3, 8))
        list_frame = tk.Frame(timeline_panel, bg=SURFACE_MUTED)
        list_frame.grid(row=2, column=0, sticky="nsew")
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
        self.timeline_list.bind("<Double-Button-1>", self.open_timeline_selection)
        timeline_scrollbar = tk.Scrollbar(list_frame, command=self.timeline_list.yview)
        timeline_scrollbar.grid(row=0, column=1, sticky="ns")
        self.timeline_list.configure(yscrollcommand=timeline_scrollbar.set)
        event_buttons = tk.Frame(timeline_panel, bg=SURFACE_MUTED)
        event_buttons.grid(row=3, column=0, sticky="e", pady=(9, 0))
        add_button = SoftButton(
            event_buttons,
            text="Add event",
            command=self.add_event,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=104,
            height=36,
        )
        add_button.pack(side="left", padx=(0, 6))
        edit_button = SoftButton(
            event_buttons,
            text="Edit",
            command=self.edit_event,
            background=SURFACE_MUTED,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            foreground=TEXT_DARK,
            width=82,
            height=36,
        )
        edit_button.pack(side="left", padx=(0, 6))
        remove_button = SoftButton(
            event_buttons,
            text="Remove",
            command=self.remove_event,
            background=SURFACE_MUTED,
            fill=DELETE_SOFT,
            hover_fill=DELETE_HOVER,
            foreground=TEXT_DARK,
            width=92,
            height=36,
        )
        remove_button.pack(side="left")

    def refresh(self, selected_location_id=None):
        selected_id = selected_location_id or self.current_location_id
        self.locations = self.controller.list_locations()
        self.location_list.delete(0, "end")

        for index, location in enumerate(self.locations):
            depth = self.location_depth(location)
            self.location_list.insert(
                "end",
                f"{'   ' * depth}{location.get('name', 'Unnamed')}",
            )

            if location.get("record_id") == selected_id:
                self.location_list.selection_set(index)
                self.location_list.see(index)

        if selected_id and self.controller.get_location(selected_id):
            self.load_location(selected_id)
        elif self.locations:
            self.location_list.selection_set(0)
            self.load_location(self.locations[0]["record_id"])
        else:
            self.clear_form()

        self.periods_page.refresh()

    def refresh_person_data(self):
        if self.current_location_id:
            self.refresh_timeline()

        self.periods_page.refresh()

    def location_depth(self, location):
        record_id = str(location.get("record_id", "") or "")
        path = location_path(record_id, self.locations)
        return max(0, path.count(" › "))

    def location_selected(self, event=None):
        selected = self.location_list.curselection()

        if selected:
            self.load_location(self.locations[selected[0]]["record_id"])

    def load_location(self, record_id):
        location = self.controller.get_location(record_id)

        if location is None:
            return

        self.current_location_id = record_id
        self.name_value.set(str(location.get("name", "") or ""))
        self.refresh_parent_picker(location.get("parent_location_id", ""))
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
        self.refresh_timeline()
        self.status_command(f"Loaded location {location.get('name', 'Unnamed')}")

    def refresh_parent_picker(self, selected_parent_id=""):
        options = self.controller.parent_options(self.current_location_id or "")
        self.parent_ids_by_label = {"No parent · top level": ""}

        for option in options:
            self.parent_ids_by_label[option["label"]] = option["record_id"]

        labels = list(self.parent_ids_by_label)
        self.parent_picker.configure(values=labels)
        selected_label = "No parent · top level"

        for label, parent_id in self.parent_ids_by_label.items():
            if parent_id == selected_parent_id:
                selected_label = label
                break

        self.parent_value.set(selected_label)

    def refresh_timeline(self):
        self.timeline_list.delete(0, "end")

        if not self.current_location_id:
            self.visible_events = []
            return

        self.visible_events = self.controller.timeline_for(self.current_location_id)

        for index, event in enumerate(self.visible_events):
            date_text = str(event.get("date", "") or "nd.")
            source_text = ""

            if event.get("propagation_distance", 0):
                source_text = (
                    f"  ·  from {event.get('origin_location_name', 'ancestor')} "
                    f"(level {event.get('source_level', 0)})"
                )

            kind_text = "  ·  mage" if event.get("event_kind") == "mage" else ""
            self.timeline_list.insert(
                "end",
                f"{date_text}  ·  {event.get('title', 'Event')}{source_text}{kind_text}",
            )

            if event.get("propagation_distance", 0):
                level = int(event.get("source_level", 0) or 0)
                color = PROPAGATED_EVENT_COLORS[
                    min(level, len(PROPAGATED_EVENT_COLORS) - 1)
                ]
            else:
                color = LOCAL_EVENT_COLORS[index % 2]

            self.timeline_list.itemconfigure(index, background=color)

    def clear_form(self):
        self.current_location_id = None
        self.name_value.set("")
        self.parent_value.set("No parent · top level")
        self.parent_picker.configure(values=["No parent · top level"])
        self.demographics_control.text.delete("1.0", "end")
        self.notes_control.text.delete("1.0", "end")
        self.timeline_list.delete(0, "end")
        self.visible_events = []

    def create_location(self):
        name = simpledialog.askstring(
            "New location",
            "Location name",
            parent=self.winfo_toplevel(),
        )

        if name is None:
            return

        parent_id = self.current_location_id or ""

        try:
            created = self.controller.create_location(
                {
                    "name": name,
                    "parent_location_id": parent_id,
                    "demographics": "",
                    "notes": "",
                    "timeline_events": [],
                }
            )
        except (TypeError, ValueError) as error:
            messagebox.showerror("Cannot create location", str(error), parent=self)
            return

        self.refresh(created["record_id"])
        self.status_command(f"Created location {created['name']}")

    def save_location(self):
        if not self.current_location_id:
            return False

        values = {
            "name": self.name_value.get(),
            "parent_location_id": self.parent_ids_by_label.get(
                self.parent_value.get(),
                "",
            ),
            "demographics": self.demographics_control.text.get("1.0", "end-1c"),
            "notes": self.notes_control.text.get("1.0", "end-1c"),
        }

        try:
            updated = self.controller.update_location(
                self.current_location_id,
                values,
            )
        except (KeyError, TypeError, ValueError) as error:
            messagebox.showerror("Cannot save location", str(error), parent=self)
            return False

        self.refresh(updated["record_id"])
        self.status_command(f"Saved location {updated['name']}")
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
            messagebox.showinfo(
                "Select a location",
                "Select or create a location before adding an event.",
                parent=self,
            )
            return

        LocationEventDialog(self, {}, self.save_new_event)

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
        selected = self.timeline_list.curselection()

        if not selected:
            return None

        return self.visible_events[selected[0]]

    def edit_event(self):
        event = self.selected_timeline_event()

        if event is None:
            return

        if event.get("event_kind") != "location" or event.get(
            "propagation_distance",
            0,
        ):
            messagebox.showinfo(
                "Inherited event",
                "Open the source location or mage to edit this event.",
                parent=self,
            )
            return

        LocationEventDialog(self, event, self.save_edited_event)

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

        self.refresh_timeline()
        self.status_command("Updated location event")
        return True

    def remove_event(self):
        event = self.selected_timeline_event()

        if event is None:
            return

        if event.get("event_kind") != "location" or event.get(
            "propagation_distance",
            0,
        ):
            messagebox.showinfo(
                "Inherited event",
                "Open the source location or mage to remove this event.",
                parent=self,
            )
            return

        if not messagebox.askyesno(
            "Remove event",
            f"Remove {event.get('title', 'this event')}?",
            parent=self,
        ):
            return

        try:
            self.controller.delete_event(
                self.current_location_id,
                event.get("event_id", ""),
            )
        except (KeyError, ValueError) as error:
            messagebox.showerror("Cannot remove event", str(error), parent=self)
            return

        self.refresh_timeline()
        self.status_command("Removed location event")

    def open_timeline_selection(self, event=None):
        selected_event = self.selected_timeline_event()

        if selected_event is None:
            return

        person_id = str(selected_event.get("related_person_id", "") or "")

        if person_id:
            self.navigate_person_command(person_id)
        else:
            self.edit_event()


class LocationEventDialog(tk.Toplevel):
    def __init__(self, parent, event, save_command):
        super().__init__(parent)
        self.event = dict(event or {})
        self.save_command = save_command
        self.title_value = tk.StringVar(value=str(self.event.get("title", "") or ""))
        self.year_value = tk.StringVar()
        self.month_value = tk.StringVar()
        self.day_value = tk.StringVar()
        year, month, day = split_partial_date(self.event.get("date", ""))
        self.year_value.set(year)
        self.month_value.set(month)
        self.day_value.set(day)
        self.title("Edit location event" if event else "Add location event")
        self.geometry("590x520")
        self.resizable(False, False)
        self.configure(bg=APP_BACKGROUND)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_dialog()
        self.bind("<Escape>", self.close_dialog)

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
        card.grid_columnconfigure(0, weight=1)
        heading = tk.Label(
            card,
            text="Location event",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(14, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")
        title_field = LabeledEntry(
            card,
            "Event title",
            self.title_value,
            background=SURFACE,
        )
        title_field.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        date_frame = tk.Frame(card, bg=SURFACE)
        date_frame.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        date_frame.grid_columnconfigure((0, 1, 2), weight=1)
        year_field = LabeledEntry(
            date_frame,
            "Year",
            self.year_value,
            background=SURFACE,
        )
        year_field.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        month_field = LabeledEntry(
            date_frame,
            "Month",
            self.month_value,
            background=SURFACE,
        )
        month_field.grid(row=0, column=1, sticky="ew", padx=6)
        day_field = LabeledEntry(
            date_frame,
            "Day",
            self.day_value,
            background=SURFACE,
        )
        day_field.grid(row=0, column=2, sticky="ew", padx=(6, 0))
        notes_label = tk.Label(
            card,
            text="Event notes",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            anchor="w",
        )
        notes_label.grid(row=3, column=0, sticky="ew", pady=(14, 5))
        self.notes_control = RoundedText(card, background=SURFACE, height=7)
        self.notes_control.grid(row=4, column=0, sticky="nsew")
        self.notes_control.text.insert(
            "1.0",
            str(self.event.get("note", "") or ""),
        )
        footer = tk.Frame(card, bg=SURFACE)
        footer.grid(row=5, column=0, sticky="e", pady=(14, 0))
        cancel_button = SoftButton(
            footer,
            text="Cancel",
            command=self.destroy,
            background=SURFACE,
            width=88,
            height=36,
        )
        cancel_button.pack(side="left", padx=(0, 6))
        save_button = SoftButton(
            footer,
            text="Save event",
            command=self.save_event,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=110,
            height=36,
        )
        save_button.pack(side="left")

    def save_event(self):
        year = self.year_value.get().strip()
        month = self.month_value.get().strip()
        day = self.day_value.get().strip()
        date_value = year

        if month:
            date_value += f"-{month}"

        if day:
            date_value += f"-{day}"

        values = {
            "event_id": self.event.get("event_id", ""),
            "title": self.title_value.get(),
            "date": date_value,
            "note": self.notes_control.text.get("1.0", "end-1c"),
        }

        if self.save_command(values):
            self.destroy()

    def close_dialog(self, event=None):
        self.destroy()
        return "break"


class LocationSectionCommand:
    def __init__(self, page, section_name):
        self.page = page
        self.section_name = section_name

    def __call__(self):
        self.page.show_section(self.section_name)
