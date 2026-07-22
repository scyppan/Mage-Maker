import tkinter as tk
from copy import deepcopy
from functools import partial
from tkinter import messagebox

from mage_maker.name_history import (
    empty_name_details,
    migrate_legacy_name_details,
    new_name_entry,
    normalize_name_entry,
)
from mage_maker.theme import (
    APP_BACKGROUND,
    BORDER,
    BORDER_SOFT,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    DELETE_HOVER,
    DELETE_SOFT,
    FIELD_BACKGROUND,
    LIST_ALTERNATE,
    LIST_HOVER,
    LIST_SELECTED,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.widgets import LabeledEntry, MultilineField, SoftButton


class NameDetailsDialog(tk.Toplevel):
    def __init__(self, parent, name_details, save_command, displayed_name=""):
        super().__init__(parent)
        self.save_command = save_command
        self.displayed_name = str(displayed_name or "").strip() or "Unnamed magician"
        migrated_details = migrate_legacy_name_details(
            name_details if isinstance(name_details, dict) else empty_name_details(),
            self.displayed_name,
        )
        self.entries = deepcopy(migrated_details["entries"])
        self.suppress_click = False
        self.dirty = False

        self.title(f"Name Details — {self.displayed_name}")
        self.geometry("820x560")
        self.minsize(700, 500)
        self.configure(bg=APP_BACKGROUND)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_header()
        self.build_workspace()
        self.refresh_entries()

        self.bind("<Escape>", self.close_dialog)
        self.bind("<Control-s>", self.save_shortcut)
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)

    def build_header(self):
        header = tk.Frame(self, bg=PRIMARY_DARK, height=62)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        title = tk.Label(
            header,
            text="Name Details",
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(17, "bold"),
            anchor="w",
            padx=22,
        )
        title.grid(row=0, column=0, sticky="nsew")

        current_name = tk.Label(
            header,
            text=self.displayed_name,
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(10),
            anchor="e",
            padx=22,
        )
        current_name.grid(row=0, column=1, sticky="nsew")

    def build_workspace(self):
        card = tk.Frame(
            self,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        card.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        card.grid_rowconfigure(2, weight=1)
        card.grid_columnconfigure(0, weight=1)

        heading = tk.Label(
            card,
            text="Name History",
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(14, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 3))

        introduction = tk.Label(
            card,
            text=(
                "Each line is one name record. Select a line to edit its type, "
                "name, date, or note."
            ),
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(10),
            justify="left",
            anchor="w",
        )
        introduction.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

        list_frame = tk.Frame(card, bg=SURFACE)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=16)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            list_frame,
            bg=FIELD_BACKGROUND,
            fg=TEXT_DARK,
            selectbackground=LIST_SELECTED,
            selectforeground=TEXT_DARK,
            relief="flat",
            highlightbackground=BORDER_SOFT,
            highlightcolor=BORDER_SOFT,
            highlightthickness=1,
            borderwidth=0,
            font=app_font(11),
            activestyle="none",
            exportselection=False,
            selectmode="browse",
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.bind("<ButtonRelease-1>", self.open_clicked_entry)
        self.listbox.bind("<Motion>", self.hover_entry)
        self.listbox.bind("<Leave>", self.clear_hover)

        scrollbar = tk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.listbox.yview,
            relief="flat",
            borderwidth=0,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        footer = tk.Frame(card, bg=SURFACE)
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=16)
        footer.grid_columnconfigure(0, weight=1)

        self.status_value = tk.StringVar(value="")
        status = tk.Label(
            footer,
            textvariable=self.status_value,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
        )
        status.grid(row=0, column=0, sticky="ew")

        add_button = SoftButton(
            footer,
            text="Add Name",
            command=self.add_entry,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=104,
            height=38,
        )
        add_button.grid(row=0, column=1, padx=(6, 0))

        edit_button = SoftButton(
            footer,
            text="Edit Selected",
            command=self.edit_selected_entry,
            background=SURFACE,
            width=122,
            height=38,
        )
        edit_button.grid(row=0, column=2, padx=(6, 0))

        delete_button = SoftButton(
            footer,
            text="Delete",
            command=self.delete_selected_entry,
            background=SURFACE,
            fill=DELETE_SOFT,
            hover_fill=DELETE_HOVER,
            width=88,
            height=38,
        )
        delete_button.grid(row=0, column=3, padx=(6, 0))

        apply_button = SoftButton(
            footer,
            text="Apply",
            command=self.save_details,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=88,
            height=38,
        )
        apply_button.grid(row=0, column=4, padx=(6, 0))

    def refresh_entries(self, selected_index=None):
        self.suppress_click = True
        self.listbox.delete(0, "end")

        for index, entry in enumerate(self.entries):
            date_text = str(entry.get("date", "") or "").strip() or "nd."
            self.listbox.insert(
                "end",
                f"{date_text}: {entry['name_entry']} ({entry['name_type']})",
            )
            self.listbox.itemconfigure(
                index,
                background=FIELD_BACKGROUND if index % 2 == 0 else LIST_ALTERNATE,
                foreground=TEXT_DARK,
                selectbackground=LIST_SELECTED,
                selectforeground=TEXT_DARK,
            )

        if selected_index is not None and 0 <= selected_index < len(self.entries):
            self.listbox.selection_set(selected_index)
            self.listbox.activate(selected_index)
            self.listbox.see(selected_index)

        entry_word = "entry" if len(self.entries) == 1 else "entries"
        self.status_value.set(f"{len(self.entries)} name history {entry_word}")
        self.suppress_click = False

    def add_entry(self):
        NameEntryDialog(
            self,
            new_name_entry(),
            self.save_new_entry,
            "Add Name",
        )

    def save_new_entry(self, entry):
        self.entries.append(normalize_name_entry(entry))
        self.dirty = True
        self.refresh_entries(len(self.entries) - 1)

    def open_clicked_entry(self, event):
        if self.suppress_click or not self.entries:
            return

        clicked_index = self.listbox.nearest(event.y)
        bounding_box = self.listbox.bbox(clicked_index)

        if bounding_box is None:
            return

        row_top = bounding_box[1]
        row_bottom = row_top + bounding_box[3]

        if not row_top <= event.y <= row_bottom:
            return

        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(clicked_index)
        self.open_entry_editor(clicked_index)

    def edit_selected_entry(self):
        selected_indices = self.listbox.curselection()

        if not selected_indices:
            messagebox.showinfo(
                "Select a name",
                "Select a name history line to edit.",
                parent=self,
            )
            return

        self.open_entry_editor(selected_indices[0])

    def open_entry_editor(self, entry_index):
        NameEntryDialog(
            self,
            self.entries[entry_index],
            partial(self.save_edited_entry, entry_index),
            "Edit Name",
        )

    def save_edited_entry(self, entry_index, entry):
        self.entries[entry_index] = normalize_name_entry(entry)
        self.dirty = True
        self.refresh_entries(entry_index)

    def delete_selected_entry(self):
        selected_indices = self.listbox.curselection()

        if not selected_indices:
            messagebox.showinfo(
                "Select a name",
                "Select a name history line to delete.",
                parent=self,
            )
            return

        selected_index = selected_indices[0]
        entry = self.entries[selected_index]

        if not messagebox.askyesno(
            "Delete name history entry",
            f"Delete {entry['name_type']}: {entry['name_entry']}?",
            parent=self,
        ):
            return

        del self.entries[selected_index]
        self.dirty = True
        next_index = min(selected_index, len(self.entries) - 1)
        self.refresh_entries(next_index if next_index >= 0 else None)

    def hover_entry(self, event):
        if not self.entries:
            return

        hovered_index = self.listbox.nearest(event.y)

        for index in range(len(self.entries)):
            if index == hovered_index and index not in self.listbox.curselection():
                background = LIST_HOVER
            elif index % 2 == 0:
                background = FIELD_BACKGROUND
            else:
                background = LIST_ALTERNATE

            self.listbox.itemconfigure(index, background=background)

    def clear_hover(self, event=None):
        for index in range(len(self.entries)):
            background = FIELD_BACKGROUND if index % 2 == 0 else LIST_ALTERNATE
            self.listbox.itemconfigure(index, background=background)

    def save_details(self):
        self.save_command({"entries": deepcopy(self.entries)})
        self.dirty = False
        self.destroy()

    def close_dialog(self, event=None):
        if self.dirty and not messagebox.askyesno(
            "Discard name changes",
            "Close Name Details without applying these changes?",
            parent=self,
        ):
            return "break"

        self.destroy()
        return "break"

    def save_shortcut(self, event=None):
        self.save_details()
        return "break"


class NameEntryDialog(tk.Toplevel):
    def __init__(self, parent, entry, save_command, title):
        super().__init__(parent)
        self.save_command = save_command
        self.entry_id = str(entry.get("entry_id", "") or "")
        self.values = {
            "name_type": tk.StringVar(value=str(entry.get("name_type", "") or "")),
            "name_entry": tk.StringVar(value=str(entry.get("name_entry", "") or "")),
            "date": tk.StringVar(value=str(entry.get("date", "") or "")),
        }

        self.title(title)
        self.geometry("650x440")
        self.minsize(560, 400)
        self.configure(bg=APP_BACKGROUND)
        self.transient(parent)
        self.grab_set()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_form(title, entry)
        self.bind("<Escape>", self.close_dialog)
        self.bind("<Control-s>", self.save_shortcut)
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)
        self.after_idle(self.focus_name_type)

    def build_form(self, title, entry):
        card = tk.Frame(
            self,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=18,
            pady=16,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        card.grid_columnconfigure((0, 1), weight=1, uniform="name_fields")
        card.grid_rowconfigure(3, weight=1)

        heading = tk.Label(
            card,
            text=title,
            bg=SURFACE,
            fg=TEXT_DARK,
            font=app_font(14, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        self.name_type_field = LabeledEntry(
            card,
            "Name type",
            self.values["name_type"],
            background=SURFACE,
        )
        self.name_type_field.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(0, 7),
            pady=(0, 12),
        )

        date_field = LabeledEntry(
            card,
            "Date (if applicable)",
            self.values["date"],
            background=SURFACE,
        )
        date_field.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(7, 0),
            pady=(0, 12),
        )

        name_entry_field = LabeledEntry(
            card,
            "Name entry",
            self.values["name_entry"],
            background=SURFACE,
        )
        name_entry_field.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 12),
        )

        note_field = MultilineField(
            card,
            "Note",
            5,
            background=SURFACE,
            hint_text="Optional context about this name.",
        )
        note_field.grid(row=3, column=0, columnspan=2, sticky="nsew")
        note_field.text.insert("1.0", str(entry.get("note", "") or ""))
        self.note_text = note_field.text

        footer = tk.Frame(card, bg=SURFACE)
        footer.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        footer.grid_columnconfigure(0, weight=1)

        cancel_button = SoftButton(
            footer,
            text="Cancel",
            command=self.close_dialog,
            background=SURFACE,
            fill=BUTTON_SOFT,
            hover_fill=BUTTON_SOFT_HOVER,
            width=88,
            height=38,
        )
        cancel_button.grid(row=0, column=1, padx=(6, 0))

        save_button = SoftButton(
            footer,
            text="Save Name",
            command=self.save_entry,
            background=SURFACE,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=106,
            height=38,
        )
        save_button.grid(row=0, column=2, padx=(6, 0))

    def get_entry(self):
        return {
            "entry_id": self.entry_id,
            "name_type": self.values["name_type"].get(),
            "name_entry": self.values["name_entry"].get(),
            "date": self.values["date"].get(),
            "note": self.note_text.get("1.0", "end-1c"),
        }

    def save_entry(self):
        try:
            entry = normalize_name_entry(self.get_entry())
        except (TypeError, ValueError) as error:
            messagebox.showerror("Cannot save name", str(error), parent=self)
            return

        self.save_command(entry)
        self.destroy()

    def close_dialog(self, event=None):
        self.destroy()
        return "break"

    def save_shortcut(self, event=None):
        self.save_entry()
        return "break"

    def focus_name_type(self):
        self.name_type_field.control.focus_set()
