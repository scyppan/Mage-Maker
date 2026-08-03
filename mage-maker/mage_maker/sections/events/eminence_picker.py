import tkinter as tk
from functools import partial

from mage_maker.sections.development.models import (
    DEVELOPMENT_SKILL_OPTIONS,
)
from mage_maker.ui.theme import (
    BORDER_SOFT,
    FIELD_BACKGROUND,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import RoundedSelect


class EventEminencePicker(tk.Frame):
    def __init__(
        self,
        parent,
        controller,
        background,
    ):
        super().__init__(
            parent,
            bg=background,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            padx=6,
            pady=3,
        )
        self.controller = controller
        self.background = background
        self.person_ids = []
        self.earned_person_ids = []
        self.skills_by_person_id = {}
        self.event_identity = ""
        self.variables_by_person_id = {}
        self.skill_variables_by_person_id = {}
        self.checkbuttons = []
        self.skill_selects = []
        self.skill_selects_by_person_id = {}
        self.rendered_rows = []
        self.is_enabled = True
        self.grid_columnconfigure(0, weight=1)
        heading = tk.Label(
            self,
            text="Eminence",
            bg=background,
            fg=TEXT_DARK,
            font=app_font(9, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew")
        hint = tk.Label(
            self,
            text="Choose who earns one Eminence point and its skill.",
            bg=background,
            fg=TEXT_MUTED,
            font=app_font(8),
            anchor="w",
        )
        hint.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 2),
        )
        self.rows = tk.Frame(self, bg=background)
        self.rows.grid(row=2, column=0, sticky="ew")
        self.rows.grid_columnconfigure(0, weight=1)

    def set_values(
        self,
        person_ids,
        earned_person_ids=(),
        skills_by_person_id=None,
        event_identity="",
    ):
        self.person_ids = []

        for person_id in person_ids or ():
            normalized_person_id = str(person_id or "").strip()

            if (
                normalized_person_id
                and normalized_person_id not in self.person_ids
            ):
                self.person_ids.append(normalized_person_id)

        requested_earned_ids = {
            str(person_id or "").strip()
            for person_id in earned_person_ids or ()
            if str(person_id or "").strip()
        }
        self.earned_person_ids = [
            person_id
            for person_id in self.person_ids
            if person_id in requested_earned_ids
            and self.person_can_earn(person_id)
        ]
        candidate_skills = (
            skills_by_person_id
            if isinstance(skills_by_person_id, dict)
            else {}
        )
        self.skills_by_person_id = {
            person_id: str(candidate_skills.get(person_id, "") or "").strip()
            for person_id in self.person_ids
            if str(candidate_skills.get(person_id, "") or "").strip()
        }
        self.event_identity = str(event_identity or "").strip()
        self.render_people()

    def update_people(self, person_ids):
        self.set_values(
            person_ids,
            self.get_values(),
            self.get_skill_values(include_unearned=True),
            self.event_identity,
        )

    def get_values(self):
        if self.variables_by_person_id:
            return [
                person_id
                for person_id in self.person_ids
                if person_id in self.variables_by_person_id
                and self.variables_by_person_id[person_id].get()
            ]

        return list(self.earned_person_ids)

    def get_skill_values(self, include_unearned=False):
        earned_ids = set(self.get_values())
        selected_skills = {}

        for person_id in self.person_ids:
            if not include_unearned and person_id not in earned_ids:
                continue

            skill_variable = self.skill_variables_by_person_id.get(
                person_id
            )
            selected_skill = (
                str(skill_variable.get() or "").strip()
                if skill_variable is not None
                else str(
                    self.skills_by_person_id.get(person_id, "") or ""
                ).strip()
            )

            if selected_skill in DEVELOPMENT_SKILL_OPTIONS:
                selected_skills[person_id] = selected_skill

        return selected_skills

    def default_skill(self, person_id):
        if self.controller is not None and hasattr(
            self.controller,
            "suggest_event_eminence_skill",
        ):
            return self.controller.suggest_event_eminence_skill(
                person_id,
                self.event_identity,
            )

        return DEVELOPMENT_SKILL_OPTIONS[0]

    def person_can_earn(self, person_id):
        if self.controller is None or not hasattr(
            self.controller,
            "person_can_earn_eminence",
        ):
            return True

        return bool(
            self.controller.person_can_earn_eminence(person_id)
        )

    def people_labels_by_id(self):
        if self.controller is None:
            return {}

        return {
            str(option.get("value", "") or "").strip(): str(
                option.get("label", "") or "Unknown person"
            ).strip()
            for option in self.controller.people_options()
            if isinstance(option, dict)
            and str(option.get("value", "") or "").strip()
        }

    def render_people(self):
        for row in self.rendered_rows:
            row.destroy()

        self.rendered_rows = []
        self.variables_by_person_id = {}
        self.skill_variables_by_person_id = {}
        self.checkbuttons = []
        self.skill_selects = []
        self.skill_selects_by_person_id = {}

        if not self.person_ids:
            self.grid_remove()
            return

        labels_by_id = self.people_labels_by_id()
        earned_ids = set(self.earned_person_ids)

        for row_index, person_id in enumerate(self.person_ids):
            row_background = (
                FIELD_BACKGROUND
                if row_index % 2 == 0
                else self.background
            )
            row = tk.Frame(
                self.rows,
                bg=row_background,
                padx=5,
                pady=1,
            )
            self.rendered_rows.append(row)
            row.grid(row=row_index, column=0, sticky="ew")
            row.grid_columnconfigure(0, weight=1)
            person_name = tk.Label(
                row,
                text=labels_by_id.get(person_id, "Unknown person"),
                bg=row_background,
                fg=TEXT_DARK,
                font=app_font(9),
                anchor="w",
            )
            person_name.grid(row=0, column=0, sticky="ew")

            if not self.person_can_earn(person_id):
                ineligible_label = tk.Label(
                    row,
                    text="Non-magical · cannot earn Eminence",
                    bg=row_background,
                    fg=TEXT_MUTED,
                    font=app_font(8, "bold"),
                    anchor="e",
                )
                ineligible_label.grid(
                    row=0,
                    column=1,
                    columnspan=2,
                    sticky="e",
                    padx=(10, 0),
                )
                continue

            earns_eminence_value = tk.BooleanVar(
                value=person_id in earned_ids
            )
            earns_eminence = tk.Checkbutton(
                row,
                text="Earns Eminence",
                variable=earns_eminence_value,
                bg=row_background,
                fg=TEXT_DARK,
                activebackground=row_background,
                activeforeground=TEXT_DARK,
                selectcolor=FIELD_BACKGROUND,
                font=app_font(9, "bold"),
                borderwidth=0,
                highlightthickness=0,
                state="normal" if self.is_enabled else "disabled",
                command=partial(
                    self.update_skill_enabled,
                    person_id,
                ),
            )
            earns_eminence.grid(
                row=0,
                column=1,
                sticky="e",
                padx=(10, 0),
            )
            selected_skill = self.skills_by_person_id.get(person_id)

            if selected_skill not in DEVELOPMENT_SKILL_OPTIONS:
                selected_skill = self.default_skill(person_id)

            skill_value = tk.StringVar(value=selected_skill)
            skill_select = RoundedSelect(
                row,
                skill_value,
                DEVELOPMENT_SKILL_OPTIONS,
                background=row_background,
                width=132,
                height=24,
                font=app_font(8),
            )
            skill_select.grid(
                row=0,
                column=2,
                sticky="e",
                padx=(8, 0),
            )
            self.variables_by_person_id[person_id] = (
                earns_eminence_value
            )
            self.skill_variables_by_person_id[person_id] = skill_value
            self.checkbuttons.append(earns_eminence)
            self.skill_selects.append(skill_select)
            self.skill_selects_by_person_id[person_id] = skill_select
            self.update_skill_enabled(person_id)

        self.grid()

    def set_enabled(self, enabled):
        self.is_enabled = bool(enabled)
        state = "normal" if self.is_enabled else "disabled"

        for checkbutton in self.checkbuttons:
            checkbutton.configure(state=state)

        for person_id in self.person_ids:
            self.update_skill_enabled(person_id)

    def update_skill_enabled(self, person_id):
        skill_select = self.skill_selects_by_person_id.get(person_id)
        earns_value = self.variables_by_person_id.get(person_id)

        if skill_select is None:
            return

        skill_select.set_enabled(
            self.is_enabled
            and earns_value is not None
            and bool(earns_value.get())
        )
