import random
from copy import deepcopy

from mage_maker.sections.development.characteristics import (
    CHARACTERISTIC_NAMES,
    available_characteristic_buys,
    characteristic_values_through_school_year,
    normalize_characteristic_name,
)
from mage_maker.sections.development.initial_bonuses import (
    STRATEGY_PREFERENCE_PROBABILITY,
    preferred_development_skills,
)
from mage_maker.sections.development.models import (
    ADULT_YEAR_MAX_BOOK_COUNT,
    DEVELOPMENT_ABILITY_BY_SKILL,
    DEVELOPMENT_ABILITY_OPTIONS,
    DEVELOPMENT_SKILL_OPTIONS,
    SCHOOL_YEAR_BOOK_COUNT,
    normalize_adult_year_record,
    normalize_adult_year_records,
    normalize_development_ability,
    normalize_development_plan,
    normalize_development_skill,
    normalize_school_year_book,
    normalize_school_year_record,
    normalize_school_year_records,
    school_year_book_identity,
)


def strategy_weighted_choice(options, preferred_options, randomizer=None):
    available_options = list(options)

    if not available_options:
        raise ValueError("At least one development option is required.")

    preferred = [
        option
        for option in preferred_options
        if option in available_options
    ]
    random_options = [
        option
        for option in available_options
        if option not in preferred
    ]
    selected_randomizer = randomizer or random
    use_preferred = (
        bool(preferred)
        and selected_randomizer.random()
        < STRATEGY_PREFERENCE_PROBABILITY
    )
    return selected_randomizer.choice(
        preferred
        if use_preferred
        else random_options or available_options
    )


def preferred_development_abilities(development_plan):
    plan = normalize_development_plan(
        development_plan,
        default_schema="Scattershot",
    )
    preferred_abilities = []

    if plan["schema"] == "Ability-focus":
        focused_ability = plan.get("focused_ability")

        if focused_ability:
            preferred_abilities.append(
                normalize_development_ability(focused_ability)
            )

    for skill in preferred_development_skills(plan):
        ability = DEVELOPMENT_ABILITY_BY_SKILL.get(skill)

        if ability and ability not in preferred_abilities:
            preferred_abilities.append(ability)

    return preferred_abilities


def random_school_year_ability(development_plan, randomizer=None):
    return strategy_weighted_choice(
        DEVELOPMENT_ABILITY_OPTIONS,
        preferred_development_abilities(development_plan),
        randomizer,
    )


def random_school_year_skill(development_plan, randomizer=None):
    return strategy_weighted_choice(
        DEVELOPMENT_SKILL_OPTIONS,
        preferred_development_skills(development_plan),
        randomizer,
    )


def random_annual_improvements(development_plan, randomizer=None):
    return {
        "ability": random_school_year_ability(
            development_plan,
            randomizer,
        ),
        "skills": [
            random_school_year_skill(
                development_plan,
                randomizer,
            ),
            random_school_year_skill(
                development_plan,
                randomizer,
            ),
        ],
    }


def random_characteristic_buy(
    characteristic_options,
    randomizer=None,
):
    available_options = [
        normalize_characteristic_name(option)
        for option in characteristic_options
    ]

    if not available_options:
        raise ValueError(
            "At least one characteristic must remain below five."
        )

    selected_randomizer = randomizer or random
    return selected_randomizer.choice(available_options)


def random_adult_year_record(
    adult_year,
    development_plan,
    randomizer=None,
    initial_characteristics=None,
    school_year_records=None,
    books=None,
    spells=None,
    proficiencies=None,
    excluded_book_identities=None,
):
    if initial_characteristics in (None, "", {}):
        reading_characteristic = ""
        reading_rolls = []
    else:
        characteristic_values = (
            characteristic_values_through_school_year(
                initial_characteristics,
                school_year_records or [],
            )
        )
        reading_characteristic = (
            "intellect"
            if characteristic_values["intellect"]
            >= characteristic_values["willpower"]
            else "willpower"
        )
        selected_randomizer = randomizer or random
        reading_rolls = [
            selected_randomizer.randint(1, 10)
            for _ in range(
                characteristic_values[reading_characteristic]
            )
        ]

    book_limit = min(
        ADULT_YEAR_MAX_BOOK_COUNT,
        max(0, sum(reading_rolls) - 20),
    )
    return normalize_adult_year_record(
        {
            "adult_year": int(adult_year),
            "reading_characteristic": reading_characteristic,
            "reading_rolls": reading_rolls,
            "books": select_school_year_books(
                development_plan,
                books or [],
                spells or [],
                proficiencies or [],
                randomizer,
                excluded_book_identities,
                target_count=book_limit,
            ),
            "eminence": [],
            "jobs": [],
        }
    )


def ensure_adult_year_records_with_improvements(
    records,
    target_year_count,
    development_plan,
    randomizer=None,
    initial_characteristics=None,
    school_year_records=None,
    books=None,
    spells=None,
    proficiencies=None,
    manage_reading=True,
):
    normalized_records = normalize_adult_year_records(records)
    records_by_year = {
        record["adult_year"]: record
        for record in normalized_records
        if record["adult_year"] <= int(target_year_count)
    }

    used_book_identities = set()

    for school_record in school_year_records or []:
        if not isinstance(school_record, dict):
            continue

        for field_name in ("assigned_books", "books"):
            for book in school_record.get(field_name, []) or []:
                used_book_identities.add(
                    school_year_book_identity(book)
                )

    for adult_year in range(1, int(target_year_count) + 1):
        existing_record = records_by_year.get(adult_year)

        if not manage_reading:
            records_by_year[adult_year] = normalize_adult_year_record(
                existing_record
                if existing_record is not None
                else {
                    "adult_year": adult_year,
                    "reading_characteristic": "",
                    "reading_rolls": [],
                    "books": [],
                    "eminence": [],
                    "jobs": [],
                }
            )
            continue

        if (
            existing_record is None
            or not existing_record.get("reading_rolls")
        ):
            generated_record = random_adult_year_record(
                adult_year,
                development_plan,
                randomizer,
                initial_characteristics,
                school_year_records,
                books,
                spells,
                proficiencies,
                used_book_identities,
            )

            if existing_record is not None:
                generated_record["eminence"] = deepcopy(
                    existing_record.get("eminence", [])
                )
                generated_record["jobs"] = deepcopy(
                    existing_record.get("jobs", [])
                )

            records_by_year[adult_year] = (
                normalize_adult_year_record(generated_record)
            )
        else:
            book_limit = int(
                existing_record.get("book_limit", 0) or 0
            )
            existing_record["books"] = select_school_year_books(
                development_plan,
                books or [],
                spells or [],
                proficiencies or [],
                randomizer,
                used_book_identities,
                existing_record.get("books", []),
                target_count=book_limit,
            )
            records_by_year[adult_year] = (
                normalize_adult_year_record(existing_record)
            )

        used_book_identities.update(
            school_year_book_identity(book)
            for book in records_by_year[adult_year].get(
                "books",
                [],
            )
        )

    return [
        records_by_year[adult_year]
        for adult_year in sorted(records_by_year)
    ]


def migrate_annual_progression_choices(
    development_plan,
    initial_characteristics,
    identity,
):
    plan = normalize_development_plan(
        development_plan,
        default_schema="Scattershot",
    )
    selected_randomizer = random.Random(str(identity or "mage"))
    migrated_school_records = []

    for record in plan.get("school_years", []):
        year_number = int(record["year"])
        characteristic_options = (
            available_characteristic_buys(
                initial_characteristics,
                migrated_school_records,
                year_number,
            )
            if initial_characteristics not in (None, "", {})
            else CHARACTERISTIC_NAMES
        )
        characteristic = normalize_characteristic_name(
            record.get("characteristic"),
            allow_blank=True,
        )

        if characteristic not in characteristic_options:
            record["characteristic"] = random_characteristic_buy(
                characteristic_options,
                selected_randomizer,
            )

        migrated_school_records.append(
            normalize_school_year_record(record)
        )

    plan["school_years"] = migrated_school_records
    plan["adult_years"] = normalize_adult_year_records(
        plan.get("adult_years", [])
    )
    return normalize_development_plan(plan)


def indexed_skill_records(records):
    records_by_id = {}
    records_by_name = {}

    for record in records or []:
        if not isinstance(record, dict):
            continue

        record_id = str(
            record.get("record_id", "") or ""
        ).strip()
        record_name = str(
            record.get("name", "") or ""
        ).strip()

        if record_id:
            records_by_id[record_id] = record

        if record_name:
            records_by_name[record_name.casefold()] = record

    return records_by_id, records_by_name


def linked_record(reference, records_by_id, records_by_name):
    if isinstance(reference, dict):
        record_id = str(
            reference.get("record_id", "") or ""
        ).strip()
        record_name = str(
            reference.get("name", "") or ""
        ).strip()
        return (
            records_by_id.get(record_id)
            or records_by_name.get(record_name.casefold())
            or reference
        )

    reference_text = str(reference or "").strip()
    return (
        records_by_id.get(reference_text)
        or records_by_name.get(reference_text.casefold())
    )


def normalized_skill_from_record(record):
    if not isinstance(record, dict):
        return None

    try:
        return normalize_development_skill(record.get("skill"))
    except ValueError:
        return None


def book_linked_skill_sets(book, spells=None, proficiencies=None):
    spell_records_by_id, spell_records_by_name = (
        indexed_skill_records(spells)
    )
    proficiency_records_by_id, proficiency_records_by_name = (
        indexed_skill_records(proficiencies)
    )
    return book_linked_skill_sets_from_indexes(
        book,
        spell_records_by_id,
        spell_records_by_name,
        proficiency_records_by_id,
        proficiency_records_by_name,
    )


def book_linked_skill_sets_from_indexes(
    book,
    spell_records_by_id,
    spell_records_by_name,
    proficiency_records_by_id,
    proficiency_records_by_name,
):
    if not isinstance(book, dict):
        return set(), set()

    explicitly_linked_skills = set()

    for spell_reference in book.get("spells", []) or []:
        spell = linked_record(
            spell_reference,
            spell_records_by_id,
            spell_records_by_name,
        )
        skill = normalized_skill_from_record(spell)

        if skill:
            explicitly_linked_skills.add(skill)

    for proficiency_reference in (
        book.get("proficiencies", []) or []
    ):
        proficiency = linked_record(
            proficiency_reference,
            proficiency_records_by_id,
            proficiency_records_by_name,
        )
        skill = normalized_skill_from_record(proficiency)

        if skill:
            explicitly_linked_skills.add(skill)

    category_skills = set()

    for category in book.get("categories", []) or []:
        try:
            category_skills.add(
                normalize_development_skill(category)
            )
        except ValueError:
            continue

    return explicitly_linked_skills, category_skills


def normalized_book_candidates(books):
    candidates = []
    seen_identities = set()

    for book in books or []:
        if not isinstance(book, dict):
            continue

        try:
            book_reference = normalize_school_year_book(book)
        except (TypeError, ValueError):
            continue

        identity = school_year_book_identity(book_reference)

        if identity in seen_identities:
            continue

        candidates.append(
            {
                "source": deepcopy(book),
                "reference": book_reference,
                "identity": identity,
            }
        )
        seen_identities.add(identity)

    return candidates


def assigned_school_books_by_year(
    school_name,
    schools,
    books=None,
):
    normalized_school_name = str(school_name or "").strip().casefold()

    if not normalized_school_name:
        return {}

    selected_school = next(
        (
            school
            for school in schools or []
            if isinstance(school, dict)
            and str(school.get("name", "") or "")
            .strip()
            .casefold()
            == normalized_school_name
        ),
        None,
    )

    if selected_school is None:
        return {}

    books_by_id, books_by_name = indexed_skill_records(books)
    assigned_by_year = {}
    seen_by_year = {}

    for course_book in selected_school.get("course_books", []) or []:
        if not isinstance(course_book, dict):
            continue

        try:
            year_number = int(course_book.get("year"))
        except (TypeError, ValueError):
            continue

        if not 1 <= year_number <= 7:
            continue

        resolved_book = linked_record(
            course_book,
            books_by_id,
            books_by_name,
        )

        try:
            book_reference = normalize_school_year_book(
                resolved_book or course_book
            )
        except (TypeError, ValueError):
            continue

        identity = school_year_book_identity(book_reference)
        year_identities = seen_by_year.setdefault(
            year_number,
            set(),
        )

        if identity in year_identities:
            continue

        assigned_by_year.setdefault(year_number, []).append(
            book_reference
        )
        year_identities.add(identity)

    return assigned_by_year


def select_school_year_books(
    development_plan,
    books,
    spells=None,
    proficiencies=None,
    randomizer=None,
    excluded_book_identities=None,
    initial_books=None,
    target_count=SCHOOL_YEAR_BOOK_COUNT,
):
    try:
        selected_target_count = max(0, int(target_count))
    except (TypeError, ValueError) as error:
        raise ValueError(
            "The number of books to select must be a whole number."
        ) from error

    if selected_target_count == 0:
        return []

    excluded_identities = set(excluded_book_identities or ())
    normalized_initial_books = []
    normalized_initial_identities = set()

    for initial_book in initial_books or []:
        try:
            normalized_initial_book = normalize_school_year_book(
                initial_book
            )
        except (TypeError, ValueError):
            continue

        identity = school_year_book_identity(
            normalized_initial_book
        )

        if (
            identity in excluded_identities
            or identity in normalized_initial_identities
        ):
            continue

        normalized_initial_books.append(normalized_initial_book)
        normalized_initial_identities.add(identity)

        if len(normalized_initial_books) >= selected_target_count:
            break

    candidates = [
        candidate
        for candidate in normalized_book_candidates(books)
        if candidate["identity"] not in excluded_identities
    ]

    if not candidates:
        return normalized_initial_books

    selected_randomizer = randomizer or random
    preferred_skills = set(
        preferred_development_skills(development_plan)
    )
    spell_records_by_id, spell_records_by_name = (
        indexed_skill_records(spells)
    )
    proficiency_records_by_id, proficiency_records_by_name = (
        indexed_skill_records(proficiencies)
    )
    skill_sets_by_identity = {}

    for candidate in candidates:
        skill_sets_by_identity[candidate["identity"]] = (
            book_linked_skill_sets_from_indexes(
                candidate["source"],
                spell_records_by_id,
                spell_records_by_name,
                proficiency_records_by_id,
                proficiency_records_by_name,
            )
        )

    candidates_by_identity = {
        candidate["identity"]: candidate
        for candidate in candidates
    }
    selected_books = []
    selected_identities = set()

    for normalized_initial_book in normalized_initial_books:
        identity = school_year_book_identity(
            normalized_initial_book
        )

        if (
            identity in selected_identities
            or identity not in candidates_by_identity
        ):
            continue

        selected_books.append(
            deepcopy(
                candidates_by_identity[identity]["reference"]
            )
        )
        selected_identities.add(identity)

        if len(selected_books) >= selected_target_count:
            break

    while (
        len(selected_books) < selected_target_count
        and len(selected_identities) < len(candidates)
    ):
        remaining_candidates = [
            candidate
            for candidate in candidates
            if candidate["identity"] not in selected_identities
        ]
        explicit_matches = [
            candidate
            for candidate in remaining_candidates
            if (
                skill_sets_by_identity[candidate["identity"]][0]
                & preferred_skills
            )
        ]
        category_matches = [
            candidate
            for candidate in remaining_candidates
            if (
                candidate not in explicit_matches
                and (
                    skill_sets_by_identity[
                        candidate["identity"]
                    ][1]
                    & preferred_skills
                )
            )
        ]
        preferred_matches = explicit_matches or category_matches
        all_matching_identities = {
            candidate["identity"]
            for candidate in explicit_matches + category_matches
        }
        deviation_matches = [
            candidate
            for candidate in remaining_candidates
            if candidate["identity"] not in all_matching_identities
        ]
        use_preferred = (
            bool(preferred_matches)
            and selected_randomizer.random()
            < STRATEGY_PREFERENCE_PROBABILITY
        )
        selection_pool = (
            preferred_matches
            if use_preferred
            else deviation_matches or remaining_candidates
        )
        selected_candidate = selected_randomizer.choice(
            selection_pool
        )
        selected_books.append(
            deepcopy(selected_candidate["reference"])
        )
        selected_identities.add(selected_candidate["identity"])

    return selected_books


def random_school_year_record(
    year_number,
    development_plan,
    books=None,
    spells=None,
    proficiencies=None,
    randomizer=None,
    school_name="",
    assigned_books=None,
    excluded_book_identities=None,
    characteristic_options=None,
):
    improvements = random_annual_improvements(
        development_plan,
        randomizer,
    )
    record = {
        "year": int(year_number),
        "school": str(school_name or "").strip(),
        "skipped": False,
        "ability": improvements["ability"],
        "skills": improvements["skills"],
        "characteristic": random_characteristic_buy(
            characteristic_options or CHARACTERISTIC_NAMES,
            randomizer,
        ),
        "assigned_books": deepcopy(assigned_books or []),
        "books": select_school_year_books(
            development_plan,
            books or [],
            spells or [],
            proficiencies or [],
            randomizer,
            excluded_book_identities,
        ),
        "eminence": [],
    }
    return normalize_school_year_record(record)


def ensure_school_year_records(
    records,
    target_year_count,
    development_plan,
    books=None,
    spells=None,
    proficiencies=None,
    randomizer=None,
    school_name="",
    assigned_books_by_year=None,
    initial_characteristics=None,
    manage_books=True,
):
    normalized_records = normalize_school_year_records(records)
    records_by_year = {
        record["year"]: record
        for record in normalized_records
        if record["year"] <= int(target_year_count)
    }

    selected_school_name = str(school_name or "").strip()
    assignments = (
        assigned_books_by_year
        if manage_books and isinstance(assigned_books_by_year, dict)
        else {}
    )
    assigned_identities = set()
    intentional_identities = set()

    for year_number in range(1, int(target_year_count) + 1):
        existing_record = records_by_year.get(year_number)
        earlier_records = [
            records_by_year[earlier_year]
            for earlier_year in sorted(records_by_year)
            if earlier_year < year_number
        ]
        characteristic_options = (
            available_characteristic_buys(
                initial_characteristics,
                earlier_records,
                year_number,
            )
            if initial_characteristics not in (None, "", {})
            else CHARACTERISTIC_NAMES
        )

        if existing_record is None:
            assigned_books = deepcopy(
                assignments.get(year_number, [])
            )

            for assigned_book in assigned_books:
                assigned_identities.add(
                    school_year_book_identity(assigned_book)
                )

            records_by_year[year_number] = random_school_year_record(
                year_number,
                development_plan,
                books if manage_books else [],
                spells,
                proficiencies,
                randomizer,
                selected_school_name,
                assigned_books,
                assigned_identities | intentional_identities,
                characteristic_options,
            )
            intentional_identities.update(
                school_year_book_identity(book)
                for book in records_by_year[year_number].get(
                    "books",
                    [],
                )
            )
            continue

        record_school = str(
            existing_record.get("school", "") or ""
        ).strip()
        existing_characteristic = normalize_characteristic_name(
            existing_record.get("characteristic"),
            allow_blank=True,
        )

        if existing_characteristic not in characteristic_options:
            existing_record["characteristic"] = (
                random_characteristic_buy(
                    characteristic_options,
                    randomizer,
                )
            )

        if bool(existing_record.get("skipped", False)):
            existing_record["school"] = selected_school_name

            if manage_books:
                for assigned_book in assignments.get(
                    year_number,
                    [],
                ):
                    assigned_identities.add(
                        school_year_book_identity(assigned_book)
                    )

                existing_record["assigned_books"] = []
                existing_record["books"] = select_school_year_books(
                    development_plan,
                    books or [],
                    spells or [],
                    proficiencies or [],
                    randomizer,
                    assigned_identities | intentional_identities,
                    existing_record.get("books", []),
                )

            records_by_year[year_number] = (
                normalize_school_year_record(existing_record)
            )
            intentional_identities.update(
                school_year_book_identity(book)
                for book in records_by_year[year_number].get(
                    "books",
                    [],
                )
            )
            continue

        if (
            not record_school
            or record_school.casefold()
            == selected_school_name.casefold()
        ):
            existing_record["school"] = selected_school_name

            if manage_books:
                existing_record["assigned_books"] = deepcopy(
                    assignments.get(year_number, [])
                )

        if manage_books:
            for assigned_book in existing_record.get(
                "assigned_books",
                [],
            ):
                assigned_identities.add(
                    school_year_book_identity(assigned_book)
                )

            existing_record["books"] = select_school_year_books(
                development_plan,
                books or [],
                spells or [],
                proficiencies or [],
                randomizer,
                assigned_identities | intentional_identities,
                existing_record.get("books", []),
            )

        records_by_year[year_number] = normalize_school_year_record(
            existing_record
        )
        intentional_identities.update(
            school_year_book_identity(book)
            for book in records_by_year[year_number].get(
                "books",
                [],
            )
        )

    return [
        records_by_year[year_number]
        for year_number in sorted(records_by_year)
    ]
