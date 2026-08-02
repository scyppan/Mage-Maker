import tkinter as tk
from tkinter import messagebox

from mage_maker.sections.organizations.controller import (
    ORGANIZATION_EVENT_FOUNDING,
    new_organization_event,
    normalize_organization_event,
)
from mage_maker.sections.events.dialog import (
    EventPersonPickerDialog,
)
from mage_maker.sections.events.eminence_picker import (
    EventEminencePicker,
)
from mage_maker.sections.events.models import split_world_event_date
from mage_maker.ui.theme import (
    APP_BACKGROUND,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    SURFACE,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import (
    CalendarAdoptionNotice,
    RoundedEntry,
    RoundedText,
    SoftButton,
)


class OrganizationEventDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        save_command,
        event=None,
        event_controller=None,
    ):
        super().__init__(parent)
        normalized_event = (
            normalize_organization_event(event)
            if isinstance(event, dict)
            else None
        )
        self.save_command = save_command
        self.event_controller = event_controller
        self.event = normalized_event
        self.is_founding = bool(
            normalized_event
            and normalized_event["event_type"]
            == ORGANIZATION_EVENT_FOUNDING
        )
        self.title_value = tk.StringVar(
            value=(
                normalized_event["title"]
                if normalized_event
                else ""
            )
        )
        event_year, event_month, event_day = split_world_event_date(
            normalized_event.get("date", "")
            if normalized_event
            else ""
        )
        self.year_value = tk.StringVar(
            value=event_year
        )
        self.month_value = tk.StringVar(value=event_month)
        self.day_value = tk.StringVar(value=event_day)
        self.selected_person_ids = list(
            normalized_event.get("person_ids", [])
            if normalized_event
            else []
        )
        self.selected_eminence_person_ids = list(
            normalized_event.get("eminence_person_ids", [])
            if normalized_event
            else []
        )
        self.selected_eminence_skills = dict(
            normalized_event.get("eminence_skills", {})
            if normalized_event
            else {}
        )
        self.title(
            "Founding event"
            if self.is_founding
            else "Organization event"
        )
        self.configure(bg=APP_BACKGROUND)
        self.geometry("700x700")
        self.minsize(620, 600)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_dialog()
        self.grab_set()
        self.after_idle(self.focus_first_field)

    def build_dialog(self):
        header = tk.Frame(self, bg=PRIMARY_DARK, height=58)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        heading = tk.Label(
            header,
            text=(
                "Founding event"
                if self.is_founding
                else "Organization event"
            ),
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(15, "bold"),
            anchor="w",
            padx=18,
        )
        heading.pack(fill="both", expand=True)

        body = tk.Frame(
            self,
            bg=SURFACE,
            padx=20,
            pady=18,
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(4, weight=1)
        body.grid_columnconfigure(0, weight=1)

        title_label = tk.Label(
            body,
            text="Title",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="ew")
        self.title_entry = RoundedEntry(
            body,
            textvariable=self.title_value,
            background=SURFACE,
            width=390,
            height=38,
            font=app_font(10),
        )
        self.title_entry.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 12),
        )
        self.title_entry.entry.configure(
            state="disabled" if self.is_founding else "normal"
        )

        date_frame = tk.Frame(body, bg=SURFACE)
        date_frame.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e",
            padx=(14, 0),
            pady=(0, 12),
        )
        date_frame.grid_columnconfigure((0, 1, 2), weight=1)

        for column, label_text in enumerate(("Year", "Month", "Day")):
            date_label = tk.Label(
                date_frame,
                text=label_text,
                bg=SURFACE,
                fg=TEXT_MUTED,
                font=app_font(9, "bold"),
                anchor="w",
            )
            date_label.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0, 5) if column < 2 else 0,
            )

        self.year_entry = RoundedEntry(
            date_frame,
            textvariable=self.year_value,
            background=SURFACE,
            width=92,
            height=38,
            font=app_font(10),
            justify="center",
        )
        self.year_entry.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(0, 5),
            pady=(5, 0),
        )
        self.month_entry = RoundedEntry(
            date_frame,
            textvariable=self.month_value,
            background=SURFACE,
            width=64,
            height=38,
            font=app_font(10),
            justify="center",
        )
        self.month_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 5),
            pady=(5, 0),
        )
        self.day_entry = RoundedEntry(
            date_frame,
            textvariable=self.day_value,
            background=SURFACE,
            width=64,
            height=38,
            font=app_font(10),
            justify="center",
        )
        self.day_entry.grid(
            row=1,
            column=2,
            sticky="ew",
            pady=(5, 0),
        )
        calendar_notice = CalendarAdoptionNotice(
            body,
            background=SURFACE,
            wraplength=620,
        )
        calendar_notice.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 8),
        )

        description_label = tk.Label(
            body,
            text="Description",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        description_label.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 5),
        )
        self.description_control = RoundedText(
            body,
            background=SURFACE,
            height=8,
        )
        self.description_control.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="nsew",
        )

        if self.event:
            self.description_control.text.insert(
                "1.0",
                self.event["description"],
            )

        people_frame = tk.Frame(body, bg=SURFACE)
        people_frame.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(14, 0),
        )
        people_frame.grid_columnconfigure(0, weight=1)
        people_label = tk.Label(
            people_frame,
            text="People linked to this event",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        people_label.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(0, 5),
        )
        self.people_list = tk.Listbox(
            people_frame,
            height=3,
            bg=SURFACE,
            fg=TEXT_DARK,
            relief="solid",
            borderwidth=1,
            font=app_font(9),
            activestyle="none",
            exportselection=False,
        )
        self.people_list.grid(
            row=1,
            column=0,
            sticky="ew",
        )
        add_person_button = SoftButton(
            people_frame,
            text="Add person",
            command=self.open_person_picker,
            background=SURFACE,
            width=104,
            height=32,
            font=app_font(9, "bold"),
        )
        add_person_button.grid(
            row=1,
            column=1,
            padx=(8, 0),
        )
        remove_person_button = SoftButton(
            people_frame,
            text="Remove",
            command=self.remove_selected_person,
            background=SURFACE,
            width=82,
            height=32,
            font=app_font(9, "bold"),
        )
        remove_person_button.grid(
            row=1,
            column=2,
            padx=(6, 0),
        )
        self.refresh_people_list()
        self.eminence_picker = EventEminencePicker(
            body,
            self.event_controller,
            SURFACE,
        )
        self.eminence_picker.grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )
        self.eminence_picker.set_values(
            self.selected_person_ids,
            self.selected_eminence_person_ids,
            self.selected_eminence_skills,
            (
                self.event.get("record_id", "")
                if self.event
                else "new-organization-event"
            ),
        )

        footer = tk.Frame(self, bg=APP_BACKGROUND)
        footer.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 16),
        )
        footer.grid_columnconfigure(0, weight=1)
        cancel_button = SoftButton(
            footer,
            text="Cancel",
            command=self.close_dialog,
            background=APP_BACKGROUND,
            width=92,
            height=36,
        )
        cancel_button.grid(row=0, column=1, padx=(0, 7))
        save_button = SoftButton(
            footer,
            text="Save event",
            command=self.save_event,
            background=APP_BACKGROUND,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=112,
            height=36,
        )
        save_button.grid(row=0, column=2)

    def focus_first_field(self):
        if self.is_founding:
            self.year_entry.entry.focus_set()
            self.year_entry.entry.selection_range(0, "end")
            return

        self.title_entry.entry.focus_set()
        self.title_entry.entry.selection_range(0, "end")

    def close_dialog(self, event=None):
        self.destroy()

    def people_options(self):
        if self.event_controller is None:
            return []

        return self.event_controller.people_options()

    def refresh_people_list(self):
        if not hasattr(self, "people_list"):
            return

        labels_by_id = {
            option["value"]: option["label"]
            for option in self.people_options()
        }
        self.people_list.delete(0, "end")

        for person_id in self.selected_person_ids:
            self.people_list.insert(
                "end",
                labels_by_id.get(
                    person_id,
                    "Unknown person",
                ),
            )

    def open_person_picker(self):
        if self.event_controller is None:
            return

        EventPersonPickerDialog(
            self,
            self.event_controller.people_options(),
            self.event_controller.recent_people_options(),
            "",
            self.add_selected_person,
            create_person_command=getattr(
                self.event_controller,
                "create_event_person",
                None,
            ),
            mage_groups=(
                self.event_controller.mage_groups()
                if hasattr(self.event_controller, "mage_groups")
                else []
            ),
        )

    def add_selected_person(self, person_id):
        normalized_person_id = str(person_id or "").strip()

        if (
            normalized_person_id
            and normalized_person_id not in self.selected_person_ids
        ):
            self.selected_person_ids.append(
                normalized_person_id
            )

        self.refresh_people_list()

        if hasattr(self, "eminence_picker"):
            self.eminence_picker.update_people(
                self.selected_person_ids
            )

    def remove_selected_person(self):
        selected = self.people_list.curselection()

        if not selected:
            return

        self.selected_person_ids = [
            person_id
            for index, person_id in enumerate(
                self.selected_person_ids
            )
            if index != int(selected[0])
        ]
        self.refresh_people_list()
        self.eminence_picker.update_people(
            self.selected_person_ids
        )

    def save_event(self):
        year_text = self.year_value.get().strip()
        month_text = self.month_value.get().strip()
        day_text = self.day_value.get().strip()

        if not year_text:
            messagebox.showerror(
                "Year required",
                "Every organization event requires a year.",
                parent=self,
            )
            return

        try:
            year = int(year_text)
        except ValueError:
            messagebox.showerror(
                "Invalid year",
                "The event year must be a whole number.",
                parent=self,
            )
            return

        if day_text and not month_text:
            messagebox.showerror(
                "Invalid date",
                "The event day requires a month.",
                parent=self,
            )
            return

        description = self.description_control.text.get(
            "1.0",
            "end-1c",
        )

        try:
            if self.is_founding:
                record = normalize_organization_event(
                    {
                        **self.event,
                        "date": "",
                        "year": year,
                        "month": month_text,
                        "day": day_text,
                        "description": description,
                        "person_ids": self.selected_person_ids,
                        "eminence_person_ids": (
                            self.eminence_picker.get_values()
                        ),
                        "eminence_skills": (
                            self.eminence_picker.get_skill_values()
                        ),
                    }
                )
            else:
                record = new_organization_event(
                    self.title_value.get(),
                    year,
                    description,
                    self.selected_person_ids,
                    self.eminence_picker.get_values(),
                    self.eminence_picker.get_skill_values(),
                    month=month_text,
                    day=day_text,
                )

                if self.event is not None:
                    record["record_id"] = self.event["record_id"]
        except (TypeError, ValueError) as error:
            messagebox.showerror(
                "Cannot save event",
                str(error),
                parent=self,
            )
            return

        self.save_command(record)
        self.destroy()
