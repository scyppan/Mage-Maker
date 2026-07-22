import tkinter as tk
from functools import partial

from mage_maker.theme import (
    BORDER_SOFT,
    FIELD_BACKGROUND,
    LIST_ALTERNATE,
    LIST_HOVER,
    LIST_SELECTED,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.widgets import RoundedEntry, SoftButton


class PeopleList(tk.Frame):
    def __init__(self, parent, selection_command, create_command):
        super().__init__(parent, bg=SURFACE)
        self.selection_command = selection_command
        self.create_command = create_command
        self.people = []
        self.visible_record_ids = []
        self.labels_by_id = {}
        self.search_text_by_id = {}
        self.rows_by_id = {}
        self.selected_record_id = None
        self.hovered_record_id = None

        self.grid_rowconfigure(2, weight=1)
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

        list_container = tk.Frame(self, bg=SURFACE)
        list_container.grid(row=2, column=0, sticky="nsew", padx=16)
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
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=14)
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

    def set_people(self, people, selected_record_id=None):
        self.people = people
        self.labels_by_id = {}
        self.search_text_by_id = {}

        for person in people:
            record_id = person["record_id"]
            name = str(person.get("displayed_name", "")).strip() or "Unnamed magician"
            birth_text = self.format_birth_date(person)
            self.labels_by_id[record_id] = f"{name}\n{birth_text}"
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
                    person.get("birth_year"),
                )
            ).casefold()

        self.selected_record_id = selected_record_id
        self.rebuild_rows()

    def format_birth_date(self, person):
        year = person.get("birth_year")
        month = person.get("birth_month")
        day = person.get("birth_day")

        if year is None:
            return "Birth date unknown"

        date_parts = [str(year)]

        if month is not None:
            date_parts.append(f"{month:02d}")

        if day is not None:
            date_parts.append(f"{day:02d}")

        return "Born " + "-".join(date_parts)

    def set_selected_record(self, record_id):
        self.selected_record_id = record_id

        if record_id not in self.visible_record_ids and self.search_value.get():
            self.search_value.set("")

        self.refresh_row_colors()
        self.scroll_selected_into_view()

    def filter_people(self, *arguments):
        self.rebuild_rows()

    def rebuild_rows(self):
        query = self.search_value.get().strip().casefold()
        self.visible_record_ids = [
            person["record_id"]
            for person in self.people
            if not query or query in self.search_text_by_id[person["record_id"]]
        ]

        for row in self.rows_by_id.values():
            row.destroy()

        self.rows_by_id = {}
        wrap_length = max(140, self.canvas.winfo_width() - 24)

        for row_index, record_id in enumerate(self.visible_record_ids):
            row = tk.Label(
                self.row_container,
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
            )
            row.grid(row=row_index, column=0, sticky="ew")
            row.bind("<Button-1>", partial(self.select_row, record_id))
            row.bind("<Enter>", partial(self.enter_row, record_id))
            row.bind("<Leave>", partial(self.leave_row, record_id))
            row.bind("<MouseWheel>", self.scroll_people)
            self.rows_by_id[record_id] = row

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

    def resize_rows(self, event):
        self.canvas.itemconfigure(self.row_window, width=max(1, event.width - 2))
        wrap_length = max(140, event.width - 24)

        for row in self.rows_by_id.values():
            row.configure(wraplength=wrap_length)

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
