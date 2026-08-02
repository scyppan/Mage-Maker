from copy import deepcopy

from mage_maker.sections.development.models import (
    ensure_adult_year_records,
    job_assignment_active_on,
    job_date_tuple,
    new_job_record,
    normalize_development_plan,
    normalize_job_record,
    normalize_job_records,
    require_job_position_available,
)
from mage_maker.sections.development.event_eminence import (
    apply_event_eminence_updates,
    prepare_event_eminence_updates,
    suggested_event_eminence_skill,
)
from mage_maker.sections.events.models import (
    normalize_world_event,
    normalize_world_events,
    split_world_event_date,
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
    location_foundation_event_state,
    recent_location_label,
)
from mage_maker.sections.organizations.controller import (
    ORGANIZATION_EVENT_FOUNDING,
    normalize_organization_jobs,
    normalize_organization_events,
    normalize_organization_record,
    organization_context_label,
    organization_event_as_world_event,
    organization_event_from_world_event,
    organization_events_as_world_events,
)
from mage_maker.sections.settings.mage_groups import (
    mage_group_definition,
    normalize_mage_groups,
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
        people_creator=None,
        mage_groups_provider=None,
    ):
        self.database = database
        self.people_provider = people_provider
        self.location_provider = location_provider
        self.period_provider = period_provider
        self.location_creator = location_creator
        self.people_creator = people_creator
        self.mage_groups_provider = mage_groups_provider

    def list_events(self):
        titled_events = [
            self.apply_title_rules(event)
            for event in self.database.list_records("events")
        ]
        organization_events = organization_events_as_world_events(
            self.database.list_records("organizations")
        )
        eligible_person_ids = self.eminence_eligible_person_ids()
        return [
            self.with_eligible_eminence(
                event,
                eligible_person_ids,
            )
            for event in normalize_world_events(
                [*titled_events, *organization_events]
            )
        ]

    def get_event(self, record_id):
        event = self.database.read_record("events", record_id)

        if event is not None:
            return self.with_eligible_eminence(
                normalize_world_event(
                    self.apply_title_rules(event)
                )
            )

        selected_id = str(record_id or "").strip()
        selected_event = next(
            (
                event
                for event in organization_events_as_world_events(
                    self.database.list_records("organizations")
                )
                if event["record_id"] == selected_id
            ),
            None,
        )

        return (
            self.with_eligible_eminence(selected_event)
            if selected_event is not None
            else None
        )

    def create_event(self, values):
        prepared = normalize_world_event(
            self.apply_event_rules(values)
        )
        normalized = self.with_eligible_eminence(
            normalize_world_event(
                self.apply_event_rules(prepared)
            )
        )
        self.validate_associations(normalized)

        if normalized["event_type"] == "organization_founding":
            return self.create_organization_founding_event(normalized)

        eminence_updates = prepare_event_eminence_updates(
            self.database,
            (),
            (normalized,),
        )
        created = self.database.create_record("events", normalized)
        self.synchronize_started_job_assignments((), (created,))
        apply_event_eminence_updates(
            self.database,
            eminence_updates,
        )
        self.remember_associations(created)
        self.database.save()
        return normalize_world_event(created)

    def create_organization_founding_event(self, values):
        organization = self.database.read_record(
            "organizations",
            values["organization_id"],
        )

        if organization is None:
            raise KeyError("The selected organization no longer exists.")

        founding_event = normalize_organization_events(
            organization.get("events", [])
        )[0]
        current = organization_event_as_world_event(
            organization,
            founding_event,
        )
        prepared = deepcopy(values)
        prepared["record_id"] = current["record_id"]
        prepared["organization_event"] = True
        prepared["organization_event_id"] = founding_event["record_id"]
        return self.update_organization_event(current, prepared)

    def update_event(self, record_id, values):
        current = self.get_event(record_id)

        if current is None:
            raise KeyError(f"Unknown event record_id: {record_id}")

        prospective = deepcopy(current)
        prospective.update(deepcopy(values))
        prospective["record_id"] = record_id
        normalized = self.with_eligible_eminence(
            normalize_world_event(
                self.apply_event_rules(prospective, current)
            )
        )
        self.validate_associations(normalized, current)

        if current.get("organization_event"):
            return self.update_organization_event(
                current,
                normalized,
            )

        eminence_updates = prepare_event_eminence_updates(
            self.database,
            (current,),
            (normalized,),
        )
        updated = self.database.update_record(
            "events",
            record_id,
            normalized,
        )
        self.synchronize_started_job_assignments(
            (current,),
            (updated,),
        )
        apply_event_eminence_updates(
            self.database,
            eminence_updates,
        )
        self.remember_associations(updated)
        self.database.save()
        return normalize_world_event(updated)

    def delete_event(self, record_id):
        current = self.get_event(record_id)

        if current is None:
            raise KeyError(f"Unknown event record_id: {record_id}")

        if current.get("organization_event"):
            return self.delete_organization_event(current)

        eminence_updates = prepare_event_eminence_updates(
            self.database,
            (current,),
            (),
        )
        deleted = self.database.delete_record("events", record_id)
        self.synchronize_started_job_assignments((current,), ())
        apply_event_eminence_updates(
            self.database,
            eminence_updates,
        )
        self.database.save()
        return normalize_world_event(deleted)

    def update_organization_event(self, current, values):
        organization_id = str(
            current.get("organization_id", "") or ""
        ).strip()
        organization_event_id = str(
            current.get("organization_event_id", "") or ""
        ).strip()
        organization = self.database.read_record(
            "organizations",
            organization_id,
        )

        if organization is None:
            raise KeyError(
                f"Unknown organization record_id: {organization_id}"
            )

        events = normalize_organization_events(
            organization.get("events", [])
        )
        existing_event = next(
            (
                event
                for event in events
                if event["record_id"] == organization_event_id
            ),
            None,
        )

        if existing_event is None:
            raise KeyError(
                "The organization event no longer exists."
            )

        updated_event = organization_event_from_world_event(
            values,
            existing_event,
        )
        updated_world_event = organization_event_as_world_event(
            organization,
            updated_event,
        )
        eminence_updates = prepare_event_eminence_updates(
            self.database,
            (current,),
            (updated_world_event,),
        )
        organization["events"] = normalize_organization_events(
            [
                (
                    updated_event
                    if event["record_id"] == organization_event_id
                    else event
                )
                for event in events
            ]
        )
        updated_organization = self.database.update_record(
            "organizations",
            organization_id,
            organization,
        )
        apply_event_eminence_updates(
            self.database,
            eminence_updates,
        )
        self.remember_associations(values)
        self.database.save()
        return organization_event_as_world_event(
            updated_organization,
            updated_event,
        )

    def delete_organization_event(self, current):
        organization_id = str(
            current.get("organization_id", "") or ""
        ).strip()
        organization_event_id = str(
            current.get("organization_event_id", "") or ""
        ).strip()
        organization = self.database.read_record(
            "organizations",
            organization_id,
        )

        if organization is None:
            raise KeyError(
                f"Unknown organization record_id: {organization_id}"
            )

        events = normalize_organization_events(
            organization.get("events", [])
        )
        selected_event = next(
            (
                event
                for event in events
                if event["record_id"] == organization_event_id
            ),
            None,
        )

        if selected_event is None:
            raise KeyError(
                "The organization event no longer exists."
            )

        if (
            selected_event["event_type"]
            == ORGANIZATION_EVENT_FOUNDING
        ):
            raise ValueError(
                "An organization's founding event cannot be deleted."
            )

        eminence_updates = prepare_event_eminence_updates(
            self.database,
            (current,),
            (),
        )
        organization["events"] = normalize_organization_events(
            [
                event
                for event in events
                if event["record_id"] != organization_event_id
            ]
        )
        self.database.update_record(
            "organizations",
            organization_id,
            organization,
        )
        apply_event_eminence_updates(
            self.database,
            eminence_updates,
        )
        self.database.save()
        return normalize_world_event(current)

    def apply_title_rules(self, event):
        titled_event = deepcopy(event) if isinstance(event, dict) else {}
        event_type = canonical_event_type(
            titled_event.get("event_type")
        )

        if event_type == "organization_founding":
            organization_id = str(
                titled_event.get("organization_id", "") or ""
            ).strip()
            organization = self.database.read_record(
                "organizations",
                organization_id,
            )
            organization_name = str(
                (organization or {}).get("name", "")
                or titled_event.get("organization_name", "")
                or ""
            ).strip()

            if organization_name:
                titled_event["organization_name"] = organization_name
                titled_event["title"] = (
                    f"Founding of {organization_name}"
                )

            titled_event["location_ids"] = []
            titled_event["locked_location_ids"] = []
            return titled_event

        if event_type != "founding":
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

    def apply_event_rules(self, event, current_event=None):
        prepared = self.apply_title_rules(event)
        event_type = canonical_event_type(
            prepared.get("event_type")
        )

        if event_type not in ("started_job", "received_raise"):
            return prepared

        organization_job = self.job_event_organization_job(prepared)

        if organization_job is None:
            return prepared

        organization = organization_job["organization"]
        job = organization_job["job"]
        prepared["organization_id"] = str(
            organization.get("record_id", "") or ""
        )
        prepared["organization_name"] = str(
            organization.get("name", "") or ""
        ).strip()
        prepared["organization_job_id"] = job["record_id"]
        prepared["job_title"] = job["title"]

        if not str(prepared.get("title", "") or "").strip():
            prepared["title"] = (
                f"{job['title']} at {prepared['organization_name']}"
            )

        if event_type == "started_job":
            record_id = str(
                prepared.get("record_id", "")
                or (current_event or {}).get("record_id", "")
                or ""
            ).strip()
            existing_assignment = self.matching_started_job_assignment(
                prepared,
            )
            prepared["job_assignment_id"] = (
                existing_assignment["record_id"]
                if existing_assignment is not None
                else self.started_job_assignment_id(record_id)
            )
        else:
            active_assignment = self.active_assignment_for_job_event(
                prepared
            )
            prepared["job_assignment_id"] = (
                active_assignment["record_id"]
                if active_assignment is not None
                else ""
            )

        return prepared

    def organization_job_options(self):
        options = []

        for organization in self.database.list_records("organizations"):
            if not isinstance(organization, dict):
                continue

            organization_id = str(
                organization.get("record_id", "") or ""
            ).strip()
            organization_name = str(
                organization.get("name", "") or "Unnamed organization"
            ).strip()

            for job in normalize_organization_jobs(
                organization.get("jobs", [])
            ):
                options.append(
                    {
                        "value": job["record_id"],
                        "label": f"{organization_name} — {job['title']}",
                        "event_title": (
                            f"{job['title']} at {organization_name}"
                        ),
                        "organization_id": organization_id,
                        "organization_name": organization_name,
                        "organization_job_id": job["record_id"],
                        "job_title": job["title"],
                        "job": deepcopy(job),
                        "organization": deepcopy(organization),
                    }
                )

        options.sort(key=self.association_option_sort_key)
        return options

    def job_event_organization_job(self, event):
        organization_id = str(
            (event or {}).get("organization_id", "") or ""
        ).strip()
        organization_job_id = str(
            (event or {}).get("organization_job_id", "") or ""
        ).strip()

        for option in self.organization_job_options():
            if (
                option["organization_id"] == organization_id
                and option["organization_job_id"]
                == organization_job_id
            ):
                return option

        return None

    def all_job_assignments(self):
        assignments = []

        for person in self.people_provider():
            if not isinstance(person, dict):
                continue

            development_plan = person.get("development_plan")

            if not isinstance(development_plan, dict):
                continue

            for adult_year in development_plan.get("adult_years", []):
                if not isinstance(adult_year, dict):
                    continue

                assignments.extend(
                    normalize_job_records(
                        adult_year.get("jobs", [])
                    )
                )

        return normalize_job_records(assignments)

    def person_job_assignments(self, person_id):
        selected_person_id = str(person_id or "").strip()
        person = next(
            (
                candidate
                for candidate in self.people_provider()
                if isinstance(candidate, dict)
                and str(candidate.get("record_id", "") or "").strip()
                == selected_person_id
            ),
            None,
        )

        if person is None:
            return []

        assignments = []
        plan = person.get("development_plan")

        if not isinstance(plan, dict):
            return []

        for adult_year in plan.get("adult_years", []):
            if isinstance(adult_year, dict):
                assignments.extend(
                    normalize_job_records(
                        adult_year.get("jobs", [])
                    )
                )

        return normalize_job_records(assignments)

    def started_job_assignment_id(self, event_id):
        normalized_event_id = str(event_id or "").strip()

        if not normalized_event_id:
            return ""

        return f"event-job:{normalized_event_id}"

    def matching_started_job_assignment(self, event):
        person_ids = list((event or {}).get("person_ids", []) or [])

        if len(person_ids) != 1:
            return None

        year, month, day = split_world_event_date(
            (event or {}).get("date", "")
        )

        if not year:
            return None

        requested_start = job_date_tuple(year, month, day)

        for assignment in self.person_job_assignments(person_ids[0]):
            if (
                assignment["organization_id"]
                != str((event or {}).get("organization_id", "") or "")
                or assignment["organization_job_id"]
                != str(
                    (event or {}).get("organization_job_id", "") or ""
                )
            ):
                continue

            assignment_start = job_date_tuple(
                assignment["start_year"],
                assignment["start_month"],
                assignment["start_day"],
            )

            if assignment_start == requested_start:
                return assignment

        return None

    def active_assignment_for_job_event(self, event):
        person_ids = list((event or {}).get("person_ids", []) or [])

        if len(person_ids) != 1:
            return None

        year, month, day = split_world_event_date(
            (event or {}).get("date", "")
        )

        if not year:
            return None

        selected_job_id = str(
            (event or {}).get("organization_job_id", "") or ""
        ).strip()

        for assignment in self.person_job_assignments(person_ids[0]):
            if (
                assignment["organization_job_id"] == selected_job_id
                and job_assignment_active_on(
                    assignment,
                    year,
                    month or 1,
                    day or 1,
                )
            ):
                return assignment

        return None

    def started_job_assignment(self, event):
        normalized_event = normalize_world_event(event)
        year, month, day = split_world_event_date(
            normalized_event["date"]
        )
        end_year, end_month, end_day = split_world_event_date(
            normalized_event.get("job_end_date", "")
        )
        assignment = new_job_record(
            normalized_event["organization_id"],
            normalized_event["organization_name"],
            normalized_event["job_title"],
            normalized_event["salary"],
            year,
            month,
            day,
            end_year or None,
            end_month or None,
            end_day or None,
            normalized_event["organization_job_id"],
        )
        assignment["record_id"] = (
            normalized_event.get("job_assignment_id")
            or self.started_job_assignment_id(
                normalized_event["record_id"]
            )
        )
        return normalize_job_record(assignment)

    def synchronize_started_job_assignments(
        self,
        previous_events,
        updated_events,
    ):
        previous_started = [
            normalize_world_event(event)
            for event in previous_events or ()
            if canonical_event_type(
                (event or {}).get("event_type")
            )
            == "started_job"
        ]
        updated_started = [
            normalize_world_event(event)
            for event in updated_events or ()
            if canonical_event_type(
                (event or {}).get("event_type")
            )
            == "started_job"
        ]
        affected_person_ids = {
            person_id
            for event in (*previous_started, *updated_started)
            for person_id in event.get("person_ids", [])
        }

        for person_id in affected_person_ids:
            person = self.database.read_person(person_id)

            if person is None:
                continue

            plan = normalize_development_plan(
                person.get("development_plan"),
                default_schema="Scattershot",
            )
            adult_years = ensure_adult_year_records(
                plan.get("adult_years", []),
                1,
            )
            removed_assignment_ids = {
                str(event.get("job_assignment_id", "") or "")
                or self.started_job_assignment_id(
                    event.get("record_id", "")
                )
                for event in previous_started
                if person_id in event.get("person_ids", [])
            }

            for adult_year in adult_years:
                adult_year["jobs"] = [
                    assignment
                    for assignment in normalize_job_records(
                        adult_year.get("jobs", [])
                    )
                    if assignment["record_id"]
                    not in removed_assignment_ids
                ]

            for event in updated_started:
                if person_id not in event.get("person_ids", []):
                    continue

                assignment = self.started_job_assignment(event)

                for adult_year in adult_years:
                    adult_year["jobs"] = [
                        stored_assignment
                        for stored_assignment in normalize_job_records(
                            adult_year.get("jobs", [])
                        )
                        if stored_assignment["record_id"]
                        != assignment["record_id"]
                    ]

                adult_years[0]["jobs"] = normalize_job_records(
                    [*adult_years[0].get("jobs", []), assignment]
                )

            plan["adult_years"] = adult_years
            self.database.update_person(
                person_id,
                {"development_plan": plan},
            )

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
        groups = self.mage_groups()
        options = [
            {
                "value": str(person.get("record_id", "") or ""),
                "label": str(
                    person.get("displayed_name", "") or "Unnamed magician"
                ).strip(),
                "person": deepcopy(person),
                "group_name": mage_group_definition(
                    person.get("mage_group_id"),
                    groups,
                )["name"],
            }
            for person in self.people_provider()
            if str(person.get("record_id", "") or "").strip()
        ]
        options.sort(key=self.association_option_sort_key)
        return options

    def person_can_earn_eminence(self, person_id):
        selected_person_id = str(person_id or "").strip()

        return selected_person_id in self.eminence_eligible_person_ids()

    def eminence_eligible_person_ids(self):
        return {
            str(person.get("record_id", "") or "").strip()
            for person in self.people_provider()
            if isinstance(person, dict)
            and str(person.get("record_id", "") or "").strip()
            and not bool(person.get("non_magical"))
        }

    def with_eligible_eminence(
        self,
        event,
        eligible_person_ids=None,
    ):
        normalized = normalize_world_event(event)
        eligible_ids = (
            self.eminence_eligible_person_ids()
            if eligible_person_ids is None
            else set(eligible_person_ids)
        )
        awarded_person_ids = [
            person_id
            for person_id in normalized.get(
                "eminence_person_ids",
                [],
            )
            if person_id in eligible_ids
        ]
        normalized["eminence_person_ids"] = awarded_person_ids
        normalized["eminence_skills"] = {
            person_id: skill
            for person_id, skill in normalized.get(
                "eminence_skills",
                {},
            ).items()
            if person_id in awarded_person_ids
        }
        return normalized

    def suggest_event_eminence_skill(
        self,
        person_id,
        event_identity="",
    ):
        selected_person_id = str(person_id or "").strip()
        person = next(
            (
                candidate
                for candidate in self.people_provider()
                if isinstance(candidate, dict)
                and str(candidate.get("record_id", "") or "").strip()
                == selected_person_id
            ),
            {},
        )
        return suggested_event_eminence_skill(
            person.get("development_plan"),
            selected_person_id,
            event_identity,
        )

    def mage_groups(self):
        if self.mage_groups_provider is not None:
            return normalize_mage_groups(
                self.mage_groups_provider()
            )

        settings = self.database.data.get(
            "_application_settings",
            {},
        )
        stored_groups = (
            settings.get("mage_groups")
            if isinstance(settings, dict)
            else None
        )
        return normalize_mage_groups(stored_groups)

    def create_event_person(self, values):
        if self.people_creator is None:
            raise ValueError("The people collection is unavailable.")

        return deepcopy(self.people_creator(values))

    def location_options(
        self,
        available_for_founding=False,
        include_ids=(),
    ):
        locations = self.location_records(
            available_for_founding=available_for_founding,
            include_ids=include_ids,
        )
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

    def location_records(
        self,
        available_for_founding=False,
        include_ids=(),
    ):
        locations = [
            deepcopy(location)
            for location in self.location_provider()
            if isinstance(location, dict)
        ]

        if not available_for_founding:
            return locations

        included_ids = {
            str(location_id or "").strip()
            for location_id in include_ids or ()
            if str(location_id or "").strip()
        }
        world_events = self.database.list_records("events")
        return [
            location
            for location in locations
            if (
                str(location.get("record_id", "") or "")
                in included_ids
                or not location_foundation_event_state(
                    location,
                    world_events,
                ).get(
                    "foundation_event_id"
                )
            )
        ]

    def location_has_foundation_event(
        self,
        location_id,
        ignored_event_id="",
    ):
        selected_id = str(location_id or "").strip()
        ignored_id = str(ignored_event_id or "").strip()
        location = next(
            (
                candidate
                for candidate in self.location_provider()
                if str(candidate.get("record_id", "") or "").strip()
                == selected_id
            ),
            None,
        )

        if location is None:
            return False

        world_events = [
            event
            for event in (
                self.database.list_records("events")
                if self.database is not None
                else []
            )
            if str(event.get("record_id", "") or "").strip()
            != ignored_id
        ]
        state = location_foundation_event_state(
            location,
            world_events,
        )
        return bool(state.get("foundation_event_id"))

    def organization_records(self):
        return [
            normalize_organization_record(organization)
            for organization in self.database.list_records(
                "organizations"
            )
            if isinstance(organization, dict)
        ]

    def organization_options(self):
        organizations = self.organization_records()
        options = [
            {
                "value": str(
                    organization.get("record_id", "") or ""
                ).strip(),
                "label": organization_context_label(
                    organization.get("record_id", ""),
                    organizations,
                ),
            }
            for organization in organizations
            if str(
                organization.get("record_id", "") or ""
            ).strip()
        ]
        options.sort(key=self.association_option_sort_key)
        return options

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

    def validate_associations(self, event, current_event=None):
        self.validate_job_event(event, current_event)

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

        if event.get("event_type") == "founding":
            founding_location_id = event["location_ids"][0]
            ignored_event_id = (
                str(current_event.get("record_id", "") or "")
                if isinstance(current_event, dict)
                else ""
            )

            if self.location_has_foundation_event(
                founding_location_id,
                ignored_event_id,
            ):
                raise ValueError(
                    "The selected location already has a founding event."
                )

        if (
            event.get("event_type") == "organization_founding"
            and not str(event.get("organization_id", "") or "").strip()
        ):
            raise ValueError(
                "Select exactly one organization for its founding event."
            )

        if (
            event.get("event_type") == "organization_founding"
            and event.get("location_ids", [])
        ):
            raise ValueError(
                "Organization founding events do not use locations."
            )

        if (
            event.get("event_type") == "began_friendship"
            and len(event.get("person_ids", [])) < 2
        ):
            raise ValueError(
                "A friendship event needs at least two people."
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
        known_organization_ids = {
            str(organization.get("record_id", "") or "")
            for organization in (
                self.database.list_records("organizations")
                if self.database is not None
                else []
            )
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

        if (
            event.get("event_type") == "organization_founding"
            and event.get("organization_id")
            not in known_organization_ids
        ):
            raise ValueError(
                "The selected organization no longer exists."
            )

    def validate_job_event(self, event, current_event=None):
        event_type = canonical_event_type(
            (event or {}).get("event_type")
        )

        if event_type not in ("started_job", "received_raise"):
            return

        person_ids = list((event or {}).get("person_ids", []) or [])

        if len(person_ids) != 1:
            raise ValueError(
                "A job event must belong to exactly one person."
            )

        if self.job_event_organization_job(event) is None:
            raise ValueError("Choose an existing organization job.")

        if (event or {}).get("salary") is None:
            raise ValueError("Enter the monthly salary for this job event.")

        if event_type == "received_raise":
            if self.active_assignment_for_job_event(event) is None:
                raise ValueError(
                    "The selected person is not holding this job on the "
                    "event date."
                )

            return

        assignment = self.started_job_assignment(event)
        selected_job = self.job_event_organization_job(event)["job"]
        ignored_assignment_id = str(
            (event or {}).get("job_assignment_id", "") or ""
        ).strip()

        if not ignored_assignment_id and current_event is not None:
            ignored_assignment_id = str(
                current_event.get("job_assignment_id", "") or ""
            ).strip()

        require_job_position_available(
            selected_job,
            assignment,
            self.all_job_assignments(),
            ignored_assignment_id,
        )


WorldEventController = EventController
