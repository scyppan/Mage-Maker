from copy import deepcopy

from mage_maker.sections.locations.models import location_path


ORGANIZATION_TYPES = (
    "Governmental",
    "Non-profit",
    "Media",
    "School",
    "Shop",
)


class OrganizationController:
    def __init__(self, database, locations_provider):
        self.database = database
        self.locations_provider = locations_provider

    def list_organizations(self):
        organizations = self.database.list_records("organizations")
        organizations.sort(key=self.organization_sort_key)
        return organizations

    def organization_sort_key(self, organization):
        return (
            str(organization.get("name", "") or "").casefold(),
            str(organization.get("organization_type", "") or "").casefold(),
        )

    def get_organization(self, record_id):
        return self.database.read_record("organizations", record_id)

    def create_organization(self, values):
        normalized = self.normalize_organization(values)
        self.validate_organization(normalized)
        created = self.database.create_record("organizations", normalized)
        self.database.save()
        return created

    def update_organization(self, record_id, values):
        current = self.get_organization(record_id)

        if current is None:
            raise KeyError(f"Unknown organization record_id: {record_id}")

        prospective = deepcopy(current)
        prospective.update(deepcopy(values))
        normalized = self.normalize_organization(prospective)
        self.validate_organization(normalized, record_id)
        updated = self.database.update_record(
            "organizations",
            record_id,
            normalized,
        )
        self.database.save()
        return updated

    def delete_organization(self, record_id):
        deleted = self.database.delete_record("organizations", record_id)
        self.database.save()
        return deleted

    def normalize_organization(self, values):
        if not isinstance(values, dict):
            raise TypeError("An organization must be an object.")

        normalized = deepcopy(values)
        normalized["name"] = str(normalized.get("name", "") or "").strip()
        normalized["organization_type"] = str(
            normalized.get("organization_type", "") or ""
        ).strip()
        normalized["location_id"] = str(
            normalized.get("location_id", "") or ""
        ).strip()
        normalized["overview"] = str(
            normalized.get("overview", "") or ""
        ).strip()
        normalized["notes"] = str(normalized.get("notes", "") or "").strip()
        return normalized

    def validate_organization(self, values, record_id=""):
        name = str(values.get("name", "") or "").strip()
        organization_type = str(
            values.get("organization_type", "") or ""
        ).strip()
        location_id = str(values.get("location_id", "") or "").strip()

        if not name:
            raise ValueError("An organization must have a name.")

        if organization_type not in ORGANIZATION_TYPES:
            raise ValueError("Choose one of the available organization types.")

        if location_id and not any(
            location.get("record_id") == location_id
            for location in self.locations_provider()
        ):
            raise ValueError("The selected organization location no longer exists.")

        for organization in self.list_organizations():
            if organization.get("record_id") == record_id:
                continue

            if str(organization.get("name", "") or "").strip().casefold() == name.casefold():
                raise ValueError(f'An organization named "{name}" already exists.')

    def location_options(self):
        locations = self.locations_provider()
        decorated = []

        for location in locations:
            record_id = str(location.get("record_id", "") or "")
            decorated.append(
                {
                    "record_id": record_id,
                    "label": location_path(record_id, locations),
                }
            )

        decorated.sort(key=self.location_option_sort_key)
        return decorated

    def location_option_sort_key(self, option):
        return str(option.get("label", "") or "").casefold()
