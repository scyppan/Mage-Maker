import tkinter as tk
from functools import partial
from tkinter import colorchooser, messagebox

from mage_maker.sections.development.models import (
    DEVELOPMENT_ASSIGNMENT_OPTIONS,
)
from mage_maker.sections.settings.mage_groups import (
    DEFAULT_MAGE_GROUP_ID,
    contrasting_text_color,
)
from mage_maker.ui.theme import (
    APP_BACKGROUND,
    BORDER_SOFT,
    DELETE_HOVER,
    DELETE_SOFT,
    FIELD_BACKGROUND,
    LIST_ALTERNATE,
    LIST_HOVER,
    LIST_SELECTED,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import (
    LabeledEntry,
    SectionPanel,
    SoftButton,
)


class SettingsPage(tk.Frame):
    def __init__(
        self,
        parent,
        controller,
        status_command,
        groups_changed_command=None,
    ):
        super().__init__(parent, bg=APP_BACKGROUND)
        self.controller = controller
        self.status_command = status_command
        self.groups_changed_command = groups_changed_command
        self.loading = False
        self.selected_group_id = None
        self.assignment_value = tk.StringVar()
        self.assignment_value.trace_add(
            "write",
            self.assignment_changed,
        )
        self.group_name_value = tk.StringVar()
        self.group_color_value = tk.StringVar()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.build_page()
        self.refresh()

    def build_page(self):
        workspace = tk.Frame(self, bg=SURFACE)
        workspace.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=18,
            pady=(10, 18),
        )
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(1, weight=1)

        heading = tk.Label(
            workspace,
            text="Settings",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(18, "bold"),
            anchor="w",
        )
        heading.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=22,
            pady=(20, 14),
        )

        settings_body = tk.Frame(workspace, bg=SURFACE)
        settings_body.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=22,
            pady=(0, 22),
        )
        settings_body.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="settings",
        )
        settings_body.grid_rowconfigure(0, weight=1)

        assignment_panel = SectionPanel(
            settings_body,
            "Assignment of development strategy",
            (
                "Choose how a development strategy is registered when a new "
                "magician is created."
            ),
        )
        assignment_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
        )
        assignment_panel.content.grid_columnconfigure(0, weight=1)

        for row_index, (policy, label_text) in enumerate(
            DEVELOPMENT_ASSIGNMENT_OPTIONS
        ):
            option = tk.Radiobutton(
                assignment_panel.content,
                text=label_text,
                value=policy,
                variable=self.assignment_value,
                bg=SURFACE_MUTED,
                fg=TEXT_DARK,
                activebackground=SURFACE_MUTED,
                activeforeground=TEXT_DARK,
                selectcolor=FIELD_BACKGROUND,
                font=app_font(10),
                anchor="w",
                justify="left",
                borderwidth=0,
                highlightthickness=0,
            )
            option.grid(
                row=row_index,
                column=0,
                sticky="ew",
                pady=5,
            )

        note = tk.Label(
            assignment_panel.content,
            text=(
                "This setting applies to future assignments. A magician's "
                "saved strategy can still be changed on their Development page."
            ),
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
            justify="left",
            wraplength=440,
        )
        note.grid(
            row=len(DEVELOPMENT_ASSIGNMENT_OPTIONS),
            column=0,
            sticky="ew",
            pady=(12, 0),
        )

        groups_panel = SectionPanel(
            settings_body,
            "Mage groups",
            (
                "Every mage belongs to one group. Its color appears beside "
                "the mage in the list and profile header."
            ),
        )
        groups_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
        )
        groups_panel.content.grid_columnconfigure(0, weight=1)
        groups_panel.content.grid_rowconfigure(0, weight=1)

        self.group_list = MageGroupList(
            groups_panel.content,
            self.select_group,
        )
        self.group_list.grid(
            row=0,
            column=0,
            sticky="nsew",
            pady=(0, 12),
        )

        editor = tk.Frame(groups_panel.content, bg=SURFACE_MUTED)
        editor.grid(row=1, column=0, sticky="ew")
        editor.grid_columnconfigure(0, weight=1)

        self.group_name_field = LabeledEntry(
            editor,
            "Group name",
            self.group_name_value,
            background=SURFACE_MUTED,
        )
        self.group_name_field.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 8),
        )

        color_block = tk.Frame(editor, bg=SURFACE_MUTED)
        color_block.grid(row=0, column=1, sticky="ne")
        color_label = tk.Label(
            color_block,
            text="Color",
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        color_label.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 5),
        )
        self.color_button = SoftButton(
            color_block,
            text="#8A738F",
            command=self.choose_group_color,
            background=SURFACE_MUTED,
            fill="#8A738F",
            hover_fill="#8A738F",
            foreground="#FFFFFF",
            width=112,
            height=40,
        )
        self.color_button.grid(row=1, column=0, sticky="e")

        actions = tk.Frame(groups_panel.content, bg=SURFACE_MUTED)
        actions.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(12, 0),
        )
        actions.grid_columnconfigure(0, weight=1)
        self.new_group_button = SoftButton(
            actions,
            text="New group",
            command=self.begin_new_group,
            background=SURFACE_MUTED,
            width=108,
            height=38,
        )
        self.new_group_button.grid(row=0, column=0, sticky="w")
        self.remove_group_button = SoftButton(
            actions,
            text="Remove",
            command=self.remove_group,
            background=SURFACE_MUTED,
            fill=DELETE_SOFT,
            hover_fill=DELETE_HOVER,
            foreground=TEXT_DARK,
            width=90,
            height=38,
        )
        self.remove_group_button.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(0, 8),
        )
        self.save_group_button = SoftButton(
            actions,
            text="Save group",
            command=self.save_group,
            background=SURFACE_MUTED,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=112,
            height=38,
        )
        self.save_group_button.grid(
            row=0,
            column=2,
            sticky="e",
        )

    def refresh(self):
        self.loading = True
        self.assignment_value.set(
            self.controller.development_assignment_policy()
        )
        groups = self.controller.mage_groups()
        available_group_ids = {
            group["group_id"]
            for group in groups
        }

        if self.selected_group_id not in available_group_ids:
            self.selected_group_id = (
                self.controller.default_mage_group_id()
            )

        self.group_list.set_groups(
            groups,
            self.controller.mage_group_usage_counts(),
            self.selected_group_id,
        )
        self.populate_group_editor()
        self.loading = False

    def assignment_changed(self, *arguments):
        if self.loading:
            return

        if self.controller.set_development_assignment_policy(
            self.assignment_value.get()
        ):
            self.status_command(
                "Development strategy assignment setting updated"
            )

    def select_group(self, group_id):
        self.selected_group_id = str(group_id or "").strip()
        self.group_list.set_selected_group(self.selected_group_id)
        self.populate_group_editor()

    def populate_group_editor(self):
        selected_group = next(
            (
                group
                for group in self.controller.mage_groups()
                if group["group_id"] == self.selected_group_id
            ),
            None,
        )

        if selected_group is None:
            self.group_name_value.set("")
            self.group_color_value.set(
                self.controller.next_mage_group_color()
            )
        else:
            self.group_name_value.set(selected_group["name"])
            self.group_color_value.set(selected_group["color"])

        self.update_color_button()
        self.remove_group_button.set_enabled(
            bool(selected_group)
            and self.selected_group_id != DEFAULT_MAGE_GROUP_ID
        )

    def begin_new_group(self):
        self.selected_group_id = None
        self.group_list.set_selected_group(None)
        self.group_name_value.set("")
        self.group_color_value.set(
            self.controller.next_mage_group_color()
        )
        self.update_color_button()
        self.remove_group_button.set_enabled(False)
        self.group_name_field.control.focus_set()

    def choose_group_color(self):
        selected_color = colorchooser.askcolor(
            color=self.group_color_value.get(),
            title="Choose mage group color",
            parent=self,
        )

        if not selected_color or not selected_color[1]:
            return

        self.group_color_value.set(selected_color[1].upper())
        self.update_color_button()

    def update_color_button(self):
        color = self.group_color_value.get() or "#8A738F"

        try:
            foreground = contrasting_text_color(color)
        except ValueError:
            color = "#8A738F"
            foreground = "#FFFFFF"

        self.group_color_value.set(color)
        self.color_button.set_text(color)
        self.color_button.set_colors(
            color,
            color,
            foreground,
        )

    def save_group(self):
        try:
            if self.selected_group_id:
                saved_group = self.controller.update_mage_group(
                    self.selected_group_id,
                    self.group_name_value.get(),
                    self.group_color_value.get(),
                )
                status_text = f"Updated mage group {saved_group['name']}"
            else:
                saved_group = self.controller.create_mage_group(
                    self.group_name_value.get(),
                    self.group_color_value.get(),
                )
                status_text = f"Created mage group {saved_group['name']}"
        except (KeyError, TypeError, ValueError) as error:
            messagebox.showerror(
                "Cannot save mage group",
                str(error),
                parent=self,
            )
            return False

        self.selected_group_id = saved_group["group_id"]
        self.refresh()
        self.notify_groups_changed()
        self.status_command(status_text)
        return True

    def remove_group(self):
        selected_group = next(
            (
                group
                for group in self.controller.mage_groups()
                if group["group_id"] == self.selected_group_id
            ),
            None,
        )

        if selected_group is None:
            return False

        usage_count = self.controller.mage_group_usage_counts().get(
            self.selected_group_id,
            0,
        )
        reassignment_text = (
            ""
            if not usage_count
            else (
                f"\n\n{usage_count} "
                f"{'mage' if usage_count == 1 else 'mages'} will move "
                "to the default group."
            )
        )

        if not messagebox.askyesno(
            "Remove mage group",
            (
                f"Remove {selected_group['name']}?"
                f"{reassignment_text}"
            ),
            parent=self,
        ):
            return False

        try:
            reassigned_count = self.controller.delete_mage_group(
                self.selected_group_id
            )
        except (KeyError, TypeError, ValueError) as error:
            messagebox.showerror(
                "Cannot remove mage group",
                str(error),
                parent=self,
            )
            return False

        self.selected_group_id = (
            self.controller.default_mage_group_id()
        )
        self.refresh()
        self.notify_groups_changed()
        self.status_command(
            (
                "Mage group removed"
                if not reassigned_count
                else (
                    "Mage group removed and "
                    f"{reassigned_count} "
                    f"{'mage was' if reassigned_count == 1 else 'mages were'} "
                    "reassigned"
                )
            )
        )
        return True

    def notify_groups_changed(self):
        if self.groups_changed_command is not None:
            self.groups_changed_command()


class MageGroupList(tk.Frame):
    def __init__(self, parent, selection_command):
        super().__init__(
            parent,
            bg=FIELD_BACKGROUND,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
        )
        self.selection_command = selection_command
        self.groups = []
        self.usage_counts = {}
        self.selected_group_id = None
        self.hovered_group_id = None
        self.rows_by_id = {}
        self.labels_by_id = {}
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            bg=FIELD_BACKGROUND,
            highlightthickness=0,
            borderwidth=0,
            height=210,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self.resize_rows)
        self.canvas.bind("<MouseWheel>", self.scroll_groups)

        scrollbar = tk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            relief="flat",
            borderwidth=0,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.row_container = tk.Frame(
            self.canvas,
            bg=FIELD_BACKGROUND,
        )
        self.row_container.grid_columnconfigure(0, weight=1)
        self.row_container.bind(
            "<Configure>",
            self.update_scroll_region,
        )
        self.row_window = self.canvas.create_window(
            (0, 0),
            window=self.row_container,
            anchor="nw",
        )

    def set_groups(
        self,
        groups,
        usage_counts,
        selected_group_id=None,
    ):
        self.groups = list(groups)
        self.usage_counts = dict(usage_counts or {})
        self.selected_group_id = selected_group_id

        for row in self.rows_by_id.values():
            row.destroy()

        self.rows_by_id = {}
        self.labels_by_id = {}

        for row_index, group in enumerate(self.groups):
            group_id = group["group_id"]
            row = tk.Frame(
                self.row_container,
                bg=FIELD_BACKGROUND,
                cursor="hand2",
            )
            row.grid(
                row=row_index,
                column=0,
                sticky="ew",
            )
            row.grid_columnconfigure(1, weight=1)
            color_bar = tk.Frame(
                row,
                bg=group["color"],
                width=8,
                cursor="hand2",
            )
            color_bar.grid(row=0, column=0, sticky="ns")
            color_bar.grid_propagate(False)
            label = tk.Label(
                row,
                text=group["name"],
                bg=FIELD_BACKGROUND,
                fg=TEXT_DARK,
                font=app_font(10, "bold"),
                anchor="w",
                padx=10,
                pady=8,
                cursor="hand2",
            )
            label.grid(row=0, column=1, sticky="ew")
            usage_count = self.usage_counts.get(group_id, 0)
            usage_text = (
                f"{usage_count} "
                f"{'mage' if usage_count == 1 else 'mages'}"
            )

            if group_id == DEFAULT_MAGE_GROUP_ID:
                usage_text = f"Default  ·  {usage_text}"

            count_label = tk.Label(
                row,
                text=usage_text,
                bg=FIELD_BACKGROUND,
                fg=TEXT_MUTED,
                font=app_font(9),
                anchor="e",
                padx=10,
                cursor="hand2",
            )
            count_label.grid(row=0, column=2, sticky="e")

            for widget in (row, color_bar, label, count_label):
                widget.bind(
                    "<Button-1>",
                    partial(self.select_group, group_id),
                )
                widget.bind(
                    "<Enter>",
                    partial(self.enter_group, group_id),
                )
                widget.bind(
                    "<Leave>",
                    partial(self.leave_group, group_id),
                )
                widget.bind("<MouseWheel>", self.scroll_groups)

            self.rows_by_id[group_id] = row
            self.labels_by_id[group_id] = (label, count_label)

        self.refresh_row_colors()
        self.update_scroll_region()

    def set_selected_group(self, group_id):
        self.selected_group_id = str(group_id or "").strip() or None
        self.refresh_row_colors()

    def select_group(self, group_id, event=None):
        self.selected_group_id = group_id
        self.refresh_row_colors()
        self.selection_command(group_id)

    def enter_group(self, group_id, event=None):
        self.hovered_group_id = group_id
        self.refresh_row_colors()

    def leave_group(self, group_id, event=None):
        if self.hovered_group_id == group_id:
            self.hovered_group_id = None

        self.refresh_row_colors()

    def refresh_row_colors(self):
        for row_index, group in enumerate(self.groups):
            group_id = group["group_id"]

            if group_id == self.selected_group_id:
                background = LIST_SELECTED
            elif group_id == self.hovered_group_id:
                background = LIST_HOVER
            elif row_index % 2:
                background = LIST_ALTERNATE
            else:
                background = FIELD_BACKGROUND

            row = self.rows_by_id.get(group_id)

            if row is not None:
                row.configure(bg=background)

            labels = self.labels_by_id.get(group_id, ())

            for label in labels:
                label.configure(bg=background)

    def resize_rows(self, event):
        self.canvas.itemconfigure(
            self.row_window,
            width=max(1, event.width),
        )
        self.update_scroll_region()

    def update_scroll_region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def scroll_groups(self, event):
        if event.delta:
            self.canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units",
            )

        return "break"
