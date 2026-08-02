import tkinter as tk
from tkinter import messagebox
from mage_maker.sections.organizations.controller import (
    new_organization_job,
    normalize_organization_job,
)
from mage_maker.ui.theme import (
    APP_BACKGROUND,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    SURFACE,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
)
from mage_maker.ui.widgets import (
    CalendarAdoptionNotice,
    RoundedEntry,
    SoftButton,
)


class OrganizationJobDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        save_command,
        existing_job=None,
        default_opened_year=None,
    ):
        super().__init__(parent)
        self.save_command = save_command
        self.existing_job = (
            normalize_organization_job(existing_job)
            if isinstance(existing_job, dict)
            else None
        )
        self.title_value = tk.StringVar(
            value=(
                self.existing_job["title"]
                if self.existing_job is not None
                else ""
            )
        )
        self.opened_year_value = tk.StringVar(
            value=(
                str(self.existing_job["opened_year"])
                if self.existing_job is not None
                else (
                    ""
                    if default_opened_year in (None, "")
                    else str(default_opened_year)
                )
            )
        )
        self.title(
            "Edit organization job"
            if self.existing_job is not None
            else "Add organization job"
        )
        self.configure(bg=APP_BACKGROUND)
        self.geometry("640x365")
        self.minsize(580, 340)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_dialog()
        self.update_idletasks()
        self.position_upper_right()
        self.grab_set()
        self.after_idle(self.focus_title)

    def build_dialog(self):
        header = tk.Frame(self, bg=PRIMARY_DARK, height=58)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        heading = tk.Label(
            header,
            text=(
                "Edit organization job"
                if self.existing_job is not None
                else "Add organization job"
            ),
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(15, "bold"),
            anchor="w",
            padx=18,
        )
        heading.pack(fill="both", expand=True)

        body = tk.Frame(
            self,
            bg=SURFACE,
            padx=20,
            pady=18,
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        title_label = tk.Label(
            body,
            text="Title",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="ew")
        self.title_entry = RoundedEntry(
            body,
            textvariable=self.title_value,
            background=SURFACE,
            width=500,
            height=38,
            font=app_font(10),
        )
        self.title_entry.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 14),
        )

        opened_year_label = tk.Label(
            body,
            text="Position opened",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=app_font(9, "bold"),
            anchor="w",
        )
        opened_year_label.grid(row=2, column=0, sticky="ew")
        opened_year_entry = RoundedEntry(
            body,
            textvariable=self.opened_year_value,
            background=SURFACE,
            width=150,
            height=38,
            font=app_font(10),
            justify="center",
        )
        opened_year_entry.grid(
            row=3,
            column=0,
            sticky="w",
            pady=(5, 0),
        )
        calendar_notice = CalendarAdoptionNotice(
            body,
            background=SURFACE,
            wraplength=500,
        )
        calendar_notice.grid(
            row=4,
            column=0,
            sticky="w",
            pady=(6, 0),
        )

        footer = tk.Frame(self, bg=APP_BACKGROUND)
        footer.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 16),
        )
        footer.grid_columnconfigure(0, weight=1)
        cancel_button = SoftButton(
            footer,
            text="Cancel",
            command=self.close_dialog,
            background=APP_BACKGROUND,
            width=92,
            height=36,
        )
        cancel_button.grid(row=0, column=1, padx=(0, 7))
        save_button = SoftButton(
            footer,
            text=(
                "Save changes"
                if self.existing_job is not None
                else "Add job"
            ),
            command=self.save_job,
            background=APP_BACKGROUND,
            fill=PRIMARY,
            hover_fill=PRIMARY_HOVER,
            foreground=TEXT_DARK,
            width=122,
            height=36,
        )
        save_button.grid(row=0, column=2)

    def position_upper_right(self):
        owner = self.master.winfo_toplevel()
        dialog_width = max(580, self.winfo_width())
        dialog_height = max(340, self.winfo_height())
        owner_left = owner.winfo_rootx()
        owner_top = owner.winfo_rooty()
        owner_width = max(owner.winfo_width(), dialog_width + 48)
        x_position = owner_left + owner_width - dialog_width - 24
        y_position = owner_top + 72
        self.geometry(
            f"{dialog_width}x{dialog_height}+{x_position}+{y_position}"
        )
        self.lift()

    def focus_title(self):
        self.title_entry.entry.focus_set()
        self.title_entry.entry.selection_range(0, "end")

    def save_job(self):
        try:
            job = new_organization_job(
                self.title_value.get(),
                self.opened_year_value.get(),
            )

            if self.existing_job is not None:
                job["record_id"] = self.existing_job[
                    "record_id"
                ]
                job = normalize_organization_job(job)
        except (TypeError, ValueError) as error:
            messagebox.showerror(
                "Cannot save organization job",
                str(error),
                parent=self,
            )
            return

        self.save_command(job)
        self.destroy()

    def close_dialog(self, event=None):
        self.destroy()
        return "break"
