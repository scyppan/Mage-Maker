import re
import uuid
from copy import deepcopy

from mage_maker.core.wizarding_currency import normalize_monthly_salary
from mage_maker.sections.events.types import (
    EVENT_LABEL_TYPES,
    EVENT_TYPE_LABELS,
    canonical_event_type,
    event_type_label,
    event_type_options,
)
from mage_maker.sections.locations.period_definitions import (
    EARLIEST_CALCULATION_YEAR,
    LATEST_CALCULATION_YEAR,
)

WORLD_EVENT_TYPES = event_type_options("period")
WORLD_EVENT_TYPE_LABELS = EVENT_TYPE_LABELS
WORLD_EVENT_LABEL_TYPES = EVENT_LABEL_TYPES
WORLD_EVENT_DATE_PATTERN = re.compile(
    r"^(-?\d{1,5})(?:-(\d{1,2})(?:-(\d{1,2}))?)?$"
)
JOB_EVENT_TYPES = frozenset(("started_job", "received_raise"))
DEATH_EVENT_TYPES = frozenset(("died", "murder"))
JOB_EVENT_ONLY_FIELDS = (
    "organization_job_id",
    "job_title",
    "job_assignment_id",
    "job_end_date",
    "salary",
)


def normalize_job_event_metadata(event):
    normalized = deepcopy(event) if isinstance(event, dict) else {}
    event_type = canonical_event_type(
        normalized.get("event_type")
    )

    if event_type not in JOB_EVENT_TYPES:
        for field_name in JOB_EVENT_ONLY_FIELDS:
            normalized.pop(field_name, None)

        return normalized

    normalized["organization_id"] = str(
        normalized.get("organization_id", "") or ""
    ).strip()
    normalized["organization_name"] = str(
        normalized.get("organization_name", "") or ""
    ).strip()
    normalized["organization_job_id"] = str(
        normalized.get("organization_job_id", "") or ""
    ).strip()
    normalized["job_title"] = str(
        normalized.get("job_title", "") or ""
    ).strip()
    normalized["job_assignment_id"] = str(
        normalized.get("job_assignment_id", "") or ""
    ).strip()
    salary_value = normalized.get("salary")
    normalized["salary"] = (
        None
        if salary_value in (None, "")
        else normalize_monthly_salary(salary_value)
    )
    job_end_date = str(
        normalized.get("job_end_date", "") or ""
    ).strip()
    normalized["job_end_date"] = (
        normalize_world_event_date(job_end_date)
        if job_end_date
        else ""
    )

    if event_type == "received_raise":
        normalized["job_end_date"] = ""

    return normalized


def normalize_world_event(event):
    if not isinstance(event, dict):
        raise TypeError("Every event must be an object.")

    normalized = deepcopy(event)
    normalized["record_id"] = str(
        normalized.get("record_id") or uuid.uuid4()
    ).strip()
    normalized["event_type"] = canonical_event_type(
        normalized.get("event_type") or "other"
    )
    normalized = normalize_job_event_metadata(normalized)
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
    if normalized["event_type"] == "murder":
        normalized["perpetrator_person_ids"] = (
            normalize_association_values(
                normalized.get("perpetrator_person_ids")
            )
        )
        normalized["victim_person_ids"] = normalize_association_values(
            normalized.get("victim_person_ids")
        )
        normalized["witness_person_ids"] = normalize_association_values(
            normalized.get("witness_person_ids")
        )
        normalized["affected_person_ids"] = normalize_association_values(
            normalized.get("affected_person_ids")
        )
        normalized["person_ids"] = normalize_association_values(
            [
                *normalized["perpetrator_person_ids"],
                *normalized["victim_person_ids"],
                *normalized["witness_person_ids"],
                *normalized["affected_person_ids"],
            ]
        )
    else:
        normalized.pop("perpetrator_person_ids", None)
        normalized.pop("victim_person_ids", None)
        normalized.pop("witness_person_ids", None)
        normalized.pop("affected_person_ids", None)
    requested_eminence_person_ids = normalize_association_values(
        normalized.get("eminence_person_ids")
    )
    normalized["eminence_person_ids"] = [
        person_id
        for person_id in requested_eminence_person_ids
        if person_id in normalized["person_ids"]
    ]
    normalized["eminence_skills"] = normalize_eminence_skill_values(
        normalized.get("eminence_skills"),
        normalized["eminence_person_ids"],
    )
    if normalized["event_type"] == "died":
        normalized["eminence_person_ids"] = []
        normalized["eminence_skills"] = {}
    elif normalized["event_type"] == "murder":
        victim_ids = set(normalized["victim_person_ids"])
        normalized["eminence_person_ids"] = [
            person_id
            for person_id in normalized["eminence_person_ids"]
            if person_id not in victim_ids
        ]
        normalized["eminence_skills"] = {
            person_id: skill
            for person_id, skill in normalized["eminence_skills"].items()
            if person_id in normalized["eminence_person_ids"]
        }
    normalized["period_names"] = normalize_association_values(
        normalized.get("period_names")
    )
    normalized["location_ids"] = normalize_association_values(
        normalized.get("location_ids")
    )
    normalized["locked_location_ids"] = normalize_association_values(
        normalized.get("locked_location_ids")
    )

    if (
        normalized["event_type"] in DEATH_EVENT_TYPES
        and len(normalized["location_ids"]) > 1
    ):
        normalized["location_ids"] = normalized["location_ids"][-1:]
        normalized["locked_location_ids"] = [
            location_id
            for location_id in normalized["locked_location_ids"]
            if location_id in normalized["location_ids"]
        ][-1:]

    for location_id in normalized["locked_location_ids"]:
        if location_id not in normalized["location_ids"]:
            normalized["location_ids"].append(location_id)

    normalized["organization_id"] = str(
        normalized.get("organization_id", "") or ""
    ).strip()
    normalized["organization_name"] = str(
        normalized.get("organization_name", "") or ""
    ).strip()

    if normalized["event_type"] not in EVENT_TYPE_LABELS:
        normalized["event_type"] = "other"

    if not normalized["title"]:
        raise ValueError("An event needs a title.")

    return normalized


def normalize_world_events(events):
    if events in (None, ""):
        return []

    if not isinstance(events, list):
        raise TypeError("Events must be a list.")

    normalized_events = []
    used_ids = set()

    for event in events:
        normalized = normalize_world_event(event)

        if normalized["record_id"] in used_ids:
            raise ValueError(
                f'Duplicate event record_id: {normalized["record_id"]}'
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


def death_event_person_ids(event):
    event_values = event if isinstance(event, dict) else {}
    event_type = canonical_event_type(event_values.get("event_type"))

    if event_type == "died":
        return normalize_association_values(
            event_values.get("person_ids")
        )

    if event_type == "murder":
        return normalize_association_values(
            event_values.get("victim_person_ids")
        )

    return []


def death_event_date_sort_key(value):
    date_text = str(value or "").strip()
    match = WORLD_EVENT_DATE_PATTERN.fullmatch(date_text)

    if match is None:
        return 100000, 13, 32

    return (
        int(match.group(1)),
        int(match.group(2) or 0),
        int(match.group(3) or 0),
    )


def death_source_sort_key(event):
    event_values = event if isinstance(event, dict) else {}
    return (
        death_event_date_sort_key(event_values.get("date")),
        str(
            event_values.get(
                "record_id",
                event_values.get("event_id", ""),
            )
            or ""
        ),
    )


def synchronize_people_death_records(database_data, person_ids=None):
    if not isinstance(database_data, dict):
        return False

    people = database_data.get("people", [])
    world_events = database_data.get("events", [])

    if not isinstance(people, list) or not isinstance(world_events, list):
        return False

    selected_ids = (
        {
            str(person_id or "").strip()
            for person_id in person_ids
            if str(person_id or "").strip()
        }
        if person_ids is not None
        else None
    )
    changed = False

    for person in people:
        if not isinstance(person, dict):
            continue

        person_id = str(person.get("record_id", "") or "").strip()

        if selected_ids is not None and person_id not in selected_ids:
            continue

        death_sources = [
            event
            for event in world_events
            if isinstance(event, dict)
            and person_id in death_event_person_ids(event)
        ]
        death_sources.extend(
            event
            for event in person.get("timeline_events", []) or []
            if isinstance(event, dict)
            and canonical_event_type(event.get("event_type")) == "died"
            and str(event.get("date", "") or "").strip()
        )
        death_sources.sort(key=death_source_sort_key)

        if death_sources:
            death_year, death_month, death_day = split_world_event_date(
                death_sources[0].get("date")
            )
            death_values = {
                "deceased": True,
                "death_year": int(death_year),
                "death_month": (
                    int(death_month) if death_month else None
                ),
                "death_day": int(death_day) if death_day else None,
            }
        else:
            death_values = {
                "deceased": False,
                "death_year": None,
                "death_month": None,
                "death_day": None,
            }

        if any(
            person.get(field_name) != value
            for field_name, value in death_values.items()
        ):
            person.update(death_values)
            changed = True

    return changed


def normalize_eminence_skill_values(values, earned_person_ids=()):
    if values in (None, ""):
        candidate_values = {}
    elif isinstance(values, dict):
        candidate_values = values
    else:
        raise TypeError("Event Eminence skills must be an object.")

    earned_ids = {
        str(person_id or "").strip()
        for person_id in earned_person_ids or ()
        if str(person_id or "").strip()
    }
    normalized_values = {}

    for person_id, skill in candidate_values.items():
        normalized_person_id = str(person_id or "").strip()
        normalized_skill = str(skill or "").strip()

        if (
            normalized_person_id in earned_ids
            and normalized_skill
        ):
            normalized_values[normalized_person_id] = normalized_skill

    return normalized_values


def normalize_world_event_date(value):
    date_text = str(value or "").strip()

    if not date_text:
        raise ValueError("An event needs a year.")

    plain_year_match = re.fullmatch(r"-?\d+", date_text)

    if plain_year_match is not None:
        plain_year = int(date_text)

        if (
            plain_year == 0
            or plain_year < EARLIEST_CALCULATION_YEAR
            or plain_year > LATEST_CALCULATION_YEAR
        ):
            raise ValueError(
                "Event year must be between -99999 and 99999, excluding 0."
            )

    match = WORLD_EVENT_DATE_PATTERN.fullmatch(date_text)

    if match is None:
        raise ValueError(
            "Event date must use YYYY, YYYY-MM, or YYYY-MM-DD."
        )

    year = int(match.group(1))
    month = int(match.group(2)) if match.group(2) else None
    day = int(match.group(3)) if match.group(3) else None

    if (
        year == 0
        or year < EARLIEST_CALCULATION_YEAR
        or year > LATEST_CALCULATION_YEAR
    ):
        raise ValueError(
            "Event year must be between -99999 and 99999, excluding 0."
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
        date_key = (100000, 13, 32)
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
    return event_type_label(event)


normalize_event = normalize_world_event
normalize_events = normalize_world_events
event_sort_key = world_event_sort_key
event_year = world_event_year
