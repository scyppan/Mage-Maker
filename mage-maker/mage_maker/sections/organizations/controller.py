import hashlib
import uuid
from copy import deepcopy

from mage_maker.core.dates import historical_year_after
from mage_maker.core.wizarding_currency import (
    format_monthly_salary,
    monthly_salary_identity,
    normalize_monthly_salary,
)
from mage_maker.sections.development.event_eminence import (
    apply_event_eminence_updates,
    prepare_event_eminence_updates,
)
from mage_maker.sections.development.models import (
    job_assignment_active_on,
    job_assignment_overlaps_year_range,
    job_date_tuple,
    normalize_job_records,
)
from mage_maker.sections.locations.models import (
    ancestor_locations,
    location_path,
    location_paths_by_id,
    recent_location_label,
)
from mage_maker.sections.events.models import (
    normalize_association_values,
    normalize_world_event,
    normalize_world_event_date,
    world_event_year,
)
from mage_maker.sections.settings.simulation import (
    DATABASE_DATE_SETTING_KEY,
    normalize_database_date,
)


ORGANIZATION_TYPES = (
    "Governmental",
    "Non-profit",
    "Media",
    "School",
    "Shop",
)
ORGANIZATION_EVENT_FOUNDING = "founding"
SHOP_STOCK_CATEGORIES = (
    ("always_in_stock", "Always in stock"),
    ("regularly_in_stock", "Regularly in stock"),
    ("sometimes_in_stock", "Sometimes in stock"),
    ("rarely_in_stock", "Rarely in stock"),
)


def normalize_organization_event(value):
    if not isinstance(value, dict):
        raise TypeError("An organization event must be an object.")

    event_type = str(
        value.get("event_type", "") or ""
    ).strip().casefold()
    title = str(value.get("title", "") or "").strip()

    if event_type == ORGANIZATION_EVENT_FOUNDING:
        title = "Founding"
    elif not title:
        raise ValueError("An organization event must have a title.")

    year_value = value.get("year")

    if year_value in (None, ""):
        year = None
    else:
        if isinstance(year_value, bool):
            raise ValueError(
                "An organization event year must be a whole number."
            )

        try:
            year = int(year_value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "An organization event year must be a whole number."
            ) from error

        if not -99999 <= year <= 99999:
            raise ValueError(
                "An organization event year must be between -99999 and 99999."
            )

    description = str(
        value.get("description", "") or ""
    ).strip()
    person_ids = normalize_association_values(
        value.get("person_ids", [])
    )
    eminence_person_ids = [
        person_id
        for person_id in normalize_association_values(
            value.get("eminence_person_ids", [])
        )
        if person_id in person_ids
    ]
    record_id = str(
        value.get("record_id", "") or ""
    ).strip()

    if event_type == ORGANIZATION_EVENT_FOUNDING:
        record_id = "organization-founding"
    elif not record_id:
        identity_text = "|".join(
            (
                title.casefold(),
                str(year or ""),
                description.casefold(),
            )
        )
        record_id = "organization-event-" + hashlib.sha256(
            identity_text.encode("utf-8")
        ).hexdigest()[:20]

    return {
        "record_id": record_id,
        "event_type": event_type or "event",
        "title": title,
        "year": year,
        "description": description,
        "person_ids": person_ids,
        "eminence_person_ids": eminence_person_ids,
    }


def normalize_organization_events(value):
    if value in (None, ""):
        candidate_events = []
    elif isinstance(value, (list, tuple)):
        candidate_events = list(value)
    else:
        raise TypeError("Organization events must be a list.")

    founding_event = None
    other_events = []

    for candidate_event in candidate_events:
        normalized_event = normalize_organization_event(
            candidate_event
        )

        if (
            normalized_event["event_type"]
            == ORGANIZATION_EVENT_FOUNDING
        ):
            if founding_event is None:
                founding_event = normalized_event

            continue

        other_events.append(normalized_event)

    if founding_event is None:
        founding_event = normalize_organization_event(
            {
                "event_type": ORGANIZATION_EVENT_FOUNDING,
                "title": "Founding",
                "year": None,
                "description": "",
            }
        )

    return [founding_event, *other_events]


def new_organization_event(
    title,
    year,
    description="",
    person_ids=(),
    eminence_person_ids=(),
):
    return normalize_organization_event(
        {
            "record_id": str(uuid.uuid4()),
            "event_type": "event",
            "title": title,
            "year": year,
            "description": description,
            "person_ids": list(person_ids),
            "eminence_person_ids": list(
                eminence_person_ids
            ),
        }
    )


def organization_event_world_id(
    organization_id,
    organization_event_id,
):
    return (
        "organization-event:"
        f"{str(organization_id or '').strip()}:"
        f"{str(organization_event_id or '').strip()}"
    )


def organization_event_as_world_event(
    organization,
    organization_event,
):
    normalized_organization = normalize_organization_record(
        organization
    )
    normalized_event = normalize_organization_event(
        organization_event
    )
    organization_id = str(
        normalized_organization.get("record_id", "") or ""
    ).strip()
    location_id = normalized_organization["location_id"]
    location_ids = [location_id] if location_id else []
    return normalize_world_event(
        {
            "record_id": organization_event_world_id(
                organization_id,
                normalized_event["record_id"],
            ),
            "event_type": (
                "founding"
                if normalized_event["event_type"]
                == ORGANIZATION_EVENT_FOUNDING
                else "other"
            ),
            "title": normalized_event["title"],
            "date": str(normalized_event["year"]),
            "description": normalized_event["description"],
            "person_ids": normalized_event["person_ids"],
            "eminence_person_ids": normalized_event[
                "eminence_person_ids"
            ],
            "location_ids": location_ids,
            "locked_location_ids": location_ids,
            "organization_id": organization_id,
            "organization_name": normalized_organization["name"],
            "organization_event_id": normalized_event["record_id"],
            "organization_event": True,
        }
    )


def organization_event_from_world_event(
    world_event,
    existing_event,
):
    normalized_world_event = normalize_world_event(world_event)
    normalized_existing = normalize_organization_event(
        existing_event
    )
    return normalize_organization_event(
        {
            **normalized_existing,
            "title": normalized_world_event["title"],
            "year": world_event_year(
                normalized_world_event["date"]
            ),
            "description": normalized_world_event["description"],
            "person_ids": normalized_world_event["person_ids"],
            "eminence_person_ids": normalized_world_event[
                "eminence_person_ids"
            ],
        }
    )


def organization_events_as_world_events(organizations):
    world_events = []

    for organization in organizations or []:
        if not isinstance(organization, dict):
            continue

        for organization_event in normalize_organization_events(
            organization.get("events", [])
        ):
            world_events.append(
                organization_event_as_world_event(
                    organization,
                    organization_event,
                )
            )

    return world_events


def normalize_organization_job(value):
    if not isinstance(value, dict):
        raise TypeError("An organization job must be an object.")

    title = str(value.get("title", "") or "").strip()
    salary = normalize_monthly_salary(value.get("salary"))
    opened_year_value = value.get(
        "opened_year",
        value.get("start_year"),
    )

    if not title:
        raise ValueError("An organization job must have a title.")

    if isinstance(opened_year_value, bool):
        raise ValueError(
            "A job opening year must be a whole number."
        )

    try:
        opened_year = int(opened_year_value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "A job opening year must be a whole number."
        ) from error

    if not -99999 <= opened_year <= 99999:
        raise ValueError(
            "A job opening year must be between -99999 and 99999."
        )

    record_id = str(
        value.get("record_id", "") or ""
    ).strip()

    if not record_id:
        identity_text = "|".join(
            (
                str(
                    value.get("organization_id", "") or ""
                ).strip().casefold(),
                title.casefold(),
                str(monthly_salary_identity(salary)),
                str(opened_year),
            )
        )
        record_id = "organization-job-" + hashlib.sha256(
            identity_text.encode("utf-8")
        ).hexdigest()[:20]

    return {
        "record_id": record_id,
        "title": title,
        "salary": salary,
        "opened_year": opened_year,
    }


def normalize_organization_jobs(value):
    if value in (None, ""):
        candidate_jobs = []
    elif isinstance(value, (list, tuple)):
        candidate_jobs = list(value)
    else:
        raise TypeError("Organization jobs must be a list.")

    normalized_jobs = []
    seen_ids = set()

    for candidate_job in candidate_jobs:
        normalized_job = normalize_organization_job(
            candidate_job
        )

        if normalized_job["record_id"] in seen_ids:
            raise ValueError(
                "Organization job record IDs must be unique."
            )

        normalized_jobs.append(normalized_job)
        seen_ids.add(normalized_job["record_id"])

    return normalized_jobs


def new_organization_job(title, salary, opened_year):
    return normalize_organization_job(
        {
            "record_id": str(uuid.uuid4()),
            "title": title,
            "salary": salary,
            "opened_year": opened_year,
        }
    )


def normalize_shop_inventory(value):
    if value in (None, ""):
        candidate_inventory = {}
    elif isinstance(value, dict):
        candidate_inventory = value
    else:
        raise TypeError("Organization shop inventory must be an object.")

    normalized_inventory = {}

    for category_key, category_label in SHOP_STOCK_CATEGORIES:
        candidate_products = candidate_inventory.get(category_key, [])

        if candidate_products in (None, ""):
            candidate_products = []
        elif not isinstance(candidate_products, (list, tuple, set)):
            raise TypeError(
                f"{category_label} products must be stored as a list."
            )

        normalized_products = []

        for product_id in candidate_products:
            normalized_product_id = str(product_id or "").strip()

            if (
                normalized_product_id
                and normalized_product_id not in normalized_products
            ):
                normalized_products.append(normalized_product_id)

        normalized_inventory[category_key] = normalized_products

    return normalized_inventory


def normalize_organization_extinction_date(value, extinct):
    if not extinct:
        return ""

    extinction_date = str(value or "").strip()

    if not extinction_date:
        raise ValueError("Enter the date this organization became extinct.")

    try:
        return normalize_world_event_date(extinction_date)
    except ValueError as error:
        message = str(error).replace("Event", "Extinction").replace(
            "event",
            "extinction",
        )
        raise ValueError(message) from error


def normalize_organization_record(values):
    if not isinstance(values, dict):
        raise TypeError("An organization must be an object.")

    normalized = deepcopy(values)
    normalized["name"] = str(
        normalized.get("name", "") or ""
    ).strip()
    normalized["organization_type"] = str(
        normalized.get("organization_type", "") or ""
    ).strip()
    has_explicit_shop_flag = "has_shop" in normalized
    normalized["has_shop"] = (
        bool(normalized.get("has_shop"))
        if has_explicit_shop_flag
        else normalized["organization_type"] == "Shop"
    )
    normalized["shop_inventory"] = normalize_shop_inventory(
        normalized.get("shop_inventory", {})
    )
    normalized["extinct"] = bool(normalized.get("extinct", False))
    normalized["extinction_date"] = (
        normalize_organization_extinction_date(
            normalized.get("extinction_date", ""),
            normalized["extinct"],
        )
    )
    normalized["location_id"] = str(
        normalized.get("location_id", "") or ""
    ).strip()
    normalized["parent_organization_id"] = str(
        normalized.get("parent_organization_id", "") or ""
    ).strip()
    normalized["school_id"] = str(
        normalized.get("school_id", "") or ""
    ).strip()
    normalized["overview"] = str(
        normalized.get("overview", "") or ""
    ).strip()
    normalized["notes"] = str(
        normalized.get("notes", "") or ""
    ).strip()
    normalized["events"] = normalize_organization_events(
        normalized.get("events", [])
    )
    normalized["jobs"] = normalize_organization_jobs(
        [
            {
                **organization_job,
                "organization_id": str(
                    normalized.get("record_id", "") or ""
                ),
            }
            if isinstance(organization_job, dict)
            else organization_job
            for organization_job in normalized.get("jobs", []) or []
        ]
    )
    return normalized


def organization_path(record_id, organizations):
    organizations_by_id = {
        str(organization.get("record_id", "") or ""): organization
        for organization in organizations
        if isinstance(organization, dict)
        and str(organization.get("record_id", "") or "")
    }
    return organization_path_from_records(
        record_id,
        organizations_by_id,
    )


def organization_path_from_records(record_id, organizations_by_id):
    current_id = str(record_id or "").strip()
    path_names = []
    visited_ids = set()

    while current_id and current_id not in visited_ids:
        organization = organizations_by_id.get(current_id)

        if organization is None:
            break

        path_names.append(
            str(
                organization.get("name", "Unnamed")
                or "Unnamed"
            ).strip()
        )
        visited_ids.add(current_id)
        current_id = str(
            organization.get(
                "parent_organization_id",
                "",
            )
            or ""
        ).strip()

    path_names.reverse()
    return " / ".join(path_names)


def organization_paths_by_id(organizations):
    organizations_by_id = {
        str(organization.get("record_id", "") or ""): organization
        for organization in organizations
        if isinstance(organization, dict)
        and str(organization.get("record_id", "") or "")
    }
    return {
        record_id: organization_path_from_records(
            record_id,
            organizations_by_id,
        )
        for record_id in organizations_by_id
    }


def organizations_by_id(organizations):
    return {
        str(organization.get("record_id", "") or "").strip(): organization
        for organization in organizations or []
        if isinstance(organization, dict)
        and str(organization.get("record_id", "") or "").strip()
    }


def organization_root_ancestor(record_id, organizations):
    records = organizations_by_id(organizations)
    current_id = str(record_id or "").strip()
    root = records.get(current_id)
    visited_ids = set()

    while current_id and current_id not in visited_ids:
        visited_ids.add(current_id)
        current = records.get(current_id)

        if current is None:
            break

        root = current
        parent_id = str(
            current.get("parent_organization_id", "") or ""
        ).strip()

        if not parent_id or parent_id not in records:
            break

        current_id = parent_id

    return root


def organization_context_label(record_id, organizations):
    records = organizations_by_id(organizations)
    selected_id = str(record_id or "").strip()
    organization = records.get(selected_id)

    if organization is None:
        return "Unknown organization"

    name = str(
        organization.get("name", "") or "Unnamed organization"
    ).strip()
    parent_id = str(
        organization.get("parent_organization_id", "") or ""
    ).strip()

    if not parent_id or parent_id not in records:
        return name

    root = organization_root_ancestor(selected_id, organizations)
    root_name = str(
        (root or {}).get("name", "") or "Unnamed organization"
    ).strip()
    return f"{name} (within {root_name})"


def organization_ids_in_scope(organizations, scope_organization_id=""):
    records = organizations_by_id(organizations)
    scope_id = str(scope_organization_id or "").strip()

    if not scope_id:
        return set(records)

    if scope_id not in records:
        return set()

    scoped_ids = organization_descendant_ids(
        scope_id,
        organizations,
    )
    scoped_ids.add(scope_id)
    return scoped_ids


def organization_id_is_in_scope(
    organization_id,
    organizations,
    scope_organization_id="",
):
    selected_id = str(organization_id or "").strip()

    if not selected_id:
        return not str(scope_organization_id or "").strip()

    return selected_id in organization_ids_in_scope(
        organizations,
        scope_organization_id,
    )


def organization_descendant_ids(record_id, organizations):
    selected_id = str(record_id or "").strip()
    descendants = set()
    changed = True

    while changed:
        changed = False

        for organization in organizations:
            if not isinstance(organization, dict):
                continue

            organization_id = str(
                organization.get("record_id", "") or ""
            ).strip()
            parent_id = str(
                organization.get(
                    "parent_organization_id",
                    "",
                )
                or ""
            ).strip()

            if (
                organization_id
                and organization_id not in descendants
                and (
                    parent_id == selected_id
                    or parent_id in descendants
                )
            ):
                descendants.add(organization_id)
                changed = True

    return descendants


class OrganizationController:
    def __init__(
        self,
        database,
        locations_provider,
        schools_provider=None,
    ):
        self.database = database
        self.locations_provider = locations_provider
        self.schools_provider = schools_provider

    def list_organizations(self):
        organizations = [
            self.apply_school_link(organization)
            for organization in self.database.list_records("organizations")
        ]
        paths_by_id = organization_paths_by_id(organizations)
        decorated = [
            (
                self.organization_sort_key_for(
                    organization,
                    organizations,
                    paths_by_id,
                ),
                organization,
            )
            for organization in organizations
        ]
        decorated.sort(key=self.decorated_organization_sort_key)
        return [
            organization
            for sort_key, organization in decorated
        ]

    def decorated_organization_sort_key(self, decorated):
        return decorated[0]

    def organization_sort_key_for(
        self,
        organization,
        organizations,
        paths_by_id=None,
    ):
        organization_id = str(
            organization.get("record_id", "") or ""
        )
        return (
            (
                paths_by_id.get(organization_id, "")
                if paths_by_id is not None
                else organization_path(
                    organization_id,
                    organizations,
                )
            ).casefold(),
            str(
                organization.get("organization_type", "") or ""
            ).casefold(),
        )

    def organization_sort_key(self, organization):
        return self.organization_sort_key_for(
            organization,
            self.list_organizations(),
        )

    def get_organization(self, record_id):
        organization = self.database.read_record(
            "organizations",
            record_id,
        )

        if organization is None:
            return None

        return self.apply_school_link(organization)

    def create_organization(self, values):
        normalized = self.normalize_organization(values)

        if not str(normalized.get("record_id", "") or "").strip():
            normalized["record_id"] = str(uuid.uuid4())

        self.validate_organization(normalized)
        eminence_updates = prepare_event_eminence_updates(
            self.database,
            (),
            organization_events_as_world_events((normalized,)),
        )
        created = self.database.create_record("organizations", normalized)
        apply_event_eminence_updates(
            self.database,
            eminence_updates,
        )
        self.database.save()
        return created

    def create_default_organization(
        self,
        parent_organization_id="",
        location_id="",
    ):
        existing_names = {
            str(organization.get("name", "") or "").strip().casefold()
            for organization in self.list_organizations()
        }
        organization_name = "New Organization"
        suffix = 2

        while organization_name.casefold() in existing_names:
            organization_name = f"New Organization {suffix}"
            suffix += 1

        database_data = getattr(self.database, "data", {})
        application_settings = (
            database_data.get("_application_settings", {})
            if isinstance(database_data, dict)
            else {}
        )
        database_date = normalize_database_date(
            application_settings.get(DATABASE_DATE_SETTING_KEY)
            if isinstance(application_settings, dict)
            else None
        )
        selected_parent_id = str(
            parent_organization_id or ""
        ).strip()
        selected_location_id = str(location_id or "").strip()
        parent = self.get_organization(selected_parent_id)

        if parent is None:
            selected_parent_id = ""
        elif not selected_location_id:
            selected_location_id = str(
                parent.get("location_id", "") or ""
            ).strip()

        return self.create_organization(
            {
                "name": organization_name,
                "organization_type": ORGANIZATION_TYPES[0],
                "location_id": selected_location_id,
                "parent_organization_id": selected_parent_id,
                "school_id": "",
                "has_shop": False,
                "shop_inventory": normalize_shop_inventory({}),
                "extinct": False,
                "extinction_date": "",
                "overview": "",
                "notes": "",
                "events": [
                    {
                        "record_id": "organization-founding",
                        "event_type": ORGANIZATION_EVENT_FOUNDING,
                        "title": "Founding",
                        "year": database_date["year"],
                        "description": "",
                        "person_ids": [],
                    }
                ],
                "jobs": [],
            }
        )

    def update_organization(self, record_id, values):
        current = self.get_organization(record_id)

        if current is None:
            raise KeyError(f"Unknown organization record_id: {record_id}")

        prospective = deepcopy(current)
        prospective.update(deepcopy(values))
        normalized = self.normalize_organization(prospective)
        self.validate_organization(normalized, record_id)
        eminence_updates = prepare_event_eminence_updates(
            self.database,
            organization_events_as_world_events((current,)),
            organization_events_as_world_events((normalized,)),
        )
        updated = self.database.update_record(
            "organizations",
            record_id,
            normalized,
        )
        apply_event_eminence_updates(
            self.database,
            eminence_updates,
        )
        self.database.save()
        return updated

    def delete_organization(self, record_id):
        organization = self.get_organization(record_id)

        if organization is None:
            raise KeyError(
                f"Unknown organization record_id: {record_id}"
            )

        child_names = [
            str(child.get("name", "Unnamed") or "Unnamed")
            for child in self.list_organizations()
            if str(
                child.get("parent_organization_id", "") or ""
            )
            == str(record_id)
        ]

        if child_names:
            raise ValueError(
                "Move or delete nested organizations before deleting "
                f"this organization: {', '.join(child_names)}."
            )

        referenced_job_ids = {
            job["organization_job_id"]
            for job in self.job_assignments()
            if job["organization_id"] == str(record_id)
        }

        if referenced_job_ids:
            raise ValueError(
                "This organization cannot be deleted while people have "
                "job assignments in it."
            )

        eminence_updates = prepare_event_eminence_updates(
            self.database,
            organization_events_as_world_events((organization,)),
            (),
        )
        deleted = self.database.delete_record("organizations", record_id)
        apply_event_eminence_updates(
            self.database,
            eminence_updates,
        )
        self.database.save()
        return deleted

    def normalize_organization(self, values):
        return self.apply_school_link(
            normalize_organization_record(values)
        )

    def apply_school_link(self, organization):
        normalized = normalize_organization_record(organization)
        school = self.school_by_id(normalized.get("school_id"))

        if school is not None:
            normalized["name"] = str(
                school.get("name", "") or ""
            ).strip()
            normalized["organization_type"] = "School"

        return normalized

    def validate_organization(self, values, record_id=""):
        name = str(values.get("name", "") or "").strip()
        organization_type = str(
            values.get("organization_type", "") or ""
        ).strip()
        location_id = str(values.get("location_id", "") or "").strip()
        parent_organization_id = str(
            values.get("parent_organization_id", "") or ""
        ).strip()
        school_id = str(values.get("school_id", "") or "").strip()

        if not name:
            raise ValueError("An organization must have a name.")

        if organization_type not in ORGANIZATION_TYPES:
            raise ValueError("Choose one of the available organization types.")

        if school_id and self.school_by_id(school_id) is None:
            raise ValueError("The linked school no longer exists.")

        if school_id:
            school = self.school_by_id(school_id)
            school_name = str(
                (school or {}).get("name", "") or ""
            ).strip()

            if name != school_name or organization_type != "School":
                raise ValueError(
                    "A linked school controls the organization name and type."
                )

        if location_id and not any(
            location.get("record_id") == location_id
            for location in self.locations_provider()
        ):
            raise ValueError("The selected organization location no longer exists.")

        organizations = self.list_organizations()
        organization_ids = {
            str(organization.get("record_id", "") or "")
            for organization in organizations
        }

        if parent_organization_id:
            if parent_organization_id == str(record_id):
                raise ValueError(
                    "An organization cannot be nested within itself."
                )

            if parent_organization_id not in organization_ids:
                raise ValueError(
                    "The selected parent organization no longer exists."
                )

            if (
                record_id
                and parent_organization_id
                in organization_descendant_ids(
                    record_id,
                    organizations,
                )
            ):
                raise ValueError(
                    "An organization cannot be nested within one of "
                    "its own descendants."
                )

        events = normalize_organization_events(
            values.get("events", [])
        )

        if events[0]["year"] is None:
            raise ValueError(
                "Every organization must have a founding year."
            )

        for event in events[1:]:
            if event["year"] is None:
                raise ValueError(
                    "Every organization event must have a year."
                )

        known_person_ids = {
            str(person.get("record_id", "") or "").strip()
            for person in (
                self.database.list_people()
                if hasattr(self.database, "list_people")
                else []
            )
            if isinstance(person, dict)
            and str(person.get("record_id", "") or "").strip()
        }

        for event in events:
            if any(
                person_id not in known_person_ids
                for person_id in event.get("person_ids", [])
            ):
                raise ValueError(
                    "Every person linked to an organization event "
                    "must exist."
                )

        founding_year = int(events[0]["year"])
        extinction_year = world_event_year(
            values.get("extinction_date", "")
        )

        if (
            bool(values.get("extinct"))
            and extinction_year is not None
            and extinction_year < founding_year
        ):
            raise ValueError(
                "An organization cannot become extinct before it was founded."
            )

        organization_jobs = normalize_organization_jobs(
            values.get("jobs", [])
        )
        organization_jobs_by_id = {
            organization_job["record_id"]: organization_job
            for organization_job in organization_jobs
        }

        for organization_job in organization_jobs:
            if organization_job["opened_year"] < founding_year:
                raise ValueError(
                    f"{organization_job['title']} cannot open before "
                    "the organization was founded."
                )

        for assignment in self.job_assignments():
            if assignment["organization_id"] != str(record_id):
                continue

            organization_job = organization_jobs_by_id.get(
                assignment["organization_job_id"]
            )

            if organization_job is None:
                raise ValueError(
                    "An assigned organization job cannot be removed."
                )

            if (
                assignment["start_year"]
                < organization_job["opened_year"]
            ):
                raise ValueError(
                    f"{organization_job['title']} cannot be moved to "
                    "an opening year after an existing assignment began."
                )

        for organization in self.list_organizations():
            if organization.get("record_id") == record_id:
                continue

            if (
                school_id
                and str(organization.get("school_id", "") or "").strip()
                == school_id
            ):
                raise ValueError(
                    "That school is already linked to another organization."
                )

            if str(organization.get("name", "") or "").strip().casefold() == name.casefold():
                raise ValueError(f'An organization named "{name}" already exists.')

    def school_records(self):
        if self.schools_provider is None:
            return []

        schools = self.schools_provider()
        return [
            deepcopy(school)
            for school in schools or []
            if isinstance(school, dict)
            and str(school.get("record_id", "") or "").strip()
        ]

    def school_by_id(self, school_id):
        selected_id = str(school_id or "").strip()

        if not selected_id:
            return None

        return next(
            (
                school
                for school in self.school_records()
                if str(school.get("record_id", "") or "").strip()
                == selected_id
            ),
            None,
        )

    def school_label(self, school_id):
        school = self.school_by_id(school_id)

        if school is None:
            return "Choose a school"

        location = str(school.get("location", "") or "").strip()
        name = str(school.get("name", "") or "Unnamed school").strip()
        return f"{name} · {location}" if location else name

    def location_records(self):
        return [
            deepcopy(location)
            for location in self.locations_provider()
            if isinstance(location, dict)
        ]

    def location_options(self):
        locations = self.locations_provider()
        decorated = []

        for location in locations:
            record_id = str(location.get("record_id", "") or "")
            decorated.append(
                {
                    "record_id": record_id,
                    "label": recent_location_label(
                        record_id,
                        locations,
                    ),
                }
            )

        decorated.sort(key=self.location_option_sort_key)
        return decorated

    def location_option_sort_key(self, option):
        return str(option.get("label", "") or "").casefold()

    def location_label(self, location_id):
        selected_id = str(location_id or "").strip()

        if not selected_id:
            return "No location selected"

        return next(
            (
                option["label"]
                for option in self.location_options()
                if option["record_id"] == selected_id
            ),
            "Unknown location",
        )

    def organization_founding_year(self, organization):
        for event in organization.get("events", []) or []:
            if not isinstance(event, dict):
                continue

            if str(event.get("event_type", "") or "").casefold() != (
                ORGANIZATION_EVENT_FOUNDING
            ):
                continue

            try:
                return int(event.get("year"))
            except (TypeError, ValueError):
                return None

        return None

    def organization_extinction_year(self, organization):
        if not bool(organization.get("extinct")):
            return None

        return world_event_year(
            organization.get("extinction_date", "")
        )

    def organization_search_text(
        self,
        organization,
        organizations=None,
        paths_by_id=None,
    ):
        organization_id = str(
            organization.get("record_id", "") or ""
        ).strip()
        location_id = str(
            organization.get("location_id", "") or ""
        ).strip()
        searchable_values = [
            organization.get("name"),
            organization.get("organization_type"),
            organization.get("overview"),
            organization.get("notes"),
            (
                paths_by_id.get(organization_id, "")
                if paths_by_id is not None
                else organization_path(
                    organization_id,
                    (
                        organizations
                        if organizations is not None
                        else self.list_organizations()
                    ),
                )
            ),
            location_path(
                location_id,
                self.locations_provider(),
            ),
            self.location_label(location_id),
            self.school_label(organization.get("school_id"))
            if organization.get("school_id")
            else "",
            "Has a shop" if organization.get("has_shop") else "",
            "Extinct" if organization.get("extinct") else "Active",
            organization.get("extinction_date"),
        ]

        for event in organization.get("events", []) or []:
            if isinstance(event, dict):
                searchable_values.extend(
                    (
                        event.get("title"),
                        event.get("year"),
                        event.get("description"),
                    )
                )

        for job in organization.get("jobs", []) or []:
            if isinstance(job, dict):
                searchable_values.extend(
                    (
                        job.get("title"),
                        format_monthly_salary(job.get("salary")),
                        job.get("opened_year"),
                    )
                )

        return " ".join(
            str(value or "").strip()
            for value in searchable_values
            if str(value or "").strip()
        ).casefold()

    def organization_matches_location(
        self,
        organization,
        location_id,
    ):
        selected_id = str(location_id or "").strip()

        if not selected_id:
            return True

        organization_location_id = str(
            organization.get("location_id", "") or ""
        ).strip()

        if not organization_location_id:
            return False

        return any(
            str(location.get("record_id", "") or "").strip()
            == selected_id
            for location in ancestor_locations(
                organization_location_id,
                self.locations_provider(),
            )
        )

    def search_organizations(
        self,
        search_text="",
        organization_type="",
        existing_year=None,
        location_id="",
        school_link="all",
    ):
        query_terms = [
            term
            for term in str(search_text or "").casefold().split()
            if term
        ]
        selected_type = str(organization_type or "").strip()
        selected_school_link = str(
            school_link or "all"
        ).strip().casefold()
        matching = []

        organizations = self.list_organizations()
        paths_by_id = organization_paths_by_id(organizations)

        for organization in organizations:
            if (
                selected_type
                and selected_type != "All types"
                and organization.get("organization_type") != selected_type
            ):
                continue

            if existing_year is not None:
                founding_year = self.organization_founding_year(
                    organization
                )
                extinction_year = self.organization_extinction_year(
                    organization
                )

                if founding_year is None or founding_year > int(existing_year):
                    continue

                if (
                    extinction_year is not None
                    and extinction_year < int(existing_year)
                ):
                    continue

            if not self.organization_matches_location(
                organization,
                location_id,
            ):
                continue

            has_school = bool(
                str(organization.get("school_id", "") or "").strip()
            )

            if selected_school_link == "linked" and not has_school:
                continue

            if selected_school_link == "unlinked" and has_school:
                continue

            search_text_value = self.organization_search_text(
                organization,
                organizations,
                paths_by_id,
            )

            if not all(
                term in search_text_value
                for term in query_terms
            ):
                continue

            matching.append(organization)

        decorated = [
            (
                self.organization_sort_key_for(
                    organization,
                    organizations,
                    paths_by_id,
                ),
                organization,
            )
            for organization in matching
        ]
        decorated.sort(key=self.decorated_organization_sort_key)
        return [
            organization
            for sort_key, organization in decorated
        ]

    def first_order_children(self, record_id):
        selected_id = str(record_id or "").strip()
        organizations = self.list_organizations()
        children = [
            organization
            for organization in organizations
            if str(
                organization.get(
                    "parent_organization_id",
                    "",
                )
                or ""
            ).strip()
            == selected_id
        ]
        paths_by_id = organization_paths_by_id(organizations)
        decorated = [
            (
                self.organization_sort_key_for(
                    organization,
                    organizations,
                    paths_by_id,
                ),
                organization,
            )
            for organization in children
        ]
        decorated.sort(key=self.decorated_organization_sort_key)
        return [
            organization
            for sort_key, organization in decorated
        ]

    def parent_options(self, record_id=""):
        organizations = self.list_organizations()
        descendant_ids = (
            organization_descendant_ids(
                record_id,
                organizations,
            )
            if str(record_id or "").strip()
            else set()
        )
        excluded_ids = {
            str(record_id or "").strip(),
            *descendant_ids,
        }
        options = [
            {
                "record_id": "",
                "label": "No parent organization",
            }
        ]

        for organization in organizations:
            organization_id = str(
                organization.get("record_id", "") or ""
            )

            if organization_id in excluded_ids:
                continue

            options.append(
                {
                    "record_id": organization_id,
                    "label": organization_context_label(
                        organization_id,
                        organizations,
                    ),
                }
            )

        options[1:] = sorted(
            options[1:],
            key=self.location_option_sort_key,
        )
        return options

    def job_assignments(self):
        assignments = []

        for person in self.database.list_people():
            development_plan = person.get(
                "development_plan",
                {},
            )

            if not isinstance(development_plan, dict):
                continue

            for adult_year in development_plan.get(
                "adult_years",
                [],
            ):
                if not isinstance(adult_year, dict):
                    continue

                assignments.extend(
                    normalize_job_records(
                        adult_year.get("jobs", [])
                    )
                )

        return assignments

    def job_assignments_with_people(self, organization_job_id):
        selected_job_id = str(
            organization_job_id or ""
        ).strip()
        assignments = []
        seen_assignment_ids = set()

        for person in self.database.list_people():
            person_id = str(
                person.get("record_id", "") or ""
            ).strip()
            person_name = str(
                person.get("displayed_name", "")
                or "Unnamed magician"
            ).strip()
            development_plan = person.get(
                "development_plan",
                {},
            )

            if not isinstance(development_plan, dict):
                continue

            for adult_year in development_plan.get(
                "adult_years",
                [],
            ):
                if not isinstance(adult_year, dict):
                    continue

                for assignment in normalize_job_records(
                    adult_year.get("jobs", [])
                ):
                    assignment_id = str(
                        assignment.get("record_id", "") or ""
                    ).strip()

                    if (
                        assignment["organization_job_id"]
                        != selected_job_id
                        or assignment_id in seen_assignment_ids
                    ):
                        continue

                    assignments.append(
                        {
                            **assignment,
                            "person_id": person_id,
                            "person_name": person_name,
                        }
                    )
                    seen_assignment_ids.add(assignment_id)

        assignments.sort(
            key=self.job_assignment_person_sort_key
        )
        return assignments

    def job_assignment_person_sort_key(self, assignment):
        return (
            job_date_tuple(
                assignment["start_year"],
                assignment["start_month"],
                assignment["start_day"],
            ),
            assignment["person_name"].casefold(),
            assignment["record_id"],
        )

    def organization_job_yearly_timeline(self, organization_job):
        normalized_job = normalize_organization_job(
            organization_job
        )
        assignments = self.job_assignments_with_people(
            normalized_job["record_id"]
        )

        if not assignments:
            return []

        database_date = normalize_database_date(
            self.database.data.get(
                "_application_settings",
                {},
            ).get(DATABASE_DATE_SETTING_KEY)
        )
        first_year = min(
            assignment["start_year"]
            for assignment in assignments
        )
        last_year = first_year

        for assignment in assignments:
            assignment_last_year = (
                assignment["end_year"]
                if assignment["end_year"] is not None
                else max(
                    assignment["start_year"],
                    database_date["year"],
                )
            )
            last_year = max(last_year, assignment_last_year)

        timeline = []
        timeline_year = first_year

        while True:
            year_assignments = [
                assignment
                for assignment in assignments
                if job_assignment_overlaps_year_range(
                    assignment,
                    timeline_year,
                )
            ]
            holder_names = []
            person_ids = []

            for assignment in year_assignments:
                person_name = assignment["person_name"]
                person_id = assignment["person_id"]

                if person_name not in holder_names:
                    holder_names.append(person_name)

                if person_id and person_id not in person_ids:
                    person_ids.append(person_id)

            holder_text = (
                " → ".join(holder_names)
                if holder_names
                else "Vacant"
            )
            timeline.append(
                {
                    "year": timeline_year,
                    "person_ids": person_ids,
                    "holder_names": holder_names,
                    "label": f"{timeline_year}  ·  {holder_text}",
                }
            )

            if timeline_year == last_year:
                break

            timeline_year = historical_year_after(
                timeline_year
            )

        return timeline

    def organization_job_is_referenced(self, organization_job_id):
        selected_id = str(
            organization_job_id or ""
        ).strip()
        return any(
            assignment["organization_job_id"] == selected_id
            for assignment in self.job_assignments()
        )

    def organization_job_status(self, organization_job):
        database_date = normalize_database_date(
            self.database.data.get(
                "_application_settings",
                {},
            ).get(DATABASE_DATE_SETTING_KEY)
        )
        job_id = str(
            organization_job.get("record_id", "") or ""
        )
        opened_year = normalize_organization_job(
            organization_job
        )["opened_year"]

        if database_date["year"] < opened_year:
            return f"Opens {opened_year}"

        active_assignment = next(
            (
                assignment
                for assignment in self.job_assignments()
                if assignment["organization_job_id"] == job_id
                and job_assignment_active_on(
                    assignment,
                    database_date["year"],
                    database_date["month"],
                    database_date["day"],
                )
            ),
            None,
        )

        if active_assignment is None:
            return "Open"

        return "Filled"
