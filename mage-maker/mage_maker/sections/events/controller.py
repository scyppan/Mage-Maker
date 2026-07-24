from copy import deepcopy

from mage_maker.sections.events.models import (
    normalize_world_event,
    normalize_world_events,
    world_event_sort_key,
    world_event_year,
)
from mage_maker.sections.events.types import (
    canonical_event_type,
    event_type_is_person_only,
)
from mage_maker.sections.locations.models import (
    ancestor_locations,
    founding_event_title,
    recent_location_label,
)


RECENT_ASSOCIATION_STORAGE_KEY = "_recent_event_associations"
RECENT_ASSOCIATION_STORAGE_LIMIT = 12
RECENT_PERSON_STORAGE_KEY = "_recent_people"
RECENT_LOCATION_STORAGE_KEY = "_recent_locations"
RECENT_WORLD_LOCATION_ID = "__mage_maker_world__"


class EventController:
    def __init__(
        self,
        database,
        people_provider,
        location_provider,
        period_provider,
        location_creator=None,
    ):
        self.database = database
        self.people_provider = people_provider
        self.location_provider = location_provider
        self.period_provider = period_provider
        self.location_creator = location_creator

    def list_events(self):
        titled_events = [
            self.apply_title_rules(event)
            for event in self.database.list_records("events")
        ]
        return normalize_world_events(titled_events)

    def get_event(self, record_id):
        event = self.database.read_record("events", record_id)
        return (
            normalize_world_event(self.apply_title_rules(event))
            if event is not None
            else None
        )

    def create_event(self, values):
        normalized = normalize_world_event(
            self.apply_title_rules(values)
        )
        self.validate_associations(normalized)
        created = self.database.create_record("events", normalized)
        self.remember_associations(created)
        self.database.save()
        return normalize_world_event(created)

    def update_event(self, record_id, values):
        current = self.get_event(record_id)

        if current is None:
            raise KeyError(f"Unknown event record_id: {record_id}")

        prospective = deepcopy(current)
        prospective.update(deepcopy(values))
        prospective["record_id"] = record_id
        normalized = normalize_world_event(
            self.apply_title_rules(prospective)
        )
        self.validate_associations(normalized)
        updated = self.database.update_record(
            "events",
            record_id,
            normalized,
        )
        self.remember_associations(updated)
        self.database.save()
        return normalize_world_event(updated)

    def delete_event(self, record_id):
        deleted = self.database.delete_record("events", record_id)
        self.database.save()
        return normalize_world_event(deleted)

    def apply_title_rules(self, event):
        titled_event = deepcopy(event) if isinstance(event, dict) else {}

        if (
            canonical_event_type(titled_event.get("event_type"))
            != "founding"
        ):
            return titled_event

        location_ids = [
            str(location_id or "").strip()
            for location_id in titled_event.get("locked_location_ids", [])
            if str(location_id or "").strip()
        ]

        if not location_ids:
            location_ids = [
                str(location_id or "").strip()
                for location_id in titled_event.get("location_ids", [])
                if str(location_id or "").strip()
            ]

        title = (
            founding_event_title(
                location_ids[0],
                self.location_provider(),
            )
            if location_ids
            else ""
        )

        if title:
            titled_event["title"] = title

        return titled_event

    def events_for_period(self, period_name, start_year, end_year):
        normalized_start = int(start_year)
        normalized_end = int(end_year)
        matching_events = []

        for event in self.list_events():
            event_year = world_event_year(event.get("date"))

            if (
                event_year is not None
                and normalized_start <= event_year <= normalized_end
            ):
                matching_events.append(event)

        matching_events.sort(key=world_event_sort_key)
        return matching_events

    def events_for_person(self, person_id):
        normalized_person_id = str(person_id or "").strip()
        return [
            event
            for event in self.list_events()
            if normalized_person_id in event["person_ids"]
        ]

    def event_has_famous_person(self, event):
        linked_person_ids = {
            str(person_id or "").strip()
            for person_id in (event or {}).get("person_ids", [])
            if str(person_id or "").strip()
        }

        if not linked_person_ids:
            return False

        return any(
            bool(person.get("famous_person"))
            and str(person.get("record_id", "") or "") in linked_person_ids
            for person in self.people_provider()
            if isinstance(person, dict)
        )

    def event_is_individual(self, event):
        return event_type_is_person_only(
            (event or {}).get("event_type")
        )

    def events_for_location(self, location_id, include_ancestors=True):
        normalized_location_id = str(location_id or "").strip()

        if not normalized_location_id:
            return []

        visible_location_ids = {normalized_location_id}

        if include_ancestors:
            visible_location_ids.update(
                str(location.get("record_id", "") or "")
                for location in ancestor_locations(
                    normalized_location_id,
                    self.location_provider(),
                )
            )

        return [
            event
            for event in self.list_events()
            if visible_location_ids.intersection(event["location_ids"])
        ]

    def people_options(self):
        options = [
            {
                "value": str(person.get("record_id", "") or ""),
                "label": str(
                    person.get("displayed_name", "") or "Unnamed magician"
                ).strip(),
            }
            for person in self.people_provider()
            if str(person.get("record_id", "") or "").strip()
        ]
        options.sort(key=self.association_option_sort_key)
        return options

    def location_options(self):
        locations = self.location_provider()
        options = [
            {
                "value": str(location.get("record_id", "") or ""),
                "label": recent_location_label(
                    location.get("record_id", ""),
                    locations,
                ),
            }
            for location in locations
            if str(location.get("record_id", "") or "").strip()
        ]
        options.sort(key=self.association_option_sort_key)
        return options

    def location_records(self):
        return [
            deepcopy(location)
            for location in self.location_provider()
            if isinstance(location, dict)
        ]

    def create_placeholder_location(self, place, parent_location_id=""):
        if self.location_creator is None:
            raise ValueError("The location collection is unavailable.")

        created = self.location_creator(
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
        return deepcopy(created)

    def defined_year_bounds(self):
        start_years = []
        end_years = []

        for period in self.period_provider():
            try:
                start_years.append(
                    int(period.get("calculation_start_year"))
                )
                end_years.append(
                    int(period.get("calculation_end_year"))
                )
            except (AttributeError, TypeError, ValueError):
                continue

        if not start_years or not end_years:
            return None, None

        return min(start_years), max(end_years)

    def clamp_year_to_defined_periods(self, year):
        normalized_year = int(year)
        periods = []

        for period in self.period_provider():
            try:
                start_year = int(
                    period.get("calculation_start_year")
                )
                end_year = int(
                    period.get("calculation_end_year")
                )
            except (AttributeError, TypeError, ValueError):
                continue

            periods.append((start_year, end_year))

        if not periods:
            return normalized_year

        periods.sort()

        if normalized_year == 0:
            normalized_year = 1

        for start_year, end_year in periods:
            if start_year <= normalized_year <= end_year:
                return normalized_year

        if normalized_year < periods[0][0]:
            return periods[0][0]

        if normalized_year > periods[-1][1]:
            return periods[-1][1]

        for index in range(len(periods) - 1):
            previous_end = periods[index][1]
            next_start = periods[index + 1][0]

            if previous_end < normalized_year < next_start:
                if (
                    normalized_year - previous_end
                    <= next_start - normalized_year
                ):
                    return previous_end

                return next_start

        return normalized_year

    def recent_people_options(self, limit=5):
        return self.recent_association_options(
            "person_ids",
            self.people_options(),
            limit,
            self.recent_interaction_ids(
                RECENT_PERSON_STORAGE_KEY,
            ),
        )

    def recent_location_options(self, limit=5):
        return self.recent_association_options(
            "location_ids",
            self.location_options(),
            limit,
            self.recent_interaction_ids(
                RECENT_LOCATION_STORAGE_KEY,
                excluded_ids=(RECENT_WORLD_LOCATION_ID,),
            ),
        )

    def recent_association_options(
        self,
        field_name,
        options,
        limit,
        preferred_ids=(),
    ):
        options_by_id = {
            str(option.get("value", "") or ""): option
            for option in options
            if str(option.get("value", "") or "").strip()
        }
        recent_options = []
        candidate_ids = [
            *[
                str(association_id or "").strip()
                for association_id in preferred_ids
                if str(association_id or "").strip()
            ],
            *self.recent_association_ids(field_name),
        ]
        used_ids = set()

        for association_id in candidate_ids:
            if association_id in used_ids:
                continue

            used_ids.add(association_id)
            option = options_by_id.get(association_id)

            if option is None:
                continue

            recent_options.append(deepcopy(option))

            if len(recent_options) >= max(0, int(limit)):
                break

        return recent_options

    def recent_interaction_ids(self, storage_key, excluded_ids=()):
        stored_history = self.database.data.get(storage_key, [])

        if not isinstance(stored_history, list):
            return []

        excluded = {
            str(record_id or "").strip()
            for record_id in excluded_ids
            if str(record_id or "").strip()
        }
        recent_ids = []

        for record_id in stored_history:
            normalized_id = str(record_id or "").strip()

            if (
                not normalized_id
                or normalized_id in excluded
                or normalized_id in recent_ids
            ):
                continue

            recent_ids.append(normalized_id)

        return recent_ids

    def recent_association_ids(self, field_name):
        if field_name not in ("person_ids", "location_ids"):
            raise KeyError(f"Unknown event association field: {field_name}")

        history = self.database.data.get(
            RECENT_ASSOCIATION_STORAGE_KEY,
            {},
        )
        stored_ids = (
            history.get(field_name, [])
            if isinstance(history, dict)
            else []
        )

        if isinstance(stored_ids, list) and stored_ids:
            return [
                str(association_id or "").strip()
                for association_id in stored_ids
                if str(association_id or "").strip()
            ]

        inferred_ids = []

        for event in reversed(self.database.list_records("events")):
            association_ids = event.get(field_name, [])

            if not isinstance(association_ids, list):
                continue

            for association_id in reversed(association_ids):
                normalized_id = str(association_id or "").strip()

                if normalized_id and normalized_id not in inferred_ids:
                    inferred_ids.append(normalized_id)

                if len(inferred_ids) >= RECENT_ASSOCIATION_STORAGE_LIMIT:
                    return inferred_ids

        return inferred_ids

    def remember_associations(self, event):
        current_history = self.database.data.get(
            RECENT_ASSOCIATION_STORAGE_KEY,
            {},
        )
        history = (
            deepcopy(current_history)
            if isinstance(current_history, dict)
            else {}
        )

        for field_name in ("person_ids", "location_ids"):
            previous_ids = self.recent_association_ids(field_name)
            event_ids = [
                str(association_id or "").strip()
                for association_id in event.get(field_name, [])
                if str(association_id or "").strip()
            ]
            history[field_name] = (
                event_ids
                + [
                    association_id
                    for association_id in previous_ids
                    if association_id not in event_ids
                ]
            )[:RECENT_ASSOCIATION_STORAGE_LIMIT]

        self.database.data[RECENT_ASSOCIATION_STORAGE_KEY] = history
        self.database.dirty = True

    def association_option_sort_key(self, option):
        return (
            str(option.get("label", "") or "").casefold(),
            str(option.get("value", "") or ""),
        )

    def association_labels(self, event):
        normalized = normalize_world_event(event)
        people_by_id = {
            str(person.get("record_id", "") or ""): str(
                person.get("displayed_name", "") or "Unnamed magician"
            ).strip()
            for person in self.people_provider()
        }
        locations = self.location_provider()
        location_labels = {
            str(location.get("record_id", "") or ""): recent_location_label(
                location.get("record_id", ""),
                locations,
            )
            for location in locations
        }
        return {
            "people": [
                people_by_id.get(person_id, "Missing person")
                for person_id in normalized["person_ids"]
            ],
            "periods": self.period_names_for_event(normalized),
            "locations": [
                location_labels.get(location_id, "Missing location")
                for location_id in normalized["location_ids"]
            ],
        }

    def infer_period_name(self, event):
        normalized = normalize_world_event(event)
        period_names = self.period_names_for_event(normalized)
        return period_names[0] if period_names else ""

    def period_names_for_event(self, event):
        normalized = normalize_world_event(event)
        return self.period_names_for_date(normalized.get("date"))

    def period_names_for_date(self, date_value):
        event_year = world_event_year(date_value)

        if event_year is None:
            return []

        matching_names = []

        for period in self.period_provider():
            try:
                start_year = int(period.get("calculation_start_year"))
                end_year = int(period.get("calculation_end_year"))
            except (TypeError, ValueError):
                continue

            period_name = str(period.get("name", "") or "").strip()

            if (
                period_name
                and start_year <= event_year <= end_year
                and period_name not in matching_names
            ):
                matching_names.append(period_name)

        return matching_names

    def validate_associations(self, event):
        if (
            event.get("event_type") == "relocated"
            and len(event.get("location_ids", [])) != 2
        ):
            raise ValueError(
                "Select exactly two locations for a relocation: "
                "where the person left and where they went."
            )

        if (
            event.get("event_type") == "founding"
            and len(event.get("location_ids", [])) != 1
        ):
            raise ValueError(
                "Select exactly one location for a founding event."
            )

        known_person_ids = {
            str(person.get("record_id", "") or "")
            for person in self.people_provider()
        }
        known_period_names = {
            str(period.get("name", "") or "")
            for period in self.period_provider()
        }
        known_location_ids = {
            str(location.get("record_id", "") or "")
            for location in self.location_provider()
        }
        missing_people = [
            person_id
            for person_id in event["person_ids"]
            if person_id not in known_person_ids
        ]
        missing_periods = [
            period_name
            for period_name in event["period_names"]
            if period_name not in known_period_names
        ]
        missing_locations = [
            location_id
            for location_id in event["location_ids"]
            if location_id not in known_location_ids
        ]

        if missing_people:
            raise ValueError(
                "One or more selected people no longer exist."
            )

        if missing_periods:
            raise ValueError(
                "One or more selected periods no longer exist."
            )

        if missing_locations:
            raise ValueError(
                "One or more selected locations no longer exist."
            )


WorldEventController = EventController
