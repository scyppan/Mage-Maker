import tkinter as tk
from tkinter import ttk

from mage_maker.sections.locations.models import (
    descendant_ids,
    location_path,
    locations_by_id,
)
from mage_maker.ui.theme import (
    BORDER_SOFT,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    FIELD_BACKGROUND,
    LIST_HOVER,
    LIST_SELECTED,
    LOCKED_BORDER,
    LOCKED_RED,
    LOCKED_RED_HOVER,
    SURFACE,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import RoundedEntry, SoftButton


WORLD_LOCATION_LABEL = "The World"
WORLD_TREE_ID = "__mage_maker_world__"


def location_ids_in_scope(locations, scope_location_id=""):
    records = locations_by_id(locations)
    normalized_scope_id = str(scope_location_id or "").strip()

    if not normalized_scope_id:
        return set(records)

    if normalized_scope_id not in records:
        return set()

    scoped_ids = descendant_ids(normalized_scope_id, locations)
    scoped_ids.add(normalized_scope_id)
    return scoped_ids


def location_id_is_in_scope(location_id, locations, scope_location_id=""):
    normalized_location_id = str(location_id or "").strip()

    if not normalized_location_id:
        return not str(scope_location_id or "").strip()

    return normalized_location_id in location_ids_in_scope(
        locations,
        scope_location_id,
    )


def location_ids_for_search(locations, search_text, scope_location_id=""):
    records = locations_by_id(locations)
    scoped_ids = location_ids_in_scope(locations, scope_location_id)
    normalized_search = " ".join(str(search_text or "").strip().split()).casefold()

    if not normalized_search or normalized_search == WORLD_LOCATION_LABEL.casefold():
        return scoped_ids

    matching_ids = set()

    for record_id, location in records.items():
        if record_id not in scoped_ids:
            continue

        name = str(location.get("name", "") or "").strip()
        path = location_path(record_id, locations)
        searchable_text = f"{name} {path}".casefold()

        if normalized_search in searchable_text:
            matching_ids.add(record_id)

    visible_ids = set(matching_ids)

    for matching_id in matching_ids:
        current_id = matching_id
        visited_ids = set()

        while current_id and current_id not in visited_ids:
            visited_ids.add(current_id)
            current = records.get(current_id)

            if current is None:
                break

            parent_id = str(
                current.get("parent_location_id", "") or ""
            ).strip()

            if (
                not parent_id
                or parent_id not in records
                or parent_id not in scoped_ids
            ):
                break

            visible_ids.add(parent_id)
            current_id = parent_id

    return visible_ids


class LocationHierarchyTree(tk.Frame):
    def __init__(
        self,
        parent,
        selection_command,
        background=SURFACE,
        scope_change_command=None,
        show_scope_controls=True,
        initial_scope_location_id="",
    ):
        super().__init__(parent, bg=background)
        self.selection_command = selection_command
        self.scope_change_command = scope_change_command
        self.background = background
        self.show_scope_controls = bool(show_scope_controls)
        self.locations = []
        self.records_by_id = {}
        self.children_by_parent_id = {}
        self.selected_location_id = ""
        self.scope_location_id = str(initial_scope_location_id or "").strip()
        self.hovered_tree_id = ""
        self.suppress_selection = False
        self.suppress_search = False
        self.search_value = tk.StringVar()
        self.scope_status_value = tk.StringVar(value="All regions")
        self.search_label_row = 1 if self.show_scope_controls else 0
        self.search_control_row = self.search_label_row + 1
        self.tree_row = self.search_control_row + 1
        self.grid_rowconfigure(self.tree_row, weight=1)
        self.grid_columnconfigure(0, weight=1)

        if self.show_scope_controls:
            self.build_scope_controls()

        self.build_search()
        self.build_tree()
        self.search_value.trace_add("write", self.search_changed)

    def build_scope_controls(self):
        scope_bar = tk.Frame(self, bg=self.background)
        scope_bar.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        scope_bar.grid_columnconfigure(0, weight=1)
        scope_status = tk.Label(
            scope_bar,
            textvariable=self.scope_status_value,
            bg=self.background,
            fg=TEXT_DARK,
            font=app_font(9, "bold"),
            anchor="w",
        )
        scope_status.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        self.scope_button = SoftButton(
            scope_bar,
            text="Lock here",
            command=self.toggle_scope,
            background=self.background,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            foreground=TEXT_DARK,
            width=92,
            height=30,
            font=app_font(9, "bold"),
        )
        self.scope_button.grid(row=0, column=1, sticky="e")

    def build_search(self):
        search_label = tk.Label(
            self,
            text="Search",
            bg=self.background,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        search_label.grid(
            row=self.search_label_row,
            column=0,
            sticky="ew",
            pady=(0, 5),
        )
        self.search_control = RoundedEntry(
            self,
            textvariable=self.search_value,
            background=self.background,
            height=36,
            font=app_font(10),
        )
        self.search_control.grid(
            row=self.search_control_row,
            column=0,
            sticky="ew",
            pady=(0, 9),
        )
        self.search_control.bind_input("<Escape>", self.clear_search)
        self.search_control.bind_input("<Return>", self.select_first_visible)

    def build_tree(self):
        self.tree_frame = tk.Frame(
            self,
            bg=FIELD_BACKGROUND,
            highlightbackground=BORDER_SOFT,
            highlightcolor=BORDER_SOFT,
            highlightthickness=1,
        )
        self.tree_frame.grid(row=self.tree_row, column=0, sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        style = ttk.Style(self)
        style.configure(
            "LocationHierarchy.Treeview",
            background=FIELD_BACKGROUND,
            fieldbackground=FIELD_BACKGROUND,
            foreground=TEXT_DARK,
            borderwidth=0,
            relief="flat",
            rowheight=30,
            indent=9,
            font=app_font(10),
        )
        style.map(
            "LocationHierarchy.Treeview",
            background=[("selected", LIST_SELECTED)],
            foreground=[("selected", TEXT_DARK)],
        )
        self.tree = ttk.Treeview(
            self.tree_frame,
            style="LocationHierarchy.Treeview",
            show="tree",
            selectmode="browse",
            takefocus=True,
        )
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(self.tree_frame, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_configure("extinct", foreground=TEXT_MUTED)
        self.tree.tag_configure("hover", background=LIST_HOVER)
        self.tree.bind("<<TreeviewSelect>>", self.tree_selected)
        self.tree.bind("<Motion>", self.tree_motion)
        self.tree.bind("<Leave>", self.tree_left)
        self.tree.bind("<Return>", self.toggle_selected_branch)
        self.tree.bind("<space>", self.toggle_selected_branch)
        self.tree.configure(cursor="hand2")

    def toggle_scope(self):
        requested_scope_id = (
            ""
            if self.scope_location_id
            else self.selected_location_id
        )

        if not requested_scope_id and not self.scope_location_id:
            return False

        self.set_scope(requested_scope_id, notify=True)
        return True

    def set_scope(self, location_id="", notify=False):
        requested_scope_id = str(location_id or "").strip()

        if (
            requested_scope_id
            and requested_scope_id not in self.records_by_id
        ):
            requested_scope_id = ""

        previous_scope_id = self.scope_location_id
        previous_selection_id = self.selected_location_id
        self.scope_location_id = requested_scope_id
        scoped_ids = location_ids_in_scope(
            self.locations,
            self.scope_location_id,
        )

        if self.selected_location_id not in scoped_ids:
            self.selected_location_id = self.scope_location_id

        if self.search_value.get():
            self.suppress_search = True
            self.search_value.set("")
            self.suppress_search = False

        self.rebuild_tree(False)

        if (
            notify
            and previous_scope_id != self.scope_location_id
            and self.scope_change_command is not None
        ):
            self.scope_change_command(self.scope_location_id)

        if (
            notify
            and previous_selection_id != self.selected_location_id
        ):
            self.selection_command(self.selected_location_id)

    def update_scope_controls(self):
        if not self.show_scope_controls:
            return

        if self.scope_location_id in self.records_by_id:
            location = self.records_by_id[self.scope_location_id]
            location_name = str(
                location.get("name", "") or "Unnamed region"
            ).strip()
            self.scope_status_value.set(f"Showing only {location_name}")
            self.scope_button.set_text("Unlock")
            self.scope_button.set_colors(
                LOCKED_RED,
                LOCKED_RED_HOVER,
                TEXT_LIGHT,
            )
            self.scope_button.set_enabled(True)
            self.tree_frame.configure(
                highlightbackground=LOCKED_BORDER,
                highlightcolor=LOCKED_BORDER,
                highlightthickness=2,
            )
            return

        self.scope_status_value.set("All regions")
        self.scope_button.set_colors(
            BUTTON_SOFT,
            BUTTON_SOFT_HOVER,
            TEXT_DARK,
        )
        self.scope_button.set_text(
            "Lock here"
            if self.selected_location_id
            else "Select to lock"
        )
        self.scope_button.set_enabled(bool(self.selected_location_id))
        self.tree_frame.configure(
            highlightbackground=BORDER_SOFT,
            highlightcolor=BORDER_SOFT,
            highlightthickness=1,
        )

    def set_locations(self, locations, selected_location_id=""):
        self.locations = [
            location
            for location in locations
            if isinstance(location, dict)
        ]
        self.records_by_id = locations_by_id(self.locations)

        if self.scope_location_id not in self.records_by_id:
            self.scope_location_id = ""

        scoped_ids = location_ids_in_scope(
            self.locations,
            self.scope_location_id,
        )
        requested_id = str(selected_location_id or "").strip()
        self.selected_location_id = (
            requested_id
            if requested_id in scoped_ids
            else self.scope_location_id
        )
        self.rebuild_tree(False)

    def search_changed(self, variable_name=None, variable_index=None, operation=None):
        if self.suppress_search:
            return

        self.rebuild_tree(True)

    def clear_search(self, event=None):
        self.search_value.set("")
        self.search_control.focus_set()
        return "break"

    def select_first_visible(self, event=None):
        visible_ids = self.visible_location_ids()

        if visible_ids:
            self.select_location(visible_ids[0], notify=True)
        else:
            self.select_location("", notify=True)

        return "break"

    def expanded_location_ids(self):
        return {
            record_id
            for record_id in self.records_by_id
            if self.tree.exists(record_id)
            and bool(self.tree.item(record_id, "open"))
        }

    def rebuild_tree(self, notify):
        expanded_ids = self.expanded_location_ids()
        visible_ids = location_ids_for_search(
            self.locations,
            self.search_value.get(),
            self.scope_location_id,
        )
        query_is_active = bool(self.search_value.get().strip())
        self.children_by_parent_id = {}

        for record_id, location in self.records_by_id.items():
            parent_id = str(
                location.get("parent_location_id", "") or ""
            ).strip()

            if parent_id not in self.records_by_id:
                parent_id = ""

            self.children_by_parent_id.setdefault(parent_id, []).append(record_id)

        for child_ids in self.children_by_parent_id.values():
            child_ids.sort(
                key=self.location_sort_key
            )

        self.suppress_selection = True
        self.hovered_tree_id = ""
        root_items = self.tree.get_children("")

        if root_items:
            self.tree.delete(*root_items)

        self.tree.insert(
            "",
            "end",
            iid=WORLD_TREE_ID,
            text=WORLD_LOCATION_LABEL,
            open=True,
        )
        inserted_ids = set()

        if (
            self.scope_location_id
            and self.scope_location_id in visible_ids
        ):
            inserted_ids.add(self.scope_location_id)
            self.insert_location_record(
                WORLD_TREE_ID,
                self.scope_location_id,
                expanded_ids,
                query_is_active,
            )
            self.insert_location_children(
                self.scope_location_id,
                self.scope_location_id,
                visible_ids,
                expanded_ids,
                query_is_active,
                inserted_ids,
            )
        elif not self.scope_location_id:
            self.insert_location_children(
                WORLD_TREE_ID,
                "",
                visible_ids,
                expanded_ids,
                query_is_active,
                inserted_ids,
            )

        for record_id in sorted(visible_ids - inserted_ids, key=self.location_sort_key):
            self.insert_location_record(
                WORLD_TREE_ID,
                record_id,
                expanded_ids,
                query_is_active,
            )

        selection_id = (
            self.selected_location_id
            if self.selected_location_id in visible_ids
            and self.tree.exists(self.selected_location_id)
            else ""
        )

        if not selection_id and query_is_active:
            visible_order = self.visible_location_ids()

            if visible_order:
                selection_id = visible_order[0]

        tree_id = selection_id or WORLD_TREE_ID
        self.selected_location_id = selection_id
        self.tree.selection_set(tree_id)
        self.tree.focus(tree_id)
        self.tree.see(tree_id)
        self.suppress_selection = False
        self.update_scope_controls()

        if notify:
            self.selection_command(self.selected_location_id)

    def insert_location_children(
        self,
        tree_parent_id,
        parent_location_id,
        visible_ids,
        expanded_ids,
        query_is_active,
        inserted_ids,
    ):
        for record_id in self.children_by_parent_id.get(parent_location_id, []):
            if record_id not in visible_ids or record_id in inserted_ids:
                continue

            inserted_ids.add(record_id)
            self.insert_location_record(
                tree_parent_id,
                record_id,
                expanded_ids,
                query_is_active,
            )
            self.insert_location_children(
                record_id,
                record_id,
                visible_ids,
                expanded_ids,
                query_is_active,
                inserted_ids,
            )

    def insert_location_record(
        self,
        tree_parent_id,
        record_id,
        expanded_ids,
        query_is_active,
    ):
        location = self.records_by_id[record_id]
        name = str(location.get("name", "") or "Unnamed").strip()
        tags = ()

        if bool(location.get("extinct")):
            extinction_year = str(
                location.get("extinction_year", "") or "unknown year"
            )
            name = f"{name}  ·  extinct {extinction_year}"
            tags = ("extinct",)

        self.tree.insert(
            tree_parent_id,
            "end",
            iid=record_id,
            text=name,
            open=query_is_active or record_id in expanded_ids,
            tags=tags,
        )

    def location_sort_key(self, record_id):
        location = self.records_by_id.get(record_id, {})
        return (
            str(location.get("name", "") or "").casefold(),
            str(record_id),
        )

    def visible_location_ids(self):
        visible_ids = []

        for child_id in self.tree.get_children(WORLD_TREE_ID):
            self.append_visible_location_ids(child_id, visible_ids)

        return visible_ids

    def append_visible_location_ids(self, tree_id, visible_ids):
        if tree_id != WORLD_TREE_ID:
            visible_ids.append(tree_id)

        for child_id in self.tree.get_children(tree_id):
            self.append_visible_location_ids(child_id, visible_ids)

    def select_location(self, location_id, notify=False):
        requested_id = str(location_id or "").strip()
        scoped_ids = location_ids_in_scope(
            self.locations,
            self.scope_location_id,
        )

        if requested_id not in scoped_ids:
            requested_id = self.scope_location_id

        if (
            requested_id in self.records_by_id
            and not self.tree.exists(requested_id)
            and self.search_value.get()
        ):
            self.suppress_search = True
            self.search_value.set("")
            self.suppress_search = False
            self.rebuild_tree(False)

        tree_id = (
            requested_id
            if requested_id
            and requested_id in self.records_by_id
            and self.tree.exists(requested_id)
            else WORLD_TREE_ID
        )
        self.selected_location_id = (
            requested_id
            if tree_id != WORLD_TREE_ID
            else ""
        )
        current_selection = self.tree.selection()

        if current_selection != (tree_id,):
            self.suppress_selection = True
            self.tree.selection_set(tree_id)
            self.tree.focus(tree_id)
            self.tree.see(tree_id)
            self.suppress_selection = False

        self.update_scope_controls()

        if notify:
            self.selection_command(self.selected_location_id)

    def tree_selected(self, event=None):
        if self.suppress_selection:
            return

        selection = self.tree.selection()

        if not selection:
            return

        tree_id = selection[0]

        if tree_id == WORLD_TREE_ID and self.scope_location_id:
            self.select_location(self.scope_location_id, notify=True)
            return

        self.selected_location_id = "" if tree_id == WORLD_TREE_ID else tree_id
        self.update_scope_controls()
        self.selection_command(self.selected_location_id)

    def toggle_selected_branch(self, event=None):
        selection = self.tree.selection()

        if not selection:
            return "break"

        tree_id = selection[0]

        if self.tree.get_children(tree_id):
            self.tree.item(
                tree_id,
                open=not bool(self.tree.item(tree_id, "open")),
            )

        return "break"

    def tree_motion(self, event):
        tree_id = self.tree.identify_row(event.y)

        if tree_id == self.hovered_tree_id:
            return

        self.clear_hover()

        if not tree_id:
            return

        tags = list(self.tree.item(tree_id, "tags"))

        if "hover" not in tags:
            tags.append("hover")

        self.tree.item(tree_id, tags=tuple(tags))
        self.hovered_tree_id = tree_id

    def tree_left(self, event=None):
        self.clear_hover()

    def clear_hover(self):
        if not self.hovered_tree_id or not self.tree.exists(self.hovered_tree_id):
            self.hovered_tree_id = ""
            return

        tags = [
            tag
            for tag in self.tree.item(self.hovered_tree_id, "tags")
            if tag != "hover"
        ]
        self.tree.item(self.hovered_tree_id, tags=tuple(tags))
        self.hovered_tree_id = ""
