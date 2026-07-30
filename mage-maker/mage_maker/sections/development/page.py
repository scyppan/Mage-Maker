import tkinter as tk
from copy import deepcopy

from mage_maker.sections.development.models import (
    DEVELOPMENT_ABILITY_OPTIONS,
    DEVELOPMENT_SCHEMA_OPTIONS,
    DEVELOPMENT_SKILL_OPTIONS,
    calculate_school_start_year,
    development_skill_count,
    normalize_academic_years_advanced,
    normalize_development_plan,
    randomized_development_plan,
)
from mage_maker.sections.profile.school_field import SchoolField
from mage_maker.ui.theme import (
    FIELD_BACKGROUND,
    LIST_HOVER,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import (
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
    ):
        super().__init__(parent, bg=SURFACE)
        self.game_database = game_database
        self.change_command = change_command
        self.loading = False
        self.birth_year = None
        self.birth_month = None
        self.birth_day = None
        self.development_plan = {
            "schema": "Scattershot",
            "academic_years_advanced": 0,
        }
        self.academic_years_advanced = 0
        self.start_year_value = tk.StringVar(value="Unknown")
        self.strategy_value = tk.StringVar(value="Scattershot")
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

        for skill_value in self.skill_values:
            skill_value.trace_add(
                "write",
                self.focus_selection_changed,
            )

        self.ability_value.trace_add(
            "write",
            self.focus_selection_changed,
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

        self.actions_button = SoftButton(
            header,
            text="Actions ▾",
            command=self.show_actions_menu,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=112,
            height=38,
        )
        self.actions_button.grid(row=0, column=1, sticky="e")

        self.actions_menu = tk.Menu(
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
        self.actions_menu.add_command(
            label="Randomly select development strategy",
            command=self.randomly_select_strategy,
        )
        self.actions_menu.add_command(
            label="Advance one year",
            command=self.advance_one_year,
        )

    def build_plan_panel(self):
        plan_panel = SectionPanel(
            self,
            "Development details",
            (
                "All schools begin on September 1. Students start at age 11 "
                "at the cutoff. The strategy guides automated development "
                "decisions for this individual."
            ),
        )
        plan_panel.grid(
            row=1,
            column=0,
            sticky="nsew",
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

        school_names = (
            self.game_database.school_names()
            if self.game_database is not None
            and self.game_database.loaded
            else []
        )
        self.school_field = SchoolField(
            academic_row,
            school_names,
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
            plan_panel.content,
            bg=SURFACE_MUTED,
        )
        strategy_block.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(20, 0),
        )
        strategy_block.grid_columnconfigure(0, weight=1)
        strategy_label = tk.Label(
            strategy_block,
            text="Strategy",
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
            width=320,
            height=42,
            font=app_font(11),
        )
        self.strategy_select.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self.focus_frame = tk.Frame(
            plan_panel.content,
            bg=SURFACE_MUTED,
        )
        self.focus_frame.grid(
            row=2,
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
                width=240,
                height=40,
                font=app_font(10),
            )
            skill_select.grid(
                row=1,
                column=0,
                sticky="ew",
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
            width=240,
            height=40,
            font=app_font(10),
        )
        self.ability_select.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self.update_focus_controls()

    def set_person(self, person):
        person_values = person if isinstance(person, dict) else {}
        plan = normalize_development_plan(
            person_values.get("development_plan"),
            default_schema="Scattershot",
        )
        self.loading = True
        self.development_plan = deepcopy(plan)
        self.academic_years_advanced = plan[
            "academic_years_advanced"
        ]
        self.strategy_value.set(plan["schema"])
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
        self.loading = False

    def set_birth_date(self, birth_year, birth_month, birth_day):
        self.birth_year = birth_year
        self.birth_month = birth_month
        self.birth_day = birth_day
        self.update_start_year()

    def get_values(self):
        plan = deepcopy(self.development_plan)
        schema = self.strategy_value.get()
        plan["schema"] = schema
        plan["academic_years_advanced"] = (
            self.academic_years_advanced
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

        return {
            "school": self.school_field.get_value(),
            "development_plan": normalize_development_plan(plan),
        }

    def school_changed(self):
        self.notify_change()

    def strategy_changed(self, *arguments):
        if self.loading:
            return

        self.loading = True
        self.update_focus_controls()
        self.loading = False
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

    def randomly_select_strategy(self):
        randomized_plan = randomized_development_plan(
            self.strategy_value.get(),
            self.academic_years_advanced,
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
        self.loading = False
        self.notify_change()

    def advance_one_year(self):
        self.academic_years_advanced = (
            normalize_academic_years_advanced(
                self.academic_years_advanced
            )
            + 1
        )
        self.notify_change()

    def focus_selection_changed(self, *arguments):
        if self.loading:
            return

        self.loading = True

        if development_skill_count(self.strategy_value.get()):
            self.update_skill_options()

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
        selected_skills = []

        for index, skill_select in enumerate(self.skill_selects):
            available_skills = [
                skill
                for skill in DEVELOPMENT_SKILL_OPTIONS
                if skill not in selected_skills
            ]
            skill_select.set_values(available_skills)
            selected_skill = self.skill_values[index].get()

            if selected_skill not in available_skills:
                selected_skill = available_skills[0]
                self.skill_values[index].set(selected_skill)

            selected_skills.append(selected_skill)

    def show_actions_menu(self):
        self.update_idletasks()

        try:
            self.actions_menu.tk_popup(
                self.actions_button.winfo_rootx(),
                (
                    self.actions_button.winfo_rooty()
                    + self.actions_button.winfo_height()
                ),
            )
        finally:
            self.actions_menu.grab_release()

    def school_display_text(self):
        school_name = self.school_field.get_value()
        return school_name if school_name else "None selected"

    def focus_school(self):
        self.school_field.picker.focus_set()

    def notify_change(self):
        if not self.loading and self.change_command is not None:
            self.change_command()
