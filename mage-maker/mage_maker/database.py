import json
import os
import shutil
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from mage_maker.name_history import migrate_legacy_name_details


class JsonDatabase:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.backup_directory = self.database_path.parent / "backups"
        self.data = {}
        self.dirty = False

    def load(self):
        with self.database_path.open("r", encoding="utf-8") as database_file:
            loaded_data = json.load(database_file)

        migrated = self.migrate_database(loaded_data)
        self.validate_database(loaded_data)
        self.data = loaded_data
        self.dirty = migrated

    def migrate_database(self, database_data):
        if not isinstance(database_data, dict):
            return False

        metadata = database_data.get("_database", {})

        if not isinstance(metadata, dict):
            return False

        schema_version = metadata.get("schema_version")

        if not isinstance(schema_version, int) or schema_version >= 3:
            return False

        migrated = False

        if schema_version < 2:
            removed_attribute_fields = (
                "generosity",
                "permissiveness",
                "wealth",
                "creativity",
                "equanimity",
                "charisma",
                "attractiveness",
                "strength",
                "agility",
                "intellect",
                "willpower",
                "fortitude",
            )

            for person in database_data.get("people", []):
                if not isinstance(person, dict):
                    continue

                displayed_name = person.pop("name", "")
                maiden_name = person.pop("maiden_name", "")
                nickname_alias = person.pop("nickname_alias", "")
                person["displayed_name"] = displayed_name
                person["name_details"] = {
                    "name_history": "",
                    "aliases": nickname_alias,
                    "sobriquets": "",
                    "name_changes": (
                        f"Maiden name: {maiden_name}" if maiden_name else ""
                    ),
                    "notes": "",
                }
                person.pop("has_other_names", None)
                person.pop("image_url", None)

                for field_name in removed_attribute_fields:
                    person.pop(field_name, None)

                imported_fields = person.get("imported_fields")

                if isinstance(imported_fields, dict):
                    imported_fields.pop("Upload character image", None)

            schema_version = 2
            migrated = True

        if schema_version < 3:
            for person in database_data.get("people", []):
                if not isinstance(person, dict):
                    continue

                person["name_details"] = migrate_legacy_name_details(
                    person.get("name_details", {}),
                    person.get("displayed_name", ""),
                    person.get("record_id", ""),
                )

            migrated = True

        metadata["schema_version"] = 3
        metadata["database_version"] = "0.3.0"
        database_data["_database"] = metadata

        return migrated

    def validate_database(self, database_data):
        if not isinstance(database_data, dict):
            raise TypeError("The database root must be a JSON object.")

        if not isinstance(database_data.get("people"), list):
            raise TypeError("The database must contain a people collection.")

        metadata = database_data.get("_database")

        if not isinstance(metadata, dict):
            raise TypeError("The database must contain _database metadata.")

        if not isinstance(metadata.get("schema_version"), int):
            raise TypeError("The database schema version must be a number.")

        seen_ids = set()
        seen_displayed_names = set()

        for person in database_data["people"]:
            if not isinstance(person, dict):
                raise TypeError("Every person must be a JSON object.")

            record_id = person.get("record_id")

            if not isinstance(record_id, str) or not record_id.strip():
                raise ValueError("Every person must have a record_id.")

            if record_id in seen_ids:
                raise ValueError(f"Duplicate person record_id: {record_id}")

            seen_ids.add(record_id)

            displayed_name = str(person.get("displayed_name", "")).strip()

            if not displayed_name:
                raise ValueError("Every person must have a displayed name.")

            normalized_name = displayed_name.casefold()

            if normalized_name in seen_displayed_names:
                raise ValueError(f"Duplicate displayed name: {displayed_name}")

            seen_displayed_names.add(normalized_name)

    def list_people(self):
        return deepcopy(self.data["people"])

    def read_person(self, record_id):
        for person in self.data["people"]:
            if person.get("record_id") == record_id:
                return deepcopy(person)

        return None

    def create_person(self, values):
        if not isinstance(values, dict):
            raise TypeError("A person must be a dictionary.")

        person = deepcopy(values)
        person.setdefault("record_id", str(uuid.uuid4()))

        if self.read_person(person["record_id"]) is not None:
            raise ValueError(f"Duplicate person record_id: {person['record_id']}")

        self.ensure_unique_displayed_name(person.get("displayed_name"))

        current_time = datetime.now(timezone.utc).isoformat()
        person.setdefault("created_at", current_time)
        person["last_updated"] = current_time
        self.data["people"].append(person)
        self.dirty = True

        return deepcopy(person)

    def update_person(self, record_id, values):
        if not isinstance(values, dict):
            raise TypeError("Person changes must be a dictionary.")

        if "record_id" in values and values["record_id"] != record_id:
            raise ValueError("A person record_id cannot be changed.")

        for person in self.data["people"]:
            if person.get("record_id") != record_id:
                continue

            prospective_person = deepcopy(person)
            prospective_person.update(deepcopy(values))
            self.ensure_unique_displayed_name(
                prospective_person.get("displayed_name"),
                excluded_record_id=record_id,
            )
            person.update(deepcopy(values))
            person["last_updated"] = datetime.now(timezone.utc).isoformat()
            self.dirty = True

            return deepcopy(person)

        raise KeyError(f"Unknown person record_id: {record_id}")

    def ensure_unique_displayed_name(self, displayed_name, excluded_record_id=None):
        normalized_name = str(displayed_name or "").strip().casefold()

        if not normalized_name:
            raise ValueError("A magician must have a displayed name.")

        for person in self.data["people"]:
            if person.get("record_id") == excluded_record_id:
                continue

            existing_name = str(person.get("displayed_name", "")).strip().casefold()

            if existing_name == normalized_name:
                raise ValueError(
                    f'A magician named "{str(displayed_name).strip()}" already exists.'
                )

    def delete_person(self, record_id):
        for index, person in enumerate(self.data["people"]):
            if person.get("record_id") != record_id:
                continue

            deleted_person = self.data["people"].pop(index)
            self.dirty = True

            return deepcopy(deleted_person)

        raise KeyError(f"Unknown person record_id: {record_id}")

    def save(self):
        self.validate_database(self.data)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        if self.database_path.exists():
            self.backup_directory.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup_path = self.backup_directory / f"mage_maker-{timestamp}.json"
            shutil.copy2(self.database_path, backup_path)

        self.data["_database"]["last_saved"] = datetime.now(
            timezone.utc
        ).isoformat()
        temporary_path = self.database_path.with_suffix(".json.tmp")

        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as database_file:
            json.dump(self.data, database_file, ensure_ascii=False, indent=2)
            database_file.write("\n")

        os.replace(temporary_path, self.database_path)
        self.dirty = False
