import tkinter as tk
from copy import deepcopy
from functools import partial
from tkinter import messagebox

from mage_maker.sections.events.models import (
    WORLD_EVENT_LABEL_TYPES,
    WORLD_EVENT_TYPES,
    WORLD_EVENT_TYPE_LABELS,
    split_world_event_date,
)
from mage_maker.sections.locations.location_hierarchy import (
    LocationHierarchyTree,
)
from mage_maker.sections.locations.models import location_path
from mage_maker.ui.theme import (
    APP_BACKGROUND,
    BORDER,
    BORDER_SOFT,
    FIELD_BACKGROUND,
    LIST_SELECTED,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import (
    LabeledEntry,
    RoundedEntry,
    RoundedSelect,
    RoundedText,
    SoftButton,
)


class WorldEventDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        controller,
        event=None,
        saved_command=None,
        default_person_ids=(),
        default_location_ids=(),
        locked_location_ids=(),
    ):
        super().__init__(parent)
        self.controller = controller
        self.saved_command = saved_command
        self.event = deepcopy(event) if isinstance(event, dict) else {}
        self.people_options = self.controller.people_options()
        self.location_options = self.controller.location_options()
        self.location_records = self.controller.location_records()
        self.recent_people_options = (
            self.controller.recent_people_options()
        )
        self.recent_location_options = (
            self.controller.recent_location_options()
        )
        self.title_value = tk.StringVar(
            value=str(self.event.get("title", "") or "")
        )
        event_type = str(self.event.get("event_type", "other") or "other")
        self.event_type_value = tk.StringVar(
            value=WORLD_EVENT_TYPE_LABELS.get(event_type, "Other")
        )
        year, month, day = split_world_event_date(
            self.event.get("date", "")
        )
        self.year_value = tk.StringVar(value=year)
        self.month_value = tk.StringVar(value=month)
        self.day_value = tk.StringVar(value=day)
        self.initial_person_ids = set(
            self.event.get("person_ids", default_person_ids)
        )
        self.selected_person_ids = [
            option["value"]
            for option in self.people_options
            if option["value"] in self.initial_person_ids
        ]
        self.locked_location_ids = {
            str(location_id or "").strip()
            for location_id in (
                list(self.event.get("locked_location_ids", []))
                + list(locked_location_ids)
            )
            if str(location_id or "").strip()
        }
        self.initial_location_ids = set(
            self.event.get("location_ids", default_location_ids)
        ).union(self.locked_location_ids)
        self.selected_location_ids = [
            option["value"]
            for option in self.location_options
            if option["value"] in self.initial_location_ids
        ]
        self.title(
            "Edit shared event"
            if self.event.get("record_id")
            else "Add shared event"
        )
        self.geometry("940x720")
        self.minsize(820, 620)
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
            padx=20,
            pady=18,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(5, weight=1)
        heading = tk.Label(
            card,
            text="Shared event",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(15, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")
        explanation = tk.Label(
            card,
            text=(
                "The required year places this event in its period automatically. "
                "Link any applicable people and locations so the same event also "
                "appears from those records."
            ),
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
            justify="left",
        )
        explanation.grid(row=1, column=0, sticky="ew", pady=(3, 14))
        main_fields = tk.Frame(card, bg=SURFACE)
        main_fields.grid(row=2, column=0, sticky="ew")
        main_fields.grid_columnconfigure(0, weight=3)
        main_fields.grid_columnconfigure(1, weight=2)
        title_field = LabeledEntry(
            main_fields,
            "Event title",
            self.title_value,
            background=SURFACE,
        )
        title_field.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        type_panel = tk.Frame(main_fields, bg=SURFACE)
        type_panel.grid(row=0, column=1, sticky="ew", padx=(7, 0))
        type_panel.grid_columnconfigure(0, weight=1)
        type_label = tk.Label(
            type_panel,
            text="Event type",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        type_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        type_picker = RoundedSelect(
            type_panel,
            textvariable=self.event_type_value,
            values=[label for event_type, label in WORLD_EVENT_TYPES],
            background=SURFACE,
            height=40,
            font=app_font(10),
        )
        type_picker.grid(row=1, column=0, sticky="ew")
        date_panel = tk.Frame(card, bg=SURFACE)
        date_panel.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        date_panel.grid_columnconfigure((0, 1, 2), weight=1)
        year_field = LabeledEntry(
            date_panel,
            "Year (required)",
            self.year_value,
            background=SURFACE,
        )
        year_field.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        month_field = LabeledEntry(
            date_panel,
            "Month",
            self.month_value,
            background=SURFACE,
        )
        month_field.grid(row=0, column=1, sticky="ew", padx=6)
        day_field = LabeledEntry(
            date_panel,
            "Day",
            self.day_value,
            background=SURFACE,
        )
        day_field.grid(row=0, column=2, sticky="ew", padx=(6, 0))
        description_panel = tk.Frame(card, bg=SURFACE)
        description_panel.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        description_panel.grid_columnconfigure(0, weight=1)
        description_label = tk.Label(
            description_panel,
            text="Description",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            anchor="w",
        )
        description_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.description_control = RoundedText(
            description_panel,
            background=SURFACE,
            height=4,
        )
        self.description_control.grid(row=1, column=0, sticky="ew")
        self.description_control.text.insert(
            "1.0",
            str(self.event.get("description", "") or ""),
        )
        associations = tk.Frame(card, bg=SURFACE)
        associations.grid(row=5, column=0, sticky="nsew", pady=(16, 0))
        associations.grid_rowconfigure(0, weight=1)
        associations.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="event_associations",
        )
        self.people_list = self.build_people_selection(
            associations,
            0,
        )
        self.locations_list = self.build_location_selection(
            associations,
            1,
        )
        footer = tk.Frame(card, bg=SURFACE)
        footer.grid(row=6, column=0, sticky="e", pady=(16, 0))
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
            width=112,
            height=36,
        )
        save_button.pack(side="left")
        self.after_idle(title_field.control.focus_set)

    def build_people_selection(self, parent, column):
        panel = tk.Frame(
            parent,
            bg=SURFACE_MUTED,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        panel.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0, 6),
        )
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        heading = tk.Label(
            panel,
            text="People",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")
        hint = tk.Label(
            panel,
            text="Add only the people linked to this event.",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(8),
            anchor="w",
        )
        hint.grid(row=1, column=0, sticky="ew", pady=(2, 7))
        list_frame = tk.Frame(panel, bg=SURFACE_MUTED)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        listbox = tk.Listbox(
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
            selectmode="extended",
            exportselection=False,
        )
        listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(list_frame, command=listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        listbox.configure(yscrollcommand=scrollbar.set)
        self.build_recent_suggestions(
            panel,
            3,
            self.recent_people_options,
            self.person_chosen,
        )
        buttons = tk.Frame(panel, bg=SURFACE_MUTED)
        buttons.grid(row=4, column=0, sticky="e", pady=(8, 0))
        add_button = SoftButton(
            buttons,
            text="Find person",
            command=self.open_person_picker,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=106,
            height=34,
        )
        add_button.pack(side="left", padx=(0, 6))
        remove_button = SoftButton(
            buttons,
            text="Remove",
            command=self.remove_selected_people,
            background=SURFACE_MUTED,
            width=88,
            height=34,
        )
        remove_button.pack(side="left")
        self.render_selected_people(listbox)
        return listbox

    def build_recent_suggestions(
        self,
        parent,
        row,
        options,
        selection_command,
    ):
        recent_panel = tk.Frame(parent, bg=SURFACE_MUTED)
        recent_panel.grid(row=row, column=0, sticky="ew")
        recent_panel.grid_columnconfigure(0, weight=1)
        recent_label = tk.Label(
            recent_panel,
            text="Recently used",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(8, "bold"),
            anchor="w",
        )
        recent_label.grid(row=0, column=0, sticky="ew", pady=(0, 3))

        if not options:
            empty_label = tk.Label(
                recent_panel,
                text="Suggestions appear here after you save events.",
                bg=SURFACE_MUTED,
                fg=TEXT_MUTED,
                font=app_font(8),
                anchor="w",
            )
            empty_label.grid(row=1, column=0, sticky="ew")
            return recent_panel

        for index, option in enumerate(options[:3]):
            suggestion = SoftButton(
                recent_panel,
                text=self.short_suggestion_label(option.get("label", "")),
                command=partial(
                    selection_command,
                    option.get("value", ""),
                ),
                background=SURFACE_MUTED,
                fill=FIELD_BACKGROUND,
                hover_fill=LIST_SELECTED,
                foreground=TEXT_DARK,
                width=320,
                height=28,
                anchor="w",
                padx=9,
                font=app_font(8),
            )
            suggestion.grid(
                row=index + 1,
                column=0,
                sticky="ew",
                pady=(0, 3),
            )

        return recent_panel

    def short_suggestion_label(self, label):
        normalized = " ".join(str(label or "").strip().split())

        if len(normalized) <= 34:
            return normalized

        return f"{normalized[:31]}..."

    def render_selected_people(self, listbox=None):
        target_listbox = listbox or self.people_list
        people_labels = {
            option["value"]: option["label"]
            for option in self.people_options
        }
        target_listbox.delete(0, "end")

        for person_id in self.selected_person_ids:
            target_listbox.insert(
                "end",
                people_labels.get(person_id, "Missing person"),
            )

    def open_person_picker(self):
        selected_id = (
            self.selected_person_ids[-1]
            if self.selected_person_ids
            else ""
        )
        EventPersonPickerDialog(
            self,
            self.people_options,
            self.recent_people_options,
            selected_id,
            self.person_chosen,
        )

    def person_chosen(self, person_id):
        normalized_id = str(person_id or "").strip()

        if normalized_id and normalized_id not in self.selected_person_ids:
            self.selected_person_ids.append(normalized_id)

        self.render_selected_people()

        if normalized_id in self.selected_person_ids:
            index = self.selected_person_ids.index(normalized_id)
            self.people_list.selection_clear(0, "end")
            self.people_list.selection_set(index)
            self.people_list.see(index)

    def remove_selected_people(self):
        selected_indices = set(self.people_list.curselection())

        if not selected_indices:
            return

        self.selected_person_ids = [
            person_id
            for index, person_id in enumerate(self.selected_person_ids)
            if index not in selected_indices
        ]
        self.render_selected_people()

    def build_location_selection(self, parent, column):
        panel = tk.Frame(
            parent,
            bg=SURFACE_MUTED,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        panel.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(6, 0),
        )
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        heading = tk.Label(
            panel,
            text="Locations",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")
        hint = tk.Label(
            panel,
            text="Add locations from a searchable hierarchy.",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(8),
            anchor="w",
        )
        hint.grid(row=1, column=0, sticky="ew", pady=(2, 7))
        list_frame = tk.Frame(panel, bg=SURFACE_MUTED)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        listbox = tk.Listbox(
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
            selectmode="extended",
            exportselection=False,
        )
        listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(list_frame, command=listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        listbox.configure(yscrollcommand=scrollbar.set)
        self.build_recent_suggestions(
            panel,
            3,
            self.recent_location_options,
            self.location_chosen,
        )
        buttons = tk.Frame(panel, bg=SURFACE_MUTED)
        buttons.grid(row=4, column=0, sticky="e", pady=(8, 0))
        add_button = SoftButton(
            buttons,
            text="Find location",
            command=self.open_location_picker,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=112,
            height=34,
        )
        add_button.pack(side="left", padx=(0, 6))
        remove_button = SoftButton(
            buttons,
            text="Remove",
            command=self.remove_selected_locations,
            background=SURFACE_MUTED,
            width=88,
            height=34,
        )
        remove_button.pack(side="left")
        self.render_selected_locations(listbox)
        return listbox

    def render_selected_locations(self, listbox=None):
        target_listbox = listbox or self.locations_list
        location_labels = {
            option["value"]: option["label"]
            for option in self.location_options
        }
        target_listbox.delete(0, "end")

        for location_id in self.selected_location_ids:
            location_label = location_labels.get(
                location_id,
                "Missing location",
            )

            if location_id in self.locked_location_ids:
                location_label = f"{location_label}  ·  source locked"

            target_listbox.insert(
                "end",
                location_label,
            )

    def open_location_picker(self):
        selected_id = (
            self.selected_location_ids[-1]
            if self.selected_location_ids
            else ""
        )
        EventLocationPickerDialog(
            self,
            self.location_records,
            selected_id,
            self.location_chosen,
        )

    def location_chosen(self, location_id):
        normalized_id = str(location_id or "").strip()

        if (
            normalized_id
            and normalized_id not in self.selected_location_ids
        ):
            self.selected_location_ids.append(normalized_id)

        self.render_selected_locations()

        if normalized_id in self.selected_location_ids:
            index = self.selected_location_ids.index(normalized_id)
            self.locations_list.selection_clear(0, "end")
            self.locations_list.selection_set(index)
            self.locations_list.see(index)

    def remove_selected_locations(self):
        selected_indices = set(self.locations_list.curselection())

        if not selected_indices:
            return

        self.selected_location_ids = [
            location_id
            for index, location_id in enumerate(self.selected_location_ids)
            if (
                index not in selected_indices
                or location_id in self.locked_location_ids
            )
        ]
        self.render_selected_locations()

    def save_event(self):
        year = self.year_value.get().strip()
        month = self.month_value.get().strip()
        day = self.day_value.get().strip()
        date_value = year

        if month:
            date_value += f"-{month}"

        if day:
            date_value += f"-{day}"

        if not year:
            messagebox.showerror(
                "Cannot save event",
                "Enter the year when this event happened.",
                parent=self,
            )
            return False

        values = {
            "event_type": WORLD_EVENT_LABEL_TYPES.get(
                self.event_type_value.get(),
                "other",
            ),
            "title": self.title_value.get(),
            "date": date_value,
            "description": self.description_control.text.get(
                "1.0",
                "end-1c",
            ),
            "person_ids": list(self.selected_person_ids),
            "period_names": [],
            "location_ids": list(
                dict.fromkeys(
                    self.selected_location_ids
                    + list(self.locked_location_ids)
                )
            ),
            "locked_location_ids": list(self.locked_location_ids),
        }

        try:
            if self.event.get("record_id"):
                saved = self.controller.update_event(
                    self.event["record_id"],
                    values,
                )
            else:
                saved = self.controller.create_event(values)
        except (KeyError, TypeError, ValueError) as error:
            messagebox.showerror(
                "Cannot save event",
                str(error),
                parent=self,
            )
            return False

        if self.saved_command is not None:
            self.saved_command(saved)

        self.destroy()
        return True

    def close_dialog(self, event=None):
        self.destroy()
        return "break"


class EventPersonPickerDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        people_options,
        recent_people_options,
        selected_person_id,
        save_command,
    ):
        super().__init__(parent)
        self.people_options = [
            deepcopy(option)
            for option in people_options
            if isinstance(option, dict)
            and str(option.get("value", "") or "").strip()
        ]
        self.recent_people_options = [
            deepcopy(option)
            for option in recent_people_options
            if isinstance(option, dict)
            and str(option.get("value", "") or "").strip()
        ]
        self.visible_options = []
        self.selected_person_id = str(
            selected_person_id or ""
        ).strip()
        self.save_command = save_command
        self.search_value = tk.StringVar()
        self.result_heading_value = tk.StringVar(value="Recently used")
        self.selection_value = tk.StringVar(
            value="Select a person to add."
        )
        self.title("Add event person")
        self.geometry("560x620")
        self.minsize(460, 500)
        self.configure(bg=APP_BACKGROUND)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_dialog()
        self.search_value.trace_add("write", self.refresh_results)
        self.refresh_results()
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
        card.grid_rowconfigure(4, weight=1)
        card.grid_columnconfigure(0, weight=1)
        heading = tk.Label(
            card,
            text="Choose a person",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(14, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")
        explanation = tk.Label(
            card,
            text=(
                "Recently used people appear first. Type any part of a "
                "name to search everyone."
            ),
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
            justify="left",
            wraplength=470,
        )
        explanation.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        self.search_control = RoundedEntry(
            card,
            textvariable=self.search_value,
            background=SURFACE,
            height=38,
            font=app_font(10),
        )
        self.search_control.grid(row=2, column=0, sticky="ew")
        self.search_control.bind_input("<Escape>", self.clear_search)
        self.search_control.bind_input("<Return>", self.choose_first_result)
        results_heading = tk.Label(
            card,
            textvariable=self.result_heading_value,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        results_heading.grid(row=3, column=0, sticky="ew", pady=(11, 5))
        results_frame = tk.Frame(
            card,
            bg=FIELD_BACKGROUND,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
        )
        results_frame.grid(row=4, column=0, sticky="nsew")
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        self.results_list = tk.Listbox(
            results_frame,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            selectbackground=LIST_SELECTED,
            selectforeground=TEXT_DARK,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=app_font(10),
            activestyle="none",
            exportselection=False,
        )
        self.results_list.grid(row=0, column=0, sticky="nsew")
        self.results_list.bind("<<ListboxSelect>>", self.person_selected)
        self.results_list.bind("<Double-Button-1>", self.choose_person)
        scrollbar = tk.Scrollbar(
            results_frame,
            command=self.results_list.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_list.configure(yscrollcommand=scrollbar.set)
        selected_label = tk.Label(
            card,
            textvariable=self.selection_value,
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(9, "bold"),
            anchor="w",
        )
        selected_label.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        footer = tk.Frame(card, bg=SURFACE)
        footer.grid(row=6, column=0, sticky="e", pady=(14, 0))
        cancel_button = SoftButton(
            footer,
            text="Cancel",
            command=self.destroy,
            background=SURFACE,
            width=88,
            height=36,
        )
        cancel_button.pack(side="left", padx=(0, 6))
        self.add_button = SoftButton(
            footer,
            text="Add person",
            command=self.choose_person,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=108,
            height=36,
        )
        self.add_button.pack(side="left")
        self.add_button.set_enabled(False)
        self.after_idle(self.search_control.focus_set)

    def refresh_results(self, *arguments):
        query = " ".join(
            self.search_value.get().strip().split()
        ).casefold()

        if query:
            self.visible_options = [
                option
                for option in self.people_options
                if query in str(option.get("label", "") or "").casefold()
            ]
            self.result_heading_value.set(
                f"Search results ({len(self.visible_options)})"
            )
        else:
            self.visible_options = list(self.recent_people_options)
            self.result_heading_value.set(
                (
                    "Recently used"
                    if self.visible_options
                    else "Start typing to search"
                )
            )

        self.results_list.delete(0, "end")

        for index, option in enumerate(self.visible_options):
            self.results_list.insert(
                "end",
                str(option.get("label", "") or "Unnamed person"),
            )

            if option.get("value") == self.selected_person_id:
                self.results_list.selection_set(index)
                self.results_list.see(index)

        if not any(
            option.get("value") == self.selected_person_id
            for option in self.visible_options
        ):
            self.selected_person_id = ""

        self.update_selection_display()

    def person_selected(self, event=None):
        selection = self.results_list.curselection()

        if not selection:
            return

        self.selected_person_id = str(
            self.visible_options[selection[0]].get("value", "") or ""
        ).strip()
        self.update_selection_display()

    def update_selection_display(self):
        selected_label = ""

        for option in self.people_options:
            if option.get("value") == self.selected_person_id:
                selected_label = str(option.get("label", "") or "")
                break

        self.selection_value.set(
            selected_label or "Select a person to add."
        )
        self.add_button.set_enabled(bool(self.selected_person_id))

    def choose_first_result(self, event=None):
        if self.visible_options and not self.selected_person_id:
            self.selected_person_id = str(
                self.visible_options[0].get("value", "") or ""
            ).strip()
            self.results_list.selection_clear(0, "end")
            self.results_list.selection_set(0)

        self.choose_person()
        return "break"

    def choose_person(self, event=None):
        if not self.selected_person_id:
            return

        self.save_command(self.selected_person_id)
        self.destroy()

    def clear_search(self, event=None):
        if self.search_value.get():
            self.search_value.set("")
            return "break"

        self.destroy()
        return "break"

    def close_dialog(self, event=None):
        self.destroy()
        return "break"


class EventLocationPickerDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        locations,
        selected_location_id,
        save_command,
    ):
        super().__init__(parent)
        self.locations = [
            deepcopy(location)
            for location in locations
            if isinstance(location, dict)
        ]
        self.selected_location_id = str(
            selected_location_id or ""
        ).strip()
        self.save_command = save_command
        self.selection_value = tk.StringVar(
            value="Select a location from the hierarchy."
        )
        self.title("Add event location")
        self.geometry("620x680")
        self.minsize(500, 520)
        self.configure(bg=APP_BACKGROUND)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_dialog()
        self.location_tree.set_locations(
            self.locations,
            self.selected_location_id,
        )
        self.location_selected(
            self.location_tree.selected_location_id
        )
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
            text="Choose a location",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(14, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")
        explanation = tk.Label(
            card,
            text=(
                "Search by any part of a location or its path, then expand "
                "the matching branch and choose the exact place."
            ),
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        explanation.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        self.location_tree = LocationHierarchyTree(
            card,
            self.location_selected,
            background=SURFACE,
            show_scope_controls=False,
        )
        self.location_tree.grid(row=2, column=0, sticky="nsew")
        selected_label = tk.Label(
            card,
            textvariable=self.selection_value,
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(9, "bold"),
            anchor="w",
        )
        selected_label.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer = tk.Frame(card, bg=SURFACE)
        footer.grid(row=4, column=0, sticky="e", pady=(14, 0))
        cancel_button = SoftButton(
            footer,
            text="Cancel",
            command=self.destroy,
            background=SURFACE,
            width=88,
            height=36,
        )
        cancel_button.pack(side="left", padx=(0, 6))
        self.add_button = SoftButton(
            footer,
            text="Add location",
            command=self.choose_location,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=118,
            height=36,
        )
        self.add_button.pack(side="left")

    def location_selected(self, location_id):
        requested_id = str(location_id or "").strip()
        self.selected_location_id = requested_id

        if not requested_id:
            self.selection_value.set(
                "Select a location from the hierarchy."
            )
            self.add_button.set_enabled(False)
            return

        self.selection_value.set(
            location_path(requested_id, self.locations)
        )
        self.add_button.set_enabled(True)

    def choose_location(self):
        if not self.selected_location_id:
            return

        self.save_command(self.selected_location_id)
        self.destroy()

    def close_dialog(self, event=None):
        self.destroy()
        return "break"
