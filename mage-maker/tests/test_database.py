import json
import tempfile
import unittest
from pathlib import Path

from mage_maker.database import JsonDatabase


class JsonDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "mage_maker.json"
        self.database_path.write_text(
            json.dumps(
                {
                    "_database": {"schema_version": 3, "last_saved": None},
                    "people": [],
                }
            ),
            encoding="utf-8",
        )
        self.database = JsonDatabase(self.database_path)
        self.database.load()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_full_crud_cycle(self):
        created = self.database.create_person({"displayed_name": "Test Magician"})
        self.assertEqual("Test Magician", created["displayed_name"])
        self.assertIsNotNone(self.database.read_person(created["record_id"]))

        updated = self.database.update_person(
            created["record_id"],
            {"displayed_name": "Updated Magician"},
        )
        self.assertEqual("Updated Magician", updated["displayed_name"])

        deleted = self.database.delete_person(created["record_id"])
        self.assertEqual("Updated Magician", deleted["displayed_name"])
        self.assertIsNone(self.database.read_person(created["record_id"]))

    def test_save_is_atomic_and_creates_backup(self):
        self.database.create_person({"displayed_name": "Backup Test"})
        self.database.save()
        backup_files = list((self.database_path.parent / "backups").glob("*.json"))
        self.assertEqual(1, len(backup_files))
        saved_data = json.loads(self.database_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "Backup Test",
            saved_data["people"][0]["displayed_name"],
        )

    def test_duplicate_displayed_names_are_rejected(self):
        self.database.create_person({"displayed_name": "Morgana"})

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.database.create_person({"displayed_name": "  MORGANA  "})

    def test_displayed_name_cannot_be_changed_to_an_existing_name(self):
        first = self.database.create_person({"displayed_name": "Morgana"})
        second = self.database.create_person({"displayed_name": "Merlin"})

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.database.update_person(
                second["record_id"],
                {"displayed_name": first["displayed_name"].lower()},
            )

    def test_version_one_database_is_migrated(self):
        old_database_path = Path(self.temporary_directory.name) / "old.json"
        old_database_path.write_text(
            json.dumps(
                {
                    "_database": {"schema_version": 1, "last_saved": None},
                    "people": [
                        {
                            "record_id": "old-person",
                            "name": "Old Name",
                            "maiden_name": "Earlier Name",
                            "nickname_alias": "Alias",
                            "image_url": "https://example.com/image.png",
                            "generosity": 3,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        old_database = JsonDatabase(old_database_path)
        old_database.load()
        person = old_database.read_person("old-person")
        self.assertEqual("Old Name", person["displayed_name"])
        self.assertEqual(
            [
                ("Alias", "Alias"),
                ("Maiden name", "Earlier Name"),
            ],
            [
                (entry["name_type"], entry["name_entry"])
                for entry in person["name_details"]["entries"]
            ],
        )
        self.assertEqual(3, old_database.data["_database"]["schema_version"])
        self.assertNotIn("image_url", person)
        self.assertNotIn("generosity", person)

    def test_version_two_name_details_are_migrated_to_line_items(self):
        old_database_path = Path(self.temporary_directory.name) / "version-two.json"
        old_database_path.write_text(
            json.dumps(
                {
                    "_database": {"schema_version": 2, "last_saved": None},
                    "people": [
                        {
                            "record_id": "version-two-person",
                            "displayed_name": "Carina Fenwick",
                            "name_details": {
                                "name_history": "",
                                "aliases": "Aunt Carina",
                                "sobriquets": "",
                                "name_changes": "Maiden name: Lorenzo Black",
                                "notes": "",
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        old_database = JsonDatabase(old_database_path)
        old_database.load()
        entries = old_database.read_person("version-two-person")["name_details"][
            "entries"
        ]
        self.assertEqual(
            [
                ("Alias", "Aunt Carina"),
                ("Maiden name", "Lorenzo Black"),
            ],
            [(entry["name_type"], entry["name_entry"]) for entry in entries],
        )


if __name__ == "__main__":
    unittest.main()
