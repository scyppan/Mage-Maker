import tkinter as tk

from mage_maker.ui.theme import (
    BORDER_SOFT,
    FIELD_BACKGROUND,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)


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
            padx=8,
            pady=6,
        )
        self.controller = controller
        self.background = background
        self.person_ids = []
        self.earned_person_ids = []
        self.variables_by_person_id = {}
        self.checkbuttons = []
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
            text="Choose which linked people earn one Eminence point.",
            bg=background,
            fg=TEXT_MUTED,
            font=app_font(8),
            anchor="w",
        )
        hint.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(1, 4),
        )
        self.rows = tk.Frame(self, bg=background)
        self.rows.grid(row=2, column=0, sticky="ew")
        self.rows.grid_columnconfigure(0, weight=1)

    def set_values(self, person_ids, earned_person_ids=()):
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
        ]
        self.render_people()

    def update_people(self, person_ids):
        self.set_values(person_ids, self.get_values())

    def get_values(self):
        if self.variables_by_person_id:
            return [
                person_id
                for person_id in self.person_ids
                if person_id in self.variables_by_person_id
                and self.variables_by_person_id[person_id].get()
            ]

        return list(self.earned_person_ids)

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
        self.checkbuttons = []

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
                padx=6,
                pady=3,
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
            )
            earns_eminence.grid(
                row=0,
                column=1,
                sticky="e",
                padx=(10, 0),
            )
            self.variables_by_person_id[person_id] = (
                earns_eminence_value
            )
            self.checkbuttons.append(earns_eminence)

        self.grid()

    def set_enabled(self, enabled):
        self.is_enabled = bool(enabled)
        state = "normal" if self.is_enabled else "disabled"

        for checkbutton in self.checkbuttons:
            checkbutton.configure(state=state)
