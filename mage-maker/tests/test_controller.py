import json
import tempfile
import unittest
from pathlib import Path

from mage_maker.controller import PeopleController
from mage_maker.database import JsonDatabase


class PeopleControllerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "mage_maker.json"
        database_path.write_text(
            json.dumps(
                {
                    "_database": {"schema_version": 3, "last_saved": None},
                    "people": [
                        {
                            "record_id": "young",
                            "displayed_name": "Young",
                            "birth_year": 1990,
                        },
                        {
                            "record_id": "old",
                            "displayed_name": "Old",
                            "birth_year": 1000,
                        },
                        {
                            "record_id": "unknown",
                            "displayed_name": "Unknown",
                            "birth_year": None,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        database = JsonDatabase(database_path)
        database.load()
        self.controller = PeopleController(database)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_people_are_sorted_oldest_first(self):
        record_ids = [person["record_id"] for person in self.controller.list_people()]
        self.assertEqual(["old", "young", "unknown"], record_ids)

    def test_creation_requires_a_name(self):
        with self.assertRaisesRegex(ValueError, "must have a displayed name"):
            self.controller.create_person({"displayed_name": ""})

    def test_birth_date_is_validated(self):
        with self.assertRaisesRegex(ValueError, "Birth month"):
            self.controller.create_person(
                {
                    "displayed_name": "Wrong Month",
                    "birth_year": "1980",
                    "birth_month": "13",
                }
            )

    def test_displayed_name_must_be_unique(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.controller.create_person({"displayed_name": "old"})

    def test_name_details_are_normalized(self):
        created = self.controller.create_person(
            {
                "displayed_name": "Name Keeper",
                "name_details": {
                    "entries": [
                        {
                            "entry_id": "keeper-alias",
                            "name_type": "  Alias  ",
                            "name_entry": "  The Keeper  ",
                            "date": "  1998  ",
                            "note": "  Used at school.  ",
                        }
                    ]
                },
            }
        )
        entry = created["name_details"]["entries"][0]
        self.assertEqual("Alias", entry["name_type"])
        self.assertEqual("The Keeper", entry["name_entry"])
        self.assertEqual("1998", entry["date"])
        self.assertEqual("Used at school.", entry["note"])

    def test_family_assignments_and_mates_are_reciprocal(self):
        mother = self.controller.create_person(
            {"displayed_name": "Mother", "can_give_birth": True}
        )
        father = self.controller.create_person(
            {"displayed_name": "Father", "can_give_birth": False}
        )
        child = self.controller.create_person(
            {
                "displayed_name": "Child",
                "biological_mother_id": mother["record_id"],
                "biological_father_id": father["record_id"],
            }
        )
        saved_mother = self.controller.get_person(mother["record_id"])
        saved_father = self.controller.get_person(father["record_id"])
        self.assertIn(father["record_id"], saved_mother["mate_ids"])
        self.assertIn(mother["record_id"], saved_father["mate_ids"])
        self.assertEqual(
            mother["record_id"],
            self.controller.get_person(child["record_id"])["biological_mother_id"],
        )

    def test_childs_new_other_parent_remains_a_reciprocal_mate(self):
        focus = self.controller.create_person(
            {"displayed_name": "Child Focus", "can_give_birth": False}
        )
        other_parent = self.controller.create_person(
            {"displayed_name": "Child Other Parent", "can_give_birth": True}
        )
        self.controller.create_person(
            {
                "displayed_name": "Their Child",
                "biological_mother_id": other_parent["record_id"],
                "biological_father_id": focus["record_id"],
            }
        )
        self.controller.update_person(
            focus["record_id"],
            {"mate_ids": [other_parent["record_id"]]},
        )
        saved_focus = self.controller.get_person(focus["record_id"])
        saved_other_parent = self.controller.get_person(other_parent["record_id"])
        self.assertIn(other_parent["record_id"], saved_focus["mate_ids"])
        self.assertIn(focus["record_id"], saved_other_parent["mate_ids"])

    def test_mates_need_opposite_birth_assignments(self):
        first = self.controller.create_person(
            {"displayed_name": "First Parent", "can_give_birth": True}
        )
        second = self.controller.create_person(
            {"displayed_name": "Second Parent", "can_give_birth": True}
        )

        with self.assertRaisesRegex(ValueError, "opposite"):
            self.controller.update_person(
                first["record_id"],
                {"mate_ids": [second["record_id"]]},
            )

    def test_parent_link_can_be_removed_without_deleting_parent(self):
        mother = self.controller.create_person(
            {"displayed_name": "Linked Mother", "can_give_birth": True}
        )
        child = self.controller.create_person(
            {
                "displayed_name": "Linked Child",
                "biological_mother_id": mother["record_id"],
            }
        )
        updated_child = self.controller.update_person(
            child["record_id"],
            {"biological_mother_id": ""},
        )
        self.assertEqual("", updated_child["biological_mother_id"])
        self.assertIsNotNone(self.controller.get_person(mother["record_id"]))

    def test_unused_birthing_parent_can_change_to_father_role(self):
        candidate = self.controller.create_person(
            {"displayed_name": "Role Change Parent", "can_give_birth": True}
        )
        updated_candidate = self.controller.update_person(
            candidate["record_id"],
            {"can_give_birth": False},
        )
        child = self.controller.create_person(
            {
                "displayed_name": "Role Change Child",
                "biological_father_id": candidate["record_id"],
            }
        )
        self.assertFalse(updated_candidate["can_give_birth"])
        self.assertEqual(candidate["record_id"], child["biological_father_id"])

    def test_adding_a_second_parent_automatically_links_both_parents_as_mates(self):
        harry = self.controller.create_person(
            {"displayed_name": "Harry", "can_give_birth": False}
        )
        ginny = self.controller.create_person(
            {"displayed_name": "Ginny", "can_give_birth": True}
        )
        carina = self.controller.create_person(
            {"displayed_name": "Carina", "can_give_birth": True}
        )
        self.controller.create_person(
            {
                "displayed_name": "Horace",
                "biological_mother_id": ginny["record_id"],
                "biological_father_id": harry["record_id"],
            }
        )
        second_child = self.controller.create_person(
            {
                "displayed_name": "Second Child",
                "biological_father_id": harry["record_id"],
            }
        )
        self.controller.update_person(
            second_child["record_id"],
            {"biological_mother_id": carina["record_id"]},
        )
        saved_harry = self.controller.get_person(harry["record_id"])
        saved_ginny = self.controller.get_person(ginny["record_id"])
        saved_carina = self.controller.get_person(carina["record_id"])
        self.assertEqual(
            {ginny["record_id"], carina["record_id"]},
            set(saved_harry["mate_ids"]),
        )
        self.assertIn(harry["record_id"], saved_ginny["mate_ids"])
        self.assertIn(harry["record_id"], saved_carina["mate_ids"])

    def test_assigning_a_child_adds_linked_timeline_events_to_both_parents(self):
        birthing_parent = self.controller.create_person(
            {"displayed_name": "Timeline Birthing", "can_give_birth": True}
        )
        non_birthing_parent = self.controller.create_person(
            {"displayed_name": "Timeline Non-birthing", "can_give_birth": False}
        )
        child = self.controller.create_person(
            {
                "displayed_name": "Linked Timeline Child",
                "birth_year": 2004,
                "birth_month": 6,
                "birth_day": 8,
                "biological_mother_id": birthing_parent["record_id"],
                "biological_father_id": non_birthing_parent["record_id"],
            }
        )

        for parent in (birthing_parent, non_birthing_parent):
            saved_parent = self.controller.get_person(parent["record_id"])
            events = [
                event
                for event in saved_parent["timeline_events"]
                if event.get("automatic_source") == "child_assignment"
            ]
            self.assertEqual(1, len(events))
            self.assertEqual("had_child", events[0]["event_type"])
            self.assertEqual(child["record_id"], events[0]["related_person_id"])
            self.assertEqual("Linked Timeline Child", events[0]["detail"])
            self.assertEqual("2004-06-08", events[0]["date"])
            self.assertIn("Linked Timeline Child", events[0]["note"])

    def test_reassigning_a_parent_moves_the_automatic_child_event(self):
        first_parent = self.controller.create_person(
            {"displayed_name": "First Timeline Parent", "can_give_birth": True}
        )
        second_parent = self.controller.create_person(
            {"displayed_name": "Second Timeline Parent", "can_give_birth": True}
        )
        child = self.controller.create_person(
            {
                "displayed_name": "Moved Timeline Child",
                "biological_mother_id": first_parent["record_id"],
            }
        )
        self.controller.update_person(
            child["record_id"],
            {"biological_mother_id": second_parent["record_id"]},
        )
        first_events = self.controller.get_person(first_parent["record_id"])[
            "timeline_events"
        ]
        second_events = self.controller.get_person(second_parent["record_id"])[
            "timeline_events"
        ]
        self.assertFalse(
            any(event.get("related_person_id") == child["record_id"] for event in first_events)
        )
        self.assertTrue(
            any(event.get("related_person_id") == child["record_id"] for event in second_events)
        )

    def test_child_details_update_without_duplicate_timeline_events(self):
        parent = self.controller.create_person(
            {"displayed_name": "Updating Timeline Parent", "can_give_birth": False}
        )
        child = self.controller.create_person(
            {
                "displayed_name": "Original Child Name",
                "birth_year": 2001,
                "biological_father_id": parent["record_id"],
            }
        )
        self.controller.update_person(
            child["record_id"],
            {
                "displayed_name": "Updated Child Name",
                "birth_month": 9,
            },
        )
        events = [
            event
            for event in self.controller.get_person(parent["record_id"])[
                "timeline_events"
            ]
            if event.get("related_person_id") == child["record_id"]
        ]
        self.assertEqual(1, len(events))
        self.assertEqual("Updated Child Name", events[0]["detail"])
        self.assertEqual("2001-09", events[0]["date"])
        self.assertEqual("Child: Updated Child Name", events[0]["note"])

    def test_missing_and_muggle_parent_states_are_canonical(self):
        child = self.controller.create_person(
            {
                "displayed_name": "Parent State Child",
                "biological_mother_status": "muggle",
            }
        )
        self.assertEqual("muggle", child["biological_mother_status"])
        self.assertEqual("unknown", child["biological_father_status"])
        self.assertEqual("", child["biological_mother_id"])


if __name__ == "__main__":
    unittest.main()
