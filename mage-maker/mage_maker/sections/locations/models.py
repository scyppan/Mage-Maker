import uuid
from copy import deepcopy

from mage_maker.core.dates import format_date_parts, normalize_partial_date
from mage_maker.sections.family_tree.spouse_relationships import (
    normalize_spouse_relationships,
)
from mage_maker.sections.timeline.events import normalize_timeline_events
from mage_maker.sections.timeline.locations import location_at_date, normalize_location


def normalize_location_event(event):
    if not isinstance(event, dict):
        raise TypeError("Every location event must be an object.")

    normalized = deepcopy(event)
    normalized["event_id"] = str(
        normalized.get("event_id") or uuid.uuid4()
    ).strip()
    normalized["date"] = normalize_partial_date(
        normalized.get("date"),
        "Location event date",
    )
    normalized["title"] = str(normalized.get("title", "") or "").strip()
    normalized["note"] = str(normalized.get("note", "") or "").strip()

    if not normalized["title"]:
        raise ValueError("A location event needs a title.")

    return normalized


def normalize_location_events(events):
    if events in (None, ""):
        return []

    if not isinstance(events, list):
        raise TypeError("Location events must be a list.")

    normalized_events = []
    seen_ids = set()

    for event in events:
        normalized = normalize_location_event(event)

        if normalized["event_id"] in seen_ids:
            normalized["event_id"] = str(uuid.uuid4())

        seen_ids.add(normalized["event_id"])
        normalized_events.append(normalized)

    normalized_events.sort(key=location_event_sort_key)
    return normalized_events


def normalize_location_record(values):
    if not isinstance(values, dict):
        raise TypeError("A location must be an object.")

    normalized = deepcopy(values)
    normalized["name"] = str(normalized.get("name", "") or "").strip()
    normalized["parent_location_id"] = str(
        normalized.get("parent_location_id", "") or ""
    ).strip()
    normalized["demographics"] = str(
        normalized.get("demographics", "") or ""
    ).strip()
    normalized["notes"] = str(normalized.get("notes", "") or "").strip()
    normalized["timeline_events"] = normalize_location_events(
        normalized.get("timeline_events", [])
    )

    if not normalized["name"]:
        raise ValueError("A location must have a name.")

    return normalized


def locations_by_id(locations):
    return {
        str(location.get("record_id", "") or "").strip(): location
        for location in locations
        if isinstance(location, dict)
        and str(location.get("record_id", "") or "").strip()
    }


def location_depth(location_id, locations):
    records = locations_by_id(locations)
    current_id = str(location_id or "").strip()
    visited = set()
    depth = 0

    while current_id:
        if current_id in visited:
            raise ValueError("Location nesting contains a cycle.")

        visited.add(current_id)
        current = records.get(current_id)

        if current is None:
            break

        parent_id = str(current.get("parent_location_id", "") or "").strip()

        if not parent_id:
            break

        depth += 1
        current_id = parent_id

    return depth


def location_path(location_id, locations):
    records = locations_by_id(locations)
    current_id = str(location_id or "").strip()
    visited = set()
    names = []

    while current_id:
        if current_id in visited:
            raise ValueError("Location nesting contains a cycle.")

        visited.add(current_id)
        current = records.get(current_id)

        if current is None:
            break

        names.append(str(current.get("name", "") or "Unnamed").strip())
        current_id = str(current.get("parent_location_id", "") or "").strip()

    names.reverse()
    return " › ".join(names)


def ancestor_locations(location_id, locations):
    records = locations_by_id(locations)
    current_id = str(location_id or "").strip()
    ancestors = []
    visited = set()

    while current_id:
        if current_id in visited:
            raise ValueError("Location nesting contains a cycle.")

        visited.add(current_id)
        current = records.get(current_id)

        if current is None:
            break

        ancestors.append(current)
        current_id = str(current.get("parent_location_id", "") or "").strip()

    return ancestors


def descendant_ids(location_id, locations):
    selected_id = str(location_id or "").strip()
    descendants = set()
    changed = True

    while changed:
        changed = False

        for location in locations:
            record_id = str(location.get("record_id", "") or "").strip()
            parent_id = str(
                location.get("parent_location_id", "") or ""
            ).strip()

            if record_id in descendants or record_id == selected_id:
                continue

            if parent_id == selected_id or parent_id in descendants:
                descendants.add(record_id)
                changed = True

    return descendants


def location_event_sort_key(event):
    date_text = str(event.get("date", "") or "").strip()

    if not date_text:
        date_key = (10000, 13, 32)
    else:
        parts = [int(part) for part in date_text.split("-")]
        date_key = (
            parts[0],
            parts[1] if len(parts) > 1 else 0,
            parts[2] if len(parts) > 2 else 0,
        )

    return (
        date_key,
        str(event.get("title", "") or "").casefold(),
        str(event.get("event_id", "") or ""),
    )


def person_location_events(people, locations):
    known_locations = {
        normalize_location(location.get("name", "")): location
        for location in locations
        if normalize_location(location.get("name", ""))
    }
    people_by_id = {
        str(person.get("record_id", "") or "").strip(): person
        for person in people
        if isinstance(person, dict)
        and str(person.get("record_id", "") or "").strip()
    }
    generated_events = []
    seen_events = set()

    for person in people_by_id.values():
        person_id = str(person.get("record_id", "") or "").strip()
        person_name = str(
            person.get("displayed_name", "") or "Unnamed magician"
        ).strip()

        for event in normalize_timeline_events(person.get("timeline_events", [])):
            event_type = str(event.get("event_type", "") or "")

            if event_type not in ("born", "got_married"):
                continue

            event_date = str(event.get("date", "") or "")
            location_name = location_at_date(person, event_date)
            location = known_locations.get(normalize_location(location_name))

            if location is None:
                continue

            detail = str(event.get("detail", "") or "").strip()
            title = (
                f"{person_name} was born"
                if event_type == "born"
                else f"{person_name} married {detail}"
                if detail
                else f"{person_name} got married"
            )
            unique_key = (
                person_id,
                event_type,
                event_date,
                detail.casefold(),
            )

            if unique_key in seen_events:
                continue

            seen_events.add(unique_key)
            generated_events.append(
                {
                    "event_id": f"mage:{person_id}:{event.get('event_id', '')}",
                    "date": event_date,
                    "title": title,
                    "note": str(event.get("note", "") or "").strip(),
                    "origin_location_id": location.get("record_id", ""),
                    "related_person_id": person_id,
                    "event_kind": "mage",
                }
            )

        for relationship in normalize_spouse_relationships(
            person.get("spouse_relationships", [])
        ):
            mate_id = relationship["person_id"]

            if not relationship["married"] or person_id >= mate_id:
                continue

            mate = people_by_id.get(mate_id)

            if mate is None:
                continue

            marriage_date = format_date_parts(
                relationship.get("marriage_year"),
                relationship.get("marriage_month"),
                relationship.get("marriage_day"),
                unknown="",
            )
            location_name = location_at_date(person, marriage_date)
            location = known_locations.get(normalize_location(location_name))

            if location is None:
                continue

            mate_name = str(
                mate.get("displayed_name", "") or "Unnamed magician"
            ).strip()
            couple_names = sorted((person_name, mate_name), key=str.casefold)
            unique_key = (
                "spouse_relationship",
                tuple(sorted((person_id, mate_id))),
                marriage_date,
            )

            if unique_key in seen_events:
                continue

            seen_events.add(unique_key)
            generated_events.append(
                {
                    "event_id": f"marriage:{person_id}:{mate_id}",
                    "date": marriage_date,
                    "title": f"{couple_names[0]} married {couple_names[1]}",
                    "note": "",
                    "origin_location_id": location.get("record_id", ""),
                    "related_person_id": person_id,
                    "event_kind": "mage",
                }
            )

    return generated_events


def visible_location_timeline(location_id, locations, people):
    selected_id = str(location_id or "").strip()
    visible_origins = ancestor_locations(selected_id, locations)
    person_events = person_location_events(people, locations)
    visible_events = []

    for propagation_distance, origin in enumerate(visible_origins):
        origin_id = str(origin.get("record_id", "") or "").strip()
        origin_name = str(origin.get("name", "") or "Unnamed").strip()
        origin_depth = location_depth(origin_id, locations)

        for event in normalize_location_events(origin.get("timeline_events", [])):
            visible_event = deepcopy(event)
            visible_event.update(
                {
                    "origin_location_id": origin_id,
                    "origin_location_name": origin_name,
                    "source_level": origin_depth,
                    "propagation_distance": propagation_distance,
                    "event_kind": "location",
                    "related_person_id": "",
                }
            )
            visible_events.append(visible_event)

        for event in person_events:
            if event.get("origin_location_id") != origin_id:
                continue

            visible_event = deepcopy(event)
            visible_event.update(
                {
                    "origin_location_name": origin_name,
                    "source_level": origin_depth,
                    "propagation_distance": propagation_distance,
                }
            )
            visible_events.append(visible_event)

    visible_events.sort(key=location_event_sort_key)
    return visible_events
