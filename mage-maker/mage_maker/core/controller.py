from copy import deepcopy

from mage_maker.core.dates import is_at_least_age, normalize_date_parts
from mage_maker.sections.family_tree.relationships import FamilyRelationshipMap
from mage_maker.sections.family_tree.spouse_relationships import (
    empty_spouse_relationship,
    merge_mate_ids,
    normalize_spouse_relationships,
    reciprocal_relationship,
    relationship_ids,
)
from mage_maker.sections.names.history import empty_name_details, normalize_name_details
from mage_maker.sections.names.timeline import synchronize_name_change_events
from mage_maker.sections.timeline.events import (
    automatic_child_timeline_event,
    normalize_timeline_events,
)
from mage_maker.sections.timeline.locations import (
    ParentLocationConflict,
    add_long_distance_note,
    born_long_distance_parent_ids,
    born_note_from_events,
    child_parent_location_context,
    ensure_life_start_events,
    remove_long_distance_note,
    starting_location_from_events,
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
        "famous_person",
    )
    number_fields = (
        "birth_year",
        "birth_month",
        "birth_day",
        "death_year",
        "death_month",
        "death_day",
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
        creation_values = deepcopy(values)
        starting_location = creation_values.pop("starting_location", None)
        long_distance_override = self.normalize_boolean(
            creation_values.pop("long_distance_parent_override", False),
            "long_distance_parent_override",
        )
        defaults = {
            "displayed_name": "",
            "name_details": empty_name_details(),
            "narrative": "",
            "birth_year": None,
            "birth_month": None,
            "birth_day": None,
            "deceased": False,
            "death_year": None,
            "death_month": None,
            "death_day": None,
            "canon": False,
            "player_character": False,
            "non_magical": False,
            "can_give_birth": False,
            "famous_person": False,
            "biological_mother_id": "",
            "biological_father_id": "",
            "biological_mother_status": "unknown",
            "biological_father_status": "unknown",
            "mate_ids": [],
            "spouse_relationships": [],
            "timeline_events": [],
            "school": "",
            "notes": "",
            "imported_fields": {},
        }
        defaults.update(creation_values)
        normalized = self.normalize_values(defaults)
        normalized = self.reconcile_spouse_fields(normalized)
        normalized = self.canonicalize_parent_states(normalized)
        normalize_date_parts(
            normalized.get("birth_year"),
            normalized.get("birth_month"),
            normalized.get("birth_day"),
            "Birth",
        )
        normalized = self.synchronize_life_start_timeline(
            normalized,
            starting_location,
            long_distance_override,
        )
        normalized["timeline_events"] = synchronize_name_change_events(
            normalized["name_details"],
            normalized["timeline_events"],
        )
        self.validate_values(normalized)
        created_person = self.database.create_person(normalized)
        self.synchronize_spouses(
            created_person["record_id"],
            [],
            created_person.get("spouse_relationships", []),
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

        update_values = deepcopy(values)
        starting_location = update_values.pop("starting_location", None)
        long_distance_override = self.normalize_boolean(
            update_values.pop("long_distance_parent_override", False),
            "long_distance_parent_override",
        )
        normalized = self.normalize_values(update_values)
        normalized = self.reconcile_spouse_fields(normalized, current_person)
        prospective_person = deepcopy(current_person)
        prospective_person.update(normalized)
        prospective_person = self.canonicalize_parent_states(prospective_person)
        normalize_date_parts(
            prospective_person.get("birth_year"),
            prospective_person.get("birth_month"),
            prospective_person.get("birth_day"),
            "Birth",
        )
        prospective_person = self.synchronize_life_start_timeline(
            prospective_person,
            starting_location,
            long_distance_override,
        )
        prospective_person["timeline_events"] = synchronize_name_change_events(
            prospective_person.get("name_details", empty_name_details()),
            prospective_person["timeline_events"],
        )
        normalized["biological_mother_status"] = prospective_person[
            "biological_mother_status"
        ]
        normalized["biological_father_status"] = prospective_person[
            "biological_father_status"
        ]
        normalized["timeline_events"] = prospective_person["timeline_events"]
        self.validate_values(prospective_person)
        old_spouse_relationships = normalize_spouse_relationships(
            current_person.get("spouse_relationships", [])
        )
        old_parent_ids = self.parent_ids_from_person(current_person)
        updated_person = self.database.update_person(record_id, normalized)
        self.synchronize_spouses(
            record_id,
            old_spouse_relationships,
            updated_person.get("spouse_relationships", []),
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

        if "spouse_relationships" in normalized:
            normalized["spouse_relationships"] = normalize_spouse_relationships(
                normalized["spouse_relationships"]
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

    def reconcile_spouse_fields(self, values, current_person=None):
        normalized = deepcopy(values)
        current = current_person if isinstance(current_person, dict) else {}

        if "spouse_relationships" in normalized:
            relationships = normalize_spouse_relationships(
                normalized.get("spouse_relationships")
            )
            normalized["spouse_relationships"] = relationships
            normalized["mate_ids"] = relationship_ids(relationships)
            return normalized

        if "mate_ids" in normalized:
            relationships = merge_mate_ids(
                current.get("spouse_relationships", []),
                normalized.get("mate_ids", []),
            )
            normalized["spouse_relationships"] = relationships
            normalized["mate_ids"] = relationship_ids(relationships)

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

        normalize_date_parts(
            values.get("birth_year"),
            values.get("birth_month"),
            values.get("birth_day"),
            "Birth",
        )
        normalize_date_parts(
            values.get("death_year"),
            values.get("death_month"),
            values.get("death_day"),
            "Death",
        )

        self.validate_relationships(values)

    def synchronize_life_start_timeline(
        self,
        person,
        requested_starting_location=None,
        long_distance_override=False,
    ):
        synchronized = deepcopy(person)
        events = normalize_timeline_events(
            synchronized.get("timeline_events", [])
        )
        starting_location = (
            str(requested_starting_location or "").strip()
            if requested_starting_location is not None
            else starting_location_from_events(events)
        )
        born_note = born_note_from_events(events)
        previous_override_ids = born_long_distance_parent_ids(events)
        location_context = child_parent_location_context(
            synchronized,
            self.database.list_people(),
        )
        override_parent_ids = []

        if location_context["conflict"]:
            override_is_current = (
                bool(previous_override_ids)
                and previous_override_ids == location_context["parent_ids"]
            )

            if not long_distance_override and not override_is_current:
                raise ParentLocationConflict(
                    synchronized.get("displayed_name", "This child"),
                    location_context["birthing_parent_name"],
                    location_context["birthing_location"],
                    location_context["non_birthing_parent_name"],
                    location_context["non_birthing_location"],
                    location_context["parent_ids"],
                )

            starting_location = location_context["birthing_location"]
            born_note = add_long_distance_note(born_note)
            override_parent_ids = location_context["parent_ids"]
        else:
            if location_context["inherited_location"]:
                starting_location = location_context["inherited_location"]

            born_note = remove_long_distance_note(born_note)

        synchronized["timeline_events"] = ensure_life_start_events(
            synchronized,
            starting_location=starting_location,
            born_note=born_note,
            long_distance_parent_ids=override_parent_ids,
        )
        return synchronized

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

            age_check = is_at_least_age(parent, values, 18)

            if age_check is False:
                raise ValueError(
                    f"The selected {role_label} must be at least 18 when the "
                    "child is born."
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

                if record_id in (
                    str(child.get("biological_mother_id", "") or ""),
                    str(child.get("biological_father_id", "") or ""),
                ) and is_at_least_age(values, child, 18) is False:
                    raise ValueError(
                        "This birth date would make the person younger than 18 "
                        f"when {child.get('displayed_name', 'their child')} was born."
                    )

    def synchronize_spouses(
        self,
        record_id,
        old_spouse_relationships,
        new_spouse_relationships,
    ):
        old_relationships = normalize_spouse_relationships(
            old_spouse_relationships
        )
        new_relationships = normalize_spouse_relationships(
            new_spouse_relationships
        )
        old_by_id = {
            relationship["person_id"]: relationship
            for relationship in old_relationships
        }
        new_by_id = {
            relationship["person_id"]: relationship
            for relationship in new_relationships
        }

        for mate_id in set(old_by_id) | set(new_by_id):
            mate = self.database.read_person(mate_id)

            if mate is None:
                continue

            reciprocal_relationships = normalize_spouse_relationships(
                mate.get("spouse_relationships", [])
            )
            reciprocal_relationships = [
                relationship
                for relationship in reciprocal_relationships
                if relationship["person_id"] != record_id
            ]

            if mate_id in new_by_id:
                reciprocal_relationships.append(
                    reciprocal_relationship(new_by_id[mate_id], record_id)
                )

            self.database.update_person(
                mate_id,
                {
                    "mate_ids": relationship_ids(reciprocal_relationships),
                    "spouse_relationships": reciprocal_relationships,
                },
            )

    def synchronize_mates(self, record_id, old_mate_ids, new_mate_ids):
        old_relationships = merge_mate_ids([], old_mate_ids)
        new_relationships = merge_mate_ids([], new_mate_ids)
        self.synchronize_spouses(record_id, old_relationships, new_relationships)

    def synchronize_coparents(self, child):
        mother_id = str(child.get("biological_mother_id", "") or "").strip()
        father_id = str(child.get("biological_father_id", "") or "").strip()

        if not mother_id or not father_id or mother_id == father_id:
            return

        mother = self.database.read_person(mother_id)
        father = self.database.read_person(father_id)

        if mother is None or father is None:
            return

        mother_relationships = merge_mate_ids(
            mother.get("spouse_relationships", []),
            mother.get("mate_ids", []),
        )
        father_relationships = merge_mate_ids(
            father.get("spouse_relationships", []),
            father.get("mate_ids", []),
        )
        mother_mates = relationship_ids(mother_relationships)
        father_mates = relationship_ids(father_relationships)

        if father_id not in mother_mates:
            mother_mates.append(father_id)
            mother_relationships.append(empty_spouse_relationship(father_id))
            self.database.update_person(
                mother_id,
                {
                    "mate_ids": mother_mates,
                    "spouse_relationships": mother_relationships,
                },
            )

        if mother_id not in father_mates:
            father_mates.append(mother_id)
            father_relationships.append(empty_spouse_relationship(mother_id))
            self.database.update_person(
                father_id,
                {
                    "mate_ids": father_mates,
                    "spouse_relationships": father_relationships,
                },
            )

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
