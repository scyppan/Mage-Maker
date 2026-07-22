import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "tools" / "import_formidable_csv.py"
SPEC = importlib.util.spec_from_file_location("import_formidable_csv", SCRIPT_PATH)
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


class ImportTests(unittest.TestCase):
    def test_duplicate_headers_are_numbered(self):
        self.assertEqual(
            ["Name", "Skill [1]", "Skill [2]"],
            IMPORTER.indexed_headers(["Name", "Skill", "Skill"]),
        )

    def test_repository_database_has_people_collection(self):
        database_path = Path(__file__).resolve().parent.parent / "data" / "mage_maker.json"
        database = json.loads(database_path.read_text(encoding="utf-8"))
        self.assertIn("people", database)
        self.assertEqual(133, len(database["people"]))
        self.assertEqual(1000, database["people"][0]["birth_year"])
        self.assertEqual(5, database["_database"]["schema_version"])
        self.assertEqual("Ioanis Tivly", database["people"][0]["displayed_name"])
        self.assertIn("name_details", database["people"][0])
        self.assertIn("entries", database["people"][0]["name_details"])
        self.assertNotIn("name", database["people"][0])
        self.assertNotIn("image_url", database["people"][0])
        self.assertNotIn("generosity", database["people"][0])
        self.assertNotIn("blood_status", database["people"][0])
        self.assertIn("non_magical", database["people"][0])
        self.assertIn("can_give_birth", database["people"][0])
        self.assertIn("mate_ids", database["people"][0])
        self.assertIn("timeline_events", database["people"][0])
        self.assertIn("biological_mother_status", database["people"][0])
        self.assertNotIn(
            "Upload character image",
            database["people"][0]["imported_fields"],
        )


if __name__ == "__main__":
    unittest.main()
