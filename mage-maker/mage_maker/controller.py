from copy import deepcopy

from mage_maker.family_relationships import FamilyRelationshipMap
from mage_maker.name_history import empty_name_details, normalize_name_details
from mage_maker.timeline_events import (
    automatic_child_timeline_event,
    normalize_timeline_events,
)


class PeopleController:
    text_fields = (
        "displayed_name",
        "narrative",
        "biological_mother_id",
        "biological_father_id",
        "biological_mother_status",
        "biological_father_status",
        "school",
        "notes",
    )
    boolean_fields = (
        "deceased",
        "canon",
        "player_character",
        "non_magical",
        "can_give_birth",
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
            "non_magical": False,
            "can_give_birth": False,
            "biological_mother_id": "",
            "biological_father_id": "",
            "biological_mother_status": "unknown",
            "biological_father_status": "unknown",
            "mate_ids": [],
            "timeline_events": [],
            "school": "",
            "notes": "",
            "imported_fields": {},
        }
        defaults.update(deepcopy(values))
        normalized = self.normalize_values(defaults)
        normalized = self.canonicalize_parent_states(normalized)
        self.validate_values(normalized)
        created_person = self.database.create_person(normalized)
        self.synchronize_mates(
            created_person["record_id"],
            [],
            created_person.get("mate_ids", []),
        )
        self.synchronize_coparents(created_person)
        self.reconcile_child_parent_timelines(created_person, [])
        self.reconcile_child_timeline_events_for_parent(
            created_person["record_id"]
        )
        self.database.save()
        return self.database.read_person(created_person["record_id"])

    def update_person(self, record_id, values):
        current_person = self.get_person(record_id)

        if current_person is None:
            raise KeyError(f"Unknown person record_id: {record_id}")

        normalized = self.normalize_values(values)
        prospective_person = deepcopy(current_person)
        prospective_person.update(normalized)
        prospective_person = self.canonicalize_parent_states(prospective_person)
        normalized["biological_mother_status"] = prospective_person[
            "biological_mother_status"
        ]
        normalized["biological_father_status"] = prospective_person[
            "biological_father_status"
        ]
        self.validate_values(prospective_person)
        old_mate_ids = list(current_person.get("mate_ids", []) or [])
        old_parent_ids = self.parent_ids_from_person(current_person)
        updated_person = self.database.update_person(record_id, normalized)
        self.synchronize_mates(
            record_id,
            old_mate_ids,
            updated_person.get("mate_ids", []),
        )
        self.synchronize_coparents(updated_person)
        self.reconcile_child_parent_timelines(updated_person, old_parent_ids)
        self.reconcile_child_timeline_events_for_parent(record_id)
        self.database.save()
        return self.database.read_person(record_id)

    def delete_person(self, record_id):
        current_person = self.database.read_person(record_id)
        old_parent_ids = self.parent_ids_from_person(current_person)
        deleted_person = self.database.delete_person(record_id)

        for parent_id in old_parent_ids:
            self.reconcile_child_timeline_events_for_parent(parent_id)

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

        if "mate_ids" in normalized:
            normalized["mate_ids"] = self.normalize_identifier_list(
                normalized["mate_ids"]
            )

        if "name_details" in normalized:
            normalized["name_details"] = normalize_name_details(
                normalized["name_details"]
            )

        if "timeline_events" in normalized:
            normalized["timeline_events"] = normalize_timeline_events(
                normalized["timeline_events"]
            )

        return normalized

    def canonicalize_parent_states(self, values):
        normalized = deepcopy(values)

        for parent_role in ("mother", "father"):
            id_field = f"biological_{parent_role}_id"
            status_field = f"biological_{parent_role}_status"
            parent_id = str(normalized.get(id_field, "") or "").strip()
            status = str(normalized.get(status_field, "unknown") or "unknown")
            status = status.strip().casefold()

            if status not in ("unknown", "muggle", "person"):
                raise ValueError(
                    "A parent status must be Unknown, Muggle, or a named person."
                )

            normalized[id_field] = parent_id
            normalized[status_field] = "person" if parent_id else (
                "muggle" if status == "muggle" else "unknown"
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
            raise ValueError(
                f"{field_name.replace('_', ' ').title()} must be a whole number."
            )

        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{field_name.replace('_', ' ').title()} must be a whole number."
            ) from error

    def normalize_identifier_list(self, values):
        if values in (None, ""):
            return []

        if not isinstance(values, list):
            raise TypeError("Mate assignments must be a list of person identifiers.")

        normalized_ids = []

        for value in values:
            record_id = str(value or "").strip()

            if record_id and record_id not in normalized_ids:
                normalized_ids.append(record_id)

        return normalized_ids

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

        self.validate_relationships(values)

    def validate_relationships(self, values):
        record_id = str(values.get("record_id", "") or "")
        mother_id = str(values.get("biological_mother_id", "") or "")
        father_id = str(values.get("biological_father_id", "") or "")
        mate_ids = self.normalize_identifier_list(values.get("mate_ids", []))
        relationship_map = FamilyRelationshipMap(self.database.list_people())

        if record_id and record_id in (mother_id, father_id):
            raise ValueError("A person cannot be their own biological parent.")

        if mother_id and mother_id == father_id:
            raise ValueError(
                "Birthing and non-birthing parents must be different people."
            )

        for parent_id, role_label, required_capability in (
            (mother_id, "birthing parent", True),
            (father_id, "non-birthing parent", False),
        ):
            if not parent_id:
                continue

            parent = relationship_map.person(parent_id)

            if parent is None:
                raise ValueError(f"The selected {role_label} no longer exists.")

            if bool(parent.get("can_give_birth")) != required_capability:
                requirement = "checked" if required_capability else "unchecked"
                raise ValueError(
                    f"A {role_label} must have Can give birth {requirement}."
                )

            if record_id and parent_id in relationship_map.descendants_of(record_id):
                raise ValueError("A descendant cannot also be a biological parent.")

        current_can_give_birth = bool(values.get("can_give_birth"))

        for mate_id in mate_ids:
            if mate_id == record_id:
                raise ValueError("A person cannot be their own mate.")

            mate = relationship_map.person(mate_id)

            if mate is None:
                raise ValueError("A selected mate no longer exists.")

            if bool(mate.get("can_give_birth")) == current_can_give_birth:
                raise ValueError(
                    "Mates must have opposite Can give birth assignments."
                )

            if record_id and (
                mate_id in relationship_map.ancestors_of(record_id)
                or mate_id in relationship_map.descendants_of(record_id)
            ):
                raise ValueError("A direct ancestor or descendant cannot be a mate.")

        if record_id:
            for child in self.database.list_people():
                if child.get("biological_mother_id") == record_id and not current_can_give_birth:
                    raise ValueError(
                        "Can give birth must remain checked while this person is listed "
                        "as a birthing parent."
                    )

                if child.get("biological_father_id") == record_id and current_can_give_birth:
                    raise ValueError(
                        "Can give birth must remain unchecked while this person is listed "
                        "as a non-birthing parent."
                    )

    def synchronize_mates(self, record_id, old_mate_ids, new_mate_ids):
        old_ids = set(self.normalize_identifier_list(old_mate_ids))
        new_ids = set(self.normalize_identifier_list(new_mate_ids))

        for mate_id in old_ids | new_ids:
            mate = self.database.read_person(mate_id)

            if mate is None:
                continue

            reciprocal_ids = self.normalize_identifier_list(mate.get("mate_ids", []))

            if mate_id in new_ids and record_id not in reciprocal_ids:
                reciprocal_ids.append(record_id)

            if mate_id not in new_ids:
                reciprocal_ids = [
                    reciprocal_id
                    for reciprocal_id in reciprocal_ids
                    if reciprocal_id != record_id
                ]

            self.database.update_person(mate_id, {"mate_ids": reciprocal_ids})

    def synchronize_coparents(self, child):
        mother_id = str(child.get("biological_mother_id", "") or "").strip()
        father_id = str(child.get("biological_father_id", "") or "").strip()

        if not mother_id or not father_id or mother_id == father_id:
            return

        mother = self.database.read_person(mother_id)
        father = self.database.read_person(father_id)

        if mother is None or father is None:
            return

        mother_mates = self.normalize_identifier_list(mother.get("mate_ids", []))
        father_mates = self.normalize_identifier_list(father.get("mate_ids", []))

        if father_id not in mother_mates:
            mother_mates.append(father_id)
            self.database.update_person(mother_id, {"mate_ids": mother_mates})

        if mother_id not in father_mates:
            father_mates.append(mother_id)
            self.database.update_person(father_id, {"mate_ids": father_mates})

    def parent_ids_from_person(self, person):
        if not isinstance(person, dict):
            return []

        return self.normalize_identifier_list(
            [
                person.get("biological_mother_id"),
                person.get("biological_father_id"),
            ]
        )

    def reconcile_child_parent_timelines(self, child, previous_parent_ids):
        parent_ids = self.normalize_identifier_list(previous_parent_ids)

        for parent_id in self.parent_ids_from_person(child):
            if parent_id not in parent_ids:
                parent_ids.append(parent_id)

        for parent_id in parent_ids:
            self.reconcile_child_timeline_events_for_parent(parent_id)

    def reconcile_child_timeline_events_for_parent(self, parent_id):
        parent = self.database.read_person(parent_id)

        if parent is None:
            return

        children = [
            person
            for person in self.database.list_people()
            if parent_id
            in (
                str(person.get("biological_mother_id", "") or ""),
                str(person.get("biological_father_id", "") or ""),
            )
        ]
        child_ids = {
            str(child.get("record_id", "") or "")
            for child in children
            if str(child.get("record_id", "") or "")
        }
        existing_events = normalize_timeline_events(
            parent.get("timeline_events", [])
        )
        original_events = deepcopy(existing_events)
        retained_events = [
            event
            for event in existing_events
            if not (
                event.get("automatic_source") == "child_assignment"
                and event.get("related_person_id") not in child_ids
            )
        ]

        for child in children:
            child_id = str(child.get("record_id", "") or "")
            matching_event = None

            for event in retained_events:
                if (
                    event.get("automatic_source") == "child_assignment"
                    and event.get("related_person_id") == child_id
                ):
                    matching_event = event
                    break

            synchronized_event = automatic_child_timeline_event(
                child,
                matching_event,
            )

            if matching_event is None:
                retained_events.append(synchronized_event)
            else:
                retained_events[retained_events.index(matching_event)] = (
                    synchronized_event
                )

        normalized_events = normalize_timeline_events(retained_events)

        if normalized_events != original_events:
            self.database.update_person(
                parent_id,
                {"timeline_events": normalized_events},
            )
