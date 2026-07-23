import tkinter as tk
from pathlib import Path

from mage_maker.core.controller import PeopleController
from mage_maker.core.database import JsonDatabase
from mage_maker.core.game_database import GameDatabase, GameDatabaseError
from mage_maker.sections.locations.controller import LocationController
from mage_maker.sections.locations.page import LocationPage
from mage_maker.sections.mages.page import MagesPage
from mage_maker.sections.organizations.controller import OrganizationController
from mage_maker.sections.organizations.page import OrganizationPage
from mage_maker.ui.theme import (
    APP_BACKGROUND,
    BUTTON_SOFT,
    BUTTON_SOFT_HOVER,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    PRIMARY_LIGHT,
    SURFACE_MUTED,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    app_font,
    configure_tk_fonts,
)
from mage_maker.ui.widgets import SoftButton


class MageMakerApp(tk.Tk):
    def __init__(self, database_path=None, game_database_directory=None):
        super().__init__()
        configure_tk_fonts(self)
        application_directory = Path(__file__).resolve().parent.parent.parent
        resolved_database_path = (
            database_path or application_directory / "data" / "mage_maker.json"
        )
        resolved_game_database_directory = (
            game_database_directory
            or application_directory / "data" / "dbm"
        )
        self.title("Mage Maker")
        self.geometry("1320x820")
        self.minsize(1040, 680)
        self.configure(bg=APP_BACKGROUND)

        try:
            self.state("zoomed")
        except tk.TclError:
            pass

        self.database = JsonDatabase(resolved_database_path)
        self.database.load()
        self.game_database = GameDatabase(resolved_game_database_directory)

        try:
            self.game_database.load()
        except GameDatabaseError as error:
            self.game_database.mark_unavailable(error)

        self.people_controller = PeopleController(self.database)
        self.location_controller = LocationController(
            self.database,
            self.people_controller.list_people,
        )
        self.organization_controller = OrganizationController(
            self.database,
            self.location_controller.list_locations,
        )
        self.status_value = tk.StringVar(value="Ready")
        self.pages = {}
        self.navigation_buttons = {}
        self.active_page_name = "mages"
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.build_header()
        self.build_pages()
        self.build_status_bar()
        self.show_page("mages", confirm_change=False)
        self.bind("<Control-s>", self.save_shortcut)
        self.bind("<Control-n>", self.create_shortcut)
        self.bind("<Control-f>", self.search_shortcut)
        self.protocol("WM_DELETE_WINDOW", self.close_application)

        if self.game_database.error:
            self.set_status(self.game_database.error)

    def build_header(self):
        header = tk.Frame(self, bg=PRIMARY_DARK, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)
        title = tk.Label(
            header,
            text="Mage Maker",
            bg=PRIMARY_DARK,
            fg=TEXT_LIGHT,
            font=app_font(19, "bold"),
            anchor="w",
            padx=24,
        )
        title.grid(row=0, column=0, sticky="nsew")
        navigation = tk.Frame(header, bg=PRIMARY_DARK)
        navigation.grid(row=0, column=1, sticky="w", padx=(12, 0))

        for page_name, label, width in (
            ("mages", "Mages", 104),
            ("locations", "Locations", 116),
            ("organizations", "Organizations", 144),
        ):
            button = SoftButton(
                navigation,
                text=label,
                command=self.navigation_command(page_name),
                background=PRIMARY_DARK,
                fill=BUTTON_SOFT,
                hover_fill=BUTTON_SOFT_HOVER,
                foreground=TEXT_DARK,
                width=width,
                height=38,
            )
            button.pack(side="left", padx=(0, 8))
            self.navigation_buttons[page_name] = button

        subtitle = tk.Label(
            header,
            text="Worldbuilding Database",
            bg=PRIMARY_DARK,
            fg=PRIMARY_LIGHT,
            font=app_font(10),
            padx=24,
        )
        subtitle.grid(row=0, column=2, sticky="e")

    def navigation_command(self, page_name):
        return NavigationCommand(self, page_name)

    def build_pages(self):
        content = tk.Frame(self, bg=APP_BACKGROUND)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        self.pages["mages"] = MagesPage(
            content,
            self.people_controller,
            self.game_database,
            self.set_status,
            self.refresh_cross_page_data,
        )
        self.pages["locations"] = LocationPage(
            content,
            self.location_controller,
            self.set_status,
            self.open_mage,
        )
        self.pages["organizations"] = OrganizationPage(
            content,
            self.organization_controller,
            self.set_status,
        )

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def build_status_bar(self):
        status_bar = tk.Label(
            self,
            textvariable=self.status_value,
            bg=SURFACE_MUTED,
            fg=TEXT_MUTED,
            font=app_font(9),
            anchor="w",
            padx=12,
            pady=7,
        )
        status_bar.grid(row=2, column=0, sticky="ew")

    def show_page(self, page_name, confirm_change=True):
        if page_name not in self.pages:
            return False

        if (
            confirm_change
            and self.active_page_name == "mages"
            and page_name != "mages"
            and not self.pages["mages"].confirm_unsaved_changes()
        ):
            return False

        self.active_page_name = page_name

        if page_name == "locations":
            self.pages["locations"].refresh()
        elif page_name == "organizations":
            self.pages["organizations"].refresh()

        self.pages[page_name].tkraise()

        for name, button in self.navigation_buttons.items():
            if name == page_name:
                button.set_colors(PRIMARY, PRIMARY_HOVER, TEXT_DARK)
            else:
                button.set_colors(BUTTON_SOFT, BUTTON_SOFT_HOVER, TEXT_DARK)

        return True

    def open_mage(self, record_id):
        if not self.show_page("mages"):
            return False

        return self.pages["mages"].select_person(record_id)

    def refresh_cross_page_data(self):
        location_page = self.pages.get("locations")

        if location_page is not None and location_page.current_location_id:
            location_page.refresh_timeline()

    def set_status(self, message):
        self.status_value.set(str(message or "Ready"))

    def close_application(self):
        if self.pages["mages"].confirm_unsaved_changes():
            self.destroy()

    def save_shortcut(self, event=None):
        if self.active_page_name == "mages":
            self.pages["mages"].save_shortcut()
        elif self.active_page_name == "locations":
            self.pages["locations"].save_location()
        elif self.active_page_name == "organizations":
            self.pages["organizations"].save_organization()

        return "break"

    def create_shortcut(self, event=None):
        if self.active_page_name == "mages":
            self.pages["mages"].create_shortcut()
        elif self.active_page_name == "locations":
            self.pages["locations"].create_location()
        elif self.active_page_name == "organizations":
            self.pages["organizations"].create_organization()

        return "break"

    def search_shortcut(self, event=None):
        if self.active_page_name == "mages":
            self.pages["mages"].search_shortcut()

        return "break"


class NavigationCommand:
    def __init__(self, application, page_name):
        self.application = application
        self.page_name = page_name

    def __call__(self):
        self.application.show_page(self.page_name)
