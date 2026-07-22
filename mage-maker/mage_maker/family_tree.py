import tkinter as tk
from copy import deepcopy
from functools import partial
from tkinter import messagebox

from mage_maker.child_dialog import AddChildDialog
from mage_maker.family_relationships import (
    FamilyRelationshipMap,
    format_person_date,
    maiden_name_for,
)
from mage_maker.relationship_picker import RelationshipPickerDialog
from mage_maker.theme import (
    BORDER,
    BORDER_SOFT,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    FAMILY_GREEN,
    FAMILY_CHILD_FADED_FILL,
    FAMILY_CHILD_FADED_LINE,
    FAMILY_CHILD_FADED_MUTED,
    FAMILY_CHILD_FADED_OUTLINE,
    FAMILY_CHILD_FADED_TEXT,
    FAMILY_GREEN_DARK,
    FAMILY_GREEN_FADED,
    FAMILY_LINE,
    FAMILY_STEP_ACTIVE,
    FAMILY_STEP_DARK,
    FAMILY_STEP_FADED,
    FAMILY_STEP_FILL,
    FIELD_BACKGROUND,
    PRIMARY,
    PRIMARY_HOVER,
    PRIMARY_SOFT,
    SURFACE,
    SURFACE_MUTED,
    SURFACE_RAISED,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)
from mage_maker.widgets import SoftButton, rounded_points


class FamilyTreeView(tk.Frame):
    generation_labels = (
        "Grandparents",
        "Parents · aunts · uncles",
        "Selected · siblings · cousins",
        "Children · nieces · nephews",
        "Grandchildren",
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
    ):
        super().__init__(parent, bg=SURFACE)
        self.change_command = change_command
        self.people_provider = people_provider
        self.create_person_command = create_person_command
        self.update_person_command = update_person_command
        self.refresh_people_command = refresh_people_command
        self.navigate_command = navigate_command
        self.current_person = {}
        self.people = []
        self.relationship_map = FamilyRelationshipMap([])
        self.mother_id = ""
        self.father_id = ""
        self.mother_status = "unknown"
        self.father_status = "unknown"
        self.mate_ids = []
        self.active_mate_id = None
        self.active_spouse_owner_id = None
        self.node_coordinates = {}

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_toolbar()

        self.canvas = tk.Canvas(
            self,
            bg=SURFACE_MUTED,
            highlightbackground=BORDER_SOFT,
            highlightcolor=BORDER_SOFT,
            highlightthickness=1,
            borderwidth=0,
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self.resize_graph)

    def build_toolbar(self):
        toolbar = tk.Frame(self, bg=SURFACE, height=46)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.grid_propagate(False)
        toolbar.grid_columnconfigure(0, weight=1)

        heading = tk.Label(
            toolbar,
            text="Five-generation family graph",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(11, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="nsew")

        self.remove_mother_button = SoftButton(
            toolbar,
            text="Unlink birthing",
            command=partial(self.remove_parent, "mother"),
            background=SURFACE,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            foreground=TEXT_DARK,
            width=126,
            height=36,
        )
        self.remove_mother_button.grid(row=0, column=1, padx=(6, 0), pady=5)

        self.remove_father_button = SoftButton(
            toolbar,
            text="Unlink non-birthing",
            command=partial(self.remove_parent, "father"),
            background=SURFACE,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            foreground=TEXT_DARK,
            width=150,
            height=36,
        )
        self.remove_father_button.grid(row=0, column=2, padx=(6, 0), pady=5)

        self.add_mate_button = SoftButton(
            toolbar,
            text="Add mate",
            command=self.open_mate_picker,
            background=SURFACE,
            fill=FAMILY_GREEN,
            hover_fill=FAMILY_GREEN_FADED,
            foreground=TEXT_DARK,
            width=96,
            height=36,
        )
        self.add_mate_button.grid(row=0, column=3, padx=(6, 0), pady=5)

        self.remove_mate_button = SoftButton(
            toolbar,
            text="Remove mate",
            command=self.remove_active_mate,
            background=SURFACE,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            foreground=TEXT_DARK,
            width=112,
            height=36,
        )
        self.remove_mate_button.grid(row=0, column=4, padx=(6, 0), pady=5)

        self.add_child_button = SoftButton(
            toolbar,
            text="Add child",
            command=self.open_add_child_dialog,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=102,
            height=36,
        )
        self.add_child_button.grid(row=0, column=5, padx=(6, 0), pady=5)

    def set_person(self, person):
        previous_record_id = str(
            self.current_person.get("record_id", "") or ""
        )
        self.current_person = deepcopy(person) if isinstance(person, dict) else {}
        current_record_id = str(
            self.current_person.get("record_id", "") or ""
        )
        self.mother_id = str(
            self.current_person.get("biological_mother_id", "") or ""
        ).strip()
        self.father_id = str(
            self.current_person.get("biological_father_id", "") or ""
        ).strip()
        self.mother_status = self.normalized_parent_status(
            self.mother_id,
            self.current_person.get("biological_mother_status", "unknown"),
        )
        self.father_status = self.normalized_parent_status(
            self.father_id,
            self.current_person.get("biological_father_status", "unknown"),
        )
        self.mate_ids = self.normalize_ids(self.current_person.get("mate_ids", []))

        if previous_record_id != current_record_id:
            self.active_mate_id = None
            self.active_spouse_owner_id = None
        elif self.active_spouse_owner_id == current_record_id and (
            self.active_mate_id not in self.mate_ids
        ):
            self.active_mate_id = None
            self.active_spouse_owner_id = None

        self.reload_people()

    def update_current_person(self, values):
        if not isinstance(values, dict):
            return

        self.current_person.update(deepcopy(values))
        self.current_person["biological_mother_id"] = self.mother_id
        self.current_person["biological_father_id"] = self.father_id
        self.current_person["biological_mother_status"] = self.mother_status
        self.current_person["biological_father_status"] = self.father_status
        self.current_person["mate_ids"] = list(self.mate_ids)
        self.reload_people()

    def get_relationship_values(self):
        return {
            "biological_mother_id": self.mother_id,
            "biological_father_id": self.father_id,
            "biological_mother_status": self.mother_status,
            "biological_father_status": self.father_status,
            "mate_ids": list(self.mate_ids),
        }

    def reload_people(self):
        self.people = self.people_provider()
        self.current_person["biological_mother_id"] = self.mother_id
        self.current_person["biological_father_id"] = self.father_id
        self.current_person["biological_mother_status"] = self.mother_status
        self.current_person["biological_father_status"] = self.father_status
        self.current_person["mate_ids"] = list(self.mate_ids)
        self.relationship_map = FamilyRelationshipMap(
            self.people,
            self.current_person,
        )
        self.redraw_graph()

    def resize_graph(self, event=None):
        self.redraw_graph()

    def redraw_graph(self):
        if not hasattr(self, "canvas"):
            return

        width = max(640, self.canvas.winfo_width())
        height = max(480, self.canvas.winfo_height())
        self.canvas.delete("all")
        self.node_coordinates = {}

        focus_id = str(self.current_person.get("record_id", "") or "")

        if not focus_id:
            self.canvas.create_text(
                width / 2,
                height / 2,
                text="Select a magician to view their family graph.",
                fill=TEXT_MUTED,
                font=app_font(11),
            )
            return

        generations = self.relationship_map.build_generations(focus_id)
        generations[1] = self.add_missing_parent_nodes(generations[1])
        lane_height = height / 5
        label_width = 154
        graph_left = label_width + 10
        graph_right = width - 12
        visible_generations = []

        for row_index, label_text in enumerate(self.generation_labels):
            lane_top = row_index * lane_height
            lane_bottom = (row_index + 1) * lane_height
            lane_fill = SURFACE_MUTED if row_index % 2 == 0 else SURFACE_RAISED
            self.canvas.create_rectangle(
                0,
                lane_top,
                width,
                lane_bottom,
                fill=lane_fill,
                outline="",
            )
            self.canvas.create_text(
                14,
                (lane_top + lane_bottom) / 2,
                text=label_text,
                fill=TEXT_MUTED,
                font=app_font(9, "bold"),
                anchor="w",
                width=label_width - 22,
            )
            visible_nodes = self.select_visible_nodes(
                generations[row_index],
                row_index,
                graph_left,
                graph_right,
                focus_id,
            )
            visible_generations.append(visible_nodes)
            positions = self.positions_for_row(
                visible_nodes,
                row_index,
                graph_left,
                graph_right,
                (lane_top + lane_bottom) / 2,
                focus_id,
            )

            for node, x_position, y_position in positions:
                record_id = str(node["person"].get("record_id", ""))
                self.node_coordinates[record_id] = (
                    x_position,
                    y_position,
                    132,
                    64,
                )

            hidden_count = len(generations[row_index]) - len(visible_nodes)

            if hidden_count > 0:
                self.canvas.create_text(
                    graph_right - 4,
                    lane_bottom - 10,
                    text=f"+{hidden_count} more",
                    fill=TEXT_MUTED,
                    font=app_font(8, "bold"),
                    anchor="e",
                )

        self.draw_relationship_lines(visible_generations)

        for row_index, nodes in enumerate(visible_generations):
            for node in nodes:
                self.draw_person_node(node, row_index, focus_id)

        self.draw_spouse_flags(focus_id)
        self.remove_mother_button.set_enabled(
            bool(self.mother_id) or self.mother_status == "muggle"
        )
        self.remove_father_button.set_enabled(
            bool(self.father_id) or self.father_status == "muggle"
        )
        self.remove_mate_button.set_enabled(
            self.active_mate_id is not None
            and self.active_spouse_owner_id == focus_id
        )

    def add_missing_parent_nodes(self, parent_nodes):
        nodes = list(parent_nodes)
        relation_names = {node.get("relation") for node in nodes}

        if not self.mother_id and "Birthing parent" not in relation_names:
            nodes.append(
                {
                    "person": {
                        "record_id": "__select_mother__",
                        "displayed_name": (
                            "Muggle" if self.mother_status == "muggle" else "Unknown"
                        ),
                    },
                    "relation": "Birthing parent",
                    "placeholder": True,
                }
            )

        if not self.father_id and "Non-birthing parent" not in relation_names:
            nodes.append(
                {
                    "person": {
                        "record_id": "__select_father__",
                        "displayed_name": (
                            "Muggle" if self.father_status == "muggle" else "Unknown"
                        ),
                    },
                    "relation": "Non-birthing parent",
                    "placeholder": True,
                }
            )

        return self.order_parent_nodes(nodes)

    def order_parent_nodes(self, nodes):
        relation_order = {
            "Birthing parent's sibling": 0,
            "Birthing parent": 1,
            "Non-birthing parent": 2,
            "Non-birthing parent's sibling": 3,
            "Aunt/uncle": 4,
        }
        return sorted(nodes, key=lambda node: relation_order.get(node["relation"], 5))

    def select_visible_nodes(
        self,
        nodes,
        row_index,
        graph_left,
        graph_right,
        focus_id,
    ):
        available_width = max(360, graph_right - graph_left)
        maximum_nodes = max(3, min(7, int(available_width // 142)))

        if len(nodes) <= maximum_nodes:
            return list(nodes)

        relation_priority = {
            "Selected person": 0,
            "Birthing parent": 0,
            "Non-birthing parent": 0,
            "Child": 0,
            "Sibling": 1,
            "1/2 Sibling": 1,
            "Grandparent": 1,
            "Grandchild": 1,
            "Birthing parent's sibling": 2,
            "Non-birthing parent's sibling": 2,
            "Niece/nephew": 3,
            "Birthing parent's cousin": 4,
            "Non-birthing parent's cousin": 4,
            "Cousin": 4,
        }
        ranked_nodes = sorted(
            enumerate(nodes),
            key=lambda item: (
                relation_priority.get(item[1].get("relation"), 5),
                item[0],
            ),
        )[:maximum_nodes]
        selected_indexes = {item[0] for item in ranked_nodes}
        return [node for index, node in enumerate(nodes) if index in selected_indexes]

    def positions_for_row(
        self,
        nodes,
        row_index,
        graph_left,
        graph_right,
        y_position,
        focus_id,
    ):
        if not nodes:
            return []

        center_x = (graph_left + graph_right) / 2

        if row_index == 2:
            focus_node = None
            other_nodes = []

            for node in nodes:
                if str(node["person"].get("record_id", "")) == focus_id:
                    focus_node = node
                else:
                    other_nodes.append(node)

            positions = []

            if focus_node is not None:
                positions.append((focus_node, center_x, y_position))

            left_nodes = other_nodes[: (len(other_nodes) + 1) // 2]
            right_nodes = other_nodes[(len(other_nodes) + 1) // 2 :]
            left_space = max(138, center_x - graph_left - 96)
            right_space = max(138, graph_right - center_x - 208)

            for index, node in enumerate(reversed(left_nodes), start=1):
                x_position = center_x - min(left_space, index * 144)
                positions.append((node, x_position, y_position))

            for index, node in enumerate(right_nodes, start=1):
                x_position = center_x + 208 + min(
                    max(0, right_space - 144),
                    (index - 1) * 144,
                )
                positions.append((node, x_position, y_position))

            return positions

        spacing = min(150, (graph_right - graph_left) / max(1, len(nodes)))
        total_width = spacing * (len(nodes) - 1)
        start_x = center_x - total_width / 2
        return [
            (node, start_x + index * spacing, y_position)
            for index, node in enumerate(nodes)
        ]

    def draw_relationship_lines(self, visible_generations):
        visible_ids = []

        for nodes in visible_generations:
            visible_ids.extend(
                str(node["person"].get("record_id", ""))
                for node in nodes
                if not node.get("placeholder")
            )

        for parent_id, child_id in self.relationship_map.visible_parent_child_edges(
            visible_ids
        ):
            parent_coordinates = self.node_coordinates.get(parent_id)
            child_coordinates = self.node_coordinates.get(child_id)

            if parent_coordinates is None or child_coordinates is None:
                continue

            parent_x, parent_y, parent_width, parent_height = parent_coordinates
            child_x, child_y, child_width, child_height = child_coordinates
            line_middle = (parent_y + child_y) / 2
            line_fill = FAMILY_LINE

            if self.child_is_faded(child_id):
                line_fill = FAMILY_CHILD_FADED_LINE

            self.canvas.create_line(
                parent_x,
                parent_y + parent_height / 2,
                parent_x,
                line_middle,
                child_x,
                line_middle,
                child_x,
                child_y - child_height / 2,
                fill=line_fill,
                width=2,
                smooth=False,
            )

    def draw_person_node(self, node, row_index, focus_id):
        person = node["person"]
        record_id = str(person.get("record_id", ""))
        x_position, y_position, node_width, node_height = self.node_coordinates[
            record_id
        ]
        left = x_position - node_width / 2
        top = y_position - node_height / 2
        right = x_position + node_width / 2
        bottom = y_position + node_height / 2
        is_focus = record_id == focus_id
        is_placeholder = bool(node.get("placeholder"))
        fill = PRIMARY_SOFT if is_focus else FIELD_BACKGROUND
        outline = BORDER
        outline_width = 2 if is_focus else 1
        text_fill = TEXT_DARK
        relation_fill = TEXT_MUTED
        plaque_fill = SURFACE_RAISED
        plaque_outline = BORDER_SOFT
        child_is_faded = self.child_is_faded(record_id)

        if self.active_mate_id:
            active_owner_id = str(
                self.active_spouse_owner_id or focus_id
            )
            parent_ids = self.relationship_map.parents_of(record_id)

            if (
                record_id in self.relationship_map.children_of(active_owner_id)
                and self.active_mate_id in parent_ids
            ):
                outline = FAMILY_GREEN_DARK
                outline_width = 3

        if child_is_faded:
            fill = FAMILY_CHILD_FADED_FILL
            outline = FAMILY_CHILD_FADED_OUTLINE
            outline_width = 1
            text_fill = FAMILY_CHILD_FADED_TEXT
            relation_fill = FAMILY_CHILD_FADED_MUTED
            plaque_fill = SURFACE_RAISED
            plaque_outline = FAMILY_CHILD_FADED_OUTLINE

        if is_placeholder:
            fill = BUTTON_SOFT
            outline = PRIMARY
            outline_width = 2

        tag_name = f"person_node:{record_id}"
        shape = self.canvas.create_polygon(
            rounded_points(node_width, node_height, 9),
            smooth=True,
            splinesteps=24,
            fill=fill,
            outline=outline,
            width=outline_width,
            tags=(tag_name,),
        )
        self.canvas.move(shape, left, top)
        display_name = str(person.get("displayed_name", "") or "Unnamed")
        maiden_name = maiden_name_for(person)
        date_text = format_person_date(person)
        detail_lines = [self.short_text(display_name, 23)]

        if not is_placeholder:
            maiden_line = (
                f"née {self.short_text(maiden_name, 18)}" if maiden_name else ""
            )
            detail_lines.extend((maiden_line, date_text))

        text_item = self.canvas.create_text(
            x_position,
            y_position,
            text="\n".join(detail_lines),
            fill=text_fill,
            font=app_font(8, "bold" if is_focus else "normal"),
            justify="center",
            width=node_width - 12,
            tags=(tag_name,),
        )
        relation_item = self.canvas.create_text(
            x_position,
            top - 7,
            text=node.get("relation", ""),
            fill=relation_fill,
            font=app_font(7, "bold"),
            justify="center",
            tags=(tag_name,),
        )
        relation_bounds = self.canvas.bbox(relation_item)
        relation_plaque = None

        if relation_bounds is not None:
            plaque_left = relation_bounds[0] - 5
            plaque_top = relation_bounds[1] - 2
            plaque_right = relation_bounds[2] + 5
            plaque_bottom = relation_bounds[3] + 2
            relation_plaque = self.canvas.create_rectangle(
                plaque_left,
                plaque_top,
                plaque_right,
                plaque_bottom,
                fill=plaque_fill,
                outline=plaque_outline,
                width=1,
                tags=(tag_name,),
            )
            self.canvas.tag_lower(relation_plaque, relation_item)

        self.canvas.tag_bind(tag_name, "<Enter>", partial(self.enter_canvas_item, tag_name))
        self.canvas.tag_bind(tag_name, "<Leave>", partial(self.leave_canvas_item, tag_name))

        if record_id == "__select_mother__":
            self.canvas.tag_bind(tag_name, "<Button-1>", self.open_mother_picker)
        elif record_id == "__select_father__":
            self.canvas.tag_bind(tag_name, "<Button-1>", self.open_father_picker)
        else:
            self.canvas.tag_bind(
                tag_name,
                "<Double-Button-1>",
                partial(self.navigate_to_person, record_id),
            )

        self.canvas.tag_raise(text_item)

        if relation_plaque is not None:
            self.canvas.tag_raise(relation_plaque)

        self.canvas.tag_raise(relation_item)

    def draw_spouse_flags(self, focus_id):
        focus_mate_ids = self.relationship_map.mates_of(focus_id)

        for mate_id in self.mate_ids:
            if mate_id not in focus_mate_ids and self.relationship_map.person(mate_id):
                focus_mate_ids.append(mate_id)

        step_parent_mates = self.relationship_map.step_parent_mates_of(focus_id)
        visible_ids = set(self.node_coordinates)
        rendered_pairs = {
            (focus_id, mate_id)
            for mate_id in focus_mate_ids
        }

        for parent_id, mate_ids in step_parent_mates.items():
            for mate_id in mate_ids:
                if mate_id not in visible_ids:
                    rendered_pairs.add((parent_id, mate_id))

        active_pair = (self.active_spouse_owner_id, self.active_mate_id)

        if active_pair not in rendered_pairs:
            self.active_spouse_owner_id = None
            self.active_mate_id = None

        self.draw_spouse_flags_for_person(
            focus_id,
            focus_mate_ids,
            is_step_parent=False,
        )

        for parent_id, mate_ids in step_parent_mates.items():
            hidden_mate_ids = [
                mate_id for mate_id in mate_ids if mate_id not in visible_ids
            ]
            self.draw_spouse_flags_for_person(
                parent_id,
                hidden_mate_ids,
                is_step_parent=True,
            )

    def draw_spouse_flags_for_person(
        self,
        owner_id,
        mate_ids,
        is_step_parent=False,
    ):
        owner_coordinates = self.node_coordinates.get(owner_id)

        if owner_coordinates is None or not mate_ids:
            return

        owner_x, owner_y, owner_width, owner_height = owner_coordinates
        flag_width = 16 if is_step_parent else 20
        flag_height = 16 if is_step_parent else 18
        flag_column_gap = 3
        flag_row_step = flag_height
        flag_column_step = flag_width + flag_column_gap
        flag_start_left = owner_x + owner_width / 2 - 3
        flag_start_top = owner_y - owner_height / 2 + 4
        flag_column_count = (len(mate_ids) + 2) // 3

        for index, mate_id in enumerate(mate_ids):
            mate = self.relationship_map.person(mate_id)

            if mate is None:
                continue

            is_active = (
                owner_id == self.active_spouse_owner_id
                and mate_id == self.active_mate_id
            )
            has_active_spouse = self.active_mate_id is not None
            flag_column = index // 3
            flag_row = index % 3
            flag_left = flag_start_left + flag_column * flag_column_step
            flag_top = flag_start_top + flag_row * flag_row_step
            normal_fill = FAMILY_STEP_FILL if is_step_parent else FAMILY_GREEN
            active_fill = FAMILY_STEP_ACTIVE if is_step_parent else FAMILY_GREEN
            faded_fill = FAMILY_STEP_FADED if is_step_parent else FAMILY_GREEN_FADED
            outline_fill = FAMILY_STEP_DARK if is_step_parent else FAMILY_GREEN_DARK
            flag_fill = active_fill if is_active else (
                faded_fill if has_active_spouse else normal_fill
            )
            flag_foreground = (
                outline_fill if is_active or not has_active_spouse else TEXT_MUTED
            )
            tag_name = f"spouse_flag:{owner_id}:{mate_id}"
            flag_shape = self.canvas.create_polygon(
                rounded_points(flag_width, flag_height, 6),
                smooth=True,
                splinesteps=24,
                fill=flag_fill,
                outline=outline_fill,
                width=1,
                tags=(tag_name,),
            )
            self.canvas.move(flag_shape, flag_left, flag_top)
            self.canvas.create_text(
                flag_left + flag_width / 2,
                flag_top + flag_height / 2,
                text="x",
                fill=flag_foreground,
                font=app_font(7, "bold"),
                tags=(tag_name,),
            )
            self.canvas.tag_bind(
                tag_name,
                "<Button-1>",
                partial(self.select_spouse, owner_id, mate_id),
            )
            self.canvas.tag_bind(
                tag_name,
                "<Enter>",
                partial(self.enter_canvas_item, tag_name),
            )
            self.canvas.tag_bind(
                tag_name,
                "<Leave>",
                partial(self.leave_canvas_item, tag_name),
            )

            if is_active:
                self.draw_spouse_detail(
                    owner_id,
                    mate,
                    flag_start_left,
                    flag_top,
                    flag_column_count,
                    flag_column_step,
                    is_step_parent,
                )

    def draw_spouse_detail(
        self,
        owner_id,
        mate,
        flag_start_left,
        flag_top,
        flag_column_count,
        flag_column_step,
        is_step_parent,
    ):
        mate_id = str(mate.get("record_id", "") or "")
        mate_name = self.short_text(mate.get("displayed_name", "Unnamed"), 20)
        detail_text = f"{mate_name}\n{format_person_date(mate)}"
        detail_width = 152
        detail_height = 34
        detail_left = flag_start_left + flag_column_count * flag_column_step + 4
        detail_top = flag_top - 7
        detail_fill = FAMILY_STEP_FILL if is_step_parent else FAMILY_GREEN
        detail_outline = FAMILY_STEP_DARK if is_step_parent else FAMILY_GREEN_DARK
        detail_tag = f"spouse_detail:{owner_id}:{mate_id}"
        detail_shape = self.canvas.create_polygon(
            rounded_points(detail_width, detail_height, 7),
            smooth=True,
            splinesteps=24,
            fill=detail_fill,
            outline=detail_outline,
            width=1,
            tags=(detail_tag,),
        )
        self.canvas.move(detail_shape, detail_left, detail_top)
        self.canvas.create_text(
            detail_left + 8,
            detail_top + detail_height / 2,
            text=detail_text,
            fill=detail_outline,
            font=app_font(7, "bold"),
            anchor="w",
            justify="left",
            tags=(detail_tag,),
        )
        self.canvas.tag_bind(
            detail_tag,
            "<Button-1>",
            partial(self.select_spouse, owner_id, mate_id),
        )
        self.canvas.tag_bind(
            detail_tag,
            "<Enter>",
            partial(self.enter_canvas_item, detail_tag),
        )
        self.canvas.tag_bind(
            detail_tag,
            "<Leave>",
            partial(self.leave_canvas_item, detail_tag),
        )

    def child_is_faded(self, child_id):
        if not self.active_mate_id:
            return False

        focus_id = str(self.current_person.get("record_id", "") or "")
        owner_id = str(
            getattr(self, "active_spouse_owner_id", None) or focus_id
        )
        child_id = str(child_id or "")

        if child_id not in self.relationship_map.children_of(owner_id):
            return False

        parent_ids = self.relationship_map.parents_of(child_id)
        return self.active_mate_id not in parent_ids

    def enter_canvas_item(self, tag_name, event=None):
        self.canvas.configure(cursor="hand2")

    def leave_canvas_item(self, tag_name, event=None):
        self.canvas.configure(cursor="")

    def navigate_to_person(self, record_id, event=None):
        current_id = str(self.current_person.get("record_id", "") or "")

        if record_id != current_id:
            self.navigate_command(record_id)

    def select_spouse(self, owner_id, mate_id, event=None):
        is_active = (
            self.active_spouse_owner_id == owner_id
            and self.active_mate_id == mate_id
        )
        self.active_spouse_owner_id = None if is_active else owner_id
        self.active_mate_id = None if is_active else mate_id
        self.redraw_graph()

    def open_mother_picker(self, event=None):
        self.open_parent_picker("mother")

    def open_father_picker(self, event=None):
        self.open_parent_picker("father")

    def open_parent_picker(self, parent_role):
        current_id = str(self.current_person.get("record_id", "") or "")
        primary_candidates = self.relationship_map.parent_candidates(
            current_id,
            parent_role,
        )
        alternate_candidates = self.relationship_map.parent_candidates(
            current_id,
            parent_role,
            alternate_role=True,
        )
        role_label = (
            "birthing parent" if parent_role == "mother" else "non-birthing parent"
        )
        alternate_role_label = (
            "non-birthing parent" if parent_role == "mother" else "birthing parent"
        )
        required_setting = "checked" if parent_role == "mother" else "unchecked"
        alternate_label = (
            "See non-birthing parent options"
            if parent_role == "mother"
            else "See birthing parent options"
        )
        alternate_note = (
            f"These people are not assigned as a {alternate_role_label} to anyone. "
            f"Selecting one will set Can give birth to {required_setting}."
        )
        RelationshipPickerDialog(
            self,
            title=f"Select {role_label}",
            heading=f"Select {role_label}",
            explanation=(
                f"Choose an existing {role_label}, or use Enter new for a "
                "name-only character entry."
            ),
            primary_people=primary_candidates,
            alternate_people=alternate_candidates,
            alternate_label=alternate_label,
            alternate_note=alternate_note,
            select_label="Select parent",
            select_command=partial(self.set_parent, parent_role),
            create_command=partial(self.create_parent, parent_role),
            new_profile_label=f"Enter a new {role_label}",
            new_profile_explanation=(
                "Only the displayed name will be entered. Can give birth will be "
                f"{required_setting}."
            ),
        )

    def set_parent(self, parent_role, record_id, change_birth_assignment=False):
        if change_birth_assignment:
            self.update_person_command(
                record_id,
                {"can_give_birth": parent_role == "mother"},
            )

        if parent_role == "mother":
            self.mother_id = record_id
            self.mother_status = "person"
        else:
            self.father_id = record_id
            self.father_status = "person"

        self.reload_people()
        self.change_command()

    def create_parent(self, parent_role, displayed_name):
        created_person = self.create_person_command(
            {
                "displayed_name": displayed_name,
                "can_give_birth": parent_role == "mother",
            }
        )
        self.set_parent(parent_role, created_person["record_id"])
        return created_person

    def remove_parent(self, parent_role):
        parent_id = self.mother_id if parent_role == "mother" else self.father_id

        if not parent_id:
            return

        parent = self.relationship_map.person(parent_id)
        role_label = (
            "birthing parent" if parent_role == "mother" else "non-birthing parent"
        )
        parent_name = (
            parent.get("displayed_name", f"this {role_label}")
            if parent
            else f"this {role_label}"
        )

        if not messagebox.askyesno(
            f"Remove {role_label}",
            (
                f"Remove {parent_name} as the {role_label}? "
                "The person's character entry will remain in Mage Maker."
            ),
            parent=self,
        ):
            return

        if parent_role == "mother":
            self.mother_id = ""
            self.mother_status = "unknown"
        else:
            self.father_id = ""
            self.father_status = "unknown"

        self.reload_people()
        self.change_command()

    def open_mate_picker(self):
        current_id = str(self.current_person.get("record_id", "") or "")
        current_can_give_birth = bool(self.current_person.get("can_give_birth"))
        primary_candidates = self.relationship_map.partner_candidates(current_id)
        alternate_candidates = self.relationship_map.partner_candidates(
            current_id,
            alternate_role=True,
        )
        required_role_label = (
            "non-birthing parent" if current_can_give_birth else "birthing parent"
        )
        alternate_role_label = (
            "birthing parent" if current_can_give_birth else "non-birthing parent"
        )
        required_setting = "unchecked" if current_can_give_birth else "checked"
        alternate_label = (
            "See birthing parent options"
            if current_can_give_birth
            else "See non-birthing parent options"
        )
        RelationshipPickerDialog(
            self,
            title="Add mate",
            heading="Add mate",
            explanation=(
                f"Choose an existing {required_role_label}, or use Enter new for "
                "a name-only character entry."
            ),
            primary_people=primary_candidates,
            alternate_people=alternate_candidates,
            alternate_label=alternate_label,
            alternate_note=(
                f"These {alternate_role_label} options have no parent or mate links "
                f"that block changing Can give birth to {required_setting}."
            ),
            select_label="Add mate",
            select_command=self.select_mate,
            create_command=self.create_mate,
            new_profile_label="Enter a new mate",
            new_profile_explanation=(
                "Only the displayed name will be entered. Can give birth will be "
                f"{required_setting}."
            ),
        )

    def select_mate(self, record_id, change_birth_assignment=False):
        if change_birth_assignment:
            self.update_person_command(
                record_id,
                {
                    "can_give_birth": not bool(
                        self.current_person.get("can_give_birth")
                    )
                },
            )

        self.add_mate(record_id)

    def create_mate(self, displayed_name):
        created_person = self.create_person_command(
            {
                "displayed_name": displayed_name,
                "can_give_birth": not bool(
                    self.current_person.get("can_give_birth")
                ),
            }
        )
        self.add_mate(created_person["record_id"])
        return created_person

    def add_mate(self, record_id):
        if record_id not in self.mate_ids:
            self.mate_ids.append(record_id)
            self.active_mate_id = record_id
            self.active_spouse_owner_id = str(
                self.current_person.get("record_id", "") or ""
            )
            self.reload_people()
            self.change_command()

    def remove_active_mate(self):
        current_id = str(self.current_person.get("record_id", "") or "")

        if (
            self.active_mate_id is None
            or self.active_spouse_owner_id != current_id
        ):
            return

        mate = self.relationship_map.person(self.active_mate_id)
        mate_name = mate.get("displayed_name", "this mate") if mate else "this mate"

        if not messagebox.askyesno(
            "Remove mate",
            f"Remove {mate_name} as a mate? Existing parent links on children will remain.",
            parent=self,
        ):
            return

        self.mate_ids = [
            mate_id for mate_id in self.mate_ids if mate_id != self.active_mate_id
        ]
        self.active_mate_id = None
        self.active_spouse_owner_id = None
        self.reload_people()
        self.change_command()

    def open_add_child_dialog(self):
        current_id = str(self.current_person.get("record_id", "") or "")

        if not current_id:
            return

        ancestors = set(self.relationship_map.ancestors_of(current_id))
        candidates = [
            person
            for person in self.people
            if person.get("record_id") != current_id
            and person.get("record_id") not in ancestors
        ]
        existing_mates = [
            self.relationship_map.person(mate_id)
            for mate_id in self.relationship_map.mates_of(current_id)
            if self.relationship_map.person(mate_id) is not None
        ]
        AddChildDialog(
            self,
            self.current_person,
            candidates,
            self.people_provider,
            self.save_child,
            self.open_child_other_parent_picker,
            existing_mates=existing_mates,
            active_other_parent_id=(
                self.active_mate_id
                if self.active_spouse_owner_id == current_id
                else None
            ),
        )

    def open_child_other_parent_picker(
        self,
        dialog_parent,
        selection_command,
        child_record_id,
    ):
        current_id = str(self.current_person.get("record_id", "") or "")
        current_can_give_birth = bool(self.current_person.get("can_give_birth"))
        excluded_ids = [child_record_id] if child_record_id else []
        primary_candidates = self.relationship_map.partner_candidates(
            current_id,
            include_existing_mates=False,
            extra_excluded_ids=excluded_ids,
        )
        alternate_candidates = self.relationship_map.partner_candidates(
            current_id,
            alternate_role=True,
            include_existing_mates=False,
            extra_excluded_ids=excluded_ids,
        )
        required_role_label = (
            "non-birthing parent" if current_can_give_birth else "birthing parent"
        )
        alternate_role_label = (
            "birthing parent" if current_can_give_birth else "non-birthing parent"
        )
        required_setting = "unchecked" if current_can_give_birth else "checked"
        alternate_label = (
            "See birthing parent options"
            if current_can_give_birth
            else "See non-birthing parent options"
        )
        RelationshipPickerDialog(
            dialog_parent,
            title="Choose other parent",
            heading=f"Choose the child's {required_role_label}",
            explanation=(
                f"Choose a {required_role_label} who is not already listed as a "
                "mate, or use Enter new for a name-only character entry."
            ),
            primary_people=primary_candidates,
            alternate_people=alternate_candidates,
            alternate_label=alternate_label,
            alternate_note=(
                f"These {alternate_role_label} options have no parent or mate links "
                f"that block changing Can give birth to {required_setting}."
            ),
            select_label="Select parent",
            select_command=selection_command,
            create_command=partial(
                self.create_child_other_parent,
                selection_command,
            ),
            new_profile_label=f"Enter a new {required_role_label}",
            new_profile_explanation=(
                "Only the displayed name will be entered. Can give birth will be "
                f"{required_setting}."
            ),
        )

    def create_child_other_parent(self, selection_command, displayed_name):
        created_person = self.create_person_command(
            {
                "displayed_name": displayed_name,
                "can_give_birth": not bool(
                    self.current_person.get("can_give_birth")
                ),
            }
        )
        selection_command(created_person["record_id"], False)
        return created_person

    def save_child(
        self,
        child_record_id,
        new_child_name,
        new_child_can_give_birth,
        other_parent_id,
        change_other_parent_assignment=False,
        other_parent_kind="person",
    ):
        current_id = str(self.current_person.get("record_id", "") or "")
        current_can_give_birth = bool(self.current_person.get("can_give_birth"))
        current_parent_field = (
            "biological_mother_id"
            if current_can_give_birth
            else "biological_father_id"
        )
        other_parent_field = (
            "biological_father_id"
            if current_can_give_birth
            else "biological_mother_id"
        )
        current_parent_status_field = current_parent_field.replace("_id", "_status")
        other_parent_status_field = other_parent_field.replace("_id", "_status")
        normalized_other_parent_kind = str(other_parent_kind or "unknown").casefold()
        relationship_values = {
            current_parent_field: current_id,
            current_parent_status_field: "person",
        }

        if normalized_other_parent_kind == "person" and other_parent_id:
            if change_other_parent_assignment:
                other_parent = self.update_person_command(
                    other_parent_id,
                    {"can_give_birth": not current_can_give_birth},
                )
            else:
                other_parent = self.relationship_map.person(other_parent_id)

            if (
                other_parent is None
                or bool(other_parent.get("can_give_birth"))
                == current_can_give_birth
            ):
                raise ValueError(
                    "The child's other parent must have the opposite Can give birth assignment."
                )

            relationship_values[other_parent_field] = other_parent_id
            relationship_values[other_parent_status_field] = "person"
        elif normalized_other_parent_kind == "muggle":
            relationship_values[other_parent_field] = ""
            relationship_values[other_parent_status_field] = "muggle"
        else:
            relationship_values[other_parent_field] = ""
            relationship_values[other_parent_status_field] = "unknown"

        if new_child_name:
            creation_values = {
                "displayed_name": new_child_name,
                "can_give_birth": bool(new_child_can_give_birth),
            }
            creation_values.update(relationship_values)
            child = self.create_person_command(creation_values)
        else:
            child = self.relationship_map.person(child_record_id)

            if child is None:
                raise ValueError("Select an existing child or enter a new child's name.")

            for field_name in (current_parent_field, other_parent_field):
                parent_id = str(relationship_values.get(field_name, "") or "")
                existing_parent_id = str(child.get(field_name, "") or "")
                status_field = field_name.replace("_id", "_status")
                existing_status = self.normalized_parent_status(
                    existing_parent_id,
                    child.get(status_field, "unknown"),
                )
                new_status = self.normalized_parent_status(
                    parent_id,
                    relationship_values.get(status_field, "unknown"),
                )

                if (
                    existing_parent_id != parent_id
                    or existing_status != new_status
                ) and (existing_parent_id or existing_status == "muggle"):
                    existing_parent = self.relationship_map.person(existing_parent_id)
                    existing_name = (
                        existing_parent.get("displayed_name", "another person")
                        if existing_parent
                        else "another person"
                    )

                    if not messagebox.askyesno(
                        "Replace parent",
                        (
                            f"{child.get('displayed_name', 'This person')} already lists "
                            f"{existing_name} in that parent role. Replace that link?"
                        ),
                        parent=self,
                    ):
                        return None

            child = self.update_person_command(child_record_id, relationship_values)

        mate_added = (
            normalized_other_parent_kind == "person"
            and other_parent_id
            and other_parent_id not in self.mate_ids
        )

        if mate_added:
            self.mate_ids.append(other_parent_id)
            updated_current_person = self.update_person_command(
                current_id,
                {"mate_ids": list(self.mate_ids)},
            )
            self.current_person["mate_ids"] = list(
                updated_current_person.get("mate_ids", self.mate_ids)
            )

        if other_parent_id:
            self.active_mate_id = other_parent_id
            self.active_spouse_owner_id = current_id
        self.refresh_people_command()
        self.reload_people()

        return child

    def normalized_parent_status(self, parent_id, status):
        if str(parent_id or "").strip():
            return "person"

        return "muggle" if str(status or "").casefold() == "muggle" else "unknown"

    def normalize_ids(self, record_ids):
        if not isinstance(record_ids, list):
            return []

        normalized_ids = []

        for record_id in record_ids:
            normalized_id = str(record_id or "").strip()

            if normalized_id and normalized_id not in normalized_ids:
                normalized_ids.append(normalized_id)

        return normalized_ids

    def short_text(self, value, maximum_length):
        text = str(value or "").strip()

        if len(text) <= maximum_length:
            return text

        return text[: maximum_length - 1].rstrip() + "…"
