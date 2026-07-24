from copy import deepcopy

from mage_maker.sections.locations.models import (
    descendant_ids,
    founding_event_title,
    location_events_for_period,
    location_depth,
    location_path,
    normalize_location_event,
    normalize_location_record,
    visible_location_timeline,
)
from mage_maker.sections.locations.periods import categorized_people_for_period
from mage_maker.sections.timeline.locations import normalize_location


RECENT_LOCATION_STORAGE_KEY = "_recent_locations"
RECENT_LOCATION_STORAGE_LIMIT = 12
RECENT_WORLD_LOCATION_ID = "__mage_maker_world__"


def mage_location_names(people):
    names = []
    used_names = set()

    for person in people if isinstance(people, list) else []:
        if not isinstance(person, dict):
            continue

        candidates = [
            person.get("starting_location"),
            person.get("birth_location"),
            person.get("current_location"),
            person.get("location"),
        ]

        for event in person.get("timeline_events", []):
            if not isinstance(event, dict):
                continue

            event_type = str(event.get("event_type", "") or "").strip()

            if event_type in ("starting_location", "relocated"):
                candidates.append(event.get("detail"))

            candidates.append(event.get("location"))

        for candidate in candidates:
            name = " ".join(str(candidate or "").strip().split())
            name_key = normalize_location(name)

            if not name_key or name_key in used_names:
                continue

            used_names.add(name_key)
            names.append(name)

    return names


class LocationController:
    def __init__(self, database, people_provider):
        self.database = database
        self.people_provider = people_provider

    def list_locations(self):
        self.synchronize_mage_locations()
        locations = self.database.list_records("locations")
        decorated = []

        for location in locations:
            record_id = str(location.get("record_id", "") or "")
            decorated.append(
                (
                    location_path(record_id, locations).casefold(),
                    location,
                )
            )

        decorated.sort(key=self.decorated_location_sort_key)
        return [location for path, location in decorated]

    def synchronize_mage_locations(self):
        locations = self.database.list_records("locations")
        known_names = {
            normalize_location(location.get("name", ""))
            for location in locations
            if normalize_location(location.get("name", ""))
        }
        created_locations = []

        for location_name in mage_location_names(self.people_provider()):
            location_key = normalize_location(location_name)

            if location_key in known_names:
                continue

            normalized = normalize_location_record(
                {
                    "name": location_name,
                    "parent_location_id": "",
                    "demographics": "",
                    "notes": "",
                    "timeline_events": [],
                }
            )
            created_locations.append(
                self.database.create_record("locations", normalized)
            )
            known_names.add(location_key)

        if created_locations:
            self.database.save()

        return created_locations

    def decorated_location_sort_key(self, decorated_location):
        return decorated_location[0]

    def get_location(self, record_id):
        return self.database.read_record("locations", record_id)

    def remember_location_interaction(self, location_id=""):
        normalized_location_id = str(location_id or "").strip()
        available_ids = {
            str(location.get("record_id", "") or "").strip()
            for location in self.database.list_records("locations")
            if str(location.get("record_id", "") or "").strip()
        }

        if normalized_location_id and normalized_location_id not in available_ids:
            return False

        encoded_location_id = (
            normalized_location_id
            if normalized_location_id
            else RECENT_WORLD_LOCATION_ID
        )
        stored_history = self.database.data.get(
            RECENT_LOCATION_STORAGE_KEY,
            [],
        )
        history = (
            [
                str(stored_location_id or "").strip()
                for stored_location_id in stored_history
                if str(stored_location_id or "").strip()
            ]
            if isinstance(stored_history, list)
            else []
        )
        updated_history = [
            encoded_location_id,
            *[
                stored_location_id
                for stored_location_id in history
                if stored_location_id != encoded_location_id
            ],
        ][:RECENT_LOCATION_STORAGE_LIMIT]

        if updated_history == history:
            return False

        self.database.data[RECENT_LOCATION_STORAGE_KEY] = updated_history
        self.database.dirty = True
        return True

    def recent_location_ids(self, limit=5):
        available_ids = {
            str(location.get("record_id", "") or "").strip()
            for location in self.database.list_records("locations")
            if str(location.get("record_id", "") or "").strip()
        }
        stored_history = self.database.data.get(
            RECENT_LOCATION_STORAGE_KEY,
            [],
        )
        candidate_ids = (
            [
                str(stored_location_id or "").strip()
                for stored_location_id in stored_history
                if str(stored_location_id or "").strip()
            ]
            if isinstance(stored_history, list)
            else []
        )
        event_history = self.database.data.get(
            "_recent_event_associations",
            {},
        )

        if isinstance(event_history, dict):
            event_location_ids = event_history.get("location_ids", [])

            if isinstance(event_location_ids, list):
                candidate_ids.extend(
                    str(location_id or "").strip()
                    for location_id in event_location_ids
                    if str(location_id or "").strip()
                )

        recent_ids = []

        for candidate_id in candidate_ids:
            normalized_id = (
                ""
                if candidate_id == RECENT_WORLD_LOCATION_ID
                else candidate_id
            )

            if normalized_id and normalized_id not in available_ids:
                continue

            if normalized_id in recent_ids:
                continue

            recent_ids.append(normalized_id)

            if len(recent_ids) >= max(0, int(limit)):
                break

        return recent_ids

    def create_location(self, values):
        normalized = normalize_location_record(values)
        self.validate_location(normalized)
        created = self.database.create_record("locations", normalized)
        self.database.save()
        return created

    def create_placeholder_location(self, place, parent_location_id=""):
        return self.create_location(
            {
                "name": str(place or "").strip(),
                "parent_location_id": str(
                    parent_location_id or ""
                ).strip(),
                "demographics": "",
                "notes": "",
                "extinct": False,
                "extinction_year": "",
                "timeline_events": [],
            }
        )

    def update_location(self, record_id, values):
        current = self.get_location(record_id)

        if current is None:
            raise KeyError(f"Unknown location record_id: {record_id}")

        prospective = deepcopy(current)
        prospective.update(deepcopy(values))
        prospective = normalize_location_record(prospective)
        self.validate_location(prospective, record_id)
        updated = self.database.update_record(
            "locations",
            record_id,
            prospective,
        )
        self.database.save()
        return updated

    def delete_location(self, record_id):
        locations = self.list_locations()
        location = self.get_location(record_id)
        children = [
            location
            for location in locations
            if str(location.get("parent_location_id", "") or "") == record_id
        ]

        if children:
            raise ValueError("Move or delete this location's nested locations first.")

        linked_organizations = [
            organization
            for organization in self.database.list_records("organizations")
            if str(organization.get("location_id", "") or "") == record_id
        ]

        if linked_organizations:
            raise ValueError(
                "Move or delete the organizations tied to this location first."
            )

        linked_events = [
            event
            for event in self.database.list_records("events")
            if record_id in event.get("location_ids", [])
        ]
        linked_person_events = [
            event
            for person in self.people_provider()
            if isinstance(person, dict)
            for event in person.get("timeline_events", [])
            if isinstance(event, dict)
            and record_id in event.get("location_ids", [])
        ]

        if linked_events or linked_person_events:
            raise ValueError(
                "Move or remove the events tied to this location first."
            )

        referenced_names = {
            normalize_location(name)
            for name in mage_location_names(self.people_provider())
        }
        location_name = normalize_location(
            (location or {}).get("name", "")
        )

        if location_name and location_name in referenced_names:
            raise ValueError(
                "Change the mages who reference this location before deleting it."
            )

        deleted = self.database.delete_record("locations", record_id)
        self.database.save()
        return deleted

    def add_event(self, location_id, event):
        location = self.get_location(location_id)

        if location is None:
            raise KeyError(f"Unknown location record_id: {location_id}")

        event_values = deepcopy(event)

        if str(event_values.get("event_type", "") or "") == "founding":
            event_values["title"] = (
                founding_event_title(location_id, self.list_locations())
                or event_values.get("title", "")
            )

        normalized_event = normalize_location_event(event_values)
        events = list(location.get("timeline_events", []))
        events.append(normalized_event)
        updated = self.update_location(
            location_id,
            {"timeline_events": events},
        )
        return updated, normalized_event

    def update_event(self, location_id, event_id, values):
        location = self.get_location(location_id)

        if location is None:
            raise KeyError(f"Unknown location record_id: {location_id}")

        event_values = deepcopy(values)

        if str(event_values.get("event_type", "") or "") == "founding":
            event_values["title"] = (
                founding_event_title(location_id, self.list_locations())
                or event_values.get("title", "")
            )

        normalized_event = normalize_location_event(
            {**event_values, "event_id": event_id}
        )
        events = []
        replaced = False

        for event in location.get("timeline_events", []):
            if event.get("event_id") == event_id:
                events.append(normalized_event)
                replaced = True
            else:
                events.append(event)

        if not replaced:
            raise KeyError(f"Unknown location event_id: {event_id}")

        updated = self.update_location(
            location_id,
            {"timeline_events": events},
        )
        return updated, normalized_event

    def delete_event(self, location_id, event_id):
        location = self.get_location(location_id)

        if location is None:
            raise KeyError(f"Unknown location record_id: {location_id}")

        events = [
            event
            for event in location.get("timeline_events", [])
            if event.get("event_id") != event_id
        ]

        if len(events) == len(location.get("timeline_events", [])):
            raise KeyError(f"Unknown location event_id: {event_id}")

        return self.update_location(location_id, {"timeline_events": events})

    def timeline_for(self, location_id):
        return visible_location_timeline(
            location_id,
            self.list_locations(),
            self.people_provider(),
            self.database.list_records("events"),
        )

    def people_for_period(
        self,
        start_year,
        end_year,
        location_id="",
        reproductive_without_children=False,
    ):
        return categorized_people_for_period(
            self.people_provider(),
            self.list_locations(),
            start_year,
            end_year,
            location_id,
            reproductive_without_children,
        )

    def events_for_period(
        self,
        start_year,
        end_year,
        location_id="",
        famous_people_only=False,
    ):
        return location_events_for_period(
            start_year,
            end_year,
            location_id,
            self.list_locations(),
            self.people_provider(),
            famous_people_only,
        )

    def parent_options(self, excluded_location_id=""):
        locations = self.list_locations()
        unavailable_ids = descendant_ids(excluded_location_id, locations)
        unavailable_ids.add(str(excluded_location_id or ""))
        options = []

        for location in locations:
            record_id = str(location.get("record_id", "") or "")

            if record_id in unavailable_ids:
                continue

            options.append(
                {
                    "record_id": record_id,
                    "label": location_path(record_id, locations),
                    "depth": location_depth(record_id, locations),
                }
            )

        return options

    def validate_location(self, values, record_id=""):
        locations = self.list_locations()
        name = str(values.get("name", "") or "").strip()
        parent_id = str(values.get("parent_location_id", "") or "").strip()

        for location in locations:
            existing_id = str(location.get("record_id", "") or "")

            if existing_id == record_id:
                continue

            if str(location.get("name", "") or "").strip().casefold() == name.casefold():
                raise ValueError(f'A location named "{name}" already exists.')

        if parent_id and self.get_location(parent_id) is None:
            raise ValueError("The selected parent location no longer exists.")

        if parent_id and parent_id == record_id:
            raise ValueError("A location cannot contain itself.")

        if record_id and parent_id in descendant_ids(record_id, locations):
            raise ValueError("A location cannot be nested inside its descendant.")
