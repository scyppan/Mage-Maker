import uuid
from copy import deepcopy

from mage_maker.core.dates import normalize_partial_date
from mage_maker.sections.events.types import (
    EVENT_LABEL_TYPES,
    EVENT_TYPE_LABELS,
    canonical_event_type,
    event_type_options,
)


EVENT_TYPES = event_type_options("person", include_automatic=True)


def normalize_timeline_events(events):
    if events in (None, ""):
        return []

    if not isinstance(events, list):
        raise TypeError("Timeline events must be a list.")

    normalized_events = []
    seen_ids = set()

    for event in events:
        normalized_event = normalize_timeline_event(event)
        event_id = normalized_event["event_id"]

        if event_id in seen_ids:
            normalized_event["event_id"] = str(uuid.uuid4())

        seen_ids.add(normalized_event["event_id"])
        normalized_events.append(normalized_event)

    return sort_timeline_events(normalized_events)


def normalize_timeline_event(event):
    if not isinstance(event, dict):
        raise TypeError("Every timeline event must be an object.")

    normalized = deepcopy(event)
    normalized["event_id"] = str(normalized.get("event_id") or uuid.uuid4()).strip()
    normalized["event_type"] = canonical_event_type(
        normalized.get("event_type") or "custom"
    )
    normalized["detail"] = str(normalized.get("detail") or "").strip()
    normalized["date"] = normalize_event_date(normalized.get("date"))
    normalized["note"] = str(normalized.get("note") or "").strip()
    normalized["related_person_id"] = str(
        normalized.get("related_person_id") or ""
    ).strip()
    normalized["related_name_entry_id"] = str(
        normalized.get("related_name_entry_id") or ""
    ).strip()
    normalized["automatic_source"] = str(
        normalized.get("automatic_source") or ""
    ).strip()

    if normalized["event_type"] not in EVENT_TYPE_LABELS:
        normalized["event_type"] = "custom"

    if normalized["event_type"] == "custom" and not normalized["detail"]:
        raise ValueError("A custom timeline event needs an event description.")

    return normalized


def normalize_event_date(value):
    return normalize_partial_date(value, "Timeline date")


def sort_timeline_events(events):
    return sorted(
        deepcopy(list(events)),
        key=timeline_event_sort_key,
    )


def timeline_event_sort_key(event):
    event_type = str(event.get("event_type") or "custom")
    life_start_priority = {
        "starting_location": 0,
        "born": 1,
        "birth_name": 2,
    }.get(event_type)
    event_date = str(event.get("date") or "")

    if life_start_priority is not None:
        return (
            life_start_priority,
            0,
            0,
            0,
            str(event.get("event_id") or ""),
        )

    if not event_date:
        return 4, 10000, 13, 32, str(event.get("event_id") or "")

    parts = [int(part) for part in event_date.split("-")]
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 0
    day = parts[2] if len(parts) > 2 else 0
    return 3, year, month, day, str(event.get("event_id") or "")


def timeline_event_summary(event):
    event_type = str(event.get("event_type") or "custom")
    detail = str(event.get("detail") or "").strip()

    if event_type == "starting_location":
        return f"Starting location: {detail or 'Unknown'}"

    if event_type == "born":
        return "Born"

    if event_type == "birth_name":
        return f"Birth name: {detail}" if detail else "Birth name"

    if event_type == "gave_birth":
        return f"Gave birth to {detail}" if detail else "Gave birth"

    if event_type == "had_child":
        return "Had a child"

    if event_type == "got_married":
        return f"Got married to {detail}" if detail else "Got married"

    if event_type == "died":
        return f"Died: {detail}" if detail else "Died"

    if event_type == "started_school":
        return f"Started at {detail} school" if detail else "Started at school"

    if event_type == "opened_business":
        return (
            f"Opened a business: {detail}"
            if detail
            else "Opened a business"
        )

    if event_type == "got_job":
        return f"Got a job: {detail}" if detail else "Got a job"

    if event_type == "relocated":
        return f"Relocated to {detail}" if detail else "Relocated"

    if event_type == "name_change":
        return f"Name change: {detail}" if detail else "Name change"

    return detail or "Custom event"


def timeline_detail_label(event_type):
    labels = {
        "starting_location": "Location",
        "born": "Birth detail",
        "birth_name": "Birth name",
        "gave_birth": "Child or event detail",
        "had_child": "Child's name",
        "got_married": "Spouse or event detail",
        "died": "Death detail",
        "started_school": "School name",
        "opened_business": "Business name",
        "got_job": "Job or employer",
        "relocated": "New location",
        "name_change": "New name",
        "custom": "Event description",
    }
    return labels.get(event_type, "Event detail")


def person_birth_timeline_date(person):
    if not isinstance(person, dict):
        return ""

    year = person.get("birth_year")
    month = person.get("birth_month")
    day = person.get("birth_day")

    if year in (None, ""):
        return ""

    date_parts = [str(year).zfill(4)]

    if month not in (None, ""):
        date_parts.append(str(month).zfill(2))

    if day not in (None, ""):
        date_parts.append(str(day).zfill(2))

    return "-".join(date_parts)


def automatic_child_timeline_event(child, existing_event=None):
    if not isinstance(child, dict):
        raise TypeError("A child timeline event needs a person record.")

    child_id = str(child.get("record_id", "") or "").strip()

    if not child_id:
        raise ValueError("A child timeline event needs a person identifier.")

    child_name = str(
        child.get("displayed_name", "") or "Unnamed child"
    ).strip()
    event = deepcopy(existing_event) if isinstance(existing_event, dict) else {}
    previous_detail = str(event.get("detail") or "").strip()
    previous_note = str(event.get("note") or "").strip()
    event.setdefault("event_id", f"had-child:{child_id}")

    if not previous_note or previous_note == f"Child: {previous_detail}":
        event["note"] = f"Child: {child_name}"

    event["event_type"] = "had_child"
    event["detail"] = child_name
    event["date"] = person_birth_timeline_date(child)
    event["related_person_id"] = child_id
    event["automatic_source"] = "child_assignment"
    return normalize_timeline_event(event)
