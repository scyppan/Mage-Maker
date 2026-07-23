import unittest

from mage_maker.sections.names.history import (
    migrate_legacy_name_details,
    normalize_name_details,
)


class NameHistoryTests(unittest.TestCase):
    def test_legacy_fields_become_individual_entries(self):
        details = migrate_legacy_name_details(
            {
                "aliases": "First Alias\nSecond Alias",
                "sobriquets": "The Excellent",
                "name_changes": "Maiden name: Earlier Name",
            },
            "Displayed Name",
            "person-one",
        )
        self.assertEqual(
            [
                ("Alias", "First Alias"),
                ("Alias", "Second Alias"),
                ("Sobriquet", "The Excellent"),
                ("Maiden name", "Earlier Name"),
            ],
            [
                (entry["name_type"], entry["name_entry"])
                for entry in details["entries"]
            ],
        )

    def test_name_entry_requires_type_and_name(self):
        with self.assertRaisesRegex(ValueError, "Name type"):
            normalize_name_details(
                {
                    "entries": [
                        {
                            "name_type": "",
                            "name_entry": "Merlin",
                        }
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()
