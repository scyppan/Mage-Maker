import tkinter as tk
from datetime import date
from functools import partial

from mage_maker.sections.development.characteristics import (
    initial_values_are_complete,
)
from mage_maker.sections.settings.mage_groups import (
    mage_group_definition,
    normalize_mage_groups,
)
from mage_maker.ui.theme import (
    BORDER_SOFT,
    BUTTON_SOFT,
    FIELD_BACKGROUND,
    LIST_ALTERNATE,
    LIST_HOVER,
    LIST_SELECTED,
    LOCKED_BORDER,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import RoundedEntry, RoundedSelect, SoftButton


FILTER_SHOW_ALL = "Show all"
AGE_FILTER_OPTIONS = (
    FILTER_SHOW_ALL,
    "0–10",
    "11–17",
    "18–29",
    "30–49",
    "50–69",
    "70+",
    "Unknown age",
)
AGE_FILTER_BOUNDS = {
    "0–10": (0, 10),
    "11–17": (11, 17),
    "18–29": (18, 29),
    "30–49": (30, 49),
    "50–69": (50, 69),
    "70+": (70, None),
}
SORT_BIRTH_YEAR = "Birth year"
SORT_BIRTH_YEAR_NEWEST = "Birth year (newest)"
SORT_NAME = "Name"
SORT_GROUP = "Group"
SORT_AGE = "Age"
SORT_OPTIONS = (
    SORT_BIRTH_YEAR,
    SORT_BIRTH_YEAR_NEWEST,
    SORT_NAME,
    SORT_GROUP,
    SORT_AGE,
)


class PeopleList(tk.Frame):
    def __init__(
        self,
        parent,
        selection_command,
        create_command,
        period_provider=None,
    ):
        super().__init__(parent, bg=SURFACE)
        self.selection_command = selection_command
        self.create_command = create_command
        self.period_provider = period_provider
        self.people = []
        self.periods = []
        self.periods_by_name = {}
        self.period_filter_options = [FILTER_SHOW_ALL]
        self.visible_record_ids = []
        self.labels_by_id = {}
        self.search_text_by_id = {}
        self.rows_by_id = {}
        self.row_labels_by_id = {}
        self.group_colors_by_id = {}
        self.group_names_by_id = {}
        self.initial_values_complete_by_id = {}
        self.unfinished_by_id = {}
        self.selected_record_id = None
        self.hovered_record_id = None
        self.filter_updates_paused = False

        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.heading = tk.Label(
            self,
            text="All People",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(15, "bold"),
            anchor="w",
        )
        self.heading.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))

        self.search_value = tk.StringVar()
        self.search_value.trace_add("write", self.filter_people)
        self.search_entry = RoundedEntry(
            self,
            textvariable=self.search_value,
            background=SURFACE,
            height=40,
            font=app_font(11),
        )
        self.search_entry.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=16,
            pady=(0, 12),
        )

        filters = tk.Frame(self, bg=SURFACE)
        filters.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=16,
            pady=(0, 8),
        )
        filters.grid_columnconfigure(1, weight=1)
        self.group_filter_value = tk.StringVar(
            value=FILTER_SHOW_ALL
        )
        self.age_filter_value = tk.StringVar(
            value=FILTER_SHOW_ALL
        )
        self.period_filter_value = tk.StringVar(
            value=FILTER_SHOW_ALL
        )
        self.sort_value = tk.StringVar(
            value=SORT_BIRTH_YEAR
        )
        self.filter_summary_value = tk.StringVar(
            value="All people · Birth year"
        )
        self.filter_button = SoftButton(
            filters,
            text="Filters ▾",
            command=self.show_filter_menu,
            background=SURFACE,
            fill=BUTTON_SOFT,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=82,
            height=30,
            font=app_font(9, "bold"),
        )
        self.filter_button.grid(
            row=0,
            column=0,
            sticky="w",
        )
        filter_summary = tk.Label(
            filters,
            textvariable=self.filter_summary_value,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(8),
            anchor="w",
        )
        filter_summary.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
        )
        self.show_all_button = SoftButton(
            filters,
            text=FILTER_SHOW_ALL,
            command=self.show_all_people,
            background=SURFACE,
            fill=BUTTON_SOFT,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=70,
            height=30,
            font=app_font(8, "bold"),
        )
        self.show_all_button.grid(
            row=0,
            column=2,
            sticky="e",
        )
        self.group_filter_options = [FILTER_SHOW_ALL]
        self.filter_menu = tk.Menu(
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
        self.refresh_periods(rebuild=False)
        self.rebuild_filter_menu()
        self.group_filter_value.trace_add(
            "write",
            self.filter_people,
        )
        self.age_filter_value.trace_add(
            "write",
            self.filter_people,
        )
        self.period_filter_value.trace_add(
            "write",
            self.filter_people,
        )
        self.sort_value.trace_add(
            "write",
            self.filter_people,
        )

        period_filter = tk.Frame(self, bg=SURFACE)
        period_filter.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=16,
            pady=(0, 10),
        )
        period_filter.grid_columnconfigure(1, weight=1)
        period_filter_label = tk.Label(
            period_filter,
            text="Alive during period",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        period_filter_label.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )
        self.period_filter_select = RoundedSelect(
            period_filter,
            self.period_filter_value,
            self.period_filter_options,
            background=SURFACE,
            height=34,
            font=app_font(9),
        )
        self.period_filter_select.grid(
            row=0,
            column=1,
            sticky="ew",
        )

        list_container = tk.Frame(self, bg=SURFACE)
        list_container.grid(row=4, column=0, sticky="nsew", padx=16)
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            list_container,
            bg=FIELD_BACKGROUND,
            highlightbackground=BORDER_SOFT,
            highlightcolor=BORDER_SOFT,
            highlightthickness=1,
            borderwidth=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self.resize_rows)
        self.canvas.bind("<MouseWheel>", self.scroll_people)

        scrollbar = tk.Scrollbar(
            list_container,
            orient="vertical",
            command=self.canvas.yview,
            relief="flat",
            borderwidth=0,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.row_container = tk.Frame(self.canvas, bg=FIELD_BACKGROUND)
        self.row_container.grid_columnconfigure(0, weight=1)
        self.row_container.bind("<Configure>", self.update_scroll_region)
        self.row_window = self.canvas.create_window(
            (0, 0),
            window=self.row_container,
            anchor="nw",
        )

        footer = tk.Frame(self, bg=SURFACE)
        footer.grid(row=5, column=0, sticky="ew", padx=16, pady=14)
        footer.grid_columnconfigure(0, weight=1)

        self.count_label = tk.Label(
            footer,
            text="0 people",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
        )
        self.count_label.grid(row=0, column=0, sticky="w")

        self.create_button = SoftButton(
            footer,
            text="Create Magician",
            command=self.create_command,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=148,
            height=38,
        )
        self.create_button.grid(row=0, column=1, sticky="e")

    def set_people(
        self,
        people,
        selected_record_id=None,
        mage_groups=None,
    ):
        if hasattr(self, "period_provider"):
            self.refresh_periods(rebuild=False)

        self.people = people
        self.labels_by_id = {}
        self.search_text_by_id = {}
        self.group_colors_by_id = {}
        self.group_names_by_id = {}
        self.initial_values_complete_by_id = {}
        self.unfinished_by_id = {}
        groups = normalize_mage_groups(mage_groups)
        group_filter_options = [
            FILTER_SHOW_ALL,
            *[group["name"] for group in groups],
        ]

        self.group_filter_options = group_filter_options

        if hasattr(self, "filter_menu"):
            self.rebuild_filter_menu()

        for person in people:
            record_id = person["record_id"]
            name = str(person.get("displayed_name", "")).strip() or "Unnamed magician"
            birth_text = self.format_birth_date(person)
            self.labels_by_id[record_id] = f"{name}\n{birth_text}"
            group = mage_group_definition(
                person.get("mage_group_id"),
                groups,
            )
            self.group_colors_by_id[record_id] = group["color"]
            self.group_names_by_id[record_id] = group["name"]
            self.initial_values_complete_by_id[record_id] = (
                initial_values_are_complete(person)
            )
            self.unfinished_by_id[record_id] = bool(
                person.get("unfinished", False)
            )
            name_details = person.get("name_details", {})
            name_entries = (
                name_details.get("entries", [])
                if isinstance(name_details, dict)
                else []
            )
            name_detail_text = " ".join(
                " ".join(
                    str(entry.get(field_name, "") or "")
                    for field_name in ("name_type", "name_entry", "date", "note")
                )
                for entry in name_entries
                if isinstance(entry, dict)
            )

            self.search_text_by_id[record_id] = " ".join(
                str(value or "")
                for value in (
                    person.get("displayed_name"),
                    name_detail_text,
                    person.get("school"),
                    group["name"],
                    person.get("birth_year"),
                    person.get("death_year"),
                )
            ).casefold()

        if (
            hasattr(self, "group_filter_value")
            and self.group_filter_value.get()
            not in group_filter_options
        ):
            previous_filter_pause = self.filter_updates_paused
            self.filter_updates_paused = True
            self.group_filter_value.set(FILTER_SHOW_ALL)
            self.filter_updates_paused = previous_filter_pause

        self.selected_record_id = selected_record_id
        self.rebuild_rows()

    def refresh_periods(self, rebuild=True):
        periods = []

        if callable(self.period_provider):
            try:
                periods = self.period_provider()
            except (OSError, TypeError, ValueError):
                periods = []

        return self.set_periods(periods, rebuild=rebuild)

    def set_periods(self, periods, rebuild=True):
        normalized_periods = []

        for period in periods or []:
            if not isinstance(period, dict):
                continue

            period_name = str(period.get("name", "") or "").strip()

            try:
                start_year = int(
                    period.get("calculation_start_year")
                )
                end_year = int(
                    period.get("calculation_end_year")
                )
            except (TypeError, ValueError):
                continue

            if not period_name or end_year < start_year:
                continue

            normalized_periods.append(
                {
                    **period,
                    "name": period_name,
                    "calculation_start_year": start_year,
                    "calculation_end_year": end_year,
                }
            )

        self.periods = normalized_periods
        self.periods_by_name = {
            period["name"]: period
            for period in self.periods
        }
        self.period_filter_options = [
            FILTER_SHOW_ALL,
            *[period["name"] for period in self.periods],
        ]

        if (
            hasattr(self, "period_filter_value")
            and self.period_filter_value.get()
            not in self.period_filter_options
        ):
            previous_filter_pause = self.filter_updates_paused
            self.filter_updates_paused = True
            self.period_filter_value.set(FILTER_SHOW_ALL)
            self.filter_updates_paused = previous_filter_pause

        if hasattr(self, "filter_menu"):
            self.rebuild_filter_menu()

        if hasattr(self, "period_filter_select"):
            self.period_filter_select.set_values(
                self.period_filter_options
            )

        if rebuild and hasattr(self, "canvas"):
            self.rebuild_rows()

        return list(self.periods)

    def rebuild_filter_menu(self):
        if not hasattr(self, "filter_menu"):
            return

        self.filter_menu.delete(0, "end")
        group_menu = tk.Menu(
            self.filter_menu,
            tearoff=False,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            activebackground=LIST_HOVER,
            activeforeground=TEXT_DARK,
            relief="solid",
            borderwidth=1,
            font=app_font(10),
        )

        for group_name in self.group_filter_options:
            group_menu.add_radiobutton(
                label=group_name,
                variable=self.group_filter_value,
                value=group_name,
            )

        age_menu = tk.Menu(
            self.filter_menu,
            tearoff=False,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            activebackground=LIST_HOVER,
            activeforeground=TEXT_DARK,
            relief="solid",
            borderwidth=1,
            font=app_font(10),
        )

        for age_option in AGE_FILTER_OPTIONS:
            age_menu.add_radiobutton(
                label=age_option,
                variable=self.age_filter_value,
                value=age_option,
            )

        period_menu = tk.Menu(
            self.filter_menu,
            tearoff=False,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            activebackground=LIST_HOVER,
            activeforeground=TEXT_DARK,
            relief="solid",
            borderwidth=1,
            font=app_font(10),
        )

        for period_name in self.period_filter_options:
            period_menu.add_radiobutton(
                label=self.period_filter_label(period_name),
                variable=self.period_filter_value,
                value=period_name,
            )

        sort_menu = tk.Menu(
            self.filter_menu,
            tearoff=False,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            activebackground=LIST_HOVER,
            activeforeground=TEXT_DARK,
            relief="solid",
            borderwidth=1,
            font=app_font(10),
        )

        for sort_option in SORT_OPTIONS:
            sort_menu.add_radiobutton(
                label=sort_option,
                variable=self.sort_value,
                value=sort_option,
            )

        self.filter_menu.add_cascade(
            label="Group",
            menu=group_menu,
        )
        self.filter_menu.add_cascade(
            label="Age",
            menu=age_menu,
        )
        self.filter_menu.add_cascade(
            label="Period",
            menu=period_menu,
        )
        self.filter_menu.add_cascade(
            label="Sort by",
            menu=sort_menu,
        )
        self.filter_menu.add_separator()
        self.filter_menu.add_command(
            label=FILTER_SHOW_ALL,
            command=self.show_all_people,
        )

    def show_filter_menu(self):
        self.filter_button.update_idletasks()

        try:
            self.filter_menu.tk_popup(
                self.filter_button.winfo_rootx(),
                (
                    self.filter_button.winfo_rooty()
                    + self.filter_button.winfo_height()
                ),
            )
        finally:
            self.filter_menu.grab_release()

    def update_filter_summary(self):
        selected_parts = []
        selected_group = self.group_filter_value.get()
        selected_age = self.age_filter_value.get()
        selected_period = self.period_filter_value.get()

        if selected_group != FILTER_SHOW_ALL:
            selected_parts.append(selected_group)

        if selected_age != FILTER_SHOW_ALL:
            selected_parts.append(selected_age)

        if selected_period != FILTER_SHOW_ALL:
            selected_parts.append(selected_period)

        if not selected_parts:
            selected_parts.append("All people")

        selected_parts.append(self.sort_value.get())
        self.filter_summary_value.set(" · ".join(selected_parts))

    def format_birth_date(self, person):
        year = person.get("birth_year")
        month = person.get("birth_month")
        day = person.get("birth_day")

        if year is None:
            return "Birth date unknown"

        date_parts = [str(year)]

        if month is not None:
            date_parts.append(f"{int(month):02d}")

        if day is not None:
            date_parts.append(f"{int(day):02d}")

        return "Born " + "-".join(date_parts)

    def set_selected_record(self, record_id):
        self.selected_record_id = record_id

        if record_id not in self.visible_record_ids:
            self.show_all_people()

        self.refresh_row_colors()
        self.scroll_selected_into_view()

    def set_initial_values_status(
        self,
        record_id,
        complete,
        unfinished=None,
    ):
        normalized_record_id = str(record_id or "").strip()

        if normalized_record_id not in self.labels_by_id:
            return

        self.initial_values_complete_by_id[
            normalized_record_id
        ] = bool(complete)

        if unfinished is not None:
            self.unfinished_by_id[normalized_record_id] = bool(
                unfinished
            )

        show_red_border = (
            not bool(complete)
            or self.unfinished_by_id.get(normalized_record_id, False)
        )
        label = self.row_labels_by_id.get(
            normalized_record_id
        )

        if label is None:
            return

        label.configure(
            highlightbackground=(
                LOCKED_BORDER if show_red_border else FIELD_BACKGROUND
            ),
            highlightcolor=(
                LOCKED_BORDER if show_red_border else FIELD_BACKGROUND
            ),
            highlightthickness=2 if show_red_border else 0,
        )

    def filter_people(self, *arguments):
        if self.filter_updates_paused:
            return

        if hasattr(self, "filter_summary_value"):
            self.update_filter_summary()

        self.rebuild_rows()

    def show_all_people(self):
        self.filter_updates_paused = True
        self.search_value.set("")
        self.group_filter_value.set(FILTER_SHOW_ALL)
        self.age_filter_value.set(FILTER_SHOW_ALL)

        if hasattr(self, "period_filter_value"):
            self.period_filter_value.set(FILTER_SHOW_ALL)

        self.filter_updates_paused = False

        if hasattr(self, "filter_summary_value"):
            self.update_filter_summary()

        self.rebuild_rows()

    def person_age(self, person):
        birth_year = self.integer_value(person.get("birth_year"))

        if birth_year is None:
            return None

        death_year = self.integer_value(person.get("death_year"))
        has_death_date = bool(person.get("deceased")) or death_year is not None
        today = date.today()
        end_year = death_year if has_death_date else today.year

        if end_year is None:
            return None

        age = end_year - birth_year
        birth_month = self.integer_value(person.get("birth_month"))
        birth_day = self.integer_value(person.get("birth_day"))

        if has_death_date:
            end_month = self.integer_value(person.get("death_month"))
            end_day = self.integer_value(person.get("death_day"))
        else:
            end_month = today.month
            end_day = today.day

        if (
            birth_month is not None
            and birth_day is not None
            and end_month is not None
            and end_day is not None
            and (end_month, end_day) < (birth_month, birth_day)
        ):
            age -= 1

        if age < 0:
            return None

        return age

    def integer_value(self, value):
        if isinstance(value, bool):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def matches_age_filter(self, person, selected_filter):
        if selected_filter == FILTER_SHOW_ALL:
            return True

        age = self.person_age(person)

        if selected_filter == "Unknown age":
            return age is None

        bounds = AGE_FILTER_BOUNDS.get(selected_filter)

        if bounds is None:
            return True

        minimum_age, maximum_age = bounds

        if age is None or age < minimum_age:
            return False

        return maximum_age is None or age <= maximum_age

    def period_filter_label(self, period_name):
        if period_name == FILTER_SHOW_ALL:
            return FILTER_SHOW_ALL

        period = self.periods_by_name.get(period_name, {})
        start_year = period.get("start_year")
        end_year = period.get("end_year")

        if start_year in (None, "") or end_year in (None, ""):
            return period_name

        return f"{period_name} ({start_year} to {end_year})"

    def matches_period_filter(self, person, selected_period_name):
        if selected_period_name == FILTER_SHOW_ALL:
            return True

        period = getattr(self, "periods_by_name", {}).get(
            selected_period_name
        )

        if period is None:
            return True

        birth_year = self.integer_value(person.get("birth_year"))

        if birth_year is None:
            return False

        period_start = int(period["calculation_start_year"])
        period_end = int(period["calculation_end_year"])

        if birth_year > period_end:
            return False

        death_year = self.integer_value(person.get("death_year"))
        has_death_date = bool(person.get("deceased")) or death_year is not None

        if not has_death_date or death_year is None:
            return True

        return death_year >= period_start

    def person_sort_key(self, person):
        selected_sort = (
            self.sort_value.get()
            if hasattr(self, "sort_value")
            else SORT_BIRTH_YEAR
        )
        record_id = person.get("record_id")
        name = str(
            person.get("displayed_name", "") or ""
        ).casefold()
        group_name = str(
            self.group_names_by_id.get(record_id, "") or ""
        ).casefold()
        birth_year = self.integer_value(person.get("birth_year"))
        birth_month = self.integer_value(person.get("birth_month"))
        birth_day = self.integer_value(person.get("birth_day"))
        birth_is_dated = birth_year is not None
        oldest_birth_key = (
            birth_is_dated,
            birth_year if birth_year is not None else 0,
            birth_month if birth_month is not None else 13,
            birth_day if birth_day is not None else 32,
            name,
        )

        if selected_sort == SORT_BIRTH_YEAR_NEWEST:
            return (
                birth_is_dated,
                -birth_year if birth_year is not None else 0,
                -birth_month if birth_month is not None else 0,
                -birth_day if birth_day is not None else 0,
                name,
            )

        if selected_sort == SORT_NAME:
            return name, *oldest_birth_key

        if selected_sort == SORT_GROUP:
            return group_name, *oldest_birth_key

        if selected_sort == SORT_AGE:
            age = self.person_age(person)
            return (
                age is None,
                -age if age is not None else 0,
                *oldest_birth_key,
            )

        return oldest_birth_key

    def filtered_people(self):
        query = self.search_value.get().strip().casefold()
        selected_group = self.group_filter_value.get()
        selected_age = self.age_filter_value.get()
        selected_period = (
            self.period_filter_value.get()
            if hasattr(self, "period_filter_value")
            else FILTER_SHOW_ALL
        )
        matched_people = []

        for person in self.people:
            record_id = person["record_id"]

            if (
                query
                and query not in self.search_text_by_id[record_id]
            ):
                continue

            if (
                selected_group != FILTER_SHOW_ALL
                and self.group_names_by_id.get(record_id)
                != selected_group
            ):
                continue

            if not self.matches_age_filter(person, selected_age):
                continue

            if not self.matches_period_filter(person, selected_period):
                continue

            matched_people.append(person)

        return sorted(
            matched_people,
            key=self.person_sort_key,
        )

    def rebuild_rows(self):
        if hasattr(self, "filter_summary_value"):
            self.update_filter_summary()

        self.visible_record_ids = [
            person["record_id"]
            for person in self.filtered_people()
        ]

        for row in self.rows_by_id.values():
            row.destroy()

        self.rows_by_id = {}
        self.row_labels_by_id = {}
        wrap_length = max(140, self.canvas.winfo_width() - 31)

        for row_index, record_id in enumerate(self.visible_record_ids):
            row = tk.Frame(
                self.row_container,
                bg=FIELD_BACKGROUND,
                cursor="hand2",
            )
            row.grid(row=row_index, column=0, sticky="ew")
            row.grid_columnconfigure(1, weight=1)
            group_bar = tk.Frame(
                row,
                bg=self.group_colors_by_id[record_id],
                width=5,
                cursor="hand2",
            )
            group_bar.grid(row=0, column=0, sticky="ns")
            group_bar.grid_propagate(False)
            label = tk.Label(
                row,
                text=self.labels_by_id[record_id],
                bg=FIELD_BACKGROUND,
                fg=TEXT_DARK,
                font=app_font(10),
                anchor="nw",
                justify="left",
                wraplength=wrap_length,
                padx=10,
                pady=8,
                cursor="hand2",
                highlightbackground=(
                    LOCKED_BORDER
                    if (
                        not self.initial_values_complete_by_id.get(
                            record_id,
                            False,
                        )
                        or self.unfinished_by_id.get(record_id, False)
                    )
                    else FIELD_BACKGROUND
                ),
                highlightcolor=(
                    LOCKED_BORDER
                    if (
                        not self.initial_values_complete_by_id.get(
                            record_id,
                            False,
                        )
                        or self.unfinished_by_id.get(record_id, False)
                    )
                    else FIELD_BACKGROUND
                ),
                highlightthickness=(
                    2
                    if (
                        not self.initial_values_complete_by_id.get(
                            record_id,
                            False,
                        )
                        or self.unfinished_by_id.get(record_id, False)
                    )
                    else 0
                ),
            )
            label.grid(row=0, column=1, sticky="ew")

            for widget in (row, group_bar, label):
                widget.bind(
                    "<Button-1>",
                    partial(self.select_row, record_id),
                )
                widget.bind(
                    "<Enter>",
                    partial(self.enter_row, record_id),
                )
                widget.bind(
                    "<Leave>",
                    partial(self.leave_row, record_id),
                )
                widget.bind("<MouseWheel>", self.scroll_people)

            self.rows_by_id[record_id] = row
            self.row_labels_by_id[record_id] = label

        visible_count = len(self.visible_record_ids)
        total_count = len(self.people)

        if visible_count == total_count:
            self.count_label.configure(text=f"{total_count} people")
        else:
            self.count_label.configure(text=f"{visible_count} of {total_count} people")

        self.refresh_row_colors()
        self.update_scroll_region()
        self.scroll_selected_into_view()

    def select_row(self, record_id, event=None):
        if self.selection_command(record_id) is not False:
            self.selected_record_id = record_id

        self.refresh_row_colors()

    def enter_row(self, record_id, event=None):
        self.hovered_record_id = record_id
        self.refresh_row_colors()

    def leave_row(self, record_id, event=None):
        if self.hovered_record_id == record_id:
            self.hovered_record_id = None

        self.refresh_row_colors()

    def refresh_row_colors(self):
        for row_index, record_id in enumerate(self.visible_record_ids):
            if record_id == self.selected_record_id:
                background = LIST_SELECTED
            elif record_id == self.hovered_record_id:
                background = LIST_HOVER
            elif row_index % 2:
                background = LIST_ALTERNATE
            else:
                background = FIELD_BACKGROUND

            row = self.rows_by_id.get(record_id)

            if row is not None:
                row.configure(bg=background)

            label = self.row_labels_by_id.get(record_id)

            if label is not None:
                label.configure(bg=background)

    def resize_rows(self, event):
        self.canvas.itemconfigure(self.row_window, width=max(1, event.width - 2))
        wrap_length = max(140, event.width - 31)

        for label in self.row_labels_by_id.values():
            label.configure(wraplength=wrap_length)

        self.update_scroll_region()

    def update_scroll_region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def scroll_people(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        return "break"

    def scroll_selected_into_view(self):
        row = self.rows_by_id.get(self.selected_record_id)

        if row is None:
            return

        self.update_idletasks()
        content_height = max(1, self.row_container.winfo_height())
        viewport_top = self.canvas.canvasy(0)
        viewport_bottom = viewport_top + self.canvas.winfo_height()
        row_top = row.winfo_y()
        row_bottom = row_top + row.winfo_height()

        if row_top < viewport_top:
            self.canvas.yview_moveto(row_top / content_height)
        elif row_bottom > viewport_bottom:
            target_top = row_bottom - self.canvas.winfo_height()
            self.canvas.yview_moveto(target_top / content_height)
