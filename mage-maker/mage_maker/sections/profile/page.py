import tkinter as tk
from copy import deepcopy
from functools import partial

from mage_maker.sections.development.page import DevelopmentView
from mage_maker.sections.family_tree.page import FamilyTreeView
from mage_maker.sections.names.details import NameDetailsDialog, NameEntryDialog
from mage_maker.sections.names.history import (
    new_name_entry,
    normalize_name_details,
    normalize_name_entry,
)
from mage_maker.sections.names.timeline import (
    name_entry_for_timeline_event,
    synchronize_name_change_events,
)
from mage_maker.sections.profile.famous_connections import (
    FamousConnectionMap,
    FamousConnectionsView,
)
from mage_maker.sections.profile.school_field import SchoolField
from mage_maker.sections.timeline.page import TimelineView
from mage_maker.sections.timeline.locations import ensure_life_start_events
from mage_maker.ui.theme import (
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    FIELD_BACKGROUND,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import (
    HoverTooltip,
    LabeledEntry,
    MultilineField,
    SectionPanel,
    SoftButton,
)


class PersonForm(tk.Frame):
    status_fields = (
        ("canon", "Canon"),
        ("player_character", "Player character"),
        ("non_magical", "Non-magical"),
        ("can_give_birth", "Can give birth"),
        ("famous_person", "This is a famous person"),
    )

    def __init__(
        self,
        parent,
        change_command,
        people_provider,
        create_person_command,
        update_person_command,
        refresh_people_command,
        navigate_command,
        game_database=None,
    ):
        super().__init__(parent, bg=SURFACE)
        self.change_command = change_command
        self.people_provider = people_provider
        self.game_database = game_database
        self.loading = False
        self.variables = {}
        self.boolean_widgets = {}
        self.tooltips = {}
        self.text_widgets = {}
        self.name_details = {}
        self.pages = {}
        self.navigation_buttons = {}
        self.active_page_name = "profile"
        self.current_record_id = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_navigation()

        self.content = tk.Frame(self, bg=SURFACE)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.build_profile_page()
        self.build_family_tree_page(
            create_person_command,
            update_person_command,
            refresh_people_command,
            navigate_command,
        )
        self.build_timeline_page(navigate_command)
        self.build_development_page()
        self.show_page("profile")

    def build_navigation(self):
        navigation = tk.Frame(self, bg=SURFACE)
        navigation.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        page_definitions = (
            ("profile", "Profile", 98),
            ("family_tree", "Family Tree", 122),
            ("timeline", "Timeline", 104),
            ("development", "Development", 126),
        )

        for page_name, button_text, width in page_definitions:
            button = SoftButton(
                navigation,
                text=button_text,
                command=partial(self.show_page, page_name),
                background=SURFACE,
                width=width,
                height=36,
            )
            button.pack(side="left", padx=(0, 6))
            self.navigation_buttons[page_name] = button

        self.current_name_value = tk.StringVar(value="Select a magician")
        current_name = tk.Label(
            navigation,
            textvariable=self.current_name_value,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="e",
        )
        current_name.pack(side="right", fill="x", expand=True)

    def build_profile_page(self):
        page = tk.Frame(self.content, bg=SURFACE)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=6, uniform="profile")
        page.grid_columnconfigure(1, weight=4, uniform="profile")
        page.grid_rowconfigure(0, weight=4, uniform="profile_rows")
        page.grid_rowconfigure(1, weight=2, uniform="profile_rows")
        self.pages["profile"] = page

        identity_panel = SectionPanel(
            page,
            "Identity",
            "The displayed name is the unique name used throughout Mage Maker.",
        )
        identity_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
            pady=(0, 7),
        )
        identity_panel.content.grid_columnconfigure(0, weight=1)

        name_school_row = tk.Frame(identity_panel.content, bg=SURFACE_MUTED)
        name_school_row.grid(row=0, column=0, sticky="ew", pady=(0, 11))
        name_school_row.grid_columnconfigure(0, weight=5)
        name_school_row.grid_columnconfigure(2, weight=4)

        displayed_name_value = tk.StringVar()
        displayed_name_value.trace_add("write", self.variable_changed)
        self.variables["displayed_name"] = displayed_name_value
        displayed_name_field = LabeledEntry(
            name_school_row,
            "Displayed name",
            displayed_name_value,
            background=SURFACE_MUTED,
            font_size=12,
        )
        displayed_name_field.grid(row=0, column=0, sticky="ew")

        self.name_details_button = SoftButton(
            name_school_row,
            text="Name Details",
            command=self.open_name_details,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=122,
            height=40,
        )
        self.name_details_button.grid(row=0, column=1, sticky="s", padx=7)
        school_names = (
            self.game_database.school_names()
            if self.game_database is not None and self.game_database.loaded
            else []
        )
        self.school_field = SchoolField(
            name_school_row,
            school_names,
            self.variable_changed,
            SURFACE_MUTED,
        )
        self.school_field.grid(row=0, column=2, sticky="ew")

        birth_frame = tk.Frame(identity_panel.content, bg=SURFACE_MUTED)
        birth_frame.grid(row=1, column=0, sticky="ew", pady=(0, 9))
        birth_frame.grid_columnconfigure((0, 1, 2), weight=1)
        birth_heading = tk.Label(
            birth_frame,
            text="Date of birth",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        birth_heading.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(0, 5),
        )
        self.add_entry_field(
            birth_frame,
            1,
            0,
            "birth_year",
            "Year",
            SURFACE_MUTED,
            (0, 6),
        )
        self.add_entry_field(
            birth_frame,
            1,
            1,
            "birth_month",
            "Month",
            SURFACE_MUTED,
            (0, 6),
        )
        self.add_entry_field(
            birth_frame,
            1,
            2,
            "birth_day",
            "Day",
            SURFACE_MUTED,
        )

        deceased_value = tk.BooleanVar(value=False)
        deceased_value.trace_add("write", self.deceased_changed)
        self.variables["deceased"] = deceased_value
        deceased_check = tk.Checkbutton(
            identity_panel.content,
            text="Dead",
            variable=deceased_value,
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            activebackground=SURFACE_MUTED,
            activeforeground=TEXT_DARK,
            selectcolor=FIELD_BACKGROUND,
            font=app_font(10),
            anchor="w",
            borderwidth=0,
            highlightthickness=0,
        )
        deceased_check.grid(row=2, column=0, sticky="w", pady=(0, 7))
        self.boolean_widgets["deceased"] = deceased_check

        self.death_date_frame = tk.Frame(
            identity_panel.content,
            bg=SURFACE_MUTED,
        )
        self.death_date_frame.grid(row=3, column=0, sticky="ew", pady=(0, 9))
        self.death_date_frame.grid_columnconfigure((0, 1, 2), weight=1)
        death_heading = tk.Label(
            self.death_date_frame,
            text="Date of death",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        death_heading.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(0, 5),
        )
        self.add_entry_field(
            self.death_date_frame,
            1,
            0,
            "death_year",
            "Year",
            SURFACE_MUTED,
            (0, 6),
        )
        self.add_entry_field(
            self.death_date_frame,
            1,
            1,
            "death_month",
            "Month",
            SURFACE_MUTED,
            (0, 6),
        )
        self.add_entry_field(
            self.death_date_frame,
            1,
            2,
            "death_day",
            "Day",
            SURFACE_MUTED,
        )
        self.death_date_frame.grid_remove()
        self.famous_connections = FamousConnectionsView(
            identity_panel.content,
            SURFACE_MUTED,
        )
        self.famous_connections.grid(row=4, column=0, sticky="ew")

        status_panel = SectionPanel(
            page,
            "Profile Overview",
            "Quick classifications used to identify this magician's role and state.",
        )
        status_panel.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, 7),
            pady=(7, 0),
        )
        status_panel.content.grid_columnconfigure((0, 1, 2), weight=1)
        self.add_boolean_fields(
            status_panel.content,
            self.status_fields,
            3,
            SURFACE_MUTED,
        )

        self.imported_count_value = tk.StringVar(value="")
        imported_label = tk.Label(
            status_panel.content,
            textvariable=self.imported_count_value,
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
            justify="left",
            wraplength=500,
        )
        imported_label.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(8, 0),
        )

        narrative_field = MultilineField(
            page,
            "Narrative",
            6,
            background=SURFACE,
            hint_text="The person's story, background, and important context.",
        )
        narrative_field.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
            pady=(0, 7),
        )
        narrative_field.text.bind("<<Modified>>", self.text_changed)
        self.text_widgets["narrative"] = narrative_field.text

        notes_field = MultilineField(
            page,
            "Notes",
            5,
            background=SURFACE,
            hint_text="Database notes and reminders that do not belong in the narrative.",
        )
        notes_field.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(7, 0),
            pady=(7, 0),
        )
        notes_field.text.bind("<<Modified>>", self.text_changed)
        self.text_widgets["notes"] = notes_field.text

    def build_family_tree_page(
        self,
        create_person_command,
        update_person_command,
        refresh_people_command,
        navigate_command,
    ):
        page = tk.Frame(self.content, bg=SURFACE)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        self.pages["family_tree"] = page

        self.family_tree = FamilyTreeView(
            page,
            change_command=self.family_tree_changed,
            people_provider=self.people_provider,
            create_person_command=create_person_command,
            update_person_command=update_person_command,
            refresh_people_command=refresh_people_command,
            navigate_command=navigate_command,
        )
        self.family_tree.grid(row=0, column=0, sticky="nsew")

    def build_development_page(self):
        page = DevelopmentView(self.content, self.game_database)
        page.grid(row=0, column=0, sticky="nsew")
        self.pages["development"] = page

    def build_timeline_page(self, navigate_command):
        page = tk.Frame(self.content, bg=SURFACE)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        self.pages["timeline"] = page

        self.timeline = TimelineView(
            page,
            self.timeline_changed,
            people_provider=self.people_provider,
            navigate_command=navigate_command,
            name_change_command=self.open_timeline_name_change,
        )
        self.timeline.grid(row=0, column=0, sticky="nsew")

    def add_entry_field(
        self,
        parent,
        row,
        column,
        field_name,
        label_text,
        background=SURFACE,
        horizontal_padding=0,
    ):
        variable = tk.StringVar()
        variable.trace_add("write", self.variable_changed)
        self.variables[field_name] = variable
        field = LabeledEntry(parent, label_text, variable, background=background)
        field.grid(
            row=row,
            column=column,
            sticky="ew",
            padx=horizontal_padding,
        )

    def add_boolean_fields(
        self,
        parent,
        fields,
        column_count,
        background=SURFACE,
        start_row=0,
    ):
        for index, (field_name, label_text) in enumerate(fields):
            variable = tk.BooleanVar(value=False)
            variable.trace_add("write", self.variable_changed)
            self.variables[field_name] = variable
            checkbutton = tk.Checkbutton(
                parent,
                text=label_text,
                variable=variable,
                bg=background,
                fg=TEXT_DARK,
                activebackground=background,
                activeforeground=TEXT_DARK,
                selectcolor=FIELD_BACKGROUND,
                font=app_font(10),
                anchor="w",
                borderwidth=0,
                highlightthickness=0,
            )
            checkbutton.grid(
                row=start_row + (index // column_count),
                column=index % column_count,
                sticky="w",
                padx=(0, 12),
                pady=4,
            )
            self.boolean_widgets[field_name] = checkbutton

            if field_name == "can_give_birth":
                self.tooltips[field_name] = HoverTooltip(checkbutton)

    def show_page(self, page_name):
        if page_name not in self.pages:
            return

        self.active_page_name = page_name

        if page_name == "family_tree" and self.current_record_id:
            self.family_tree.update_current_person(self.current_profile_values())

        if page_name == "profile":
            self.update_famous_connections()

        self.pages[page_name].tkraise()

        for name, button in self.navigation_buttons.items():
            if name == page_name:
                button.set_colors(PRIMARY, PRIMARY_HOVER, TEXT_DARK)
            else:
                button.set_colors(BUTTON_SOFT, BUTTON_SOFT_HOVER, TEXT_DARK)

    def open_name_details(self):
        NameDetailsDialog(
            self,
            self.name_details,
            self.save_name_details,
            self.variables["displayed_name"].get(),
        )

    def save_name_details(self, name_details):
        normalized_details = normalize_name_details(name_details)
        timeline_person = self.current_profile_values()
        timeline_person["name_details"] = deepcopy(normalized_details)
        timeline_person["timeline_events"] = self.timeline.get_events()
        synchronized_events = synchronize_name_change_events(
            normalized_details,
            ensure_life_start_events(timeline_person),
        )

        if (
            normalized_details == self.name_details
            and synchronized_events == self.timeline.get_events()
        ):
            return

        self.name_details = deepcopy(normalized_details)
        self.timeline.set_events(synchronized_events)

        if self.current_record_id:
            self.family_tree.update_current_person(self.current_profile_values())

        if not self.loading:
            self.change_command()

    def open_timeline_name_change(self, event=None):
        event_values = event if isinstance(event, dict) else {}
        entry = name_entry_for_timeline_event(self.name_details, event_values)

        if entry is None:
            entry = new_name_entry()
            entry.update(
                {
                    "name_type": (
                        "birth name"
                        if event_values.get("event_type") == "birth_name"
                        else ""
                    ),
                    "name_entry": str(event_values.get("detail", "") or ""),
                    "date": str(event_values.get("date", "") or ""),
                    "note": str(event_values.get("note", "") or ""),
                }
            )

        source_event_id = str(event_values.get("event_id", "") or "")
        NameEntryDialog(
            self,
            entry,
            partial(self.save_timeline_name_change, source_event_id),
            "Edit Name" if event_values else "Add Name",
        )

    def save_timeline_name_change(self, source_event_id, entry):
        normalized_entry = normalize_name_entry(entry)
        entries = deepcopy(self.name_details.get("entries", []))
        replacement_index = None

        for index, existing_entry in enumerate(entries):
            if existing_entry.get("entry_id") == normalized_entry["entry_id"]:
                replacement_index = index
                break

        if replacement_index is None:
            entries.append(normalized_entry)
        else:
            entries[replacement_index] = normalized_entry

        events = [
            event
            for event in self.timeline.get_events()
            if not source_event_id or event.get("event_id") != source_event_id
        ]
        self.name_details = normalize_name_details({"entries": entries})
        timeline_person = self.current_profile_values()
        timeline_person["name_details"] = deepcopy(self.name_details)
        timeline_person["timeline_events"] = events
        synchronized_events = synchronize_name_change_events(
            self.name_details,
            ensure_life_start_events(timeline_person),
        )
        self.timeline.selected_event_id = (
            "life-start:birth-name"
            if normalized_entry["name_type"].strip().casefold() == "birth name"
            else f"name-change:{normalized_entry['entry_id']}"
        )
        self.timeline.set_events(synchronized_events)

        if self.current_record_id:
            self.family_tree.update_current_person(self.current_profile_values())

        if not self.loading:
            self.change_command()

    def set_person(self, person):
        self.loading = True
        self.current_record_id = person.get("record_id")
        displayed_name = person.get("displayed_name", "")
        self.current_name_value.set(displayed_name or "Unnamed magician")

        for field_name, variable in self.variables.items():
            value = person.get(field_name)

            if isinstance(variable, tk.BooleanVar):
                variable.set(bool(value))
            else:
                variable.set("" if value is None else str(value))

        self.school_field.set_value(person.get("school", ""))
        self.update_death_date_visibility()

        for field_name, text_widget in self.text_widgets.items():
            text_widget.delete("1.0", "end")
            text_widget.insert("1.0", str(person.get(field_name, "") or ""))
            text_widget.edit_modified(False)

        name_details = person.get("name_details", {})
        self.name_details = (
            deepcopy(name_details)
            if isinstance(name_details, dict)
            else {"entries": []}
        )
        imported_fields = person.get("imported_fields", {})
        imported_count = len(imported_fields) if isinstance(imported_fields, dict) else 0
        self.imported_count_value.set(
            (
                f"{imported_count} original Formidable fields are preserved with this record. "
                "Additional sections can expose them as Mage Maker develops."
            )
            if imported_count
            else ""
        )
        self.family_tree.set_person(person)
        timeline_person = deepcopy(person)
        timeline_person["name_details"] = deepcopy(self.name_details)
        timeline_person["timeline_events"] = person.get("timeline_events", [])
        self.timeline.set_events(
            synchronize_name_change_events(
                self.name_details,
                ensure_life_start_events(timeline_person),
            )
        )
        self.update_can_give_birth_control()
        self.update_famous_connections()
        self.show_page(self.active_page_name)
        self.loading = False

    def current_profile_values(self):
        return {
            "record_id": self.current_record_id,
            "displayed_name": self.variables["displayed_name"].get(),
            "birth_year": self.variables["birth_year"].get(),
            "birth_month": self.variables["birth_month"].get(),
            "birth_day": self.variables["birth_day"].get(),
            "deceased": self.variables["deceased"].get(),
            "death_year": self.variables["death_year"].get(),
            "death_month": self.variables["death_month"].get(),
            "death_day": self.variables["death_day"].get(),
            "can_give_birth": self.variables["can_give_birth"].get(),
            "famous_person": self.variables["famous_person"].get(),
            "school": self.school_field.get_value(),
            "timeline_events": self.timeline.get_events(),
            "name_details": deepcopy(self.name_details),
        }

    def get_values(self):
        values = {}

        for field_name, variable in self.variables.items():
            values[field_name] = variable.get()

        for field_name, text_widget in self.text_widgets.items():
            values[field_name] = text_widget.get("1.0", "end-1c")

        values["school"] = self.school_field.get_value()
        values["name_details"] = deepcopy(self.name_details)
        values["timeline_events"] = self.timeline.get_events()
        values.update(self.family_tree.get_relationship_values())

        return values

    def family_tree_changed(self):
        self.update_can_give_birth_control()
        self.update_famous_connections()

        if not self.loading:
            self.change_command()

    def timeline_changed(self):
        if not self.loading:
            self.change_command()

    def deceased_changed(self, *arguments):
        self.update_death_date_visibility()

        if not self.loading:
            self.change_command()

    def update_death_date_visibility(self):
        if not hasattr(self, "death_date_frame"):
            return

        if self.variables["deceased"].get():
            self.death_date_frame.grid()
        else:
            self.death_date_frame.grid_remove()

    def update_famous_connections(self):
        if not self.current_record_id or not hasattr(self, "family_tree"):
            self.famous_connections.set_connections([])
            return

        current_person = deepcopy(self.family_tree.current_person)
        current_person.update(self.current_profile_values())
        current_person.update(self.family_tree.get_relationship_values())
        connection_map = FamousConnectionMap(
            self.people_provider(),
            current_person,
        )
        self.famous_connections.set_connections(
            connection_map.labels_for(self.current_record_id)
        )

    def update_can_give_birth_control(self):
        checkbutton = self.boolean_widgets.get("can_give_birth")
        tooltip = self.tooltips.get("can_give_birth")

        if checkbutton is None or tooltip is None:
            return

        record_id = str(self.current_record_id or "")

        if not record_id:
            checkbutton.configure(state="disabled")
            tooltip.set_text("Select a magician before changing this setting.")
            return

        relationship_map = self.family_tree.relationship_map
        birthing_children = relationship_map.children_for_parent_role(
            record_id,
            "mother",
        )
        non_birthing_children = relationship_map.children_for_parent_role(
            record_id,
            "father",
        )

        if birthing_children:
            child_names = [
                str(child.get("displayed_name", "Unnamed"))
                for child in birthing_children
            ]
            visible_names = ", ".join(child_names[:3])

            if len(child_names) > 3:
                visible_names += f", and {len(child_names) - 3} more"

            checkbutton.configure(state="disabled")
            tooltip.set_text(
                "Can give birth is locked because this person is the birthing "
                f"parent of {visible_names}. Remove those family links before "
                "changing it."
            )
            return

        if non_birthing_children:
            child_names = [
                str(child.get("displayed_name", "Unnamed"))
                for child in non_birthing_children
            ]
            visible_names = ", ".join(child_names[:3])

            if len(child_names) > 3:
                visible_names += f", and {len(child_names) - 3} more"

            checkbutton.configure(state="disabled")
            tooltip.set_text(
                "Can give birth is locked because this person is the non-birthing "
                f"parent of {visible_names}. Remove those family links before "
                "changing it."
            )
            return

        mate_ids = relationship_map.mates_of(record_id)

        if mate_ids:
            mate_names = []

            for mate_id in mate_ids:
                mate = relationship_map.person(mate_id)
                mate_names.append(
                    str(mate.get("displayed_name", "Unnamed"))
                    if mate
                    else "Unnamed"
                )

            visible_names = ", ".join(mate_names[:3])

            if len(mate_names) > 3:
                visible_names += f", and {len(mate_names) - 3} more"

            checkbutton.configure(state="disabled")
            tooltip.set_text(
                "Can give birth is locked because this person is linked as a mate "
                f"to {visible_names}. Remove those mate links before changing it."
            )
            return

        checkbutton.configure(state="normal")
        tooltip.set_text(
            "This setting becomes locked once the person is linked as a mate or "
            "as a birthing or non-birthing parent."
        )

    def variable_changed(self, *arguments):
        if not self.loading:
            self.change_command()

    def text_changed(self, event):
        if event.widget.edit_modified():
            event.widget.edit_modified(False)

            if not self.loading:
                self.change_command()
