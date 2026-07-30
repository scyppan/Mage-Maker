import random

from mage_maker.sections.development.initial_bonuses import (
    initial_bonus_requirements,
    normalize_initial_bonuses,
)
from mage_maker.sections.development.initial_values import (
    BLOOD_STATUS_HALFBLOOD,
    normalize_blood_status,
    normalize_developmental_environment,
    normalize_parental_values,
)


CHARACTERISTIC_NAMES = (
    "creativity",
    "equanimity",
    "charisma",
    "attractiveness",
    "strength",
    "agility",
    "intellect",
    "willpower",
    "fortitude",
)
CHARACTERISTIC_BASE_VALUE = 1
CHARACTERISTIC_MAXIMUM_VALUE = 5
CHARACTERISTIC_POINTS_TO_SPEND = 8
CHARACTERISTIC_REQUIRED_TOTAL = (
    len(CHARACTERISTIC_NAMES) * CHARACTERISTIC_BASE_VALUE
    + CHARACTERISTIC_POINTS_TO_SPEND
)


def randomized_characteristics():
    randomized_values = {
        field_name: CHARACTERISTIC_BASE_VALUE
        for field_name in CHARACTERISTIC_NAMES
    }

    for _ in range(CHARACTERISTIC_POINTS_TO_SPEND):
        available_fields = [
            field_name
            for field_name in CHARACTERISTIC_NAMES
            if (
                randomized_values[field_name]
                < CHARACTERISTIC_MAXIMUM_VALUE
            )
        ]
        selected_field = random.choice(available_fields)
        randomized_values[selected_field] += 1

    return normalize_characteristics(
        randomized_values,
        allow_uninitialized=False,
    )


def normalize_characteristics(value, allow_uninitialized=True):
    if value in (None, "", {}):
        if allow_uninitialized:
            return None

        raise ValueError("Characteristics have not been assigned.")

    if not isinstance(value, dict):
        raise TypeError("Characteristics must be a dictionary.")

    normalized = {}

    for field_name in CHARACTERISTIC_NAMES:
        candidate = value.get(
            field_name,
            value.get(field_name.title()),
        )

        if candidate in (None, ""):
            candidate = CHARACTERISTIC_BASE_VALUE

        if isinstance(candidate, bool):
            raise ValueError(
                f"{field_name.title()} must be a whole number."
            )

        try:
            normalized_value = int(candidate)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{field_name.title()} must be a whole number."
            ) from error

        if (
            isinstance(candidate, float)
            and not candidate.is_integer()
        ):
            raise ValueError(
                f"{field_name.title()} must be a whole number."
            )

        if not (
            CHARACTERISTIC_BASE_VALUE
            <= normalized_value
            <= CHARACTERISTIC_MAXIMUM_VALUE
        ):
            raise ValueError(
                f"{field_name.title()} must be between "
                f"{CHARACTERISTIC_BASE_VALUE} and "
                f"{CHARACTERISTIC_MAXIMUM_VALUE}."
            )

        normalized[field_name] = normalized_value

    assigned_total = sum(normalized.values())

    if assigned_total > CHARACTERISTIC_REQUIRED_TOTAL:
        raise ValueError(
            "Characteristics cannot use more than "
            f"{CHARACTERISTIC_POINTS_TO_SPEND} starting points."
        )

    if (
        not allow_uninitialized
        and assigned_total != CHARACTERISTIC_REQUIRED_TOTAL
    ):
        raise ValueError(
            "Spend all "
            f"{CHARACTERISTIC_POINTS_TO_SPEND} characteristic points."
        )

    return normalized


def characteristic_points_remaining(value):
    normalized = normalize_characteristics(value)

    if normalized is None:
        return CHARACTERISTIC_POINTS_TO_SPEND

    return CHARACTERISTIC_REQUIRED_TOTAL - sum(normalized.values())


def characteristics_are_complete(value):
    try:
        normalized = normalize_characteristics(
            value,
            allow_uninitialized=False,
        )
    except (TypeError, ValueError):
        return False

    return sum(normalized.values()) == CHARACTERISTIC_REQUIRED_TOTAL


def incomplete_initial_value_names(person):
    person_values = person if isinstance(person, dict) else {}
    incomplete_values = []

    try:
        blood_status = normalize_blood_status(
            person_values.get("blood_status")
        )
    except (TypeError, ValueError):
        blood_status = None
        incomplete_values.append("blood status")

    try:
        parental_values = normalize_parental_values(
            person_values.get("parental_values")
        )
    except (TypeError, ValueError):
        parental_values = None

    if parental_values is None:
        incomplete_values.append("parental values")

    requirements = None

    if blood_status is not None:
        try:
            developmental_environment = (
                normalize_developmental_environment(
                    person_values.get("developmental_environment"),
                    blood_status,
                )
            )
            requirements = initial_bonus_requirements(
                blood_status,
                developmental_environment,
                parental_values,
            )
        except (TypeError, ValueError):
            if blood_status == BLOOD_STATUS_HALFBLOOD:
                incomplete_values.append(
                    "developmental environment"
                )

    try:
        initial_bonuses = normalize_initial_bonuses(
            person_values.get("initial_bonuses")
        )
    except (TypeError, ValueError):
        initial_bonuses = None

    if requirements is not None:
        selected_skills = (
            initial_bonuses.get("skill_bonuses", [])
            if initial_bonuses is not None
            else []
        )
        selected_traits = (
            initial_bonuses.get("traits", [])
            if initial_bonuses is not None
            else []
        )

        if (
            len(selected_skills)
            != requirements["skill_bonus_count"]
        ):
            incomplete_values.append("initial skill bonuses")

        if len(selected_traits) != requirements["trait_count"]:
            incomplete_values.append("initial traits")

    if not characteristics_are_complete(
        person_values.get("characteristics")
    ):
        incomplete_values.append("characteristics")

    return tuple(incomplete_values)


def initial_values_are_complete(person):
    return not incomplete_initial_value_names(person)
