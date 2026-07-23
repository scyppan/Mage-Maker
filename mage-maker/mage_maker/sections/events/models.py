import re
import uuid
from copy import deepcopy


WORLD_EVENT_TYPES = (
    ("birth", "Birth"),
    ("death", "Death"),
    ("marriage", "Marriage"),
    ("relocation", "Relocation"),
    ("founding", "Founding"),
    ("political", "Political"),
    ("conflict", "Conflict"),
    ("discovery", "Discovery"),
    ("education", "Education"),
    ("cultural", "Cultural"),
    ("disaster", "Disaster"),
    ("other", "Other"),
)
WORLD_EVENT_TYPE_LABELS = dict(WORLD_EVENT_TYPES)
WORLD_EVENT_LABEL_TYPES = {
    label: event_type
    for event_type, label in WORLD_EVENT_TYPES
}
WORLD_EVENT_DATE_PATTERN = re.compile(
    r"^(-?\d{1,4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?$"
)


def normalize_world_event(event):
    if not isinstance(event, dict):
        raise TypeError("Every shared event must be an object.")

    normalized = deepcopy(event)
    normalized["record_id"] = str(
        normalized.get("record_id") or uuid.uuid4()
    ).strip()
    normalized["event_type"] = str(
        normalized.get("event_type") or "other"
    ).strip()
    normalized["title"] = " ".join(
        str(normalized.get("title", "") or "").strip().split()
    )
    normalized["date"] = normalize_world_event_date(
        normalized.get("date")
    )
    normalized["description"] = str(
        normalized.get("description", "") or ""
    ).strip()
    normalized["person_ids"] = normalize_association_values(
        normalized.get("person_ids")
    )
    normalized["period_names"] = normalize_association_values(
        normalized.get("period_names")
    )
    normalized["location_ids"] = normalize_association_values(
        normalized.get("location_ids")
    )
    normalized["locked_location_ids"] = normalize_association_values(
        normalized.get("locked_location_ids")
    )

    for location_id in normalized["locked_location_ids"]:
        if location_id not in normalized["location_ids"]:
            normalized["location_ids"].append(location_id)

    if normalized["event_type"] not in WORLD_EVENT_TYPE_LABELS:
        normalized["event_type"] = "other"

    if not normalized["title"]:
        raise ValueError("A shared event needs a title.")

    return normalized


def normalize_world_events(events):
    if events in (None, ""):
        return []

    if not isinstance(events, list):
        raise TypeError("Shared events must be a list.")

    normalized_events = []
    used_ids = set()

    for event in events:
        normalized = normalize_world_event(event)

        if normalized["record_id"] in used_ids:
            raise ValueError(
                f'Duplicate shared event record_id: {normalized["record_id"]}'
            )

        used_ids.add(normalized["record_id"])
        normalized_events.append(normalized)

    normalized_events.sort(key=world_event_sort_key)
    return normalized_events


def normalize_association_values(values):
    if values in (None, ""):
        return []

    if not isinstance(values, (list, tuple, set)):
        raise TypeError("Event associations must be a list.")

    normalized_values = []
    used_values = set()

    for value in values:
        normalized = str(value or "").strip()

        if not normalized or normalized in used_values:
            continue

        used_values.add(normalized)
        normalized_values.append(normalized)

    return normalized_values


def normalize_world_event_date(value):
    date_text = str(value or "").strip()

    if not date_text:
        raise ValueError("A shared event needs a year.")

    match = WORLD_EVENT_DATE_PATTERN.fullmatch(date_text)

    if match is None:
        raise ValueError(
            "Event date must use YYYY, YYYY-MM, or YYYY-MM-DD."
        )

    year = int(match.group(1))
    month = int(match.group(2)) if match.group(2) else None
    day = int(match.group(3)) if match.group(3) else None

    if year == 0 or year < -9999 or year > 9999:
        raise ValueError(
            "Event year must be between -9999 and 9999, excluding 0."
        )

    if month is not None and not 1 <= month <= 12:
        raise ValueError("Event month must be between 1 and 12.")

    if day is not None and not 1 <= day <= 31:
        raise ValueError("Event day must be between 1 and 31.")

    if day is not None and month is None:
        raise ValueError("Event day requires a month.")

    normalized = str(year)

    if month is not None:
        normalized += f"-{month:02d}"

    if day is not None:
        normalized += f"-{day:02d}"

    return normalized


def split_world_event_date(value):
    if not str(value or "").strip():
        return "", "", ""

    normalized = normalize_world_event_date(value)

    match = WORLD_EVENT_DATE_PATTERN.fullmatch(normalized)
    return (
        match.group(1),
        match.group(2) or "",
        match.group(3) or "",
    )


def world_event_year(value):
    date_text = str(value or "").strip()
    match = WORLD_EVENT_DATE_PATTERN.fullmatch(date_text)

    if match is None:
        return None

    year = int(match.group(1))
    return year if year != 0 else None


def world_event_sort_key(event):
    date_text = str(event.get("date", "") or "")
    match = WORLD_EVENT_DATE_PATTERN.fullmatch(date_text)

    if match is None:
        date_key = (10000, 13, 32)
    else:
        date_key = (
            int(match.group(1)),
            int(match.group(2) or 0),
            int(match.group(3) or 0),
        )

    return (
        date_key,
        str(event.get("title", "") or "").casefold(),
        str(event.get("record_id", "") or ""),
    )


def world_event_type_label(event):
    event_type = str(
        (event or {}).get("event_type", "other") or "other"
    )
    return WORLD_EVENT_TYPE_LABELS.get(event_type, "Other")
