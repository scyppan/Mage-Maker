import tkinter as tk
from copy import deepcopy
from functools import partial

from mage_maker.sections.development.bonus_dialogs import (
    InitialSkillBonusDialog,
    TraitSelectionDialog,
)
from mage_maker.sections.development.characteristics import (
    CHARACTERISTIC_BASE_VALUE,
    CHARACTERISTIC_MAXIMUM_VALUE,
    CHARACTERISTIC_NAMES,
    CHARACTERISTIC_POINTS_TO_SPEND,
    CHARACTERISTIC_REQUIRED_TOTAL,
    characteristic_points_remaining,
    initial_values_are_complete,
    normalize_characteristics,
    randomized_characteristics,
)
from mage_maker.sections.development.initial_bonuses import (
    INITIAL_SELECTION_MANUAL,
    allowance_sickles,
    format_wizard_currency,
    initial_bonus_requirements,
    normalize_initial_bonuses,
    reconcile_initial_bonuses,
    summarize_initial_skill_bonuses,
)
from mage_maker.sections.development.initial_values import (
    BLOOD_STATUS_HALFBLOOD,
    BLOOD_STATUS_OPTIONS,
    DEVELOPMENTAL_ENVIRONMENT_MAGICAL,
    DEVELOPMENTAL_ENVIRONMENT_OPTIONS,
    PARENTAL_MODE_FULLY_RANDOMIZED,
    PARENTAL_MODE_OVERRIDE,
    PARENTAL_MODE_SHARED,
    PARENTAL_MODE_SLIGHTLY_RANDOMIZED,
    PARENTAL_VALUE_NAMES,
    blood_status_options,
    initialize_parental_values,
    normalize_blood_status,
    normalize_developmental_environment,
    normalize_parental_values,
    parental_sibling_reference,
    parental_values_for_mode,
    rebase_parental_values,
    resolved_blood_status,
    resolved_developmental_environment,
)
from mage_maker.sections.development.models import (
    ACADEMIC_YEARS_TO_ADULTHOOD,
    DEVELOPMENT_ABILITY_OPTIONS,
    DEVELOPMENT_SCHEMA_OPTIONS,
    DEVELOPMENT_SKILL_OPTIONS,
    calculate_school_start_year,
    development_skill_count,
    normalize_academic_years_advanced,
    normalize_development_plan,
    normalize_school_started,
    randomized_development_plan,
    school_progress_text,
    visible_school_year_count,
)
from mage_maker.sections.development.traits import trait_effect_text
from mage_maker.sections.profile.school_field import SchoolField
from mage_maker.ui.theme import (
    BORDER_SOFT,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    FIELD_BACKGROUND,
    LIST_HOVER,
    LOCKED_BORDER,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import (
    RoundedEntry,
    RoundedSelect,
    SectionPanel,
    SoftButton,
)


class DevelopmentView(tk.Frame):
    def __init__(
        self,
        parent,
        game_database=None,
        change_command=None,
        people_provider=None,
    ):
        super().__init__(parent, bg=SURFACE)
        self.game_database = game_database
        self.change_command = change_command
        self.people_provider = people_provider
        self.loading = False
        self.birth_year = None
        self.birth_month = None
        self.birth_day = None
        self.current_person = {}
        self.development_plan = {
            "schema": "Scattershot",
            "academic_years_advanced": 0,
            "school_started": False,
        }
        self.academic_years_advanced = 0
        self.school_started = False
        self.start_year_value = tk.StringVar(value="Unknown")
        self.strategy_value = tk.StringVar(value="Scattershot")
        self.blood_status_value = tk.StringVar(
            value=BLOOD_STATUS_OPTIONS[0]
        )
        self.developmental_environment_value = tk.StringVar(
            value=DEVELOPMENTAL_ENVIRONMENT_MAGICAL
        )
        self.parental_mode_value = tk.StringVar(
            value=PARENTAL_MODE_SHARED
        )
        self.parental_value_variables = {
            field_name: tk.StringVar()
            for field_name in PARENTAL_VALUE_NAMES
        }
        self.parental_values = None
        self.initial_bonuses = None
        self.characteristics = None
        self.characteristics_editing = False
        self.skill_bonus_summary_value = tk.StringVar(
            value="Initial skill bonuses have not been assigned"
        )
        self.trait_summary_value = tk.StringVar(
            value="Traits have not been assigned"
        )
        self.muggles_bonus_summary_value = tk.StringVar()
        self.characteristic_points_value = tk.StringVar(
            value=(
                f"{CHARACTERISTIC_POINTS_TO_SPEND} "
                "points to spend"
            )
        )
        self.characteristic_variables = {
            field_name: tk.IntVar(
                value=CHARACTERISTIC_BASE_VALUE
            )
            for field_name in CHARACTERISTIC_NAMES
        }
        self.characteristic_value_labels = {}
        self.characteristic_decrease_buttons = {}
        self.characteristic_increase_buttons = {}
        self.active_year_tab = 0
        self.year_tab_buttons = {}
        self.year_placeholder_value = tk.StringVar()
        self.skill_values = [
            tk.StringVar(value=DEVELOPMENT_SKILL_OPTIONS[index])
            for index in range(3)
        ]
        self.ability_value = tk.StringVar(
            value=DEVELOPMENT_ABILITY_OPTIONS[0]
        )
        self.strategy_value.trace_add(
            "write",
            self.strategy_changed,
        )
        self.blood_status_value.trace_add(
            "write",
            self.blood_status_changed,
        )
        self.developmental_environment_value.trace_add(
            "write",
            self.developmental_environment_changed,
        )
        self.parental_mode_value.trace_add(
            "write",
            self.parental_mode_changed,
        )

        for skill_value in self.skill_values:
            skill_value.trace_add(
                "write",
                self.focus_selection_changed,
            )

        self.ability_value.trace_add(
            "write",
            self.focus_selection_changed,
        )

        for parental_value in self.parental_value_variables.values():
            parental_value.trace_add(
                "write",
                self.parental_value_changed,
            )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.build_header()
        self.build_plan_panel()

    def build_header(self):
        header = tk.Frame(self, bg=SURFACE)
        header.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 14),
        )
        header.grid_columnconfigure(0, weight=1)

        heading = tk.Label(
            header,
            text="Development Plan",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(16, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")

        self.random_strategy_button = SoftButton(
            header,
            text="Random strategy",
            command=self.randomly_select_strategy,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=148,
            height=38,
        )
        self.random_strategy_button.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(6, 0),
        )

        self.advance_year_button = SoftButton(
            header,
            text="Start school",
            command=self.advance_one_year,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=148,
            height=38,
        )
        self.advance_year_button.grid(
            row=0,
            column=2,
            sticky="e",
            padx=(6, 0),
        )

        self.advance_adulthood_button = SoftButton(
            header,
            text="Advance to adulthood",
            command=self.advance_to_adulthood,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=178,
            height=38,
        )
        self.advance_adulthood_button.grid(
            row=0,
            column=3,
            sticky="e",
            padx=(6, 0),
        )

    def build_plan_panel(self):
        panels = tk.Frame(self, bg=SURFACE)
        panels.grid(
            row=1,
            column=0,
            sticky="nsew",
        )
        panels.grid_rowconfigure(0, weight=1)
        panels.grid_columnconfigure(0, weight=3)
        panels.grid_columnconfigure(1, weight=2)

        left_panels = tk.Frame(
            panels,
            bg=SURFACE,
        )
        left_panels.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
        )
        left_panels.grid_columnconfigure(0, weight=1)
        left_panels.grid_rowconfigure(1, weight=1)

        plan_panel = SectionPanel(
            left_panels,
            "Development overview",
            "Academic placement and developmental direction.",
        )
        plan_panel.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 7),
        )
        plan_panel.content.grid_columnconfigure(0, weight=1)

        academic_row = tk.Frame(
            plan_panel.content,
            bg=SURFACE_MUTED,
        )
        academic_row.grid(
            row=0,
            column=0,
            sticky="ew",
        )
        academic_row.grid_columnconfigure(2, weight=1)

        school_records = (
            self.game_database.schools()
            if self.game_database is not None
            and self.game_database.loaded
            else []
        )
        self.school_field = SchoolField(
            academic_row,
            school_records,
            self.school_changed,
            SURFACE_MUTED,
        )
        self.school_field.grid(
            row=0,
            column=0,
            sticky="nw",
        )

        start_year_block = tk.Frame(
            academic_row,
            bg=SURFACE_MUTED,
        )
        start_year_block.grid(
            row=0,
            column=1,
            sticky="nw",
            padx=(28, 0),
        )
        start_year_label = tk.Label(
            start_year_block,
            text="Academic start year",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        start_year_label.grid(
            row=0,
            column=0,
            sticky="w",
        )
        start_year_value_label = tk.Label(
            start_year_block,
            textvariable=self.start_year_value,
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        start_year_value_label.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(5, 0),
        )

        strategy_block = tk.Frame(
            academic_row,
            bg=SURFACE_MUTED,
        )
        strategy_block.grid(
            row=0,
            column=2,
            sticky="nw",
            padx=(28, 0),
        )
        strategy_block.grid_columnconfigure(0, weight=1)
        strategy_label = tk.Label(
            strategy_block,
            text="Developmental strategy",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        strategy_label.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 5),
        )
        self.strategy_select = RoundedSelect(
            strategy_block,
            self.strategy_value,
            DEVELOPMENT_SCHEMA_OPTIONS,
            background=SURFACE_MUTED,
            width=190,
            height=42,
            font=app_font(11),
        )
        self.strategy_select.grid(
            row=1,
            column=0,
            sticky="w",
        )

        self.focus_frame = tk.Frame(
            plan_panel.content,
            bg=SURFACE_MUTED,
        )
        self.focus_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(18, 0),
        )
        self.focus_frame.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="development_focus",
        )
        self.skill_blocks = []
        self.skill_labels = []
        self.skill_selects = []

        for index in range(3):
            skill_block = tk.Frame(
                self.focus_frame,
                bg=SURFACE_MUTED,
            )
            skill_block.grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(
                    (0, 6)
                    if index == 0
                    else (6, 6)
                    if index == 1
                    else (6, 0)
                ),
            )
            skill_block.grid_columnconfigure(0, weight=1)
            skill_label = tk.Label(
                skill_block,
                text=f"Skill {index + 1}",
                bg=SURFACE_MUTED,
                fg=TEXT_MUTED,
                font=app_font(9, "bold"),
                anchor="w",
            )
            skill_label.grid(
                row=0,
                column=0,
                sticky="ew",
                pady=(0, 5),
            )
            skill_select = RoundedSelect(
                skill_block,
                self.skill_values[index],
                DEVELOPMENT_SKILL_OPTIONS,
                background=SURFACE_MUTED,
                width=190,
                height=40,
                font=app_font(10),
            )
            skill_select.grid(
                row=1,
                column=0,
                sticky="w",
            )
            self.skill_blocks.append(skill_block)
            self.skill_labels.append(skill_label)
            self.skill_selects.append(skill_select)

        self.ability_block = tk.Frame(
            self.focus_frame,
            bg=SURFACE_MUTED,
        )
        self.ability_block.grid(
            row=0,
            column=0,
            sticky="ew",
        )
        self.ability_block.grid_columnconfigure(0, weight=1)
        ability_label = tk.Label(
            self.ability_block,
            text="Ability",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        ability_label.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 5),
        )
        self.ability_select = RoundedSelect(
            self.ability_block,
            self.ability_value,
            DEVELOPMENT_ABILITY_OPTIONS,
            background=SURFACE_MUTED,
            width=140,
            height=40,
            font=app_font(10),
        )
        self.ability_select.grid(
            row=1,
            column=0,
            sticky="w",
        )

        years_panel = SectionPanel(
            panels,
            "School years",
            "Academic development by school year.",
        )
        self.school_years_panel = years_panel
        years_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
        )
        years_panel.grid_rowconfigure(2, weight=1)
        years_panel.content.grid_rowconfigure(0, weight=1)

        self.year_tabs_container = tk.Frame(
            years_panel.content,
            bg=SURFACE_MUTED,
        )
        self.year_tabs_container.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        self.year_tabs_container.grid_columnconfigure(0, weight=1)
        self.year_tabs_container.grid_rowconfigure(2, weight=1)
        available_years_heading = tk.Label(
            self.year_tabs_container,
            text="Available years",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(10, "bold"),
            anchor="w",
        )
        available_years_heading.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )
        self.remove_year_button = SoftButton(
            self.year_tabs_container,
            text="Remove latest year",
            command=self.remove_latest_school_year,
            background=SURFACE_MUTED,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            foreground=TEXT_DARK,
            width=126,
            height=32,
            font=app_font(9, "bold"),
        )
        self.remove_year_button.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(8, 0),
            pady=(0, 8),
        )
        year_button_row = tk.Frame(
            self.year_tabs_container,
            bg=SURFACE_MUTED,
        )
        year_button_row.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
        )
        year_button_row.grid_columnconfigure(
            tuple(range(ACADEMIC_YEARS_TO_ADULTHOOD)),
            weight=1,
            uniform="school_year_tabs",
        )

        for year_number in range(
            1,
            ACADEMIC_YEARS_TO_ADULTHOOD + 1,
        ):
            year_button = SoftButton(
                year_button_row,
                text=f"Year {year_number}",
                command=partial(
                    self.select_year_tab,
                    year_number,
                ),
                background=SURFACE_MUTED,
                fill=BUTTON_SOFT,
                hover_fill=BUTTON_SOFT_HOVER,
                foreground=TEXT_DARK,
                width=60,
                height=32,
                font=app_font(9, "bold"),
                padx=6,
            )
            year_button.grid(
                row=0,
                column=year_number - 1,
                sticky="ew",
                padx=(
                    (0, 2)
                    if year_number == 1
                    else (2, 0)
                    if year_number
                    == ACADEMIC_YEARS_TO_ADULTHOOD
                    else (2, 2)
                ),
                pady=(0, 6),
            )
            year_button.grid_remove()
            self.year_tab_buttons[year_number] = year_button

        year_placeholder = tk.Label(
            self.year_tabs_container,
            textvariable=self.year_placeholder_value,
            bg=FIELD_BACKGROUND,
            fg=TEXT_MUTED,
            font=app_font(10),
            anchor="nw",
            justify="left",
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        year_placeholder.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )
        self.year_tabs_container.grid_remove()

        initial_values_panel = SectionPanel(
            left_panels,
            "Initial values",
            "Values established before academic advancement begins.",
        )
        self.initial_values_panel = initial_values_panel
        initial_values_panel.configure(
            padx=14,
            pady=10,
        )
        initial_values_panel.description_label.grid_configure(
            pady=(2, 8),
        )
        initial_values_panel.grid(
            row=1,
            column=0,
            sticky="nsew",
            pady=(7, 0),
        )
        initial_values_panel.content.grid_columnconfigure(
            (0, 2),
            weight=1,
            uniform="initial_value_status",
        )
        blood_status_block = tk.Frame(
            initial_values_panel.content,
            bg=SURFACE_MUTED,
        )
        blood_status_block.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6),
        )
        blood_status_block.grid_columnconfigure(0, weight=1)
        blood_status_label = tk.Label(
            blood_status_block,
            text="Blood status",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        blood_status_label.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 5),
        )
        self.blood_status_select = RoundedSelect(
            blood_status_block,
            self.blood_status_value,
            BLOOD_STATUS_OPTIONS,
            background=SURFACE_MUTED,
            width=140,
            height=36,
            font=app_font(10),
        )
        self.blood_status_select.grid(
            row=1,
            column=0,
            sticky="w",
        )
        self.blood_status_text = tk.Label(
            blood_status_block,
            textvariable=self.blood_status_value,
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
            padx=2,
            pady=8,
        )
        self.blood_status_text.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self.environment_block = tk.Frame(
            initial_values_panel.content,
            bg=SURFACE_MUTED,
        )
        self.environment_block.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(6, 0),
        )
        self.environment_block.grid_columnconfigure(0, weight=1)
        environment_label = tk.Label(
            self.environment_block,
            text="Developmental environment",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        environment_label.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 5),
        )
        self.environment_select = RoundedSelect(
            self.environment_block,
            self.developmental_environment_value,
            DEVELOPMENTAL_ENVIRONMENT_OPTIONS,
            background=SURFACE_MUTED,
            width=120,
            height=36,
            font=app_font(10),
        )
        self.environment_select.grid(
            row=1,
            column=0,
            sticky="w",
        )

        parental_header = tk.Frame(
            initial_values_panel.content,
            bg=SURFACE_MUTED,
        )
        parental_header.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(12, 5),
        )
        parental_header.grid_columnconfigure(0, weight=1)
        parental_heading = tk.Label(
            parental_header,
            text="Parental values",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        parental_heading.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        self.parental_handling_button = SoftButton(
            parental_header,
            text="Handling ▾",
            command=self.show_parental_handling_menu,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=112,
            height=30,
        )
        self.parental_handling_button.grid(
            row=0,
            column=1,
            sticky="e",
        )

        self.parental_handling_menu = tk.Menu(
            self,
            tearoff=False,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            activebackground=LIST_HOVER,
            activeforeground=TEXT_DARK,
            relief="solid",
            borderwidth=1,
            font=app_font(10),
        )

        self.update_parental_handling_menu()

        parental_values_row = tk.Frame(
            initial_values_panel.content,
            bg=SURFACE_MUTED,
        )
        parental_values_row.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(2, 0),
        )
        parental_values_row.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="parental_values",
        )
        self.parental_value_entries = {}

        for index, field_name in enumerate(PARENTAL_VALUE_NAMES):
            value_block = tk.Frame(
                parental_values_row,
                bg=SURFACE_MUTED,
            )
            value_block.grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(
                    (0, 5)
                    if index == 0
                    else (5, 5)
                    if index == 1
                    else (5, 0)
                ),
            )
            value_block.grid_columnconfigure(0, weight=1)
            value_label = tk.Label(
                value_block,
                text=field_name.title(),
                bg=SURFACE_MUTED,
                fg=TEXT_MUTED,
                font=app_font(9, "bold"),
                anchor="w",
            )
            value_label.grid(
                row=0,
                column=0,
                sticky="ew",
                pady=(0, 5),
            )
            value_entry = RoundedEntry(
                value_block,
                textvariable=self.parental_value_variables[
                    field_name
                ],
                background=SURFACE_MUTED,
                width=110,
                height=34,
                font=app_font(10),
                justify="center",
            )
            value_entry.grid(
                row=1,
                column=0,
                sticky="ew",
            )
            self.parental_value_entries[field_name] = value_entry

        initial_assignments = tk.Frame(
            initial_values_panel.content,
            bg=SURFACE_MUTED,
        )
        initial_assignments.grid(
            row=3,
            column=0,
            sticky="new",
            padx=(0, 14),
            pady=(12, 0),
        )
        initial_assignments.grid_columnconfigure(0, weight=1)
        initial_assignments_heading = tk.Label(
            initial_assignments,
            text="Developmental bonuses",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        initial_assignments_heading.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 8),
        )
        self.skill_bonus_summary = tk.Label(
            initial_assignments,
            textvariable=self.skill_bonus_summary_value,
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(10),
            anchor="w",
            justify="left",
            wraplength=430,
        )
        self.skill_bonus_summary.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=3,
        )
        self.skill_bonus_button = SoftButton(
            initial_assignments,
            text="Select",
            command=self.open_initial_skill_bonus_dialog,
            background=SURFACE_MUTED,
            width=76,
            height=32,
            font=app_font(9, "bold"),
        )
        self.skill_bonus_button.grid(
            row=1,
            column=1,
            sticky="e",
            padx=(8, 0),
        )
        self.trait_summary = tk.Label(
            initial_assignments,
            textvariable=self.trait_summary_value,
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(10),
            anchor="w",
            justify="left",
            wraplength=430,
        )
        self.trait_summary.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=3,
        )
        self.trait_button = SoftButton(
            initial_assignments,
            text="Select",
            command=self.open_trait_dialog,
            background=SURFACE_MUTED,
            width=76,
            height=32,
            font=app_font(9, "bold"),
        )
        self.trait_button.grid(
            row=2,
            column=1,
            sticky="e",
            padx=(8, 0),
        )
        self.muggles_bonus_summary = tk.Label(
            initial_assignments,
            textvariable=self.muggles_bonus_summary_value,
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(10),
            anchor="w",
        )
        self.muggles_bonus_summary.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=3,
        )

        initial_characteristics_divider = tk.Frame(
            initial_values_panel.content,
            bg=BORDER_SOFT,
            width=1,
        )
        initial_characteristics_divider.grid(
            row=3,
            column=1,
            sticky="ns",
            pady=(12, 0),
        )

        characteristics_section = tk.Frame(
            initial_values_panel.content,
            bg=SURFACE_MUTED,
        )
        characteristics_section.grid(
            row=3,
            column=2,
            sticky="new",
            padx=(14, 0),
            pady=(12, 0),
        )
        characteristics_section.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="characteristics",
        )
        characteristics_heading = tk.Label(
            characteristics_section,
            text="Characteristics",
            bg=SURFACE_MUTED,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        characteristics_heading.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
        )
        characteristic_points = tk.Label(
            characteristics_section,
            textvariable=self.characteristic_points_value,
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="e",
        )
        characteristic_points.grid(
            row=0,
            column=2,
            sticky="e",
        )

        for index, field_name in enumerate(
            CHARACTERISTIC_NAMES
        ):
            characteristic_block = tk.Frame(
                characteristics_section,
                bg=SURFACE_MUTED,
            )
            characteristic_block.grid(
                row=(index // 3) + 1,
                column=index % 3,
                sticky="ew",
                padx=(
                    (0, 6)
                    if index % 3 == 0
                    else (6, 6)
                    if index % 3 == 1
                    else (6, 0)
                ),
                pady=(3, 0),
            )
            characteristic_block.grid_columnconfigure(
                0,
                weight=1,
            )
            characteristic_label = tk.Label(
                characteristic_block,
                text=field_name.title(),
                bg=SURFACE_MUTED,
                fg=TEXT_DARK,
                font=app_font(9),
                anchor="w",
            )
            characteristic_label.grid(
                row=0,
                column=0,
                sticky="ew",
                padx=(0, 4),
            )

            characteristic_stepper = tk.Frame(
                characteristic_block,
                bg=SURFACE_MUTED,
            )
            characteristic_stepper.grid(
                row=0,
                column=1,
                sticky="e",
            )

            decrease_button = SoftButton(
                characteristic_stepper,
                text="−",
                command=partial(
                    self.adjust_characteristic,
                    field_name,
                    -1,
                ),
                background=SURFACE_MUTED,
                fill=BUTTON_SOFT,
                hover_fill=BUTTON_SOFT_HOVER,
                foreground=TEXT_DARK,
                width=24,
                height=24,
                radius=7,
                font=app_font(10, "bold"),
                padx=0,
            )
            decrease_button.grid(
                row=0,
                column=0,
                sticky="w",
                padx=(0, 2),
            )

            characteristic_value = tk.Label(
                characteristic_stepper,
                textvariable=self.characteristic_variables[
                    field_name
                ],
                bg=FIELD_BACKGROUND,
                fg=TEXT_DARK,
                font=app_font(10, "bold"),
                anchor="center",
                highlightbackground=BORDER_SOFT,
                highlightthickness=1,
                width=2,
                padx=3,
                pady=2,
            )
            characteristic_value.grid(
                row=0,
                column=1,
            )

            increase_button = SoftButton(
                characteristic_stepper,
                text="+",
                command=partial(
                    self.adjust_characteristic,
                    field_name,
                    1,
                ),
                background=SURFACE_MUTED,
                fill=BUTTON_SOFT,
                hover_fill=BUTTON_SOFT_HOVER,
                foreground=TEXT_DARK,
                width=24,
                height=24,
                radius=7,
                font=app_font(10, "bold"),
                padx=0,
            )
            increase_button.grid(
                row=0,
                column=2,
                sticky="e",
                padx=(2, 0),
            )

            self.characteristic_value_labels[field_name] = (
                characteristic_value
            )
            self.characteristic_decrease_buttons[field_name] = (
                decrease_button
            )
            self.characteristic_increase_buttons[field_name] = (
                increase_button
            )

        characteristic_buttons = tk.Frame(
            characteristics_section,
            bg=SURFACE_MUTED,
        )
        characteristic_buttons.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(5, 0),
        )
        self.characteristic_submit_button = SoftButton(
            characteristic_buttons,
            text="Edit",
            command=self.handle_characteristics_action,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=82,
            height=28,
            font=app_font(9, "bold"),
        )
        self.characteristic_submit_button.pack(
            side="left",
        )
        self.characteristic_reset_button = SoftButton(
            characteristic_buttons,
            text="Start Over",
            command=self.reset_characteristics,
            background=SURFACE_MUTED,
            width=96,
            height=28,
            font=app_font(9, "bold"),
        )
        self.characteristic_reset_button.pack(
            side="left",
            padx=(6, 0),
        )

        self.update_focus_controls()
        self.update_blood_status_control()
        self.update_parental_controls()
        self.update_initial_bonus_controls()
        self.update_characteristic_points()
        self.update_school_progress_controls()
        self.update_initial_values_completion()

    def set_person(self, person):
        person_values = person if isinstance(person, dict) else {}
        plan = normalize_development_plan(
            person_values.get("development_plan"),
            default_schema="Scattershot",
        )
        self.loading = True
        self.current_person = deepcopy(person_values)
        self.development_plan = deepcopy(plan)
        self.academic_years_advanced = plan[
            "academic_years_advanced"
        ]
        self.school_started = plan["school_started"]
        self.active_year_tab = 0
        self.strategy_value.set(plan["schema"])
        self.blood_status_value.set(
            resolved_blood_status(
                person_values,
                self.available_people(),
            )
        )
        self.developmental_environment_value.set(
            resolved_developmental_environment(
                person_values,
                self.available_people(),
            )
            or DEVELOPMENTAL_ENVIRONMENT_MAGICAL
        )
        self.parental_values = normalize_parental_values(
            person_values.get("parental_values")
        )
        self.initial_bonuses = normalize_initial_bonuses(
            person_values.get("initial_bonuses")
        )
        self.characteristics = normalize_characteristics(
            person_values.get("characteristics")
        )

        if self.parental_values is not None:
            self.parental_values = rebase_parental_values(
                self.current_person,
                self.available_people(),
                self.parental_values,
            )
            self.current_person["parental_values"] = deepcopy(
                self.parental_values
            )

        self.apply_parental_values_to_controls()
        focused_skills = plan.get("focused_skills", [])

        for index, skill_value in enumerate(self.skill_values):
            selected_skill = (
                focused_skills[index]
                if index < len(focused_skills)
                else DEVELOPMENT_SKILL_OPTIONS[index]
            )
            skill_value.set(selected_skill)

        self.ability_value.set(
            plan.get(
                "focused_ability",
                DEVELOPMENT_ABILITY_OPTIONS[0],
            )
        )
        self.birth_year = person_values.get("birth_year")
        self.birth_month = person_values.get("birth_month")
        self.birth_day = person_values.get("birth_day")
        self.school_field.set_value(person_values.get("school", ""))
        self.update_start_year()
        self.update_focus_controls()
        self.update_blood_status_control()
        self.update_parental_controls()
        self.update_initial_bonus_controls()
        self.set_characteristic_controls()
        self.update_school_progress_controls()
        self.update_initial_values_completion()
        self.loading = False

    def activate(self):
        if not self.current_person.get("record_id"):
            return False

        previous_loading = self.loading
        self.loading = True
        changed = False

        if self.parental_values is None:
            self.parental_values = initialize_parental_values(
                self.current_person,
                self.available_people(),
            )
            self.current_person["parental_values"] = deepcopy(
                self.parental_values
            )
            self.apply_parental_values_to_controls()
            changed = True

        if hasattr(self, "initial_bonuses"):
            previous_bonuses = deepcopy(self.initial_bonuses)
            self.initial_bonuses = reconcile_initial_bonuses(
                self.initial_bonuses,
                self.initial_bonus_person_values(),
                self.current_development_plan(),
            )
            self.current_person["initial_bonuses"] = deepcopy(
                self.initial_bonuses
            )
            changed = (
                changed
                or previous_bonuses != self.initial_bonuses
            )

        if getattr(self, "characteristics", None) is None:
            self.characteristics = randomized_characteristics()
            self.current_person["characteristics"] = deepcopy(
                self.characteristics
            )

            if hasattr(self, "characteristic_variables"):
                self.set_characteristic_controls()

            changed = True

        self.update_parental_controls()
        self.update_initial_bonus_controls()
        self.update_initial_values_completion()
        self.loading = previous_loading
        return changed

    def set_birth_date(self, birth_year, birth_month, birth_day):
        self.birth_year = birth_year
        self.birth_month = birth_month
        self.birth_day = birth_day
        self.current_person["birth_year"] = birth_year
        self.current_person["birth_month"] = birth_month
        self.current_person["birth_day"] = birth_day
        self.update_start_year()

        if self.parental_values is not None:
            previous_loading = self.loading
            self.loading = True
            self.parental_values = rebase_parental_values(
                self.current_person,
                self.available_people(),
                self.parental_values,
            )
            self.current_person["parental_values"] = deepcopy(
                self.parental_values
            )
            self.apply_parental_values_to_controls()
            self.update_parental_controls()
            self.reconcile_initial_bonus_assignments()
            self.loading = previous_loading
        else:
            self.update_parental_handling_menu()

    def set_parentage(self, relationship_values):
        if not isinstance(relationship_values, dict):
            return

        previous_loading = self.loading
        self.loading = True

        for field_name in (
            "biological_mother_id",
            "biological_father_id",
            "biological_mother_status",
            "biological_father_status",
        ):
            if field_name in relationship_values:
                self.current_person[field_name] = relationship_values[
                    field_name
                ]

        self.update_blood_status_control()

        if self.parental_values is not None:
            if (
                self.parental_mode_value.get()
                == PARENTAL_MODE_OVERRIDE
            ):
                try:
                    self.parental_values = (
                        self.parental_values_from_controls()
                    )
                except (TypeError, ValueError):
                    pass

            self.parental_values = rebase_parental_values(
                self.current_person,
                self.available_people(),
                self.parental_values,
            )
            self.current_person["parental_values"] = deepcopy(
                self.parental_values
            )
            self.apply_parental_values_to_controls()
            self.update_parental_controls()
            self.reconcile_initial_bonus_assignments()

        self.loading = previous_loading

    def get_values(self):
        plan = self.current_development_plan()
        blood_status = normalize_blood_status(
            self.blood_status_value.get()
        )
        parental_values = self.parental_values_from_controls()
        developmental_environment = normalize_developmental_environment(
            self.developmental_environment_value.get(),
            blood_status,
        )

        if self.initial_bonuses is not None:
            previous_loading = self.loading
            self.loading = True
            self.current_person["blood_status"] = blood_status
            self.current_person["developmental_environment"] = (
                developmental_environment
            )
            self.current_person["parental_values"] = deepcopy(
                parental_values
            )
            self.reconcile_initial_bonus_assignments()
            self.loading = previous_loading

        return {
            "school": self.school_field.get_value(),
            "blood_status": blood_status,
            "developmental_environment": developmental_environment,
            "parental_values": parental_values,
            "initial_bonuses": deepcopy(self.initial_bonuses),
            "characteristics": deepcopy(self.characteristics),
            "development_plan": plan,
        }

    def current_development_plan(self):
        plan = deepcopy(self.development_plan)
        schema = self.strategy_value.get()
        plan["schema"] = schema
        plan["academic_years_advanced"] = (
            self.academic_years_advanced
        )
        plan["school_started"] = bool(
            getattr(self, "school_started", False)
        )
        required_skill_count = development_skill_count(schema)

        if required_skill_count:
            plan["focused_skills"] = [
                skill_value.get()
                for skill_value in self.skill_values[
                    :required_skill_count
                ]
            ]
            plan.pop("focused_ability", None)
        elif schema == "Ability-focus":
            plan["focused_ability"] = self.ability_value.get()
            plan.pop("focused_skills", None)
        else:
            plan.pop("focused_skills", None)
            plan.pop("focused_ability", None)

        return normalize_development_plan(plan)

    def parental_values_from_controls(self):
        if self.parental_values is None:
            return None

        stored_parental_values = deepcopy(self.parental_values)
        stored_parental_values["mode"] = (
            self.parental_mode_value.get()
        )

        for field_name in PARENTAL_VALUE_NAMES:
            stored_parental_values[field_name] = (
                self.parental_value_variables[
                    field_name
                ].get()
            )

        return normalize_parental_values(
            stored_parental_values,
            allow_uninitialized=False,
        )

    def school_changed(self):
        self.notify_change()

    def strategy_changed(self, *arguments):
        if self.loading:
            return

        randomized_plan = randomized_development_plan(
            years_advanced=self.academic_years_advanced,
            selected_schema=self.strategy_value.get(),
            school_started=self.school_started,
        )
        self.loading = True
        self.development_plan = deepcopy(randomized_plan)
        focused_skills = randomized_plan.get("focused_skills", [])

        for index, skill_value in enumerate(self.skill_values):
            selected_skill = (
                focused_skills[index]
                if index < len(focused_skills)
                else DEVELOPMENT_SKILL_OPTIONS[index]
            )
            skill_value.set(selected_skill)

        self.ability_value.set(
            randomized_plan.get(
                "focused_ability",
                DEVELOPMENT_ABILITY_OPTIONS[0],
            )
        )
        self.update_focus_controls()
        self.reconcile_initial_bonus_assignments(
            refresh_automatic=True
        )
        self.loading = False
        self.notify_change()

    def blood_status_changed(self, *arguments):
        if self.loading:
            return

        self.current_person["blood_status"] = normalize_blood_status(
            self.blood_status_value.get()
        )
        self.update_blood_status_control()
        self.reconcile_initial_bonus_assignments()
        self.notify_change()

    def developmental_environment_changed(self, *arguments):
        if self.loading:
            return

        self.current_person["developmental_environment"] = (
            normalize_developmental_environment(
                self.developmental_environment_value.get(),
                self.blood_status_value.get(),
            )
        )
        self.reconcile_initial_bonus_assignments()
        self.notify_change()

    def parental_mode_changed(self, *arguments):
        if self.loading or self.parental_values is None:
            return

        self.loading = True
        self.parental_values = parental_values_for_mode(
            self.current_person,
            self.available_people(),
            self.parental_values,
            self.parental_mode_value.get(),
        )
        self.current_person["parental_values"] = deepcopy(
            self.parental_values
        )
        self.apply_parental_values_to_controls()
        self.update_parental_controls()
        self.reconcile_initial_bonus_assignments()
        self.loading = False
        self.notify_change()

    def parental_value_changed(self, *arguments):
        if (
            self.loading
            or self.parental_values is None
            or self.parental_mode_value.get()
            != PARENTAL_MODE_OVERRIDE
        ):
            return

        try:
            self.parental_values = self.parental_values_from_controls()
        except (TypeError, ValueError):
            self.notify_change()
            return

        self.current_person["parental_values"] = deepcopy(
            self.parental_values
        )
        self.reconcile_initial_bonus_assignments()
        self.notify_change()

    def update_start_year(self):
        start_year = calculate_school_start_year(
            self.birth_year,
            self.birth_month,
            self.birth_day,
        )
        self.start_year_value.set(
            "Unknown" if start_year is None else str(start_year)
        )

    def set_characteristic_controls(self):
        stored_values = (
            self.characteristics
            if self.characteristics is not None
            else {
                field_name: CHARACTERISTIC_BASE_VALUE
                for field_name in CHARACTERISTIC_NAMES
            }
        )
        previous_loading = self.loading
        self.loading = True
        self.characteristics_editing = self.characteristics is None

        for field_name in CHARACTERISTIC_NAMES:
            self.characteristic_variables[field_name].set(
                stored_values[field_name]
            )

        self.loading = previous_loading
        self.update_characteristic_points()

    def characteristic_changed(self, field_name, raw_value):
        if self.loading or field_name not in CHARACTERISTIC_NAMES:
            return

        try:
            requested_value = int(round(float(raw_value)))
        except (TypeError, ValueError):
            requested_value = CHARACTERISTIC_BASE_VALUE

        other_total = sum(
            self.characteristic_variables[
                other_field
            ].get()
            for other_field in CHARACTERISTIC_NAMES
            if other_field != field_name
        )
        maximum_available = min(
            CHARACTERISTIC_MAXIMUM_VALUE,
            CHARACTERISTIC_REQUIRED_TOTAL - other_total,
        )
        normalized_value = max(
            CHARACTERISTIC_BASE_VALUE,
            min(requested_value, maximum_available),
        )

        if (
            self.characteristic_variables[field_name].get()
            != normalized_value
        ):
            previous_loading = self.loading
            self.loading = True
            self.characteristic_variables[field_name].set(
                normalized_value
            )
            self.loading = previous_loading

        self.update_characteristic_points()

    def adjust_characteristic(self, field_name, delta):
        if self.loading or field_name not in CHARACTERISTIC_NAMES:
            return

        try:
            current_value = int(
                self.characteristic_variables[field_name].get()
            )
            adjustment = int(delta)
        except (TypeError, ValueError):
            current_value = CHARACTERISTIC_BASE_VALUE
            adjustment = 0

        self.characteristic_changed(
            field_name,
            current_value + adjustment,
        )

    def update_characteristic_points(self):
        if not hasattr(self, "characteristic_submit_button"):
            return

        draft_values = {
            field_name: self.characteristic_variables[
                field_name
            ].get()
            for field_name in CHARACTERISTIC_NAMES
        }
        remaining_points = characteristic_points_remaining(
            draft_values
        )
        editing = bool(
            getattr(self, "characteristics_editing", True)
        )

        if not editing:
            point_text = (
                f"All {CHARACTERISTIC_POINTS_TO_SPEND} "
                "points assigned"
            )
        elif remaining_points == 0:
            point_text = (
                f"All {CHARACTERISTIC_POINTS_TO_SPEND} "
                "points assigned"
            )
        elif remaining_points == 1:
            point_text = "1 point to spend"
        else:
            point_text = f"{remaining_points} points to spend"

        self.characteristic_points_value.set(point_text)
        self.characteristic_submit_button.set_text(
            "Save" if editing else "Edit"
        )
        self.characteristic_submit_button.set_enabled(
            not editing or remaining_points == 0
        )
        reset_button = getattr(
            self,
            "characteristic_reset_button",
            None,
        )

        if reset_button is not None:
            if editing:
                reset_button.pack(
                    side="left",
                    padx=(6, 0),
                )
            else:
                reset_button.pack_forget()

        decrease_buttons = getattr(
            self,
            "characteristic_decrease_buttons",
            {},
        )
        increase_buttons = getattr(
            self,
            "characteristic_increase_buttons",
            {},
        )
        value_labels = getattr(
            self,
            "characteristic_value_labels",
            {},
        )

        for field_name in CHARACTERISTIC_NAMES:
            current_value = draft_values[field_name]
            decrease_button = decrease_buttons.get(field_name)
            increase_button = increase_buttons.get(field_name)
            value_label = value_labels.get(field_name)

            if decrease_button is not None:
                if editing:
                    decrease_button.grid()
                    decrease_button.set_enabled(
                        current_value > CHARACTERISTIC_BASE_VALUE
                    )
                else:
                    decrease_button.grid_remove()

            if increase_button is not None:
                if editing:
                    increase_button.grid()
                    increase_button.set_enabled(
                        current_value
                        < CHARACTERISTIC_MAXIMUM_VALUE
                        and remaining_points > 0
                    )
                else:
                    increase_button.grid_remove()

            if value_label is not None:
                value_label.configure(
                    bg=(
                        FIELD_BACKGROUND
                        if editing
                        else SURFACE_MUTED
                    ),
                    highlightthickness=1 if editing else 0,
                    padx=3 if editing else 0,
                    pady=2 if editing else 0,
                )

    def handle_characteristics_action(self):
        if not self.characteristics_editing:
            self.characteristics_editing = True
            self.update_characteristic_points()
            return

        self.submit_characteristics()

    def submit_characteristics(self):
        draft_values = {
            field_name: self.characteristic_variables[
                field_name
            ].get()
            for field_name in CHARACTERISTIC_NAMES
        }

        try:
            submitted_values = normalize_characteristics(
                draft_values,
                allow_uninitialized=False,
            )
        except (TypeError, ValueError):
            self.update_characteristic_points()
            return

        self.characteristics = submitted_values
        self.current_person["characteristics"] = deepcopy(
            submitted_values
        )
        self.characteristics_editing = False
        self.update_characteristic_points()
        self.update_initial_values_completion()
        self.notify_change()

    def reset_characteristics(self):
        previous_loading = self.loading
        self.loading = True

        for field_name in CHARACTERISTIC_NAMES:
            self.characteristic_variables[field_name].set(
                CHARACTERISTIC_BASE_VALUE
            )

        self.characteristics = None
        self.current_person["characteristics"] = None
        self.characteristics_editing = True
        self.loading = previous_loading
        self.update_characteristic_points()
        self.update_initial_values_completion()
        self.notify_change()

    def school_progress_display_text(self):
        return school_progress_text(
            self.school_started,
            self.academic_years_advanced,
        )

    def update_school_progress_controls(
        self,
        select_latest=False,
    ):
        self.academic_years_advanced = (
            normalize_academic_years_advanced(
                self.academic_years_advanced
            )
        )
        self.school_started = normalize_school_started(
            self.school_started,
            self.academic_years_advanced,
        )
        visible_years = visible_school_year_count(
            self.school_started,
            self.academic_years_advanced,
        )
        graduated = (
            self.academic_years_advanced
            >= ACADEMIC_YEARS_TO_ADULTHOOD
        )

        if hasattr(self, "advance_year_button"):
            self.advance_year_button.set_text(
                "Start school"
                if not self.school_started
                else "Advance one year"
                if not graduated
                else "Graduated"
            )
            self.advance_year_button.set_enabled(not graduated)

        if hasattr(self, "advance_adulthood_button"):
            self.advance_adulthood_button.set_enabled(
                not graduated
            )

        if hasattr(self, "remove_year_button"):
            self.remove_year_button.set_text(
                f"Remove Year {visible_years}"
                if visible_years
                else "Remove latest year"
            )
            self.remove_year_button.set_enabled(
                visible_years > 0
            )

        if not hasattr(self, "year_tabs_container"):
            return

        for year_number, year_button in (
            self.year_tab_buttons.items()
        ):
            if year_number <= visible_years:
                year_button.grid()
            else:
                year_button.grid_remove()

        if visible_years == 0:
            self.active_year_tab = 0
            self.year_tabs_container.grid_remove()
            return

        self.year_tabs_container.grid()

        if (
            select_latest
            or self.active_year_tab < 1
            or self.active_year_tab > visible_years
        ):
            self.active_year_tab = visible_years

        self.select_year_tab(self.active_year_tab)

    def select_year_tab(self, year_number):
        visible_years = visible_school_year_count(
            self.school_started,
            self.academic_years_advanced,
        )

        if not 1 <= int(year_number) <= visible_years:
            return

        self.active_year_tab = int(year_number)
        self.year_placeholder_value.set(
            f"Year {self.active_year_tab} development details "
            "will be added here."
        )

        for tab_year, year_button in self.year_tab_buttons.items():
            if tab_year == self.active_year_tab:
                year_button.set_colors(
                    PRIMARY,
                    PRIMARY_HOVER,
                    TEXT_DARK,
                )
            else:
                year_button.set_colors(
                    BUTTON_SOFT,
                    BUTTON_SOFT_HOVER,
                    TEXT_DARK,
                )

    def monthly_allowance_text(self):
        selected_traits = (
            list(self.initial_bonuses["traits"])
            if self.initial_bonuses is not None
            else []
        )
        total_sickles = allowance_sickles(
            self.parental_values,
            selected_traits,
        )
        allowance_text = format_wizard_currency(total_sickles)
        frugal_text = (
            " (includes Frugal)"
            if "Frugal" in selected_traits
            else ""
        )
        return f"{allowance_text}{frugal_text}"

    def initial_values_complete(self):
        person_values = self.initial_bonus_person_values()
        person_values["initial_bonuses"] = deepcopy(
            self.initial_bonuses
        )
        person_values["characteristics"] = deepcopy(
            self.characteristics
        )
        return initial_values_are_complete(person_values)

    def update_initial_values_completion(self):
        if not hasattr(self, "initial_values_panel"):
            return True

        complete = (
            True
            if not self.current_person.get("record_id")
            else self.initial_values_complete()
        )
        self.initial_values_panel.configure(
            highlightbackground=(
                BORDER_SOFT if complete else LOCKED_BORDER
            ),
            highlightthickness=2,
        )
        return complete

    def randomly_select_strategy(self):
        randomized_plan = randomized_development_plan(
            self.strategy_value.get(),
            self.academic_years_advanced,
            school_started=self.school_started,
        )
        self.loading = True
        self.development_plan = deepcopy(randomized_plan)
        self.strategy_value.set(randomized_plan["schema"])
        focused_skills = randomized_plan.get("focused_skills", [])

        for index, skill_value in enumerate(self.skill_values):
            selected_skill = (
                focused_skills[index]
                if index < len(focused_skills)
                else DEVELOPMENT_SKILL_OPTIONS[index]
            )
            skill_value.set(selected_skill)

        self.ability_value.set(
            randomized_plan.get(
                "focused_ability",
                DEVELOPMENT_ABILITY_OPTIONS[0],
            )
        )
        self.update_focus_controls()
        self.reconcile_initial_bonus_assignments(
            refresh_automatic=True
        )
        self.loading = False
        self.notify_change()

    def advance_one_year(self):
        completed_years = normalize_academic_years_advanced(
            self.academic_years_advanced
        )

        if not bool(getattr(self, "school_started", False)):
            self.school_started = True
        elif completed_years < ACADEMIC_YEARS_TO_ADULTHOOD:
            self.academic_years_advanced = completed_years + 1

        self.update_school_progress_controls(
            select_latest=True
        )
        self.notify_change()

    def advance_to_adulthood(self):
        self.school_started = True
        self.academic_years_advanced = (
            ACADEMIC_YEARS_TO_ADULTHOOD
        )
        self.update_school_progress_controls(
            select_latest=True
        )
        self.notify_change()

    def remove_latest_school_year(self):
        visible_years = visible_school_year_count(
            self.school_started,
            self.academic_years_advanced,
        )

        if visible_years == 0:
            return

        remaining_years = visible_years - 1

        if remaining_years == 0:
            self.school_started = False
            self.academic_years_advanced = 0
        else:
            self.school_started = True
            self.academic_years_advanced = remaining_years - 1

        self.update_school_progress_controls(
            select_latest=True
        )
        self.notify_change()

    def focus_selection_changed(self, *arguments):
        if self.loading:
            return

        self.loading = True

        if development_skill_count(self.strategy_value.get()):
            self.update_skill_options()

        self.reconcile_initial_bonus_assignments(
            refresh_automatic=True
        )
        self.loading = False
        self.notify_change()

    def update_focus_controls(self):
        schema = self.strategy_value.get()
        required_skill_count = development_skill_count(schema)

        if required_skill_count:
            self.focus_frame.grid()
            self.ability_block.grid_remove()
            self.skill_labels[0].configure(
                text=(
                    "Skill"
                    if required_skill_count == 1
                    else "Skill 1"
                )
            )

            for index, skill_block in enumerate(self.skill_blocks):
                if index < required_skill_count:
                    skill_block.grid()
                else:
                    skill_block.grid_remove()

            self.update_skill_options()
            return

        for skill_block in self.skill_blocks:
            skill_block.grid_remove()

        if schema == "Ability-focus":
            self.focus_frame.grid()
            self.ability_block.grid()
        else:
            self.ability_block.grid_remove()
            self.focus_frame.grid_remove()

    def update_skill_options(self):
        active_skill_count = len(self.skill_values)

        if hasattr(self, "strategy_value"):
            try:
                active_skill_count = development_skill_count(
                    self.strategy_value.get()
                )
            except ValueError:
                active_skill_count = len(self.skill_values)

        active_skill_count = max(
            0,
            min(active_skill_count, len(self.skill_values)),
        )
        selected_skills = []

        for skill_value in self.skill_values[:active_skill_count]:
            selected_skill = skill_value.get()

            if (
                selected_skill not in DEVELOPMENT_SKILL_OPTIONS
                or selected_skill in selected_skills
            ):
                selected_skill = next(
                    skill
                    for skill in DEVELOPMENT_SKILL_OPTIONS
                    if skill not in selected_skills
                )
                skill_value.set(selected_skill)

            selected_skills.append(selected_skill)

        for index, skill_select in enumerate(self.skill_selects):
            if index >= active_skill_count:
                skill_select.set_values(DEVELOPMENT_SKILL_OPTIONS)
                continue

            selected_by_other_controls = {
                self.skill_values[other_index].get()
                for other_index in range(active_skill_count)
                if other_index != index
            }
            available_skills = [
                skill
                for skill in DEVELOPMENT_SKILL_OPTIONS
                if skill not in selected_by_other_controls
            ]
            skill_select.set_values(available_skills)

    def apply_parental_values_to_controls(self):
        if not hasattr(self, "parental_value_variables"):
            return

        if self.parental_values is None:
            self.parental_mode_value.set(PARENTAL_MODE_SHARED)

            for parental_value in self.parental_value_variables.values():
                parental_value.set("")

            return

        self.parental_mode_value.set(
            self.parental_values["mode"]
        )

        for field_name in PARENTAL_VALUE_NAMES:
            self.parental_value_variables[field_name].set(
                str(self.parental_values[field_name])
            )

    def update_parental_controls(self):
        if not hasattr(self, "parental_handling_button"):
            return

        self.update_parental_handling_menu()
        initialized = self.parental_values is not None
        self.parental_handling_button.set_enabled(initialized)
        entries_are_editable = (
            initialized
            and self.parental_mode_value.get()
            == PARENTAL_MODE_OVERRIDE
        )

        for entry in self.parental_value_entries.values():
            entry.set_enabled(entries_are_editable)

    def update_parental_handling_menu(self):
        if not hasattr(self, "parental_handling_menu"):
            return

        self.parental_handling_menu.delete(0, "end")
        sibling = parental_sibling_reference(
            self.current_person,
            self.available_people(),
            excluded_record_id=self.current_person.get("record_id"),
        )

        if sibling is not None:
            sibling_name = str(
                sibling.get("displayed_name", "") or ""
            ).strip()
            self.parental_handling_menu.add_radiobutton(
                label=f"Base on {sibling_name}",
                variable=self.parental_mode_value,
                value=PARENTAL_MODE_SHARED,
            )

        for parental_mode in (
            PARENTAL_MODE_SLIGHTLY_RANDOMIZED,
            PARENTAL_MODE_FULLY_RANDOMIZED,
            PARENTAL_MODE_OVERRIDE,
        ):
            self.parental_handling_menu.add_radiobutton(
                label=parental_mode,
                variable=self.parental_mode_value,
                value=parental_mode,
            )

    def initial_bonus_person_values(self):
        person_values = deepcopy(self.current_person)
        person_values["blood_status"] = normalize_blood_status(
            self.blood_status_value.get()
        )
        person_values["developmental_environment"] = (
            normalize_developmental_environment(
                self.developmental_environment_value.get(),
                person_values["blood_status"],
            )
        )
        person_values["parental_values"] = deepcopy(
            self.parental_values
        )
        return person_values

    def reconcile_initial_bonus_assignments(
        self,
        refresh_automatic=False,
    ):
        if self.initial_bonuses is None:
            self.update_initial_bonus_controls()
            return False

        previous_bonuses = deepcopy(self.initial_bonuses)
        self.initial_bonuses = reconcile_initial_bonuses(
            self.initial_bonuses,
            self.initial_bonus_person_values(),
            self.current_development_plan(),
            refresh_automatic=refresh_automatic,
        )
        self.current_person["initial_bonuses"] = deepcopy(
            self.initial_bonuses
        )
        self.update_initial_bonus_controls()
        return previous_bonuses != self.initial_bonuses

    def update_initial_bonus_controls(self):
        if not hasattr(self, "skill_bonus_summary_value"):
            return

        requirements = initial_bonus_requirements(
            self.blood_status_value.get(),
            self.developmental_environment_value.get(),
            self.parental_values,
        )
        skill_count = requirements["skill_bonus_count"]
        trait_count = requirements["trait_count"]
        muggles_bonus = requirements["muggles_skill_bonus"]
        selected_skills = (
            list(self.initial_bonuses["skill_bonuses"])
            if self.initial_bonuses is not None
            else []
        )
        selected_traits = (
            list(self.initial_bonuses["traits"])
            if self.initial_bonuses is not None
            else []
        )

        if skill_count == 0:
            self.skill_bonus_summary_value.set(
                "No initial skill bonuses"
            )
            self.skill_bonus_button.grid_remove()
        else:
            skill_label = (
                "initial skill bonus"
                if skill_count == 1
                else "initial skill bonuses"
            )
            selected_skill_text = (
                summarize_initial_skill_bonuses(
                    selected_skills
                )
            )
            selected_text = (
                f": {selected_skill_text}"
                if selected_skill_text
                else ""
            )
            self.skill_bonus_summary_value.set(
                f"+{skill_count} {skill_label}{selected_text}"
            )
            self.skill_bonus_button.grid()
            self.skill_bonus_button.set_enabled(
                self.initial_bonuses is not None
            )

        if trait_count == 0:
            self.trait_summary_value.set("No traits")
            self.trait_button.grid_remove()
        else:
            trait_label = "trait" if trait_count == 1 else "traits"
            selected_text = (
                "\n"
                + "\n".join(
                    f"{trait_name}: "
                    f"{trait_effect_text(trait_name)}"
                    for trait_name in selected_traits
                )
                if selected_traits
                else ""
            )
            self.trait_summary_value.set(
                f"{trait_count} {trait_label}{selected_text}"
            )
            self.trait_button.grid()
            self.trait_button.set_enabled(
                self.initial_bonuses is not None
            )

        if muggles_bonus:
            self.muggles_bonus_summary_value.set(
                f"+{muggles_bonus} Muggles skill"
            )
            self.muggles_bonus_summary.grid()
        else:
            self.muggles_bonus_summary_value.set("")
            self.muggles_bonus_summary.grid_remove()

        self.update_initial_values_completion()

    def open_initial_skill_bonus_dialog(self):
        if self.initial_bonuses is None:
            return

        requirements = initial_bonus_requirements(
            self.blood_status_value.get(),
            self.developmental_environment_value.get(),
            self.parental_values,
        )
        required_count = requirements["skill_bonus_count"]

        if required_count <= 0:
            return

        InitialSkillBonusDialog(
            self,
            required_count,
            self.initial_bonuses["skill_bonuses"],
            self.save_initial_skill_bonuses,
        )

    def save_initial_skill_bonuses(self, selected_skills):
        if self.initial_bonuses is None:
            return

        requirements = initial_bonus_requirements(
            self.blood_status_value.get(),
            self.developmental_environment_value.get(),
            self.parental_values,
        )
        required_count = requirements["skill_bonus_count"]
        normalized_bonuses = deepcopy(self.initial_bonuses)
        normalized_bonuses["skill_selection_mode"] = (
            INITIAL_SELECTION_MANUAL
        )
        normalized_bonuses["skill_bonuses"] = list(
            selected_skills
        )
        normalized_bonuses = normalize_initial_bonuses(
            normalized_bonuses,
            allow_uninitialized=False,
        )

        if len(normalized_bonuses["skill_bonuses"]) != required_count:
            raise ValueError(
                f"Select exactly {required_count} initial skills."
            )

        self.initial_bonuses = normalized_bonuses
        self.current_person["initial_bonuses"] = deepcopy(
            self.initial_bonuses
        )
        self.update_initial_bonus_controls()
        self.notify_change()

    def open_trait_dialog(self):
        if self.initial_bonuses is None:
            return

        requirements = initial_bonus_requirements(
            self.blood_status_value.get(),
            self.developmental_environment_value.get(),
            self.parental_values,
        )
        required_count = requirements["trait_count"]

        if required_count <= 0:
            return

        TraitSelectionDialog(
            self,
            required_count,
            self.initial_bonuses["traits"],
            self.save_initial_traits,
        )

    def save_initial_traits(self, selected_traits):
        if self.initial_bonuses is None:
            return

        requirements = initial_bonus_requirements(
            self.blood_status_value.get(),
            self.developmental_environment_value.get(),
            self.parental_values,
        )
        required_count = requirements["trait_count"]
        normalized_bonuses = deepcopy(self.initial_bonuses)
        normalized_bonuses["trait_selection_mode"] = (
            INITIAL_SELECTION_MANUAL
        )
        normalized_bonuses["traits"] = list(selected_traits)
        normalized_bonuses = normalize_initial_bonuses(
            normalized_bonuses,
            allow_uninitialized=False,
        )

        if len(normalized_bonuses["traits"]) != required_count:
            raise ValueError(
                f"Select exactly {required_count} initial traits."
            )

        self.initial_bonuses = normalized_bonuses
        self.current_person["initial_bonuses"] = deepcopy(
            self.initial_bonuses
        )
        self.update_initial_bonus_controls()
        self.notify_change()

    def available_people(self):
        if self.people_provider is None:
            return []

        people = self.people_provider()
        return list(people) if people is not None else []

    def update_blood_status_control(self):
        available_people = self.available_people()
        available_options = blood_status_options(
            self.current_person,
            available_people,
        )
        selected_status = resolved_blood_status(
            {
                **self.current_person,
                "blood_status": self.blood_status_value.get(),
            },
            available_people,
        )
        previous_loading = self.loading
        self.loading = True
        self.blood_status_value.set(selected_status)
        self.current_person["blood_status"] = selected_status
        selected_environment = normalize_developmental_environment(
            (
                self.developmental_environment_value.get()
                or self.current_person.get(
                    "developmental_environment",
                    "",
                )
            ),
            selected_status,
        )
        self.current_person["developmental_environment"] = (
            selected_environment
        )

        if selected_environment:
            self.developmental_environment_value.set(
                selected_environment
            )

        if hasattr(self, "blood_status_select"):
            self.blood_status_select.set_values(available_options)

            if len(available_options) == 1:
                self.blood_status_select.grid_remove()
                self.blood_status_text.grid()
            else:
                self.blood_status_text.grid_remove()
                self.blood_status_select.grid()

        if hasattr(self, "environment_block"):
            if selected_status == BLOOD_STATUS_HALFBLOOD:
                self.environment_block.grid()
            else:
                self.environment_block.grid_remove()

        self.loading = previous_loading

    def show_parental_handling_menu(self):
        self.update_idletasks()

        try:
            self.parental_handling_menu.tk_popup(
                self.parental_handling_button.winfo_rootx(),
                (
                    self.parental_handling_button.winfo_rooty()
                    + self.parental_handling_button.winfo_height()
                ),
            )
        finally:
            self.parental_handling_menu.grab_release()

    def school_display_text(self):
        school_name = self.school_field.get_value()
        return school_name if school_name else "none"

    def focus_school(self):
        self.school_field.open_selector()

    def notify_change(self):
        if not self.loading and self.change_command is not None:
            self.change_command()
