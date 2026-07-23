import tkinter as tk
from copy import deepcopy
from tkinter import messagebox

from mage_maker.core.dates import split_partial_date
from mage_maker.ui.theme import (
    APP_BACKGROUND,
    BORDER,
    BORDER_SOFT,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    FIELD_BACKGROUND,
    LIST_ALTERNATE,
    LIST_SELECTED,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)
from mage_maker.sections.events.models import world_event_type_label
from mage_maker.sections.timeline.events import (
    EVENT_LABEL_TYPES,
    EVENT_TYPES,
    EVENT_TYPE_LABELS,
    normalize_timeline_event,
    normalize_timeline_events,
    sort_timeline_events,
    timeline_detail_label,
    timeline_event_summary,
)
from mage_maker.ui.widgets import (
    LabeledEntry,
    RoundedSelect,
    RoundedText,
    SoftButton,
)


EVENT_COLORS = {
    "starting_location": "#DDD2EA",
    "born": "#EAD7E7",
    "birth_name": "#E2D6ED",
    "gave_birth": "#F1D9E4",
    "had_child": "#E7D5F0",
    "got_married": "#D5EAD9",
    "started_school": "#D9E3F1",
    "opened_business": "#E8D9C4",
    "got_job": "#D8E3EC",
    "relocated": "#EFE3C7",
    "name_change": "#DDD2EA",
    "custom": "#E0D2E8",
}


class TimelineView(tk.Frame):
    def __init__(
        self,
        parent,
        change_command,
        people_provider=None,
        navigate_command=None,
        name_change_command=None,
        linked_event_create_command=None,
        linked_event_edit_command=None,
    ):
        super().__init__(parent, bg=SURFACE)
        self.change_command = change_command
        self.people_provider = people_provider
        self.navigate_command = navigate_command
        self.name_change_command = name_change_command
        self.linked_event_create_command = linked_event_create_command
        self.linked_event_edit_command = linked_event_edit_command
        self.events = []
        self.linked_events = []
        self.visible_events = []
        self.selected_event_id = None
        self.related_person_id = ""
        self.loading = False
        self.search_value = tk.StringVar()
        self.search_value.trace_add("write", self.filter_events)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_toolbar()
        self.build_workspace()

    def build_toolbar(self):
        toolbar = tk.Frame(self, bg=SURFACE, height=44)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.grid_propagate(False)
        toolbar.grid_columnconfigure(0, weight=1)

        heading = tk.Label(
            toolbar,
            text="Timeline",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="nsew")

        self.add_button = SoftButton(
            toolbar,
            text="Add event",
            command=self.open_add_dialog,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=104,
            height=36,
        )
        self.add_button.grid(row=0, column=1, padx=(6, 0), pady=4)

        self.add_linked_button = None

        if self.linked_event_create_command is not None:
            self.add_linked_button = SoftButton(
                toolbar,
                text="Add shared event",
                command=self.linked_event_create_command,
                background=SURFACE,
                fill=PRIMARY,
                hover_fill=PRIMARY_HOVER,
                foreground=TEXT_DARK,
                width=138,
                height=36,
            )
            self.add_linked_button.grid(
                row=0,
                column=2,
                padx=(6, 0),
                pady=4,
            )

        self.edit_button = SoftButton(
            toolbar,
            text="Edit event",
            command=self.open_edit_dialog,
            background=SURFACE,
            width=104,
            height=36,
        )
        self.edit_button.grid(row=0, column=3, padx=(6, 0), pady=4)

        self.remove_button = SoftButton(
            toolbar,
            text="Remove",
            command=self.remove_event,
            background=SURFACE,
            width=92,
            height=36,
        )
        self.remove_button.grid(row=0, column=4, padx=(6, 0), pady=4)

    def build_workspace(self):
        workspace = tk.Frame(self, bg=SURFACE)
        workspace.grid(row=1, column=0, sticky="nsew")
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=5, uniform="timeline")
        workspace.grid_columnconfigure(1, weight=4, uniform="timeline")

        list_panel = tk.Frame(
            workspace,
            bg=SURFACE_MUTED,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        list_panel.grid_rowconfigure(2, weight=1)
        list_panel.grid_columnconfigure(0, weight=1)

        list_heading = tk.Label(
            list_panel,
            text="Events in date order",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        list_heading.grid(row=0, column=0, sticky="ew")

        search_entry = LabeledEntry(
            list_panel,
            "Search timeline",
            self.search_value,
            background=SURFACE_MUTED,
        )
        search_entry.grid(row=1, column=0, sticky="ew", pady=(10, 9))

        list_frame = tk.Frame(list_panel, bg=SURFACE_MUTED)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            list_frame,
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
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", self.select_event)
        self.listbox.bind("<Double-Button-1>", self.open_edit_dialog)

        scrollbar = tk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        details_panel = tk.Frame(
            workspace,
            bg=SURFACE_MUTED,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        details_panel.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        details_panel.grid_rowconfigure(6, weight=1)
        details_panel.grid_columnconfigure(0, weight=1)

        details_heading = tk.Label(
            details_panel,
            text="Selected event",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        details_heading.grid(row=0, column=0, sticky="ew")

        self.type_value = tk.StringVar(value="No event selected")
        self.date_value = tk.StringVar(value="Date: nd.")
        self.summary_value = tk.StringVar(value="Select an event to view its details.")

        type_label = tk.Label(
            details_panel,
            textvariable=self.type_value,
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        type_label.grid(row=1, column=0, sticky="ew", pady=(14, 2))

        date_label = tk.Label(
            details_panel,
            textvariable=self.date_value,
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
        )
        date_label.grid(row=2, column=0, sticky="ew")

        summary_label = tk.Label(
            details_panel,
            textvariable=self.summary_value,
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(12, "bold"),
            anchor="w",
            justify="left",
            wraplength=360,
        )
        summary_label.grid(row=3, column=0, sticky="ew", pady=(10, 12))

        note_heading = tk.Label(
            details_panel,
            text="Event notes",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(9, "bold"),
            anchor="w",
        )
        note_heading.grid(row=4, column=0, sticky="ew", pady=(0, 5))

        self.related_person_button = SoftButton(
            details_panel,
            text="Open child",
            command=self.open_related_person,
            background=SURFACE_MUTED,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            foreground=TEXT_DARK,
            width=190,
            height=32,
        )
        self.related_person_button.grid(
            row=5,
            column=0,
            sticky="w",
            pady=(0, 8),
        )
        self.related_person_button.grid_remove()

        self.note_text = tk.Text(
            details_panel,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            relief="flat",
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            borderwidth=0,
            font=app_font(10),
            wrap="word",
            padx=10,
            pady=9,
            state="disabled",
        )
        self.note_text.grid(row=6, column=0, sticky="nsew")
        self.update_button_state()

    def set_events(self, events):
        self.loading = True
        self.events = normalize_timeline_events(events)

        if self.selected_event_id not in {
            event["event_id"]
            for event in self.events
        }.union({
            str(event.get("record_id", "") or "")
            for event in self.linked_events
        }):
            self.selected_event_id = None

        self.filter_events()
        self.loading = False

    def get_events(self):
        return deepcopy(self.events)

    def set_linked_events(self, events):
        self.linked_events = [
            deepcopy(event)
            for event in events
            if isinstance(event, dict)
            and str(event.get("record_id", "") or "").strip()
        ]

        if self.selected_event_id not in {
            event["event_id"]
            for event in self.events
        }.union({
            str(event.get("record_id", "") or "")
            for event in self.linked_events
        }):
            self.selected_event_id = None

        self.filter_events()

    def filter_events(self, *arguments):
        query = self.search_value.get().strip().casefold()
        candidate_events = [deepcopy(event) for event in self.events]

        for linked_event in self.linked_events:
            display_event = deepcopy(linked_event)
            display_event["event_id"] = display_event["record_id"]
            display_event["_shared_event"] = True
            display_event["detail"] = display_event.get("title", "")
            display_event["note"] = display_event.get("description", "")
            candidate_events.append(display_event)

        self.visible_events = []

        for event in candidate_events:
            summary = self.event_summary_text(event)

            if (
                query
                and query not in summary.casefold()
                and query not in str(event.get("detail") or "").casefold()
                and query not in str(event.get("note") or "").casefold()
                and query not in str(event.get("date") or "").casefold()
            ):
                continue

            self.visible_events.append(event)

        self.visible_events.sort(key=self.display_event_sort_key)
        self.listbox.delete(0, "end")

        for index, event in enumerate(self.visible_events):
            event_date = str(event.get("date") or "nd.")
            self.listbox.insert(
                "end",
                f"{event_date}: {self.event_summary_text(event)}",
            )
            self.listbox.itemconfigure(
                index,
                background=(
                    LIST_ALTERNATE
                    if event.get("_shared_event")
                    else EVENT_COLORS.get(
                        event.get("event_type"),
                        FIELD_BACKGROUND,
                    )
                ),
            )

            if event.get("event_id") == self.selected_event_id:
                self.listbox.selection_set(index)
                self.listbox.see(index)

        self.refresh_details()

    def event_summary_text(self, event):
        if event.get("_shared_event"):
            return (
                f"Shared · {world_event_type_label(event)} · "
                f"{event.get('title', 'Event')}"
            )

        return timeline_event_summary(event)

    def display_event_sort_key(self, event):
        date_text = str(event.get("date", "") or "")
        date_parts = date_text.split("-")

        if date_text.startswith("-"):
            date_parts = date_text[1:].split("-")
            year_text = f"-{date_parts[0]}"
        else:
            year_text = date_parts[0] if date_parts else ""

        try:
            year = int(year_text)
        except (TypeError, ValueError):
            year = 10000

        try:
            month = int(date_parts[1]) if len(date_parts) > 1 else 0
        except (TypeError, ValueError):
            month = 0

        try:
            day = int(date_parts[2]) if len(date_parts) > 2 else 0
        except (TypeError, ValueError):
            day = 0

        return (
            year,
            month,
            day,
            self.event_summary_text(event).casefold(),
            str(event.get("event_id", "") or ""),
        )

    def select_event(self, event=None):
        selected_indexes = self.listbox.curselection()

        if not selected_indexes:
            return

        self.selected_event_id = self.visible_events[selected_indexes[0]]["event_id"]
        self.refresh_details()

    def selected_event(self):
        for event in self.visible_events:
            if event.get("event_id") == self.selected_event_id:
                return event

        return None

    def refresh_details(self):
        event = self.selected_event()
        self.related_person_id = ""
        self.related_person_button.grid_remove()
        self.note_text.configure(state="normal")
        self.note_text.delete("1.0", "end")

        if event is None:
            self.type_value.set("No event selected")
            self.date_value.set("Date: nd.")
            self.summary_value.set("Select an event to view its details.")
        else:
            if event.get("_shared_event"):
                self.type_value.set(
                    f"Shared event · {world_event_type_label(event)}"
                )
            else:
                self.type_value.set(
                    EVENT_TYPE_LABELS.get(
                        event.get("event_type"),
                        "Custom event",
                    )
                )
            self.date_value.set(f"Date: {event.get('date') or 'nd.'}")
            self.summary_value.set(self.event_summary_text(event))
            self.note_text.insert("1.0", str(event.get("note") or ""))
            related_person_id = str(
                (
                    event.get("person_ids", [""])[0]
                    if event.get("_shared_event")
                    and event.get("person_ids")
                    else event.get("related_person_id")
                )
                or ""
            ).strip()
            related_person = self.related_person(related_person_id)

            if related_person is not None and self.navigate_command is not None:
                related_name = str(
                    related_person.get("displayed_name") or "child"
                ).strip()
                self.related_person_id = related_person_id
                self.related_person_button.set_text(f"Open {related_name}")
                self.related_person_button.grid()

        self.note_text.configure(state="disabled")
        self.update_button_state()

    def related_person(self, record_id):
        if not record_id or self.people_provider is None:
            return None

        for person in self.people_provider():
            if str(person.get("record_id", "") or "") == record_id:
                return person

        return None

    def open_related_person(self):
        if self.related_person_id and self.navigate_command is not None:
            self.navigate_command(self.related_person_id)

    def update_button_state(self):
        selected_event = self.selected_event()
        has_selection = selected_event is not None
        is_shared = bool(
            has_selection and selected_event.get("_shared_event")
        )
        can_remove = bool(
            has_selection
            and not is_shared
            and selected_event.get("automatic_source") != "life_start"
            and selected_event.get("automatic_source") != "name_change"
        )
        self.edit_button.set_enabled(
            has_selection
            and (
                not is_shared
                or self.linked_event_edit_command is not None
            )
        )
        self.remove_button.set_enabled(can_remove)

    def open_add_dialog(self):
        TimelineEventDialog(
            self,
            None,
            self.save_event,
            name_change_command=self.name_change_command,
        )

    def open_edit_dialog(self, event=None):
        selected_event = self.selected_event()

        if selected_event is None:
            return

        if selected_event.get("_shared_event"):
            if self.linked_event_edit_command is not None:
                self.linked_event_edit_command(selected_event)

            return

        if (
            selected_event.get("event_type") in ("name_change", "birth_name")
            and self.name_change_command is not None
        ):
            self.name_change_command(selected_event)
            return

        TimelineEventDialog(self, selected_event, self.save_event)

    def save_event(self, event):
        normalized_event = normalize_timeline_event(event)

        if (
            normalized_event.get("event_type") == "name_change"
            and self.name_change_command is not None
        ):
            self.after_idle(self.name_change_command, None)
            return True

        replacement_index = None

        for index, existing_event in enumerate(self.events):
            if existing_event.get("event_id") == normalized_event["event_id"]:
                replacement_index = index
                break

        if replacement_index is None:
            self.events.append(normalized_event)
        else:
            self.events[replacement_index] = normalized_event

        self.events = sort_timeline_events(self.events)
        self.selected_event_id = normalized_event["event_id"]
        self.filter_events()

        if not self.loading:
            self.change_command()

        return True

    def remove_event(self):
        selected_event = self.selected_event()

        if selected_event is None:
            return

        if selected_event.get("_shared_event"):
            return

        if selected_event.get("automatic_source") == "life_start":
            messagebox.showinfo(
                "Required timeline event",
                (
                    "Starting location and Born are required at the "
                    "beginning of every timeline."
                ),
                parent=self,
            )
            return

        if selected_event.get("automatic_source") == "name_change":
            messagebox.showinfo(
                "Name change event",
                "Edit or remove this event through Name Details.",
                parent=self,
            )
            return

        if not messagebox.askyesno(
            "Remove timeline event",
            f"Remove {timeline_event_summary(selected_event)}?",
            parent=self,
        ):
            return

        self.events = [
            event
            for event in self.events
            if event.get("event_id") != self.selected_event_id
        ]
        self.selected_event_id = None
        self.filter_events()

        if not self.loading:
            self.change_command()


class TimelineEventDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        event,
        save_command,
        name_change_command=None,
    ):
        super().__init__(parent)
        self.save_command = save_command
        self.name_change_command = name_change_command
        self.event = deepcopy(event) if isinstance(event, dict) else {}
        self.event_type_value = tk.StringVar()
        self.year_value = tk.StringVar()
        self.month_value = tk.StringVar()
        self.day_value = tk.StringVar()
        self.detail_value = tk.StringVar()
        self.detail_label_value = tk.StringVar(value="Event detail")

        event_type = str(self.event.get("event_type") or "custom")
        self.event_type_value.set(EVENT_TYPE_LABELS.get(event_type, "Custom event"))
        year, month, day = split_partial_date(self.event.get("date", ""))
        self.year_value.set(year)
        self.month_value.set(month)
        self.day_value.set(day)
        self.detail_value.set(str(self.event.get("detail") or ""))
        self.event_type_value.trace_add("write", self.update_detail_label)

        self.title("Edit event" if event else "Add event")
        self.geometry("620x585")
        self.resizable(False, False)
        self.configure(bg=APP_BACKGROUND)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

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
            text="Event",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(14, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")

        explanation = tk.Label(
            card,
            text="Choose a common event or Custom event, then add its date and notes.",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
            justify="left",
        )
        explanation.grid(row=1, column=0, sticky="ew", pady=(4, 12))

        type_label = tk.Label(
            card,
            text="Event type",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        type_label.grid(row=2, column=0, sticky="ew", pady=(0, 5))

        available_event_types = (
            EVENT_TYPES
            if self.event.get("automatic_source") == "life_start"
            else tuple(
                event_definition
                for event_definition in EVENT_TYPES
                if event_definition[0] not in (
                    "starting_location",
                    "born",
                    "birth_name",
                )
            )
        )
        self.type_picker = RoundedSelect(
            card,
            textvariable=self.event_type_value,
            values=[label for event_key, label in available_event_types],
            background=SURFACE,
            height=40,
            font=app_font(10),
        )
        self.type_picker.grid(row=3, column=0, sticky="ew")
        self.type_picker.bind(
            "<<RoundedSelectSelected>>",
            self.event_type_selected,
        )

        if self.event.get("automatic_source") == "life_start":
            self.type_picker.set_enabled(False)

        fields = tk.Frame(card, bg=SURFACE)
        fields.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        fields.grid_columnconfigure(0, weight=1)

        detail_field = LabeledEntry(
            fields,
            "Event detail",
            self.detail_value,
            background=SURFACE,
        )
        detail_field.grid(row=0, column=0, sticky="ew")
        detail_field.label.configure(textvariable=self.detail_label_value)

        date_fields = tk.Frame(fields, bg=SURFACE)
        date_fields.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        date_fields.grid_columnconfigure((0, 1, 2), weight=1)
        year_field = LabeledEntry(
            date_fields,
            "Year",
            self.year_value,
            background=SURFACE,
        )
        year_field.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        month_field = LabeledEntry(
            date_fields,
            "Month",
            self.month_value,
            background=SURFACE,
        )
        month_field.grid(row=0, column=1, sticky="ew", padx=6)
        day_field = LabeledEntry(
            date_fields,
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
        notes_label.grid(row=5, column=0, sticky="ew", pady=(14, 5))

        self.notes_control = RoundedText(
            card,
            background=SURFACE,
            height=7,
        )
        self.notes_control.grid(row=6, column=0, sticky="nsew")
        self.notes_control.text.insert("1.0", str(self.event.get("note") or ""))

        footer = tk.Frame(card, bg=SURFACE)
        footer.grid(row=7, column=0, sticky="e", pady=(14, 0))

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

        self.bind("<Escape>", self.close_dialog)
        self.update_detail_label()
        self.after_idle(detail_field.control.focus_set)

    def update_detail_label(self, *arguments):
        event_type = EVENT_LABEL_TYPES.get(self.event_type_value.get(), "custom")
        self.detail_label_value.set(timeline_detail_label(event_type))

    def event_type_selected(self, event=None):
        self.update_detail_label()

        if (
            not self.event
            and self.event_type_value.get() == EVENT_TYPE_LABELS["name_change"]
            and self.name_change_command is not None
        ):
            self.destroy()
            self.master.after_idle(self.name_change_command, None)

    def save_event(self):
        event_type = EVENT_LABEL_TYPES.get(self.event_type_value.get(), "custom")
        year = self.year_value.get().strip()
        month = self.month_value.get().strip()
        day = self.day_value.get().strip()
        date_value = year

        if month:
            date_value += f"-{month}"

        if day:
            date_value += f"-{day}"

        event = {
            "event_id": self.event.get("event_id"),
            "event_type": event_type,
            "detail": self.detail_value.get(),
            "date": date_value,
            "note": self.notes_control.text.get("1.0", "end-1c"),
            "related_person_id": self.event.get("related_person_id", ""),
            "automatic_source": self.event.get("automatic_source", ""),
        }

        try:
            saved = self.save_command(event)
        except (TypeError, ValueError) as error:
            messagebox.showerror("Cannot save event", str(error), parent=self)
            return

        if saved:
            self.destroy()

    def close_dialog(self, event=None):
        self.destroy()
        return "break"
