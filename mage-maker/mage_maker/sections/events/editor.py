import tkinter as tk
from copy import deepcopy

from mage_maker.core.wizarding_currency import (
    currency_component_input_is_valid,
)
from mage_maker.sections.events.types import (
    EVENT_TYPE_LABELS,
    event_type_from_label,
    event_type_label,
    event_type_options,
)
from mage_maker.sections.events.dialog import (
    EventLocationPickerDialog,
    EventPersonPickerDialog,
)
from mage_maker.sections.events.eminence_picker import (
    EventEminencePicker,
)
from mage_maker.sections.development.organization_dialogs import (
    OrganizationSelectionDialog,
)
from mage_maker.ui.theme import (
    BORDER_SOFT,
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
from mage_maker.ui.widgets import (
    CalendarAdoptionNotice,
    LabeledEntry,
    RoundedEntry,
    RoundedSelect,
    RoundedText,
    SoftButton,
)


NEW_EVENT_DRAFT_ID = "__new-event-draft__"


def split_editor_date(value):
    date_text = str(value or "").strip()

    if not date_text:
        return "", "", ""

    negative = date_text.startswith("-")
    date_body = date_text[1:] if negative else date_text
    parts = date_body.split("-")
    year = parts[0] if parts else ""

    if negative and year:
        year = f"-{year}"

    month = parts[1] if len(parts) > 1 else ""
    day = parts[2] if len(parts) > 2 else ""
    return year, month, day


class EventAssociationPicker(tk.Frame):
    def __init__(
        self,
        parent,
        controller,
        association_kind,
        background=SURFACE_MUTED,
    ):
        super().__init__(
            parent,
            bg=background,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=4,
            pady=3,
        )
        self.controller = controller
        self.association_kind = str(association_kind or "")
        self.background = background
        self.options = []
        self.visible_options = []
        self.selected_ids = []
        self.locked_ids = set()
        self.locked_order = []
        self.is_enabled = True
        self.single_selection = False
        self.foundation_only = False
        self.include_recent = True
        self.change_command = None
        self.instruction_text = ""
        self.result_heading_value = tk.StringVar(value="Recently viewed")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_controls()

    def build_controls(self):
        heading_row = tk.Frame(self, bg=self.background)
        heading_row.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        heading_row.grid_columnconfigure(0, weight=1)
        heading_labels = {
            "people": "People",
            "locations": "Locations",
            "organizations": "Organizations",
        }
        heading = tk.Label(
            heading_row,
            text=heading_labels.get(
                self.association_kind,
                "Records",
            ),
            bg=self.background,
            fg=TEXT_DARK,
            font=app_font(9, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")
        recent_heading = tk.Label(
            heading_row,
            textvariable=self.result_heading_value,
            bg=self.background,
            fg=TEXT_MUTED,
            font=app_font(8, "bold"),
            anchor="w",
        )
        recent_heading.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(8, 0),
        )
        list_frame = tk.Frame(
            self,
            bg=FIELD_BACKGROUND,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
        )
        list_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
        )
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        self.listbox = tk.Listbox(
            list_frame,
            height=5,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            selectbackground=LIST_SELECTED,
            selectforeground=TEXT_DARK,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=app_font(8),
            activestyle="none",
            exportselection=False,
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.bind(
            "<<ListboxSelect>>",
            self.selection_changed,
        )
        self.listbox.bind("<ButtonRelease-1>", self.toggle_selected)
        self.listbox.bind("<space>", self.toggle_selected)
        self.listbox.bind("<Return>", self.toggle_selected)
        scrollbar = tk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)
        select_button_labels = {
            "people": "Select another person",
            "locations": "Select another location",
            "organizations": "Select an organization",
        }
        self.select_button = SoftButton(
            self,
            text=select_button_labels.get(
                self.association_kind,
                "Select a record",
            ),
            command=self.open_selector,
            background=self.background,
            fill=FIELD_BACKGROUND,
            hover_fill=LIST_SELECTED,
            foreground=TEXT_DARK,
            height=24,
            font=app_font(8, "bold"),
        )
        self.select_button.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(2, 0),
        )

    def set_values(self, selected_ids=(), locked_ids=()):
        self.selected_ids = []

        for association_id in selected_ids:
            normalized_id = str(association_id or "").strip()

            if normalized_id and normalized_id not in self.selected_ids:
                self.selected_ids.append(normalized_id)

        self.locked_order = []

        for association_id in locked_ids:
            locked_id = str(association_id or "").strip()

            if locked_id and locked_id not in self.locked_order:
                self.locked_order.append(locked_id)

        self.locked_ids = set(self.locked_order)

        for locked_id in self.locked_order:
            if locked_id not in self.selected_ids:
                self.selected_ids.append(locked_id)

        if self.single_selection and len(self.selected_ids) > 1:
            if self.locked_order:
                self.selected_ids = self.locked_order[:1]
            else:
                self.selected_ids = self.selected_ids[-1:]

        self.refresh_options()

    def set_instruction(self, instruction=""):
        self.instruction_text = str(instruction or "").strip()
        self.refresh_results()

    def get_values(self):
        return list(self.selected_ids)

    def refresh_options(self):
        if self.association_kind == "people":
            self.options = self.controller.people_options()
        elif self.association_kind == "organizations":
            self.options = self.controller.organization_options()
        else:
            if getattr(self, "foundation_only", False):
                self.options = self.controller.location_options(
                    available_for_founding=True,
                    include_ids=self.selected_ids,
                )
            else:
                self.options = self.controller.location_options()

        self.refresh_results()

    def recent_options(self, limit=12):
        if self.association_kind == "people":
            return self.controller.recent_people_options(limit=limit)

        if self.association_kind == "organizations":
            return []

        return self.controller.recent_location_options(limit=limit)

    def refresh_results(self, *arguments):
        options_by_id = {
            str(option.get("value", "") or ""): option
            for option in self.options
            if str(option.get("value", "") or "").strip()
        }
        visible_ids = []

        for association_id in self.locked_order:
            if association_id in options_by_id:
                visible_ids.append(association_id)

        for association_id in self.selected_ids:
            if (
                association_id in options_by_id
                and association_id not in visible_ids
            ):
                visible_ids.append(association_id)

        if self.include_recent:
            recent_count = 0

            for option in self.recent_options():
                association_id = str(
                    option.get("value", "") or ""
                ).strip()

                if not association_id or association_id in self.locked_ids:
                    continue

                if association_id not in visible_ids:
                    visible_ids.append(association_id)

                recent_count += 1

                if recent_count >= 5:
                    break

        self.visible_options = [
            deepcopy(options_by_id[association_id])
            for association_id in visible_ids
            if association_id in options_by_id
        ]

        instruction_text = str(
            getattr(self, "instruction_text", "") or ""
        ).strip()

        if instruction_text:
            self.result_heading_value.set(instruction_text)
        elif (
            self.association_kind == "people"
            and self.locked_ids
            and not self.include_recent
        ):
            self.result_heading_value.set("Current person")
        elif self.association_kind == "people" and self.locked_ids:
            self.result_heading_value.set(
                "Current person and recently viewed"
            )
        elif self.selected_ids:
            self.result_heading_value.set(
                "Selected and recently viewed"
            )
        else:
            self.result_heading_value.set(
                "Recently viewed"
                if self.visible_options
                else "No recently viewed records"
            )

        self.render_results()

    def render_results(self):
        selected_row_id = self.selected_row_id()
        self.listbox.delete(0, "end")

        for index, option in enumerate(self.visible_options):
            association_id = str(option.get("value", "") or "")
            label = str(option.get("label", "") or "Unnamed")

            if association_id in self.locked_ids:
                display_label = (
                    f"✓ {label}  ·  current person"
                    if self.association_kind == "people"
                    else f"✓ {label}  ·  fixed"
                )
            elif association_id in self.selected_ids:
                display_label = f"✓ {label}"
            else:
                display_label = label

            self.listbox.insert("end", display_label)
            self.listbox.itemconfigure(
                index,
                background=(
                    FIELD_BACKGROUND
                    if index % 2 == 0
                    else LIST_ALTERNATE
                ),
            )

            if association_id == selected_row_id:
                self.listbox.selection_set(index)

        self.selection_changed()

    def selected_row_id(self):
        selected = self.listbox.curselection()

        if not selected or selected[0] >= len(self.visible_options):
            return ""

        return str(
            self.visible_options[selected[0]].get("value", "") or ""
        ).strip()

    def selection_changed(self, event=None):
        return self.selected_row_id()

    def toggle_selected(self, event=None):
        if not self.is_enabled:
            return "break"

        association_id = self.selected_row_id()

        if not association_id or association_id in self.locked_ids:
            return "break"

        if association_id in self.selected_ids:
            self.selected_ids = [
                selected_id
                for selected_id in self.selected_ids
                if selected_id != association_id
            ]
        elif self.single_selection:
            self.selected_ids = [
                locked_id
                for locked_id in self.locked_order
            ]
            self.selected_ids.append(association_id)
        else:
            self.selected_ids.append(association_id)

        self.refresh_results()

        if self.change_command is not None:
            self.change_command()

        return "break"

    def open_selector(self):
        if not self.is_enabled:
            return False

        selected_id = next(
            (
                association_id
                for association_id in reversed(self.selected_ids)
                if association_id not in self.locked_ids
            ),
            "",
        )

        if self.association_kind == "people":
            recent_options = [
                option
                for option in self.recent_options(limit=12)
                if str(option.get("value", "") or "").strip()
                not in self.locked_ids
            ][:5]
            EventPersonPickerDialog(
                self,
                self.options,
                recent_options,
                selected_id,
                self.selector_chosen,
                create_person_command=getattr(
                    self.controller,
                    "create_event_person",
                    None,
                ),
                mage_groups=(
                    self.controller.mage_groups()
                    if hasattr(self.controller, "mage_groups")
                    else []
                ),
            )
        elif self.association_kind == "locations":
            location_records = (
                self.controller.location_records(
                    available_for_founding=True,
                    include_ids=self.selected_ids,
                )
                if getattr(self, "foundation_only", False)
                else self.controller.location_records()
            )
            EventLocationPickerDialog(
                self,
                location_records,
                selected_id,
                self.selector_chosen,
                create_location_command=getattr(
                    self.controller,
                    "create_placeholder_location",
                    None,
                ),
            )
        else:
            OrganizationSelectionDialog(
                self,
                self.controller.organization_records(),
                self.organization_selector_chosen,
            )

        return True

    def selector_chosen(self, association_id):
        normalized_id = str(association_id or "").strip()

        if not normalized_id:
            return False

        if self.association_kind == "people":
            self.options = self.controller.people_options()
        elif self.association_kind == "organizations":
            self.options = self.controller.organization_options()
        else:
            if getattr(self, "foundation_only", False):
                self.options = self.controller.location_options(
                    available_for_founding=True,
                    include_ids=(*self.selected_ids, normalized_id),
                )
            else:
                self.options = self.controller.location_options()

        if self.single_selection:
            self.selected_ids = [
                locked_id
                for locked_id in self.locked_order
            ]

        if normalized_id not in self.selected_ids:
            self.selected_ids.append(normalized_id)

        self.refresh_results()

        for index, option in enumerate(self.visible_options):
            if str(option.get("value", "") or "") != normalized_id:
                continue

            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(index)
            self.listbox.see(index)
            break

        self.selection_changed()

        if self.change_command is not None:
            self.change_command()

        return True

    def organization_selector_chosen(self, organization):
        if not isinstance(organization, dict):
            return False

        return self.selector_chosen(
            organization.get("record_id", "")
        )

    def set_enabled(self, enabled):
        self.is_enabled = bool(enabled)
        self.listbox.configure(state="normal")
        self.select_button.set_enabled(self.is_enabled)


class EventEditor(tk.Frame):
    def __init__(
        self,
        parent,
        controller,
        save_command,
        cancel_command=None,
        context="period",
        background=SURFACE_MUTED,
    ):
        super().__init__(
            parent,
            bg=background,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
        )
        self.controller = controller
        self.save_command = save_command
        self.cancel_command = cancel_command
        self.context = str(context or "period")
        self.compact_no_scroll = self.context == "location"
        self.background = background
        self.event = {}
        self.storage_kind = "shared"
        self.editor_mode = "empty"
        self.controls_enabled = False
        self.read_only = True
        self.lock_type = False
        self.lock_title = False
        self.lock_date = False
        self.lock_people = False
        self.description_only = False
        self.title_and_description_only = False
        self.title_from_location = False
        self.hide_locations = False
        self.feedback_after_id = None
        self.minimum_year = None
        self.maximum_year = None
        self.founding_title_locked = False
        self.generated_founding_title = ""
        self.generated_extinction_title = ""
        self.generated_job_event_title = ""
        self.saved_editor_values = None
        self.saving = False
        self.job_event_options = []
        self.job_event_options_by_label = {}
        self.heading_value = tk.StringVar(value="Event details")
        self.explanation_value = tk.StringVar(
            value="Select an event or add a new one."
        )
        self.title_value = tk.StringVar()
        self.event_type_value = tk.StringVar()
        self.year_value = tk.StringVar()
        self.month_value = tk.StringVar()
        self.day_value = tk.StringVar()
        self.period_value = tk.StringVar(value="Period: determined by year")
        self.feedback_value = tk.StringVar()
        self.job_event_value = tk.StringVar()
        self.salary_galleons_value = tk.StringVar(value="0")
        self.salary_sickles_value = tk.StringVar(value="0")
        self.salary_knuts_value = tk.StringVar(value="0")
        self.adjusting_year = False
        self.year_value.trace_add("write", self.update_period_display)
        self.month_value.trace_add("write", self.update_period_display)
        self.day_value.trace_add("write", self.update_period_display)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.scrollbar_visible = True
        self.build_scrollable_form()

        if self.context == "location":
            self.people_picker.listbox.configure(height=6)
            self.locations_picker.listbox.configure(height=3)
            self.scrollbar.grid_remove()
            self.scrollbar_visible = False

        self.event_type_value.trace_add(
            "write",
            self.event_type_changed,
        )
        self.job_event_value.trace_add(
            "write",
            self.job_event_selection_changed,
        )
        self.clear()

    def build_scrollable_form(self):
        self.canvas = tk.Canvas(
            self,
            bg=self.background,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = tk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.form = tk.Frame(
            self.canvas,
            bg=self.background,
            padx=8,
            pady=4,
        )
        self.form_window = self.canvas.create_window(
            0,
            0,
            window=self.form,
            anchor="nw",
        )
        self.form.grid_columnconfigure(0, weight=1)
        self.form.bind("<Configure>", self.form_resized)
        self.canvas.bind("<Configure>", self.canvas_resized)
        self.canvas.bind("<MouseWheel>", self.mousewheel)
        self.form.bind("<MouseWheel>", self.mousewheel)
        self.build_form()

    def build_form(self):
        form_columnspan = 2 if self.compact_no_scroll else 1

        if self.compact_no_scroll:
            self.form.grid_columnconfigure(
                (0, 1),
                weight=1,
                uniform="location_event_compact",
            )

        header = tk.Frame(self.form, bg=self.background)
        header.grid(
            row=0,
            column=0,
            columnspan=form_columnspan,
            sticky="ew",
            pady=(0, 2),
        )
        header.grid_columnconfigure(1, weight=1)
        heading = tk.Label(
            header,
            textvariable=self.heading_value,
            bg=self.background,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="w", padx=(0, 12))
        explanation = tk.Label(
            header,
            textvariable=self.explanation_value,
            bg=self.background,
            fg=TEXT_MUTED,
            font=app_font(8),
            anchor="e",
            justify="right",
            wraplength=500,
        )
        explanation.grid(row=0, column=1, sticky="ew")
        main_fields = tk.Frame(self.form, bg=self.background)
        main_fields.grid(
            row=1,
            column=0,
            columnspan=form_columnspan,
            sticky="ew",
        )
        main_fields.grid_columnconfigure(0, weight=2)
        main_fields.grid_columnconfigure(1, weight=3)
        type_panel = tk.Frame(main_fields, bg=self.background)
        type_panel.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        type_panel.grid_columnconfigure(0, weight=1)
        type_label = tk.Label(
            type_panel,
            text="Event type",
            bg=self.background,
            fg=TEXT_MUTED,
            font=app_font(8, "bold"),
            anchor="w",
        )
        type_label.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self.type_picker = RoundedSelect(
            type_panel,
            textvariable=self.event_type_value,
            values=[],
            background=self.background,
            height=28,
            font=app_font(9),
        )
        self.type_picker.grid(row=1, column=0, sticky="ew")
        self.title_field = LabeledEntry(
            main_fields,
            "Event title",
            self.title_value,
            background=self.background,
            control_height=28,
        )
        self.title_field.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(5, 0),
        )
        date_panel = tk.Frame(self.form, bg=self.background)
        date_panel.grid(
            row=2,
            column=0,
            columnspan=form_columnspan,
            sticky="ew",
            pady=(2, 0),
        )
        date_panel.grid_columnconfigure((0, 1, 2), weight=1)
        self.year_field = LabeledEntry(
            date_panel,
            "Year",
            self.year_value,
            background=self.background,
            control_height=28,
        )
        self.year_field.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.year_field.control.bind_input(
            "<FocusOut>",
            self.clamp_year_to_editor_bounds,
        )
        self.month_field = LabeledEntry(
            date_panel,
            "Month",
            self.month_value,
            background=self.background,
            control_height=28,
        )
        self.month_field.grid(row=0, column=1, sticky="ew", padx=4)
        self.day_field = LabeledEntry(
            date_panel,
            "Day",
            self.day_value,
            background=self.background,
            control_height=28,
        )
        self.day_field.grid(row=0, column=2, sticky="ew", padx=(4, 0))
        calendar_notice = CalendarAdoptionNotice(
            date_panel,
            background=self.background,
            wraplength=560,
            date_variables=(
                self.year_value,
                self.month_value,
                self.day_value,
            ),
        )
        calendar_notice.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(3, 0),
        )
        self.job_event_panel = tk.Frame(
            self.form,
            bg=self.background,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=6,
            pady=5,
        )
        self.job_event_panel.grid(
            row=3,
            column=0,
            columnspan=form_columnspan,
            sticky="ew",
            pady=(3, 0),
        )
        self.job_event_panel.grid_columnconfigure(0, weight=2)
        self.job_event_panel.grid_columnconfigure(
            (1, 2, 3),
            weight=1,
        )
        job_label = tk.Label(
            self.job_event_panel,
            text="Organization job",
            bg=self.background,
            fg=TEXT_DARK,
            font=app_font(8, "bold"),
            anchor="w",
        )
        job_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 4),
        )
        self.job_event_picker = RoundedSelect(
            self.job_event_panel,
            textvariable=self.job_event_value,
            values=[],
            background=self.background,
            height=28,
            font=app_font(8),
        )
        self.job_event_picker.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(0, 4),
        )
        self.job_salary_label = tk.Label(
            self.job_event_panel,
            text="Starting monthly salary",
            bg=self.background,
            fg=TEXT_DARK,
            font=app_font(8, "bold"),
            anchor="w",
        )
        self.job_salary_label.grid(
            row=0,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=(4, 0),
        )
        self.job_salary_entries = []

        for column, label_text, value, maximum in (
            (1, "Galleons", self.salary_galleons_value, ""),
            (2, "Sickles", self.salary_sickles_value, "16"),
            (3, "Knuts", self.salary_knuts_value, "28"),
        ):
            salary_block = tk.Frame(
                self.job_event_panel,
                bg=self.background,
            )
            salary_block.grid(
                row=1,
                column=column,
                sticky="ew",
                padx=(4, 0),
            )
            salary_block.grid_columnconfigure(0, weight=1)
            salary_label = tk.Label(
                salary_block,
                text=label_text,
                bg=self.background,
                fg=TEXT_MUTED,
                font=app_font(7, "bold"),
                anchor="w",
            )
            salary_label.grid(row=0, column=0, sticky="ew")
            salary_entry = RoundedEntry(
                salary_block,
                textvariable=value,
                background=self.background,
                width=92,
                height=28,
                font=app_font(8),
                justify="center",
            )
            salary_entry.grid(
                row=1,
                column=0,
                sticky="ew",
                pady=(2, 0),
            )
            salary_entry.entry.configure(
                validate="key",
                validatecommand=(
                    self.register(currency_component_input_is_valid),
                    "%P",
                    maximum,
                ),
            )
            self.job_salary_entries.append(salary_entry)

        self.job_event_panel.grid_remove()
        description_heading = tk.Frame(
            self.form,
            bg=self.background,
        )
        description_heading.grid(
            row=4,
            column=0,
            columnspan=form_columnspan,
            sticky="ew",
            pady=(2, 1),
        )
        description_heading.grid_columnconfigure(0, weight=1)
        description_label = tk.Label(
            description_heading,
            text="Description",
            bg=self.background,
            fg=TEXT_DARK,
            font=app_font(9, "bold"),
            anchor="w",
        )
        description_label.grid(row=0, column=0, sticky="w")
        period_label = tk.Label(
            description_heading,
            textvariable=self.period_value,
            bg=self.background,
            fg=TEXT_MUTED,
            font=app_font(8, "bold"),
            anchor="e",
        )
        period_label.grid(row=0, column=1, sticky="e", padx=(12, 0))
        self.description_control = RoundedText(
            self.form,
            background=self.background,
            height=4 if self.compact_no_scroll else 1,
            minimum_height=96 if self.compact_no_scroll else 43,
            font=app_font(9),
        )
        self.description_control.grid(
            row=5,
            column=0,
            sticky="nsew" if self.compact_no_scroll else "ew",
            padx=(0, 4) if self.compact_no_scroll else 0,
        )
        self.association_panel = tk.Frame(
            self.form,
            bg=self.background,
        )
        if self.compact_no_scroll:
            self.association_panel.grid(
                row=5,
                column=1,
                sticky="nsew",
                padx=(4, 0),
            )
        else:
            self.association_panel.grid(
                row=6,
                column=0,
                sticky="ew",
                pady=(2, 0),
            )
        self.association_panel.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="event_associations",
        )
        self.people_picker = EventAssociationPicker(
            self.association_panel,
            self.controller,
            "people",
            background=self.background,
        )
        self.people_picker.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 4),
        )
        self.people_picker.change_command = (
            self.people_selection_changed
        )
        self.locations_picker = EventAssociationPicker(
            self.association_panel,
            self.controller,
            "locations",
            background=self.background,
        )
        self.locations_picker.change_command = (
            self.location_selection_changed
        )
        self.locations_picker.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(4, 0),
        )
        self.organizations_picker = EventAssociationPicker(
            self.association_panel,
            self.controller,
            "organizations",
            background=self.background,
        )
        self.organizations_picker.single_selection = True
        self.organizations_picker.include_recent = False
        self.organizations_picker.change_command = (
            self.organization_selection_changed
        )
        self.organizations_picker.grid_remove()
        self.eminence_picker = EventEminencePicker(
            self.form,
            self.controller,
            self.background,
        )
        self.eminence_picker.grid(
            row=7,
            column=0,
            columnspan=form_columnspan,
            sticky="ew",
            pady=(3, 0),
        )
        footer = tk.Frame(self.form, bg=self.background)
        footer.grid(
            row=8,
            column=0,
            columnspan=form_columnspan,
            sticky="ew",
            pady=(2, 0),
        )
        footer.grid_columnconfigure(0, weight=1)
        feedback = tk.Label(
            footer,
            textvariable=self.feedback_value,
            bg=self.background,
            fg=TEXT_DARK,
            font=app_font(8, "bold"),
            anchor="w",
            justify="left",
            wraplength=230,
        )
        feedback.grid(row=0, column=0, sticky="ew")
        self.cancel_button = SoftButton(
            footer,
            text="Cancel",
            command=self.cancel,
            background=self.background,
            width=76,
            height=26,
            font=app_font(8, "bold"),
        )
        self.cancel_button.grid(row=0, column=1, padx=(5, 0))
        self.save_button = SoftButton(
            footer,
            text="Save event",
            command=self.save,
            background=self.background,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=98,
            height=26,
            font=app_font(8, "bold"),
        )
        self.save_button.grid(row=0, column=2, padx=(5, 0))

    def form_resized(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.after_idle(self.update_scrollbar_visibility)

    def canvas_resized(self, event):
        self.canvas.itemconfigure(
            self.form_window,
            width=max(1, event.width),
        )
        self.after_idle(self.update_scrollbar_visibility)

    def update_scrollbar_visibility(self):
        if self.compact_no_scroll:
            if self.scrollbar_visible:
                self.scrollbar.grid_remove()
                self.scrollbar_visible = False

            self.canvas.yview_moveto(0)
            return

        bounds = self.canvas.bbox("all")
        content_height = (
            max(0, bounds[3] - bounds[1])
            if bounds
            else 0
        )
        available_height = max(1, self.canvas.winfo_height())
        needs_scrollbar = content_height > available_height + 2

        if needs_scrollbar and not self.scrollbar_visible:
            self.scrollbar.grid(row=0, column=1, sticky="ns")
            self.scrollbar_visible = True
        elif not needs_scrollbar and self.scrollbar_visible:
            self.scrollbar.grid_remove()
            self.scrollbar_visible = False
            self.canvas.yview_moveto(0)

    def mousewheel(self, event):
        if not self.scrollbar_visible:
            return None

        if event.delta:
            self.canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units",
            )

        return "break"

    def clear(self, message="Select an event or add a new one."):
        self.event = {}
        self.storage_kind = "shared"
        self.editor_mode = "empty"
        self.read_only = True
        self.lock_type = False
        self.lock_title = False
        self.lock_date = False
        self.lock_people = False
        self.description_only = False
        self.title_and_description_only = False
        self.title_from_location = False
        self.founding_title_locked = False
        self.generated_founding_title = ""
        self.generated_extinction_title = ""
        self.people_picker.include_recent = True
        self.locations_picker.single_selection = False
        self.locations_picker.foundation_only = False
        if hasattr(self.locations_picker, "set_instruction"):
            self.locations_picker.set_instruction("")
        self.set_year_bounds()
        self.heading_value.set("Event details")
        self.explanation_value.set(message)
        self.title_value.set("")
        self.event_type_value.set("")
        self.year_value.set("")
        self.month_value.set("")
        self.day_value.set("")
        if hasattr(self, "job_event_value"):
            self.job_event_value.set("")
            self.salary_galleons_value.set("0")
            self.salary_sickles_value.set("0")
            self.salary_knuts_value.set("0")
            self.job_event_panel.grid_remove()
        self.description_control.text.configure(state="normal")
        self.description_control.text.delete("1.0", "end")
        self.people_picker.set_values(())

        if hasattr(self, "eminence_picker"):
            self.eminence_picker.set_values((), (), {}, "")

        self.locations_picker.set_values(())
        if hasattr(self, "organizations_picker"):
            self.organizations_picker.set_values(())
        self.show_locations(True)
        self.set_controls_enabled(False)
        self.clear_feedback()
        self.canvas.yview_moveto(0)
        self.saved_editor_values = None
        self.saving = False

    def start_new(
        self,
        context=None,
        default_person_ids=(),
        locked_person_ids=(),
        default_location_ids=(),
        locked_location_ids=(),
        hide_locations=False,
        minimum_year=None,
        maximum_year=None,
    ):
        self.event = {}
        self.storage_kind = "shared"
        self.editor_mode = "new"
        self.context = str(context or self.context or "period")
        self.read_only = False
        self.lock_type = False
        self.lock_title = False
        self.lock_date = False
        self.lock_people = False
        self.description_only = False
        self.title_and_description_only = False
        self.title_from_location = False
        self.founding_title_locked = False
        self.generated_founding_title = ""
        self.generated_extinction_title = ""
        self.generated_job_event_title = ""
        self.people_picker.include_recent = True
        self.locations_picker.single_selection = False
        self.locations_picker.foundation_only = False
        if hasattr(self.locations_picker, "set_instruction"):
            self.locations_picker.set_instruction("")
        self.set_year_bounds(minimum_year, maximum_year)
        self.heading_value.set("New event")
        self.explanation_value.set(
            "Choose the event type, enter its date, and link the records it belongs to."
        )
        self.title_value.set("")
        self.year_value.set("")
        self.month_value.set("")
        self.day_value.set("")
        if hasattr(self, "job_event_value"):
            self.job_event_value.set("")
            self.salary_galleons_value.set("0")
            self.salary_sickles_value.set("0")
            self.salary_knuts_value.set("0")
        self.description_control.text.configure(state="normal")
        self.description_control.text.delete("1.0", "end")
        self.configure_type_options()
        self.event_type_value.set(self.default_type_label())
        self.people_picker.set_values(
            default_person_ids,
            locked_person_ids,
        )
        if hasattr(self, "eminence_picker"):
            self.eminence_picker.set_values(
                self.people_picker.get_values(),
                (),
                {},
                NEW_EVENT_DRAFT_ID,
            )
        self.locations_picker.set_values(
            default_location_ids,
            locked_location_ids,
        )
        if hasattr(self, "organizations_picker"):
            self.organizations_picker.set_values(())
        self.show_locations(not hide_locations)
        self.set_controls_enabled(True)
        self.clear_feedback()
        self.update_period_display()
        self.canvas.yview_moveto(0)
        self.saved_editor_values = None

    def is_new_event(self):
        return self.editor_mode == "new" and not self.read_only

    def ensure_new_event_editable(self):
        if not self.is_new_event():
            return False

        self.set_controls_enabled(True)

        if self.description_only:
            self.description_control.text.focus_set()
        else:
            self.title_field.control.focus_set()

        return True

    def begin_edit(self):
        if (
            not self.event
            or self.read_only
            or self.editor_mode not in ("view", "edit")
        ):
            return False

        self.editor_mode = "edit"
        self.heading_value.set("Edit event")
        self.explanation_value.set(
            "Changes saved here update this event everywhere it appears."
        )
        self.set_controls_enabled(True)
        self.type_picker.set_enabled(
            not self.description_only and not self.lock_type
        )

        if self.description_only:
            self.description_control.text.focus_set()
        else:
            self.title_field.control.focus_set()

        return True

    def ensure_loaded_event_editable(self):
        if not self.event or self.read_only:
            return False

        return self.begin_edit()

    def load_event(
        self,
        event,
        storage_kind="shared",
        context=None,
        person_ids=(),
        locked_person_ids=(),
        location_ids=(),
        locked_location_ids=(),
        hide_locations=False,
        read_only=False,
        explanation="",
        minimum_year=None,
        maximum_year=None,
        lock_title=False,
        lock_date=False,
        lock_people=False,
        single_location=False,
        title_from_location=False,
        display_title=None,
        description_only=False,
        title_and_description_only=False,
    ):
        self.event = deepcopy(event) if isinstance(event, dict) else {}
        self.storage_kind = str(storage_kind or "shared")
        self.context = str(context or self.context or "period")
        self.read_only = bool(read_only)
        self.editor_mode = "view" if self.read_only else "edit"
        self.set_year_bounds(minimum_year, maximum_year)
        self.lock_type = bool(
            self.event.get("automatic_source")
            or self.event.get("organization_event")
        )
        self.lock_title = bool(
            lock_title or self.event.get("organization_event")
        )
        self.lock_date = bool(lock_date)
        self.lock_people = bool(lock_people)
        self.description_only = bool(description_only)
        self.title_and_description_only = bool(
            title_and_description_only
        )
        self.title_from_location = bool(title_from_location)
        self.founding_title_locked = False
        self.generated_founding_title = ""
        self.generated_extinction_title = ""
        self.people_picker.include_recent = not self.lock_people
        loaded_event_type = str(
            self.event.get("event_type", "") or ""
        ).strip()
        self.locations_picker.single_selection = bool(
            single_location
            or loaded_event_type in (
                "relocated",
                "founding",
                "extinction",
            )
        )
        self.locations_picker.foundation_only = (
            self.event.get("event_type") == "founding"
        )
        self.heading_value.set(
            "Event details" if self.read_only else "Edit event"
        )
        self.explanation_value.set(
            explanation
            or (
                "This event is generated from its source record."
                if self.read_only
                else "Changes saved here update this event everywhere it appears."
            )
        )
        self.title_value.set(
            self.loaded_title()
            if display_title is None
            else str(display_title or "")
        )
        self.configure_type_options()
        self.event_type_value.set(
            event_type_label(self.event.get("event_type"))
        )
        year, month, day = split_editor_date(
            self.event.get("date", "")
        )
        self.year_value.set(year)
        self.month_value.set(month)
        self.day_value.set(day)
        self.load_job_event_values()
        self.update_job_event_panel()
        self.description_control.text.configure(state="normal")
        self.description_control.text.delete("1.0", "end")
        self.description_control.text.insert(
            "1.0",
            self.loaded_description(),
        )
        stored_person_ids = self.event.get("person_ids", [])
        stored_location_ids = self.event.get("location_ids", [])
        stored_locked_location_ids = self.event.get(
            "locked_location_ids",
            [],
        )
        self.people_picker.set_values(
            list(stored_person_ids or ()) + list(person_ids or ()),
            locked_person_ids,
        )
        if hasattr(self, "eminence_picker"):
            self.eminence_picker.set_values(
                self.people_picker.get_values(),
                self.event.get("eminence_person_ids", []),
                self.event.get("eminence_skills", {}),
                self.event.get(
                    "record_id",
                    self.event.get("event_id", ""),
                ),
            )
        loaded_location_ids = (
            list(stored_location_ids or ()) + list(location_ids or ())
        )
        loaded_locked_location_ids = (
            list(stored_locked_location_ids or ())
            + list(locked_location_ids or ())
        )

        if loaded_event_type == "relocated" and loaded_location_ids:
            loaded_location_ids = loaded_location_ids[-1:]
            loaded_locked_location_ids = []

        self.locations_picker.set_values(
            loaded_location_ids,
            loaded_locked_location_ids,
        )
        organization_id = str(
            self.event.get("organization_id", "") or ""
        ).strip()
        if hasattr(self, "organizations_picker"):
            self.organizations_picker.set_values(
                (organization_id,) if organization_id else (),
                (
                    (organization_id,)
                    if organization_id
                    and self.event.get("organization_event")
                    else ()
                ),
            )
            self.organization_selection_changed()
        self.location_selection_changed()
        self.show_locations(not hide_locations)
        self.set_controls_enabled(not self.read_only)
        self.clear_feedback()
        self.update_period_display()
        self.canvas.yview_moveto(0)
        self.saved_editor_values = deepcopy(self.values())

    def loaded_title(self):
        if self.storage_kind == "shared":
            return str(self.event.get("title", "") or "")

        if self.storage_kind == "timeline":
            return str(self.event.get("detail", "") or "")

        return str(self.event.get("title", "") or "")

    def loaded_description(self):
        if self.storage_kind == "shared":
            return str(self.event.get("description", "") or "")

        return str(self.event.get("note", "") or "")

    def refresh_job_event_options(self):
        if not hasattr(self, "job_event_picker"):
            return

        option_provider = getattr(
            self.controller,
            "organization_job_options",
            None,
        )
        self.job_event_options = (
            list(option_provider())
            if callable(option_provider)
            else []
        )
        self.job_event_options_by_label = {
            str(option.get("label", "") or ""): option
            for option in self.job_event_options
            if str(option.get("label", "") or "").strip()
        }
        self.job_event_picker.set_values(
            list(self.job_event_options_by_label)
        )

    def selected_job_event_option(self):
        if not hasattr(self, "job_event_value"):
            return None

        return self.job_event_options_by_label.get(
            self.job_event_value.get(),
        )

    def load_job_event_values(self):
        if not hasattr(self, "job_event_value"):
            return

        self.refresh_job_event_options()
        organization_id = str(
            self.event.get("organization_id", "") or ""
        ).strip()
        organization_job_id = str(
            self.event.get("organization_job_id", "") or ""
        ).strip()
        selected_label = ""

        for option in self.job_event_options:
            if (
                str(option.get("organization_id", "") or "")
                == organization_id
                and str(
                    option.get("organization_job_id", "") or ""
                )
                == organization_job_id
            ):
                selected_label = str(
                    option.get("label", "") or ""
                )
                break

        self.job_event_value.set(selected_label)
        salary = self.event.get("salary")

        if isinstance(salary, dict):
            self.salary_galleons_value.set(
                str(salary.get("galleons", 0) or 0)
            )
            self.salary_sickles_value.set(
                str(salary.get("sickles", 0) or 0)
            )
            self.salary_knuts_value.set(
                str(salary.get("knuts", 0) or 0)
            )
        else:
            self.salary_galleons_value.set("0")
            self.salary_sickles_value.set("0")
            self.salary_knuts_value.set("0")

    def job_event_selection_changed(self, *arguments):
        option = self.selected_job_event_option()

        if option is None:
            return

        generated_title = str(
            option.get("event_title", option.get("label", ""))
            or ""
        ).strip()
        current_title = self.title_value.get().strip()

        if (
            generated_title
            and (
                not current_title
                or current_title == self.generated_job_event_title
            )
        ):
            self.title_value.set(generated_title)

        self.generated_job_event_title = generated_title

    def update_job_event_panel(self):
        if not hasattr(self, "job_event_panel"):
            return

        event_type = event_type_from_label(
            self.event_type_value.get(),
            "other",
        )
        is_job_event = event_type in (
            "started_job",
            "received_raise",
        )

        if not is_job_event:
            self.job_event_panel.grid_remove()
            self.form.after_idle(self.form_resized)
            return

        self.refresh_job_event_options()
        self.job_salary_label.configure(
            text=(
                "New monthly salary"
                if event_type == "received_raise"
                else "Starting monthly salary"
            )
        )
        self.job_event_panel.grid()
        self.job_event_picker.set_enabled(self.controls_enabled)

        for salary_entry in self.job_salary_entries:
            salary_entry.set_enabled(self.controls_enabled)

        self.form.after_idle(self.form_resized)

    def configure_type_options(self):
        options = event_type_options(
            self.context,
            include_automatic=bool(
                self.event.get("automatic_source")
            ),
            current_event_type=self.event.get("event_type"),
        )
        self.type_picker.set_values(
            [label for event_type, label in options]
        )

    def default_type_label(self):
        if self.context == "person":
            return EVENT_TYPE_LABELS["custom"]

        return EVENT_TYPE_LABELS["other"]

    def set_year_bounds(self, minimum_year=None, maximum_year=None):
        self.minimum_year = (
            int(minimum_year)
            if minimum_year not in (None, "")
            else None
        )
        self.maximum_year = (
            int(maximum_year)
            if maximum_year not in (None, "")
            else None
        )

        if self.minimum_year is None or self.maximum_year is None:
            self.year_field.label.configure(text="Year")
            return

        self.year_field.label.configure(
            text=(
                f"Year ({self.minimum_year:,} to "
                f"{self.maximum_year:,})"
            )
        )

    def show_locations(self, visible):
        self.hide_locations = not bool(visible)

        self.update_association_layout()
        self.form.after_idle(self.form_resized)

    def update_association_layout(self):
        event_type = event_type_from_label(
            self.event_type_value.get(),
            "other",
        )
        self.people_picker.grid_remove()
        self.locations_picker.grid_remove()
        if hasattr(self, "organizations_picker"):
            self.organizations_picker.grid_remove()

        self.people_picker.grid(
            row=0,
            column=0,
            columnspan=(
                1
                if event_type == "organization_founding"
                or not self.hide_locations
                else 2
            ),
            sticky="ew",
            padx=(0, 4) if not self.hide_locations else 0,
        )

        if (
            event_type == "organization_founding"
            and hasattr(self, "organizations_picker")
        ):
            self.organizations_picker.grid(
                row=0,
                column=1,
                sticky="ew",
                padx=(4, 0),
            )
            return

        if not self.hide_locations:
            self.locations_picker.grid(
                row=0,
                column=1,
                sticky="ew",
                padx=(4, 0),
            )

    def set_controls_enabled(self, enabled):
        editable = bool(enabled)
        self.controls_enabled = editable
        field_editable = (
            editable
            and not self.description_only
            and not self.title_and_description_only
        )
        title_editable = editable and not self.description_only
        self.type_picker.set_enabled(field_editable and not self.lock_type)
        self.title_field.control.set_enabled(
            title_editable
            and not self.lock_title
            and not self.founding_title_locked
        )
        self.year_field.control.set_enabled(
            field_editable and not self.lock_date
        )
        self.month_field.control.set_enabled(
            field_editable and not self.lock_date
        )
        self.day_field.control.set_enabled(
            field_editable and not self.lock_date
        )
        self.description_control.text.configure(
            state="normal" if editable else "disabled"
        )
        self.people_picker.set_enabled(
            field_editable and not self.lock_people
        )
        if hasattr(self, "eminence_picker"):
            self.eminence_picker.set_enabled(field_editable)

        self.locations_picker.set_enabled(field_editable)
        if hasattr(self, "organizations_picker"):
            self.organizations_picker.set_enabled(
                field_editable
                and not bool(self.event.get("organization_event"))
            )
        if hasattr(self, "job_event_picker"):
            self.job_event_picker.set_enabled(field_editable)

            for salary_entry in self.job_salary_entries:
                salary_entry.set_enabled(field_editable)

        self.save_button.set_enabled(editable)
        self.cancel_button.set_enabled(True)

    def people_selection_changed(self):
        if hasattr(self, "eminence_picker"):
            self.eminence_picker.update_people(
                self.people_picker.get_values()
            )

        self.form.after_idle(self.form_resized)

    def location_selection_changed(self):
        selected_type = event_type_from_label(
            self.event_type_value.get(),
            "other",
        )

        if selected_type == "founding":
            self.apply_founding_title()
            return

        if selected_type == "extinction":
            self.apply_extinction_title()
            return

        if not self.title_from_location:
            return

        selected_location_ids = self.locations_picker.get_values()

        if not selected_location_ids:
            self.title_value.set("")
            return

        selected_location_id = selected_location_ids[-1]

        for location in self.controller.location_records():
            if (
                str(location.get("record_id", "") or "").strip()
                != selected_location_id
            ):
                continue

            self.title_value.set(
                str(location.get("name", "") or "").strip()
            )
            return

    def organization_selection_changed(self):
        if (
            event_type_from_label(
                self.event_type_value.get(),
                "other",
            )
            == "organization_founding"
        ):
            self.apply_organization_founding_title()

    def event_type_changed(self, *arguments):
        self.update_job_event_panel()
        selected_type = event_type_from_label(
            self.event_type_value.get(),
            "other",
        )
        self.locations_picker.single_selection = (
            selected_type in ("relocated", "founding", "extinction")
        )
        self.locations_picker.foundation_only = (
            selected_type == "founding"
        )
        if hasattr(self.locations_picker, "set_instruction"):
            self.locations_picker.set_instruction(
                "(only pick the destination location)."
                if selected_type == "relocated"
                else ""
            )

        if (
            selected_type in ("relocated", "founding", "extinction")
            and len(self.locations_picker.get_values()) > 1
        ):
            retained_location_ids = (
                self.locations_picker.locked_order[:1]
                or self.locations_picker.get_values()[-1:]
            )
            self.locations_picker.set_values(
                retained_location_ids,
                self.locations_picker.locked_order[:1],
            )

        if hasattr(self.locations_picker, "refresh_options"):
            self.locations_picker.refresh_options()
        self.update_association_layout()

        if selected_type == "founding":
            self.apply_founding_title()
            return

        if selected_type == "organization_founding":
            self.apply_organization_founding_title()
            return

        if selected_type == "extinction":
            self.apply_extinction_title()
            return

        if (
            self.generated_founding_title
            and self.title_value.get()
            == self.generated_founding_title
        ):
            self.title_value.set("")

        self.generated_founding_title = ""
        self.founding_title_locked = False

        if (
            self.generated_extinction_title
            and self.title_value.get()
            == self.generated_extinction_title
        ):
            self.title_value.set("")

        self.generated_extinction_title = ""

        if hasattr(self, "title_field"):
            self.title_field.control.set_enabled(
                self.controls_enabled
                and not self.lock_title
            )

    def apply_founding_title(self):
        location_ids = list(self.locations_picker.locked_order)

        if not location_ids:
            location_ids = self.locations_picker.get_values()

        selected_location_id = (
            str(location_ids[0] or "").strip()
            if location_ids
            else ""
        )
        selected_location = next(
            (
                location
                for location in self.controller.location_records()
                if str(location.get("record_id", "") or "").strip()
                == selected_location_id
            ),
            None,
        )
        location_name = str(
            (selected_location or {}).get("name", "") or ""
        ).strip()
        generated_title = (
            f"Founding of {location_name}"
            if location_name
            else ""
        )
        previous_generated_title = self.generated_founding_title

        if (
            not generated_title
            and previous_generated_title
            and self.title_value.get() == previous_generated_title
        ):
            self.title_value.set("")

        self.founding_title_locked = bool(generated_title)
        self.generated_founding_title = generated_title

        if generated_title:
            self.title_value.set(generated_title)

        if hasattr(self, "title_field"):
            self.title_field.control.set_enabled(
                self.controls_enabled
                and not self.lock_title
                and not self.founding_title_locked
            )

    def apply_organization_founding_title(self):
        if not hasattr(self, "organizations_picker"):
            return

        organization_ids = (
            self.organizations_picker.get_values()
            if hasattr(self, "organizations_picker")
            else []
        )
        selected_id = organization_ids[0] if organization_ids else ""
        selected_organization = next(
            (
                organization
                for organization in self.controller.organization_records()
                if str(
                    organization.get("record_id", "") or ""
                ).strip()
                == selected_id
            ),
            None,
        )
        organization_name = str(
            (selected_organization or {}).get("name", "") or ""
        ).strip()
        generated_title = (
            f"Founding of {organization_name}"
            if organization_name
            else ""
        )
        previous_generated_title = self.generated_founding_title

        if (
            not generated_title
            and previous_generated_title
            and self.title_value.get() == previous_generated_title
        ):
            self.title_value.set("")

        self.generated_founding_title = generated_title
        self.founding_title_locked = bool(generated_title)

        if generated_title:
            self.title_value.set(generated_title)

        self.title_field.control.set_enabled(
            self.controls_enabled
            and not self.lock_title
            and not self.founding_title_locked
        )

    def apply_extinction_title(self):
        location_ids = list(self.locations_picker.locked_order)

        if not location_ids:
            location_ids = self.locations_picker.get_values()

        selected_location_id = (
            str(location_ids[0] or "").strip()
            if location_ids
            else ""
        )
        selected_location = next(
            (
                location
                for location in self.controller.location_records()
                if str(location.get("record_id", "") or "").strip()
                == selected_location_id
            ),
            None,
        )
        location_name = str(
            (selected_location or {}).get("name", "") or ""
        ).strip()
        generated_title = (
            f"Extinction of {location_name}"
            if location_name
            else ""
        )
        current_title = self.title_value.get().strip()

        if (
            generated_title
            and (
                not current_title
                or current_title == self.generated_extinction_title
                or current_title == "New event"
            )
        ):
            self.title_value.set(generated_title)

        self.generated_extinction_title = generated_title

    def update_period_display(self, *arguments):
        if getattr(self, "adjusting_year", False):
            return

        year = self.year_value.get().strip()

        if not year:
            self.period_value.set("Period: determined by year")
            return

        period_names = self.controller.period_names_for_date(year)

        if not period_names:
            try:
                numeric_year = int(year)
            except ValueError:
                numeric_year = None

            clamp_command = getattr(
                self.controller,
                "clamp_year_to_defined_periods",
                None,
            )

            if numeric_year is not None and callable(clamp_command):
                clamped_year = clamp_command(numeric_year)

                if clamped_year != numeric_year:
                    self.adjusting_year = True
                    self.year_value.set(str(clamped_year))
                    self.adjusting_year = False
                    year = str(clamped_year)
                    period_names = (
                        self.controller.period_names_for_date(year)
                    )

        self.period_value.set(
            "Period: "
            + (
                ", ".join(period_names)
                if period_names
                else "outside the defined periods"
            )
        )

    def clamp_year_to_editor_bounds(self, event=None):
        if (
            self.minimum_year is None
            or self.maximum_year is None
        ):
            return False

        try:
            event_year = int(self.year_value.get().strip())
        except ValueError:
            return False

        clamped_year = min(
            self.maximum_year,
            max(self.minimum_year, event_year),
        )

        if clamped_year == event_year:
            return False

        self.adjusting_year = True
        self.year_value.set(str(clamped_year))
        self.adjusting_year = False
        self.update_period_display()
        return True

    def date_value(self):
        year = self.year_value.get().strip()
        month = self.month_value.get().strip()
        day = self.day_value.get().strip()
        date_value = year

        if month:
            date_value += f"-{month}"

        if day:
            date_value += f"-{day}"

        return date_value

    def values(self):
        selected_locations = self.locations_picker.get_values()
        locked_locations = list(self.locations_picker.locked_order)
        event_type = event_type_from_label(
            self.event_type_value.get(),
            "other",
        )
        job_option = self.selected_job_event_option()
        organization_ids = (
            self.organizations_picker.get_values()
            if hasattr(self, "organizations_picker")
            else []
        )
        selected_organization_id = (
            organization_ids[0] if organization_ids else ""
        )
        organization_records_command = getattr(
            self.controller,
            "organization_records",
            None,
        )
        organization_records = (
            organization_records_command()
            if selected_organization_id
            and callable(organization_records_command)
            else []
        )
        selected_organization = next(
            (
                organization
                for organization in organization_records
                if str(
                    organization.get("record_id", "") or ""
                ).strip()
                == selected_organization_id
            ),
            None,
        )
        return {
            "event_type": event_type,
            "title": self.title_value.get(),
            "date": self.date_value(),
            "description": self.description_control.text.get(
                "1.0",
                "end-1c",
            ),
            "person_ids": self.people_picker.get_values(),
            "eminence_person_ids": (
                self.eminence_picker.get_values()
                if hasattr(self, "eminence_picker")
                else self.event.get("eminence_person_ids", [])
            ),
            "eminence_skills": (
                self.eminence_picker.get_skill_values()
                if hasattr(self, "eminence_picker")
                else self.event.get("eminence_skills", {})
            ),
            "period_names": [],
            "location_ids": (
                []
                if event_type == "organization_founding"
                else list(
                    dict.fromkeys(
                        selected_locations + locked_locations
                    )
                )
            ),
            "locked_location_ids": (
                []
                if event_type == "organization_founding"
                else locked_locations
            ),
            "organization_id": (
                selected_organization_id
                if event_type == "organization_founding"
                else (
                    str(job_option.get("organization_id", "") or "")
                    if job_option is not None
                    else ""
                )
            ),
            "organization_name": (
                str(
                    (selected_organization or {}).get("name", "")
                    or ""
                )
                if event_type == "organization_founding"
                else (
                    str(job_option.get("organization_name", "") or "")
                    if job_option is not None
                    else ""
                )
            ),
            "organization_job_id": (
                str(
                    job_option.get("organization_job_id", "")
                    or ""
                )
                if job_option is not None
                else ""
            ),
            "job_title": (
                str(job_option.get("job_title", "") or "")
                if job_option is not None
                else ""
            ),
            "job_assignment_id": str(
                self.event.get("job_assignment_id", "") or ""
            ),
            "job_end_date": str(
                self.event.get("job_end_date", "") or ""
            ),
            "salary": (
                {
                    "galleons": self.salary_galleons_value.get(),
                    "sickles": self.salary_sickles_value.get(),
                    "knuts": self.salary_knuts_value.get(),
                }
                if event_type in ("started_job", "received_raise")
                else None
            ),
        }

    def save(self):
        if self.read_only:
            return False

        self.clamp_year_to_editor_bounds()
        values = self.values()

        if self.storage_kind == "shared" and not values["date"]:
            self.show_error("Enter the year when this event happened.")
            return False

        if values["event_type"] in ("started_job", "received_raise"):
            if not values["organization_job_id"]:
                self.show_error("Choose the organization job.")
                return False

            if len(values["person_ids"]) != 1:
                self.show_error(
                    "A job event must belong to exactly one person."
                )
                return False

        if (
            values["event_type"] == "relocated"
            and len(values["location_ids"]) != 1
        ):
            self.show_error(
                "Select exactly one destination location for a relocation."
            )
            return False

        if (
            values["event_type"] == "founding"
            and len(values["location_ids"]) != 1
        ):
            self.show_error(
                "Select exactly one location for a founding event."
            )
            return False

        if (
            values["event_type"] == "extinction"
            and len(values["location_ids"]) != 1
        ):
            self.show_error(
                "Select exactly one location for an extinction event."
            )
            return False

        if (
            values["event_type"] == "organization_founding"
            and not values["organization_id"]
        ):
            self.show_error(
                "Select exactly one organization for its founding event."
            )
            return False

        if (
            values["event_type"] == "began_friendship"
            and len(values["person_ids"]) < 2
        ):
            self.show_error(
                "A friendship event needs at least two people."
            )
            return False

        if (
            values["event_type"] == "died"
            and len(values["person_ids"]) != 1
        ):
            self.show_error(
                "A Death event must belong to exactly one person."
            )
            return False

        if (
            self.minimum_year is not None
            and self.maximum_year is not None
        ):
            try:
                event_year = int(self.year_value.get().strip())
            except ValueError:
                event_year = None

            if (
                event_year is not None
                and not (
                    self.minimum_year
                    <= event_year
                    <= self.maximum_year
                )
            ):
                self.show_error(
                    f"Enter a year from {self.minimum_year:,} to "
                    f"{self.maximum_year:,} for this period."
                )
                return False

        self.saving = True

        try:
            saved = self.save_command(
                values,
                self.storage_kind,
                deepcopy(self.event),
            )
        except (KeyError, TypeError, ValueError) as error:
            self.show_error(str(error))
            return False
        finally:
            self.saving = False

        if saved is False:
            return False

        self.saved_editor_values = deepcopy(self.values())
        self.show_saved()
        return True

    def has_unsaved_changes(self):
        if self.read_only or self.editor_mode == "empty":
            return False

        saved_values = getattr(self, "saved_editor_values", None)

        if saved_values is None:
            return self.is_new_event()

        return self.values() != saved_values

    def cancel(self):
        self.clear_feedback()
        self.editor_mode = "empty"
        self.saved_editor_values = None

        if self.cancel_command is not None:
            self.cancel_command()
        else:
            self.clear()

    def show_error(self, message):
        self.clear_feedback()
        self.feedback_value.set(str(message or "Cannot save this event."))

    def show_saved(self):
        self.clear_feedback()
        self.feedback_value.set("✓ Event saved")
        self.save_button.set_text("✓ Saved")
        self.feedback_after_id = self.after(
            2400,
            self.clear_feedback,
        )

    def clear_feedback(self):
        if self.feedback_after_id is not None:
            try:
                self.after_cancel(self.feedback_after_id)
            except tk.TclError:
                pass

            self.feedback_after_id = None

        self.feedback_value.set("")

        if hasattr(self, "save_button"):
            self.save_button.set_text("Save event")
