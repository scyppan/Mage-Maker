import unittest
from copy import deepcopy
from unittest.mock import patch

from mage_maker.sections.events.editor import (
    NEW_EVENT_DRAFT_ID,
    EventAssociationPicker,
    EventEditor,
)
from mage_maker.sections.events.period_view import PeriodEventsView
from mage_maker.sections.locations.page import LocationPage
from mage_maker.sections.locations.models import recent_location_label
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
        self.text = ""

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

    def focus_set(self):
        self.focused = True

    def set_text(self, text):
        self.text = str(text)


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
        self.state = "normal"

    def delete(self, start, end):
        if self.state == "disabled":
            return

        self.rows = []
        self.selection = ()

    def insert(self, index, value):
        if self.state == "disabled":
            return

        self.rows.append(str(value))

    def itemconfigure(self, index, **values):
        if int(index) >= len(self.rows):
            raise IndexError(f"item number {index} out of range")

        return None

    def selection_set(self, index):
        self.selection = (int(index),)

    def selection_clear(self, start, end):
        self.selection = ()

    def see(self, index):
        return None

    def curselection(self):
        return self.selection

    def configure(self, **values):
        if "state" in values:
            self.state = str(values["state"])


class FakeAssociationController:
    def people_options(self):
        return [
            {"value": "maeve", "label": "Maeve"},
            {"value": "merlin", "label": "Merlin"},
            {"value": "morgana", "label": "Morgana"},
            {"value": "helga", "label": "Helga"},
            {"value": "godric", "label": "Godric"},
            {"value": "rowena", "label": "Rowena"},
            {"value": "salazar", "label": "Salazar"},
        ]

    def location_options(self):
        return [{"value": "limerick", "label": "Limerick"}]

    def location_records(self):
        return [
            {
                "record_id": "limerick",
                "name": "Limerick",
                "parent_location_id": "",
            }
        ]

    def recent_people_options(self, limit=5):
        return self.people_options()[:limit]

    def recent_location_options(self, limit=5):
        return self.location_options()[:limit]


class FakeLabel:
    def __init__(self):
        self.text = ""

    def configure(self, **values):
        if "text" in values:
            self.text = str(values["text"])


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


class EventAssociationPickerFactory:
    @staticmethod
    def build():
        picker = object.__new__(EventAssociationPicker)
        picker.controller = FakeAssociationController()
        picker.association_kind = "people"
        picker.options = []
        picker.visible_options = []
        picker.selected_ids = []
        picker.locked_ids = set()
        picker.locked_order = []
        picker.is_enabled = True
        picker.result_heading_value = FakeVariable()
        picker.listbox = FakeListbox()
        picker.selection_hint = FakeLabel()
        picker.toggle_button = FakeControl()
        picker.select_button = FakeControl()
        return picker


class EventAssociationPickerStateTests(unittest.TestCase):
    def test_read_only_picker_can_repopulate_without_tk_item_error(self):
        picker = EventAssociationPickerFactory.build()

        picker.set_enabled(False)
        picker.set_values(("maeve",), ("maeve",))

        self.assertEqual("normal", picker.listbox.state)
        self.assertEqual(
            [
                "✓ Maeve  ·  current person",
                "Merlin",
                "Morgana",
                "Helga",
                "Godric",
                "Rowena",
            ],
            picker.listbox.rows,
        )
        self.assertEqual(
            "Current person and recently viewed",
            picker.result_heading_value.get(),
        )
        self.assertFalse(picker.select_button.enabled)
        self.assertFalse(picker.toggle_button.enabled)

    def test_current_person_cannot_be_unlinked(self):
        picker = EventAssociationPickerFactory.build()
        picker.set_values(("maeve",), ("maeve",))
        picker.listbox.selection_set(0)
        picker.selection_changed()

        self.assertEqual("Fixed", picker.toggle_button.text)
        self.assertFalse(picker.toggle_button.enabled)
        self.assertEqual(["maeve"], picker.get_values())
        picker.toggle_selected()
        self.assertEqual(["maeve"], picker.get_values())

    def test_selected_person_from_search_joins_current_person(self):
        picker = EventAssociationPickerFactory.build()
        picker.set_values(("maeve",), ("maeve",))

        self.assertTrue(picker.selector_chosen("salazar"))
        self.assertEqual(["maeve", "salazar"], picker.get_values())
        self.assertIn("✓ Salazar", picker.listbox.rows)

    @patch(
        "mage_maker.sections.events.editor.EventPersonPickerDialog"
    )
    def test_select_another_person_opens_search_dialog(self, dialog):
        picker = EventAssociationPickerFactory.build()
        picker.set_values(("maeve",), ("maeve",))

        self.assertTrue(picker.open_selector())
        dialog.assert_called_once()
        arguments = dialog.call_args.args
        self.assertEqual(7, len(arguments[1]))
        self.assertEqual(
            ["merlin", "morgana", "helga", "godric", "rowena"],
            [option["value"] for option in arguments[2]],
        )

    @patch(
        "mage_maker.sections.events.editor.EventLocationPickerDialog"
    )
    def test_select_another_location_opens_hierarchy_dialog(self, dialog):
        picker = EventAssociationPickerFactory.build()
        picker.association_kind = "locations"
        picker.set_values(())

        self.assertTrue(picker.open_selector())
        dialog.assert_called_once()
        arguments = dialog.call_args.args
        self.assertEqual("limerick", arguments[1][0]["record_id"])


class EventEditorStateTests(unittest.TestCase):
    def test_selected_editable_event_opens_with_every_field_unlocked(self):
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

        self.assertEqual("edit", editor.editor_mode)
        self.assertTrue(editor.controls_enabled)
        self.assertTrue(editor.save_button.enabled)
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

    def test_person_event_keeps_the_current_person_locked(self):
        editor = EventEditorFactory.build()
        editor.start_new(
            context="person",
            default_person_ids=("maeve",),
            locked_person_ids=("maeve",),
        )

        self.assertEqual(["maeve"], editor.people_picker.selected_ids)
        self.assertEqual({"maeve"}, editor.people_picker.locked_ids)
        self.assertTrue(editor.people_picker.enabled)


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
        self.assertEqual(
            ("maeve",),
            view.event_editor.start_arguments["locked_person_ids"],
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


class LocationAssociationLabelTests(unittest.TestCase):
    def setUp(self):
        self.locations = [
            {
                "record_id": "region",
                "name": "Region",
                "parent_location_id": "",
            },
            {
                "record_id": "country",
                "name": "Country",
                "parent_location_id": "region",
            },
            {
                "record_id": "fourth",
                "name": "Fourth",
                "parent_location_id": "country",
            },
            {
                "record_id": "fifth",
                "name": "Fifth",
                "parent_location_id": "fourth",
            },
            {
                "record_id": "sixth",
                "name": "Sixth",
                "parent_location_id": "fifth",
            },
            {
                "record_id": "seventh",
                "name": "Seventh",
                "parent_location_id": "sixth",
            },
        ]

    def test_location_labels_follow_world_depth_rules(self):
        self.assertEqual(
            "The World",
            recent_location_label("", self.locations),
        )
        self.assertEqual(
            "Region",
            recent_location_label("region", self.locations),
        )
        self.assertEqual(
            "Country",
            recent_location_label("country", self.locations),
        )
        self.assertEqual(
            "Fourth, Country",
            recent_location_label("fourth", self.locations),
        )
        self.assertEqual(
            "Fifth (Fourth, Country)",
            recent_location_label("fifth", self.locations),
        )
        self.assertEqual(
            "Sixth (an area in Fourth, Country)",
            recent_location_label("sixth", self.locations),
        )
        self.assertEqual(
            "Seventh (an area in Fourth, Country)",
            recent_location_label("seventh", self.locations),
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
