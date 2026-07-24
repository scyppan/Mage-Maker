import unittest
from copy import deepcopy

from mage_maker.sections.events.editor import (
    NEW_EVENT_DRAFT_ID,
    EventEditor,
)
from mage_maker.sections.events.period_view import PeriodEventsView
from mage_maker.sections.locations.page import LocationPage
from mage_maker.sections.timeline.page import TimelineView


class FakeVariable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeControl:
    def __init__(self):
        self.enabled = True
        self.focused = False

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

    def focus_set(self):
        self.focused = True


class FakeField:
    def __init__(self):
        self.control = FakeControl()


class FakeText:
    def __init__(self):
        self.state = "normal"
        self.value = ""

    def configure(self, **values):
        if "state" in values:
            self.state = values["state"]

    def delete(self, start, end):
        self.value = ""

    def insert(self, start, value):
        self.value = str(value)

    def get(self, start, end):
        return self.value


class FakeTextControl:
    def __init__(self):
        self.text = FakeText()


class FakePicker:
    def __init__(self):
        self.selected_ids = []
        self.locked_ids = set()
        self.enabled = True
        self.visible = True

    def set_values(self, selected_ids=(), locked_ids=()):
        self.selected_ids = list(selected_ids)
        self.locked_ids = set(locked_ids)

    def get_values(self):
        return list(self.selected_ids)

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

    def grid(self, **values):
        self.visible = True

    def grid_remove(self):
        self.visible = False


class FakeSelect(FakeControl):
    def __init__(self):
        super().__init__()
        self.values = []

    def set_values(self, values):
        self.values = list(values)


class FakeCanvas:
    def __init__(self):
        self.position = 0

    def yview_moveto(self, position):
        self.position = position


class FakeForm:
    def after_idle(self, command):
        return None


class FakeController:
    def period_names_for_date(self, value):
        return ["Test period"] if str(value or "").strip() else []


class FakeListbox:
    def __init__(self):
        self.rows = []
        self.selection = ()

    def delete(self, start, end):
        self.rows = []
        self.selection = ()

    def insert(self, index, value):
        self.rows.append(str(value))

    def itemconfigure(self, index, **values):
        return None

    def selection_set(self, index):
        self.selection = (int(index),)

    def selection_clear(self, start, end):
        self.selection = ()

    def see(self, index):
        return None

    def curselection(self):
        return self.selection


class FakeInlineEditor:
    def __init__(self):
        self.mode = "empty"
        self.enabled = False
        self.start_arguments = {}

    def is_new_event(self):
        return self.mode == "new"

    def start_new(self, **values):
        self.mode = "new"
        self.enabled = True
        self.start_arguments = deepcopy(values)

    def ensure_new_event_editable(self):
        if self.mode != "new":
            return False

        self.enabled = True
        return True

    def show_error(self, message):
        return None


class FakeLoadedEditor:
    def __init__(self):
        self.loaded_event = None
        self.load_values = {}
        self.edit_started = False
        self.canvas = FakeCanvas()

    def is_new_event(self):
        return False

    def load_event(self, event, **values):
        self.loaded_event = deepcopy(event)
        self.load_values = deepcopy(values)

    def begin_edit(self):
        self.edit_started = True
        return True

    def clear(self, message):
        self.loaded_event = None


class FakeEventController:
    def __init__(self, event):
        self.event = deepcopy(event)

    def get_event(self, record_id):
        if record_id != self.event.get("record_id"):
            return None

        return deepcopy(self.event)


class PersonTimelineHarness(TimelineView):
    def __init__(self):
        self.event_controller = object()
        self.events = []
        self.linked_events = []
        self.visible_events = []
        self.draft_event = None
        self.selected_event_id = None
        self.search_value = FakeVariable()
        self.listbox = FakeListbox()
        self.event_editor = FakeInlineEditor()

    def current_person_id(self):
        return "maeve"

    def reset_remove_confirmation(self):
        return None

    def show_event_editor(self):
        return None

    def hide_event_editor(self):
        return None

    def update_button_state(self):
        return None


class LocationPageHarness(LocationPage):
    def __init__(self):
        self.current_location_id = "limerick"
        self.event_controller = object()
        self.draft_event = None
        self.selected_timeline_event_id = ""
        self.event_editor = FakeInlineEditor()
        self.timeline_edit_button = FakeControl()
        self.timeline_remove_button = FakeControl()

    def reset_event_remove_confirmation(self):
        return None

    def refresh_timeline(self):
        self.update_timeline_details()

    def selected_timeline_event(self):
        return self.draft_event

    def show_event_editor(self):
        return None

    def status_command(self, message):
        return None


class PeriodEventsHarness(PeriodEventsView):
    def __init__(self):
        self.period = {
            "name": "Test period",
            "calculation_start_year": 900,
            "calculation_end_year": 999,
        }
        self.draft_event = None
        self.selected_event_id = ""
        self.event_editor = FakeInlineEditor()

    def reset_remove_confirmation(self):
        return None

    def refresh(self, selected_event_id=""):
        self.update_editor()

    def selected_event(self):
        return self.draft_event

    def show_event_editor(self):
        return None

    def status_command(self, message):
        return None


class LocationSelectionHarness(LocationPage):
    def __init__(self):
        self.current_location_id = "limerick"
        self.selected_timeline_event_id = "event-1"
        self.selected_event_value = {
            "event_id": "event-1",
            "record_id": "event-1",
            "event_kind": "global",
            "event_type": "other",
            "title": "Limerick grows",
            "date": "951",
            "propagation_distance": 0,
            "origin_location_id": "limerick",
        }
        self.event_controller = FakeEventController(
            {
                "record_id": "event-1",
                "event_type": "other",
                "title": "Limerick grows",
                "date": "951",
                "description": "",
                "person_ids": [],
                "period_names": [],
                "location_ids": ["limerick"],
                "locked_location_ids": ["limerick"],
            }
        )
        self.event_editor = FakeLoadedEditor()
        self.timeline_edit_button = FakeControl()
        self.timeline_remove_button = FakeControl()

    def selected_timeline_event(self):
        return self.selected_event_value

    def show_event_editor(self):
        return None


class EventEditorFactory:
    @staticmethod
    def build():
        editor = object.__new__(EventEditor)
        editor.controller = FakeController()
        editor.context = "person"
        editor.event = {}
        editor.storage_kind = "shared"
        editor.editor_mode = "empty"
        editor.controls_enabled = False
        editor.read_only = True
        editor.lock_type = False
        editor.hide_locations = False
        editor.feedback_after_id = None
        editor.heading_value = FakeVariable()
        editor.explanation_value = FakeVariable()
        editor.title_value = FakeVariable()
        editor.event_type_value = FakeVariable()
        editor.year_value = FakeVariable()
        editor.month_value = FakeVariable()
        editor.day_value = FakeVariable()
        editor.period_value = FakeVariable()
        editor.feedback_value = FakeVariable()
        editor.type_picker = FakeSelect()
        editor.title_field = FakeField()
        editor.year_field = FakeField()
        editor.month_field = FakeField()
        editor.day_field = FakeField()
        editor.description_control = FakeTextControl()
        editor.people_picker = FakePicker()
        editor.locations_picker = FakePicker()
        editor.save_button = FakeControl()
        editor.cancel_button = FakeControl()
        editor.canvas = FakeCanvas()
        editor.form = FakeForm()
        return editor


class EventEditorStateTests(unittest.TestCase):
    def test_selected_editable_event_requires_edit_then_unlocks_every_field(self):
        editor = EventEditorFactory.build()
        editor.load_event(
            {
                "event_type": "custom",
                "detail": "Relocates to Limerick",
                "date": "0965",
                "note": "A move.",
                "automatic_source": "",
            },
            storage_kind="timeline",
            context="person",
            person_ids=("maeve",),
            read_only=False,
        )

        self.assertEqual("view", editor.editor_mode)
        self.assertFalse(editor.controls_enabled)
        self.assertFalse(editor.save_button.enabled)
        self.assertTrue(editor.begin_edit())
        self.assertEqual("edit", editor.editor_mode)
        self.assertTrue(editor.controls_enabled)
        self.assertTrue(editor.type_picker.enabled)
        self.assertTrue(editor.title_field.control.enabled)
        self.assertTrue(editor.year_field.control.enabled)
        self.assertTrue(editor.month_field.control.enabled)
        self.assertTrue(editor.day_field.control.enabled)
        self.assertEqual("normal", editor.description_control.text.state)
        self.assertTrue(editor.people_picker.enabled)
        self.assertTrue(editor.locations_picker.enabled)
        self.assertTrue(editor.save_button.enabled)

    def test_generated_event_cannot_be_unlocked(self):
        editor = EventEditorFactory.build()
        editor.load_event(
            {
                "event_type": "born",
                "detail": "",
                "date": "0901",
                "automatic_source": "life_start",
            },
            storage_kind="timeline",
            context="person",
            read_only=True,
        )

        self.assertEqual("view", editor.editor_mode)
        self.assertFalse(editor.begin_edit())
        self.assertFalse(editor.controls_enabled)

    def test_new_event_is_immediately_editable(self):
        editor = EventEditorFactory.build()
        editor.start_new(
            context="location",
            default_location_ids=("limerick",),
            locked_location_ids=("limerick",),
            hide_locations=True,
        )

        self.assertEqual("new", editor.editor_mode)
        self.assertTrue(editor.controls_enabled)
        self.assertTrue(editor.save_button.enabled)
        self.assertFalse(editor.locations_picker.visible)
        self.assertEqual(["limerick"], editor.locations_picker.selected_ids)
        self.assertEqual({"limerick"}, editor.locations_picker.locked_ids)


class DraftRowWorkflowTests(unittest.TestCase):
    def test_person_add_event_creates_a_selected_visible_draft(self):
        view = PersonTimelineHarness()

        TimelineView.start_add_event(view)

        self.assertEqual(NEW_EVENT_DRAFT_ID, view.selected_event_id)
        self.assertEqual(
            ["New event (unsaved)"],
            view.listbox.rows,
        )
        self.assertEqual((0,), view.listbox.curselection())
        self.assertTrue(view.event_editor.enabled)
        self.assertEqual(
            ("maeve",),
            view.event_editor.start_arguments["default_person_ids"],
        )

    def test_location_add_event_creates_a_selected_locked_draft(self):
        page = LocationPageHarness()

        LocationPage.add_event(page)

        self.assertEqual(
            NEW_EVENT_DRAFT_ID,
            page.selected_timeline_event_id,
        )
        self.assertTrue(page.event_editor.enabled)
        self.assertEqual(
            ("limerick",),
            page.event_editor.start_arguments["default_location_ids"],
        )
        self.assertEqual(
            ("limerick",),
            page.event_editor.start_arguments["locked_location_ids"],
        )
        self.assertTrue(page.event_editor.start_arguments["hide_locations"])

    def test_period_add_event_creates_a_selected_visible_draft(self):
        view = PeriodEventsHarness()

        PeriodEventsView.add_event(view)

        self.assertEqual(NEW_EVENT_DRAFT_ID, view.selected_event_id)
        self.assertTrue(view.event_editor.enabled)
        self.assertEqual(
            "period",
            view.event_editor.start_arguments["context"],
        )


class EventButtonStateTests(unittest.TestCase):
    def test_person_manual_event_enables_edit_and_remove(self):
        view = object.__new__(TimelineView)
        view.visible_events = [
            {
                "event_id": "move",
                "event_type": "custom",
                "detail": "Relocates to Limerick",
                "automatic_source": "",
            }
        ]
        view.selected_event_id = "move"
        view.listbox = FakeListbox()
        view.edit_button = FakeControl()
        view.remove_button = FakeControl()

        TimelineView.update_button_state(view)

        self.assertTrue(view.edit_button.enabled)
        self.assertTrue(view.remove_button.enabled)

    def test_location_local_event_enables_edit_then_unlocks_editor(self):
        page = LocationSelectionHarness()

        LocationPage.update_timeline_details(page)

        self.assertTrue(page.timeline_edit_button.enabled)
        self.assertTrue(page.timeline_remove_button.enabled)
        self.assertFalse(page.event_editor.load_values["read_only"])
        LocationPage.edit_event(page)
        self.assertTrue(page.event_editor.edit_started)

    def test_period_stored_event_enables_edit_and_remove(self):
        view = object.__new__(PeriodEventsView)
        view.events = [
            {
                "event_id": "event-1",
                "event_kind": "global",
            }
        ]
        view.selected_event_id = "event-1"
        view.listbox = FakeListbox()
        view.edit_button = FakeControl()
        view.remove_button = FakeControl()

        PeriodEventsView.update_button_state(view)

        self.assertTrue(view.edit_button.enabled)
        self.assertTrue(view.remove_button.enabled)


if __name__ == "__main__":
    unittest.main()
