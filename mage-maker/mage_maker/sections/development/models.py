import hashlib
import random
from copy import deepcopy


DEVELOPMENT_SCHEMA_OPTIONS = (
    "One skill",
    "Two skill",
    "Three skills",
    "Ability-focus",
    "Material Crafting",
    "Ingredient Crafting",
    "Spell-crafting",
    "Social",
    "Scattershot",
)

DEVELOPMENT_SKILL_OPTIONS = (
    "Alchemy",
    "Ancient Runes",
    "Arithmancy",
    "Artificing",
    "Astronomy",
    "Charms",
    "Dark Arts",
    "Defense",
    "Divination",
    "Flying",
    "Herbology",
    "History",
    "Magical Creatures",
    "Muggles",
    "Perception",
    "Potions",
    "Social skills",
    "Transfiguration",
)

DEVELOPMENT_ABILITY_OPTIONS = (
    "Power",
    "Erudition",
    "Panache",
    "Naturalism",
)

DEVELOPMENT_SKILLS_BY_ABILITY = {
    "Power": (
        "Charms",
        "Transfiguration",
        "Defense",
        "Dark Arts",
    ),
    "Erudition": (
        "Arithmancy",
        "Ancient Runes",
        "History",
        "Muggles",
    ),
    "Panache": (
        "Potions",
        "Alchemy",
        "Artificing",
        "Flying",
        "Herbology",
    ),
    "Naturalism": (
        "Magical Creatures",
        "Astronomy",
        "Divination",
        "Perception",
        "Social skills",
    ),
}

DEVELOPMENT_ABILITY_BY_SKILL = {
    skill: ability
    for ability, skills in DEVELOPMENT_SKILLS_BY_ABILITY.items()
    for skill in skills
}

DEVELOPMENT_ASSIGNMENT_RANDOM = "random"
DEVELOPMENT_ASSIGNMENT_PROMPT = "prompt"
DEVELOPMENT_ASSIGNMENT_SCATTERSHOT = "scattershot"
DEVELOPMENT_ASSIGNMENT_DEFAULT = DEVELOPMENT_ASSIGNMENT_RANDOM
DEVELOPMENT_ASSIGNMENT_SETTING_KEY = "development_strategy_assignment"
DEVELOPMENT_ASSIGNMENT_OPTIONS = (
    (
        DEVELOPMENT_ASSIGNMENT_RANDOM,
        "Always randomly assign development strategy",
    ),
    (
        DEVELOPMENT_ASSIGNMENT_PROMPT,
        "Always prompt to pick",
    ),
    (
        DEVELOPMENT_ASSIGNMENT_SCATTERSHOT,
        "Always pick Scattershot",
    ),
)
ACADEMIC_YEARS_TO_ADULTHOOD = 7


def normalize_development_schema(value):
    normalized_value = " ".join(
        str(value or "").strip().casefold().replace("_", " ").split()
    )
    aliases = {
        "one skill": "One skill",
        "one-skill": "One skill",
        "two skill": "Two skill",
        "two skills": "Two skill",
        "two-skill": "Two skill",
        "three skill": "Three skills",
        "three skills": "Three skills",
        "three-skill": "Three skills",
        "ability focus": "Ability-focus",
        "ability-focus": "Ability-focus",
        "ability focused": "Ability-focus",
        "crafting": "Material Crafting",
        "material crafting": "Material Crafting",
        "material-crafting": "Material Crafting",
        "ingredient crafting": "Ingredient Crafting",
        "ingredient-crafting": "Ingredient Crafting",
        "spell crafting": "Spell-crafting",
        "spell-crafting": "Spell-crafting",
        "social": "Social",
        "scattershot": "Scattershot",
    }
    schema = aliases.get(normalized_value)

    if schema is None:
        valid_values = ", ".join(DEVELOPMENT_SCHEMA_OPTIONS)
        raise ValueError(
            f"Development strategy must be one of: {valid_values}."
        )

    return schema


def development_skill_count(schema):
    normalized_schema = normalize_development_schema(schema)
    counts = {
        "One skill": 1,
        "Two skill": 2,
        "Three skills": 3,
    }
    return counts.get(normalized_schema, 0)


def normalize_development_skill(value):
    normalized_value = " ".join(
        str(value or "").strip().casefold().replace("_", " ").split()
    )
    aliases = {
        skill.casefold(): skill
        for skill in DEVELOPMENT_SKILL_OPTIONS
    }
    aliases.update(
        {
            "care of magical creatures": "Magical Creatures",
            "creatures": "Magical Creatures",
            "darkarts": "Dark Arts",
            "history of magic": "History",
            "muggle studies": "Muggles",
            "runes": "Ancient Runes",
            "social": "Social skills",
            "social skill": "Social skills",
            "social skills": "Social skills",
        }
    )
    skill = aliases.get(normalized_value)

    if skill is None:
        valid_values = ", ".join(DEVELOPMENT_SKILL_OPTIONS)
        raise ValueError(
            f"Development skill must be one of: {valid_values}."
        )

    return skill


def normalize_development_ability(value):
    normalized_value = " ".join(
        str(value or "").strip().casefold().replace("_", " ").split()
    )
    abilities = {
        ability.casefold(): ability
        for ability in DEVELOPMENT_ABILITY_OPTIONS
    }
    ability = abilities.get(normalized_value)

    if ability is None:
        valid_values = ", ".join(DEVELOPMENT_ABILITY_OPTIONS)
        raise ValueError(
            f"Development ability must be one of: {valid_values}."
        )

    return ability


def normalize_focused_skills(value, required_count):
    if value in (None, ""):
        candidate_values = []
    elif isinstance(value, str):
        candidate_values = [value]
    elif isinstance(value, (list, tuple)):
        candidate_values = list(value)
    else:
        raise TypeError("Focused skills must be a list.")

    focused_skills = []

    for candidate_value in candidate_values:
        skill = normalize_development_skill(candidate_value)

        if skill not in focused_skills:
            focused_skills.append(skill)

    for skill in DEVELOPMENT_SKILL_OPTIONS:
        if len(focused_skills) >= required_count:
            break

        if skill not in focused_skills:
            focused_skills.append(skill)

    return focused_skills[:required_count]


def normalize_academic_years_advanced(value):
    if value in (None, ""):
        return 0

    if isinstance(value, bool):
        raise ValueError(
            "Academic years advanced must be a whole number."
        )

    try:
        years_advanced = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Academic years advanced must be a whole number."
        ) from error

    if years_advanced < 0:
        raise ValueError(
            "Academic years advanced cannot be negative."
        )

    return min(years_advanced, ACADEMIC_YEARS_TO_ADULTHOOD)


def normalize_school_started(value, years_advanced=0):
    normalized_years = normalize_academic_years_advanced(
        years_advanced
    )

    if normalized_years > 0:
        return True

    if value in (None, ""):
        return False

    if isinstance(value, bool):
        return value

    normalized_value = str(value).strip().casefold()

    if normalized_value in ("yes", "true", "1", "started"):
        return True

    if normalized_value in (
        "no",
        "false",
        "0",
        "not started",
    ):
        return False

    raise ValueError("School started must be Yes or No.")


def school_progress_text(school_started, years_advanced):
    normalized_years = normalize_academic_years_advanced(
        years_advanced
    )
    normalized_started = normalize_school_started(
        school_started,
        normalized_years,
    )

    if not normalized_started:
        return "Not yet started school"

    if normalized_years >= ACADEMIC_YEARS_TO_ADULTHOOD:
        return "Graduated"

    return f"Year {normalized_years + 1}"


def visible_school_year_count(school_started, years_advanced):
    normalized_years = normalize_academic_years_advanced(
        years_advanced
    )
    normalized_started = normalize_school_started(
        school_started,
        normalized_years,
    )

    if not normalized_started:
        return 0

    if normalized_years >= ACADEMIC_YEARS_TO_ADULTHOOD:
        return ACADEMIC_YEARS_TO_ADULTHOOD

    return normalized_years + 1


def normalize_development_plan(value, default_schema=None):
    if isinstance(value, str):
        plan = {"schema": value}
    elif isinstance(value, dict):
        plan = deepcopy(value)
    elif value in (None, ""):
        plan = {}
    else:
        raise TypeError("A development plan must be an object.")

    schema_value = plan.get("schema", default_schema)

    if schema_value in (None, ""):
        raise ValueError(
            "Every magician must have a development strategy."
        )

    schema = normalize_development_schema(schema_value)
    plan["schema"] = schema
    plan["academic_years_advanced"] = normalize_academic_years_advanced(
        plan.get("academic_years_advanced", 0)
    )
    plan["school_started"] = normalize_school_started(
        plan.get("school_started"),
        plan["academic_years_advanced"],
    )
    plan.pop("age", None)

    required_skill_count = development_skill_count(schema)

    if required_skill_count:
        focused_skill_values = plan.get("focused_skills")

        if focused_skill_values in (None, ""):
            focused_skill_values = plan.get(
                "skills",
                plan.get(
                    "preferred_skills",
                    plan.get(
                        "preferred_skill",
                        plan.get("skill"),
                    ),
                ),
            )

        plan["focused_skills"] = normalize_focused_skills(
            focused_skill_values,
            required_skill_count,
        )
        plan.pop("focused_ability", None)
    elif schema == "Ability-focus":
        focused_ability = plan.get(
            "focused_ability",
            plan.get(
                "ability",
                plan.get("preferred_ability"),
            ),
        )

        if focused_ability in (None, ""):
            focused_ability = DEVELOPMENT_ABILITY_OPTIONS[0]

        plan["focused_ability"] = normalize_development_ability(
            focused_ability
        )
        plan.pop("focused_skills", None)
    else:
        plan.pop("focused_skills", None)
        plan.pop("focused_ability", None)

    for legacy_field in (
        "ability",
        "preferred_ability",
        "preferred_skill",
        "preferred_skills",
        "skill",
        "skills",
    ):
        plan.pop(legacy_field, None)

    return plan


def normalize_development_assignment_policy(value):
    normalized_value = " ".join(
        str(value or "").strip().casefold().replace("_", " ").split()
    )
    aliases = {
        "": DEVELOPMENT_ASSIGNMENT_DEFAULT,
        "random": DEVELOPMENT_ASSIGNMENT_RANDOM,
        "always randomly assign development strategy": (
            DEVELOPMENT_ASSIGNMENT_RANDOM
        ),
        "prompt": DEVELOPMENT_ASSIGNMENT_PROMPT,
        "always prompt to pick": DEVELOPMENT_ASSIGNMENT_PROMPT,
        "scattershot": DEVELOPMENT_ASSIGNMENT_SCATTERSHOT,
        "always pick scattershot": DEVELOPMENT_ASSIGNMENT_SCATTERSHOT,
    }
    policy = aliases.get(normalized_value)

    if policy is None:
        return DEVELOPMENT_ASSIGNMENT_DEFAULT

    return policy


def random_development_schema(current_schema=None):
    normalized_current = None

    if current_schema not in (None, ""):
        normalized_current = normalize_development_schema(current_schema)

    choices = [
        schema
        for schema in DEVELOPMENT_SCHEMA_OPTIONS
        if schema != normalized_current
    ]

    if not choices:
        choices = list(DEVELOPMENT_SCHEMA_OPTIONS)

    return random.choice(choices)


def randomized_development_plan(
    current_schema=None,
    years_advanced=0,
    selected_schema=None,
    school_started=None,
):
    schema = (
        normalize_development_schema(selected_schema)
        if selected_schema not in (None, "")
        else random_development_schema(current_schema)
    )
    plan = {
        "schema": schema,
        "academic_years_advanced": normalize_academic_years_advanced(
            years_advanced
        ),
        "school_started": normalize_school_started(
            school_started,
            years_advanced,
        ),
    }
    required_skill_count = development_skill_count(schema)

    if required_skill_count:
        plan["focused_skills"] = random.sample(
            list(DEVELOPMENT_SKILL_OPTIONS),
            required_skill_count,
        )
    elif schema == "Ability-focus":
        plan["focused_ability"] = random.choice(
            DEVELOPMENT_ABILITY_OPTIONS
        )

    return normalize_development_plan(plan)


def new_development_plan(assignment_policy, selected_schema=None):
    if selected_schema not in (None, ""):
        return randomized_development_plan(
            years_advanced=0,
            selected_schema=selected_schema,
        )

    policy = normalize_development_assignment_policy(
        assignment_policy
    )

    if policy == DEVELOPMENT_ASSIGNMENT_RANDOM:
        return randomized_development_plan()
    elif policy == DEVELOPMENT_ASSIGNMENT_SCATTERSHOT:
        schema = "Scattershot"
    else:
        raise ValueError(
            "Choose a development strategy before creating this magician."
        )

    return normalize_development_plan(
        {
            "schema": schema,
            "academic_years_advanced": 0,
            "school_started": False,
        }
    )


def migrated_development_plan(value, assignment_policy, record_id):
    stored_plan = (
        deepcopy(value)
        if isinstance(value, dict)
        else {"schema": value}
        if isinstance(value, str)
        else {}
    )
    supplied_skill_focus = any(
        stored_plan.get(field_name) not in (None, "", [])
        for field_name in (
            "focused_skills",
            "skills",
            "preferred_skills",
            "preferred_skill",
            "skill",
        )
    )
    supplied_ability_focus = any(
        stored_plan.get(field_name) not in (None, "")
        for field_name in (
            "focused_ability",
            "ability",
            "preferred_ability",
        )
    )
    identity = str(record_id or "unidentified-magician").encode(
        "utf-8"
    )
    digest = hashlib.sha256(identity).hexdigest()

    if value not in (None, ""):
        plan = normalize_development_plan(value)
    else:
        policy = normalize_development_assignment_policy(
            assignment_policy
        )

        if policy == DEVELOPMENT_ASSIGNMENT_RANDOM:
            schema_index = int(digest, 16) % len(
                DEVELOPMENT_SCHEMA_OPTIONS
            )
            schema = DEVELOPMENT_SCHEMA_OPTIONS[schema_index]
        else:
            schema = "Scattershot"

        plan = normalize_development_plan(
            {
                "schema": schema,
                "academic_years_advanced": 0,
                "school_started": False,
            }
        )

    schema = plan["schema"]
    required_skill_count = development_skill_count(schema)

    if required_skill_count and not supplied_skill_focus:
        starting_index = int(digest[:8], 16) % len(
            DEVELOPMENT_SKILL_OPTIONS
        )
        rotated_skills = (
            DEVELOPMENT_SKILL_OPTIONS[starting_index:]
            + DEVELOPMENT_SKILL_OPTIONS[:starting_index]
        )
        plan["focused_skills"] = list(
            rotated_skills[:required_skill_count]
        )
    elif schema == "Ability-focus" and not supplied_ability_focus:
        ability_index = int(digest[:8], 16) % len(
            DEVELOPMENT_ABILITY_OPTIONS
        )
        plan["focused_ability"] = DEVELOPMENT_ABILITY_OPTIONS[
            ability_index
        ]

    return plan


def calculate_school_start_year(birth_year, birth_month=None, birth_day=None):
    if birth_year in (None, ""):
        return None

    if isinstance(birth_year, bool):
        return None

    try:
        normalized_year = int(birth_year)
    except (TypeError, ValueError):
        return None

    normalized_month = None
    normalized_day = None

    if birth_month not in (None, ""):
        try:
            normalized_month = int(birth_month)
        except (TypeError, ValueError):
            return None

    if birth_day not in (None, ""):
        try:
            normalized_day = int(birth_day)
        except (TypeError, ValueError):
            return None

    after_cutoff = (
        normalized_month is not None
        and (
            normalized_month > 9
            or (
                normalized_month == 9
                and normalized_day is not None
                and normalized_day > 1
            )
        )
    )
    return normalized_year + (12 if after_cutoff else 11)
