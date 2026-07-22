from copy import deepcopy

from mage_maker.name_history import empty_name_details, normalize_name_details


class PeopleController:
    text_fields = (
        "displayed_name",
        "narrative",
        "blood_status",
        "biological_mother",
        "biological_father",
        "school",
        "notes",
    )
    boolean_fields = (
        "deceased",
        "canon",
        "player_character",
        "muggle",
        "squib",
    )
    number_fields = (
        "birth_year",
        "birth_month",
        "birth_day",
    )

    def __init__(self, database):
        self.database = database

    def list_people(self):
        people = self.database.list_people()
        people.sort(key=self.person_sort_key)

        return people

    def person_sort_key(self, person):
        birth_year = self.sortable_number(person.get("birth_year"), 10000)
        birth_month = self.sortable_number(person.get("birth_month"), 13)
        birth_day = self.sortable_number(person.get("birth_day"), 32)
        name = str(person.get("displayed_name", "")).casefold()

        return birth_year, birth_month, birth_day, name

    def sortable_number(self, value, fallback):
        if isinstance(value, bool):
            return fallback

        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def get_person(self, record_id):
        return self.database.read_person(record_id)

    def create_person(self, values):
        defaults = {
            "displayed_name": "",
            "name_details": empty_name_details(),
            "narrative": "",
            "birth_year": None,
            "birth_month": None,
            "birth_day": None,
            "deceased": False,
            "canon": False,
            "player_character": False,
            "muggle": False,
            "squib": False,
            "blood_status": "",
            "biological_mother": "",
            "biological_father": "",
            "school": "",
            "notes": "",
            "imported_fields": {},
        }
        defaults.update(deepcopy(values))
        normalized = self.normalize_values(defaults)
        self.validate_values(normalized)
        created_person = self.database.create_person(normalized)
        self.database.save()

        return created_person

    def update_person(self, record_id, values):
        current_person = self.get_person(record_id)

        if current_person is None:
            raise KeyError(f"Unknown person record_id: {record_id}")

        normalized = self.normalize_values(values)
        prospective_person = deepcopy(current_person)
        prospective_person.update(normalized)
        self.validate_values(prospective_person)
        updated_person = self.database.update_person(record_id, normalized)
        self.database.save()

        return updated_person

    def delete_person(self, record_id):
        deleted_person = self.database.delete_person(record_id)
        self.database.save()

        return deleted_person

    def normalize_values(self, values):
        normalized = deepcopy(values)

        for field_name in self.text_fields:
            if field_name in normalized:
                normalized[field_name] = str(normalized[field_name] or "").strip()

        for field_name in self.boolean_fields:
            if field_name in normalized:
                normalized[field_name] = self.normalize_boolean(
                    normalized[field_name],
                    field_name,
                )

        for field_name in self.number_fields:
            if field_name in normalized:
                normalized[field_name] = self.normalize_number(
                    normalized[field_name],
                    field_name,
                )

        if "name_details" in normalized:
            normalized["name_details"] = normalize_name_details(
                normalized["name_details"]
            )

        return normalized

    def normalize_boolean(self, value, field_name):
        if isinstance(value, bool):
            return value

        normalized = str(value or "").strip().casefold()

        if normalized in ("yes", "true", "1"):
            return True

        if normalized in ("", "no", "false", "0"):
            return False

        raise ValueError(f"{field_name.replace('_', ' ').title()} must be Yes or No.")

    def normalize_number(self, value, field_name):
        if value in (None, ""):
            return None

        if isinstance(value, bool):
            raise ValueError(f"{field_name.replace('_', ' ').title()} must be a whole number.")

        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{field_name.replace('_', ' ').title()} must be a whole number."
            ) from error

    def validate_values(self, values):
        if not values.get("displayed_name", "").strip():
            raise ValueError("A magician must have a displayed name.")

        birth_year = values.get("birth_year")
        birth_month = values.get("birth_month")
        birth_day = values.get("birth_day")

        if birth_year is not None and not 1 <= birth_year <= 9999:
            raise ValueError("Birth year must be between 1 and 9999.")

        if birth_month is not None and not 1 <= birth_month <= 12:
            raise ValueError("Birth month must be between 1 and 12.")

        if birth_day is not None and not 1 <= birth_day <= 31:
            raise ValueError("Birth day must be between 1 and 31.")
