import re
from datetime import date


DATE_PART_FIELDS = ("year", "month", "day")
PARTIAL_DATE_PATTERN = re.compile(r"^(\d{1,4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?$")


def normalize_date_parts(year, month, day, label="Date"):
    values = []

    for value, field_name in zip((year, month, day), DATE_PART_FIELDS):
        if value in (None, ""):
            values.append(None)
            continue

        if isinstance(value, bool):
            raise ValueError(f"{label} {field_name} must be a whole number.")

        try:
            values.append(int(value))
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{label} {field_name} must be a whole number."
            ) from error

    normalized_year, normalized_month, normalized_day = values

    if normalized_year is not None and not 1 <= normalized_year <= 9999:
        raise ValueError(f"{label} year must be between 1 and 9999.")

    if normalized_month is not None and not 1 <= normalized_month <= 12:
        raise ValueError(f"{label} month must be between 1 and 12.")

    if normalized_day is not None and not 1 <= normalized_day <= 31:
        raise ValueError(f"{label} day must be between 1 and 31.")

    if normalized_day is not None and normalized_month is None:
        raise ValueError(f"{label} day requires a month.")

    if (
        normalized_year is not None
        and normalized_month is not None
        and normalized_day is not None
    ):
        try:
            date(normalized_year, normalized_month, normalized_day)
        except ValueError as error:
            raise ValueError(f"{label} is not a valid calendar date.") from error

    return normalized_year, normalized_month, normalized_day


def person_date_parts(person, prefix="birth"):
    if not isinstance(person, dict):
        return None, None, None

    return (
        person.get(f"{prefix}_year"),
        person.get(f"{prefix}_month"),
        person.get(f"{prefix}_day"),
    )


def is_at_least_age(older_person, younger_person, minimum_age=18):
    older_year, older_month, older_day = person_date_parts(older_person)
    younger_year, younger_month, younger_day = person_date_parts(younger_person)

    if older_year in (None, "") or younger_year in (None, ""):
        return None

    older_year = int(older_year)
    younger_year = int(younger_year)
    year_gap = younger_year - older_year

    if year_gap > minimum_age:
        return True

    if year_gap < minimum_age:
        return False

    if older_month in (None, "") or younger_month in (None, ""):
        return True

    older_month = int(older_month)
    younger_month = int(younger_month)

    if younger_month > older_month:
        return True

    if younger_month < older_month:
        return False

    if older_day in (None, "") or younger_day in (None, ""):
        return True

    return int(younger_day) >= int(older_day)


def format_date_parts(year, month, day, unknown="nd."):
    if year in (None, ""):
        return unknown

    formatted = str(year).zfill(4)

    if month not in (None, ""):
        formatted += f"-{int(month):02d}"

    if day not in (None, ""):
        formatted += f"-{int(day):02d}"

    return formatted


def normalize_partial_date(value, label="Date"):
    date_text = str(value or "").strip()

    if not date_text:
        return ""

    match = PARTIAL_DATE_PATTERN.fullmatch(date_text)

    if match is None:
        raise ValueError(f"{label} must use YYYY, YYYY-MM, or YYYY-MM-DD.")

    year, month, day = normalize_date_parts(
        match.group(1),
        match.group(2),
        match.group(3),
        label,
    )
    normalized = str(year).zfill(4)

    if month is not None:
        normalized += f"-{month:02d}"

    if day is not None:
        normalized += f"-{day:02d}"

    return normalized


def split_partial_date(value, label="Date"):
    normalized = normalize_partial_date(value, label)

    if not normalized:
        return "", "", ""

    parts = normalized.split("-")
    return (
        parts[0],
        parts[1] if len(parts) > 1 else "",
        parts[2] if len(parts) > 2 else "",
    )
