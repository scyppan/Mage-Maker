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


if __name__ == "__main__":
    unittest.main()
