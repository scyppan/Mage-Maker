import tkinter as tk
from copy import deepcopy
from functools import partial

from mage_maker.name_details import NameDetailsDialog
from mage_maker.theme import (
    BORDER_SOFT,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    FIELD_BACKGROUND,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.widgets import (
    LabeledEntry,
    MultilineField,
    SectionPanel,
    SoftButton,
)


class PersonForm(tk.Frame):
    status_fields = (
        ("deceased", "Dead or permanently neutralized"),
        ("canon", "Canon"),
        ("player_character", "Player character"),
    )
    family_status_fields = (
        ("muggle", "Muggle"),
        ("squib", "Squib"),
    )

    def __init__(self, parent, change_command):
        super().__init__(parent, bg=SURFACE)
        self.change_command = change_command
        self.loading = False
        self.variables = {}
        self.text_widgets = {}
        self.name_details = {}
        self.pages = {}
        self.navigation_buttons = {}
        self.active_page_name = "profile"

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_navigation()

        self.content = tk.Frame(self, bg=SURFACE)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.build_profile_page()
        self.build_family_tree_page()
        self.build_development_page()
        self.show_page("profile")

    def build_navigation(self):
        navigation = tk.Frame(self, bg=SURFACE)
        navigation.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        page_definitions = (
            ("profile", "Profile", 98),
            ("family_tree", "Family Tree", 122),
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
        page.grid_columnconfigure(0, weight=5, uniform="profile")
        page.grid_columnconfigure(1, weight=4, uniform="profile")
        page.grid_rowconfigure(0, weight=3, uniform="profile_rows")
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
        identity_panel.content.grid_columnconfigure(0, weight=3)
        identity_panel.content.grid_columnconfigure(1, weight=2)

        displayed_name_value = tk.StringVar()
        displayed_name_value.trace_add("write", self.variable_changed)
        self.variables["displayed_name"] = displayed_name_value
        displayed_name_field = LabeledEntry(
            identity_panel.content,
            "Displayed name",
            displayed_name_value,
            background=SURFACE_MUTED,
            font_size=12,
        )
        displayed_name_field.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 10),
            pady=(0, 12),
        )
        self.name_details_button = SoftButton(
            identity_panel.content,
            text="Open Name Details",
            command=self.open_name_details,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_LIGHT,
            width=164,
            height=40,
        )
        self.name_details_button.grid(
            row=0,
            column=1,
            sticky="se",
            pady=(0, 12),
        )

        self.add_entry_field(
            identity_panel.content,
            1,
            0,
            "school",
            "School",
            SURFACE_MUTED,
            (0, 10),
        )

        birth_frame = tk.Frame(identity_panel.content, bg=SURFACE_MUTED)
        birth_frame.grid(row=1, column=1, sticky="ew")
        birth_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.add_entry_field(
            birth_frame,
            0,
            0,
            "birth_year",
            "Birth year",
            SURFACE_MUTED,
            (0, 6),
        )
        self.add_entry_field(
            birth_frame,
            0,
            1,
            "birth_month",
            "Month",
            SURFACE_MUTED,
            (0, 6),
        )
        self.add_entry_field(
            birth_frame,
            0,
            2,
            "birth_day",
            "Day",
            SURFACE_MUTED,
            0,
        )

        status_panel = SectionPanel(
            page,
            "Record Status",
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
            row=1,
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

    def build_family_tree_page(self):
        page = tk.Frame(self.content, bg=SURFACE)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure((0, 1), weight=1, uniform="family")
        page.grid_rowconfigure(0, weight=1)
        self.pages["family_tree"] = page

        relationships_panel = SectionPanel(
            page,
            "Biological Parents",
            "Record known biological relationships here. A full tree editor can build on these links later.",
        )
        relationships_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
        )
        relationships_panel.content.grid_columnconfigure((0, 1), weight=1)
        self.add_entry_field(
            relationships_panel.content,
            0,
            0,
            "biological_mother",
            "Biological mother",
            SURFACE_MUTED,
            (0, 8),
        )
        self.add_entry_field(
            relationships_panel.content,
            0,
            1,
            "biological_father",
            "Biological father",
            SURFACE_MUTED,
            (8, 0),
        )

        lineage_panel = SectionPanel(
            page,
            "Magical Lineage",
            "Blood status and exceptions belong with the person's family background.",
        )
        lineage_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
        )
        lineage_panel.content.grid_columnconfigure(0, weight=2)
        lineage_panel.content.grid_columnconfigure(1, weight=3)
        self.add_entry_field(
            lineage_panel.content,
            0,
            0,
            "blood_status",
            "Blood status",
            SURFACE_MUTED,
            (0, 16),
        )
        magical_status = tk.Frame(lineage_panel.content, bg=SURFACE_MUTED)
        magical_status.grid(row=0, column=1, sticky="ew")
        magical_status.grid_columnconfigure((0, 1), weight=1)
        magical_status_label = tk.Label(
            magical_status,
            text="Magical status",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        magical_status_label.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 5),
        )
        self.add_boolean_fields(
            magical_status,
            self.family_status_fields,
            2,
            SURFACE_MUTED,
            start_row=1,
        )

    def build_development_page(self):
        page = tk.Frame(self.content, bg=SURFACE)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        self.pages["development"] = page

        placeholder_panel = SectionPanel(
            page,
            "Development",
            "This section is ready for the development fields and workflows you define next.",
        )
        placeholder_panel.grid(row=0, column=0, sticky="nsew")
        placeholder_panel.content.grid_rowconfigure(0, weight=1)
        placeholder = tk.Label(
            placeholder_panel.content,
            text="No development fields have been added yet.",
            bg=FIELD_BACKGROUND,
            fg=TEXT_MUTED,
            font=app_font(11),
            justify="center",
            padx=24,
            pady=42,
        )
        placeholder.grid(row=0, column=0, sticky="nsew")

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
        field = LabeledEntry(
            parent,
            label_text,
            variable,
            background=background,
        )
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

    def show_page(self, page_name):
        if page_name not in self.pages:
            return

        self.active_page_name = page_name
        self.pages[page_name].tkraise()

        for name, button in self.navigation_buttons.items():
            if name == page_name:
                button.set_colors(PRIMARY, PRIMARY_HOVER, TEXT_LIGHT)
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
        if name_details == self.name_details:
            return

        self.name_details = deepcopy(name_details)

        if not self.loading:
            self.change_command()

    def set_person(self, person):
        self.loading = True
        displayed_name = person.get("displayed_name", "")
        self.current_name_value.set(displayed_name or "Unnamed magician")

        for field_name, variable in self.variables.items():
            value = person.get(field_name)

            if isinstance(variable, tk.BooleanVar):
                variable.set(bool(value))
            else:
                variable.set("" if value is None else str(value))

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
            f"{imported_count} original Formidable fields are preserved with this record. "
            "Additional sections can expose them as Mage Maker develops."
        )
        self.show_page(self.active_page_name)
        self.loading = False

    def get_values(self):
        values = {}

        for field_name, variable in self.variables.items():
            values[field_name] = variable.get()

        for field_name, text_widget in self.text_widgets.items():
            values[field_name] = text_widget.get("1.0", "end-1c")

        values["name_details"] = deepcopy(self.name_details)

        return values

    def variable_changed(self, *arguments):
        if not self.loading:
            self.change_command()

    def text_changed(self, event):
        if event.widget.edit_modified():
            event.widget.edit_modified(False)

            if not self.loading:
                self.change_command()
