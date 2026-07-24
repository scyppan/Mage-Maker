import tkinter as tk
from copy import deepcopy

from mage_maker.sections.events.editor import (
    NEW_EVENT_DRAFT_ID,
    EventEditor,
)
from mage_maker.sections.events.types import event_type_label
from mage_maker.sections.timeline.events import (
    EVENT_TYPE_LABELS,
    normalize_timeline_event,
    normalize_timeline_events,
    sort_timeline_events,
    timeline_event_summary,
)
from mage_maker.ui.theme import (
    BORDER_SOFT,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    FIELD_BACKGROUND,
    LIST_ALTERNATE,
    LIST_SELECTED,
    PRIMARY,
    PRIMARY_HOVER,
    PRIMARY_SOFT,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    app_font,
)
from mage_maker.ui.widgets import LabeledEntry, SoftButton


EVENT_COLORS = {
    "starting_location": "#DDD2EA",
    "born": "#EAD7E7",
    "birth_name": "#E2D6ED",
    "gave_birth": "#F1D9E4",
    "had_child": "#E7D5F0",
    "got_married": "#D5EAD9",
    "died": "#EBCFD6",
    "started_school": "#D9E3F1",
    "opened_business": "#E8D9C4",
    "got_job": "#D8E3EC",
    "relocated": "#EFE3C7",
    "name_change": "#DDD2EA",
    "custom": "#E0D2E8",
    "other": "#E0D2E8",
}
LIFE_START_PRIORITIES = {
    "starting_location": 0,
    "born": 1,
    "birth_name": 2,
}


class TimelineView(tk.Frame):
    def __init__(
        self,
        parent,
        change_command,
        people_provider=None,
        navigate_command=None,
        name_change_command=None,
        event_controller=None,
        person_id_provider=None,
        linked_events_changed_command=None,
        linked_event_create_command=None,
        linked_event_edit_command=None,
    ):
        super().__init__(parent, bg=SURFACE)
        self.change_command = change_command
        self.people_provider = people_provider
        self.navigate_command = navigate_command
        self.name_change_command = name_change_command
        self.event_controller = event_controller
        self.person_id_provider = person_id_provider
        self.linked_events_changed_command = linked_events_changed_command
        self.events = []
        self.linked_events = []
        self.visible_events = []
        self.draft_event = None
        self.selected_event_id = None
        self.event_editor_visible = False
        self.loading = False
        self.remove_armed_event_id = ""
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
            text="Events",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="nsew")
        self.add_button = SoftButton(
            toolbar,
            text="Add event",
            command=self.start_add_event,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=104,
            height=36,
        )
        self.add_button.grid(row=0, column=1, padx=(6, 0), pady=4)
        self.edit_button = SoftButton(
            toolbar,
            text="Edit event",
            command=self.edit_selected_event,
            background=SURFACE,
            fill=PRIMARY_SOFT,
            hover_fill=PRIMARY_HOVER,
            width=104,
            height=36,
        )
        self.edit_button.grid(row=0, column=2, padx=(6, 0), pady=4)
        self.remove_button = SoftButton(
            toolbar,
            text="Remove",
            command=self.remove_event,
            background=SURFACE,
            width=118,
            height=36,
        )
        self.remove_button.grid(row=0, column=3, padx=(6, 0), pady=4)

    def build_workspace(self):
        self.workspace = tk.Frame(self, bg=SURFACE)
        self.workspace.grid(row=1, column=0, sticky="nsew")
        self.workspace.grid_rowconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(0, weight=5, uniform="timeline")
        self.workspace.grid_columnconfigure(1, weight=4, uniform="timeline")
        self.list_panel = tk.Frame(
            self.workspace,
            bg=SURFACE_MUTED,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        self.list_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
        )
        self.list_panel.grid_rowconfigure(2, weight=1)
        self.list_panel.grid_columnconfigure(0, weight=1)
        list_heading = tk.Label(
            self.list_panel,
            text="Events in date order",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        list_heading.grid(row=0, column=0, sticky="ew")
        search_entry = LabeledEntry(
            self.list_panel,
            "Search events",
            self.search_value,
            background=SURFACE_MUTED,
        )
        search_entry.grid(row=1, column=0, sticky="ew", pady=(10, 9))
        list_frame = tk.Frame(self.list_panel, bg=SURFACE_MUTED)
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
        self.listbox.bind("<Double-Button-1>", self.edit_selected_event)
        scrollbar = tk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.event_editor = EventEditor(
            self.workspace,
            self.event_controller,
            self.save_editor_event,
            self.cancel_editor,
            context="person",
            background=SURFACE_MUTED,
        )
        self.event_editor.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
        )
        self.hide_event_editor()
        self.update_button_state()

    def show_event_editor(self):
        if self.event_editor_visible:
            return

        self.workspace.grid_columnconfigure(
            0,
            weight=5,
            uniform="timeline",
        )
        self.workspace.grid_columnconfigure(
            1,
            weight=4,
            uniform="timeline",
        )
        self.list_panel.grid(
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
        self.workspace.grid_columnconfigure(
            0,
            weight=1,
            uniform="",
        )
        self.workspace.grid_columnconfigure(
            1,
            weight=0,
            uniform="",
        )
        self.list_panel.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=0,
        )
        self.event_editor_visible = False

    def current_person_id(self):
        if self.person_id_provider is None:
            return ""

        return str(self.person_id_provider() or "").strip()

    def set_events(self, events):
        self.loading = True

        if (
            self.draft_event is not None
            and self.draft_event.get("_person_id") != self.current_person_id()
        ):
            self.draft_event = None
            self.selected_event_id = None

        self.events = normalize_timeline_events(events)
        available_ids = {
            event["event_id"]
            for event in self.events
        }.union(
            {
                str(event.get("record_id", "") or "")
                for event in self.linked_events
            }
        )

        if self.draft_event is not None:
            available_ids.add(NEW_EVENT_DRAFT_ID)

        if self.selected_event_id not in available_ids:
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
        available_ids = {
            event["event_id"]
            for event in self.events
        }.union(
            {
                str(event.get("record_id", "") or "")
                for event in self.linked_events
            }
        )

        if self.draft_event is not None:
            available_ids.add(NEW_EVENT_DRAFT_ID)

        if self.selected_event_id not in available_ids:
            self.selected_event_id = None

        self.filter_events()

    def filter_events(self, *arguments):
        query = self.search_value.get().strip().casefold()
        candidate_events = [deepcopy(event) for event in self.events]

        for linked_event in self.linked_events:
            display_event = deepcopy(linked_event)
            display_event["event_id"] = display_event["record_id"]
            display_event["_stored_event"] = True
            display_event["detail"] = display_event.get("title", "")
            display_event["note"] = display_event.get("description", "")
            candidate_events.append(display_event)

        if self.draft_event is not None:
            candidate_events.append(deepcopy(self.draft_event))

        self.visible_events = []

        for event in candidate_events:
            summary = self.event_summary_text(event)

            if (
                not event.get("_draft_event")
                and query
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
            if event.get("_draft_event"):
                self.listbox.insert("end", "New event (unsaved)")
            else:
                event_date = str(event.get("date") or "nd.")
                self.listbox.insert(
                    "end",
                    f"{event_date}: {self.event_summary_text(event)}",
                )

            self.listbox.itemconfigure(
                index,
                background=(
                    PRIMARY_SOFT
                    if event.get("_draft_event")
                    else (
                        LIST_ALTERNATE
                        if event.get("_stored_event")
                        else EVENT_COLORS.get(
                            event.get("event_type"),
                            FIELD_BACKGROUND,
                        )
                    )
                ),
            )

            if event.get("event_id") == self.selected_event_id:
                self.listbox.selection_set(index)
                self.listbox.see(index)

        self.refresh_editor()
        self.update_button_state()

    def event_summary_text(self, event):
        if event.get("_draft_event"):
            return "New event (unsaved)"

        if event.get("_stored_event"):
            return (
                f"{event_type_label(event)} · "
                f"{event.get('title', 'Event')}"
            )

        return timeline_event_summary(event)

    def display_event_sort_key(self, event):
        if event.get("_draft_event"):
            return -1, 0, 0, 0, ""

        event_type = str(event.get("event_type", "") or "")

        if not event.get("_stored_event") and event_type in LIFE_START_PRIORITIES:
            return (
                0,
                LIFE_START_PRIORITIES[event_type],
                0,
                0,
                "",
            )

        year, month, day = self.event_date_parts(event.get("date"))
        return (
            1,
            year,
            month,
            day,
            self.event_summary_text(event).casefold(),
        )

    def event_date_parts(self, value):
        date_text = str(value or "").strip()

        if not date_text:
            return 10000, 13, 32

        negative = date_text.startswith("-")
        body = date_text[1:] if negative else date_text
        parts = body.split("-")

        try:
            year = int(parts[0])
        except (TypeError, ValueError, IndexError):
            return 10000, 13, 32

        if negative:
            year = -year

        try:
            month = int(parts[1]) if len(parts) > 1 else 0
        except (TypeError, ValueError):
            month = 0

        try:
            day = int(parts[2]) if len(parts) > 2 else 0
        except (TypeError, ValueError):
            day = 0

        return year, month, day

    def select_event(self, event=None):
        selected_indexes = self.listbox.curselection()

        if not selected_indexes:
            return

        self.selected_event_id = self.visible_events[
            selected_indexes[0]
        ]["event_id"]
        self.reset_remove_confirmation()
        self.refresh_editor()
        self.update_button_state()

    def selected_event(self):
        for event in self.visible_events:
            if event.get("event_id") == self.selected_event_id:
                return event

        selected_indexes = self.listbox.curselection()

        if (
            selected_indexes
            and selected_indexes[0] < len(self.visible_events)
        ):
            selected_event = self.visible_events[selected_indexes[0]]
            self.selected_event_id = selected_event.get("event_id")
            return selected_event

        return None

    def refresh_editor(self):
        selected_event = self.selected_event()

        if selected_event is None:
            if self.event_editor.is_new_event():
                self.show_event_editor()
                self.event_editor.ensure_new_event_editable()
                return

            self.event_editor.clear(
                "Select an event to view it, or click Add event."
            )
            self.hide_event_editor()
            return

        if selected_event.get("_draft_event"):
            self.show_event_editor()

            if not self.event_editor.is_new_event():
                self.event_editor.start_new(
                    context="person",
                    default_person_ids=(self.current_person_id(),),
                )

            self.event_editor.ensure_new_event_editable()
            return

        self.show_event_editor()
        person_id = self.current_person_id()

        if selected_event.get("_stored_event"):
            stored_event = (
                self.event_controller.get_event(
                    selected_event.get("record_id", "")
                )
                if self.event_controller is not None
                else None
            )

            if stored_event is None:
                self.event_editor.clear("This event no longer exists.")
                return

            self.event_editor.load_event(
                stored_event,
                storage_kind="shared",
                context="person",
                person_ids=(person_id,),
                read_only=False,
            )
            return

        automatic_source = str(
            selected_event.get("automatic_source", "") or ""
        )
        read_only = bool(automatic_source)
        explanation = ""

        if automatic_source == "life_start":
            explanation = (
                "This required opening event is synchronized from the "
                "person's profile and Name Details."
            )
        elif automatic_source:
            explanation = (
                "This event is synchronized automatically from its source record."
            )

        self.event_editor.load_event(
            selected_event,
            storage_kind="timeline",
            context="person",
            person_ids=(person_id,),
            read_only=read_only,
            explanation=explanation,
        )

    def start_add_event(self):
        person_id = self.current_person_id()

        if self.event_controller is None or not person_id:
            self.show_event_editor()
            self.event_editor.show_error(
                "Save this person before adding an event."
            )
            return

        self.draft_event = {
            "event_id": NEW_EVENT_DRAFT_ID,
            "event_type": "custom",
            "detail": "New event",
            "date": "",
            "note": "",
            "_person_id": person_id,
            "_draft_event": True,
        }
        self.selected_event_id = NEW_EVENT_DRAFT_ID
        self.reset_remove_confirmation()
        self.filter_events()
        self.event_editor.ensure_new_event_editable()

    def open_add_dialog(self):
        self.start_add_event()

    def edit_selected_event(self, event=None):
        selected_event = self.selected_event()

        if selected_event is None:
            return

        if selected_event.get("_draft_event"):
            self.show_event_editor()
            self.event_editor.ensure_new_event_editable()
            return

        if selected_event.get("automatic_source"):
            return

        self.refresh_editor()
        self.event_editor.begin_edit()
        self.event_editor.canvas.yview_moveto(0)

    def open_edit_dialog(self, event=None):
        self.edit_selected_event(event)

    def save_editor_event(self, values, storage_kind, original_event):
        if storage_kind == "shared":
            if self.event_controller is None:
                raise ValueError("The event collection is unavailable.")

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

            self.draft_event = None
            self.selected_event_id = saved["record_id"]
            person_id = self.current_person_id()
            self.linked_events = (
                self.event_controller.events_for_person(person_id)
                if person_id
                else []
            )
            self.filter_events()

            if self.linked_events_changed_command is not None:
                self.linked_events_changed_command(saved)

            return saved

        timeline_event = deepcopy(original_event)
        timeline_event.update(
            {
                "event_type": values["event_type"],
                "detail": values["title"],
                "date": values["date"],
                "note": values["description"],
            }
        )
        return self.save_event(timeline_event)

    def save_event(self, event):
        normalized_event = normalize_timeline_event(event)
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

        return normalized_event

    def cancel_editor(self):
        if (
            self.draft_event is not None
            or self.event_editor.is_new_event()
        ):
            self.draft_event = None
            self.selected_event_id = None
            self.listbox.selection_clear(0, "end")
            self.filter_events()
            return

        self.refresh_editor()

    def update_button_state(self):
        selected_event = self.selected_event()
        has_selection = selected_event is not None
        automatic = bool(
            has_selection
            and selected_event.get("automatic_source")
        )
        draft = bool(
            has_selection
            and selected_event.get("_draft_event")
        )
        self.edit_button.set_enabled(
            has_selection and not automatic and not draft
        )
        self.remove_button.set_enabled(
            has_selection and not automatic and not draft
        )

    def remove_event(self):
        selected_event = self.selected_event()

        if selected_event and selected_event.get("_draft_event"):
            self.cancel_editor()
            return

        if selected_event is None or selected_event.get("automatic_source"):
            return

        event_id = str(selected_event.get("event_id", "") or "")

        if self.remove_armed_event_id != event_id:
            self.remove_armed_event_id = event_id
            self.remove_button.set_text("Confirm remove")
            self.event_editor.show_error(
                "Click Confirm remove again to delete this event."
            )
            return

        if selected_event.get("_stored_event"):
            if self.event_controller is None:
                return

            deleted = self.event_controller.delete_event(
                selected_event.get("record_id", "")
            )
            person_id = self.current_person_id()
            self.linked_events = (
                self.event_controller.events_for_person(person_id)
                if person_id
                else []
            )

            if self.linked_events_changed_command is not None:
                self.linked_events_changed_command(deleted)
        else:
            self.events = [
                event
                for event in self.events
                if event.get("event_id") != event_id
            ]

            if not self.loading:
                self.change_command()

        self.selected_event_id = None
        self.reset_remove_confirmation()
        self.filter_events()

    def reset_remove_confirmation(self):
        self.remove_armed_event_id = ""
        self.remove_button.set_text("Remove")
