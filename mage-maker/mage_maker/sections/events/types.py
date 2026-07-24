EVENT_TYPE_DEFINITIONS = (
    ("starting_location", "Starting location", ("person",), True),
    ("born", "Born", ("person",), True),
    ("birth_name", "Birth name", ("person",), True),
    ("gave_birth", "Gave birth", ("person",), False),
    ("had_child", "Had a child", ("person",), False),
    ("got_married", "Got married", ("person",), False),
    ("died", "Died", ("person",), False),
    ("started_school", "Started at school", ("person",), False),
    ("opened_business", "Opened a business", ("person",), False),
    ("got_job", "Got a job", ("person",), False),
    ("relocated", "Relocated", ("person",), False),
    ("name_change", "Name change", ("person",), False),
    ("custom", "Custom event", ("person",), False),
    ("founding", "Founding", ("location",), False),
    ("political", "Political", ("location",), False),
    ("conflict", "Conflict", ("location",), False),
    ("discovery", "Discovery", ("location",), False),
    ("education", "Education", ("location",), False),
    ("cultural", "Cultural", ("location",), False),
    ("disaster", "Disaster", ("location",), False),
    ("other", "General event", ("location",), False),
)
EVENT_TYPE_LABELS = {
    event_type: label
    for event_type, label, contexts, automatic in EVENT_TYPE_DEFINITIONS
}
EVENT_LABEL_TYPES = {
    label: event_type
    for event_type, label, contexts, automatic in EVENT_TYPE_DEFINITIONS
}
LEGACY_EVENT_TYPE_ALIASES = {
    "birth": "born",
    "death": "died",
    "marriage": "got_married",
    "relocation": "relocated",
}
HIDDEN_OUTSIDE_PERSON_EVENT_TYPES = {
    "starting_location",
    "birth_name",
}


def canonical_event_type(event_type):
    normalized = str(event_type or "").strip()
    return LEGACY_EVENT_TYPE_ALIASES.get(normalized, normalized)


def event_type_label(event_or_type):
    if isinstance(event_or_type, dict):
        requested_type = event_or_type.get("event_type")
    else:
        requested_type = event_or_type

    normalized_type = canonical_event_type(requested_type)
    return EVENT_TYPE_LABELS.get(normalized_type, "General event")


def event_type_from_label(label, fallback="other"):
    return EVENT_LABEL_TYPES.get(str(label or "").strip(), fallback)


def event_type_options(
    context,
    include_automatic=False,
    current_event_type="",
):
    normalized_context = str(context or "").strip().casefold()
    options = []

    for event_type, label, contexts, automatic in EVENT_TYPE_DEFINITIONS:
        if automatic and not include_automatic:
            continue

        if normalized_context == "period" or normalized_context in contexts:
            options.append((event_type, label))

    current_type = canonical_event_type(current_event_type)

    if current_type and current_type in EVENT_TYPE_LABELS:
        current_option = (current_type, EVENT_TYPE_LABELS[current_type])

        if current_option not in options:
            options.insert(0, current_option)

    return tuple(options)


def event_type_contexts(event_type):
    normalized_type = canonical_event_type(event_type)

    for candidate_type, label, contexts, automatic in EVENT_TYPE_DEFINITIONS:
        if candidate_type == normalized_type:
            return tuple(contexts)

    return ()


def event_type_is_automatic(event_type):
    normalized_type = canonical_event_type(event_type)

    for candidate_type, label, contexts, automatic in EVENT_TYPE_DEFINITIONS:
        if candidate_type == normalized_type:
            return bool(automatic)

    return False


def event_type_is_person_only(event_type):
    return event_type_contexts(event_type) == ("person",)


def event_visible_outside_person(event_type):
    return (
        canonical_event_type(event_type)
        not in HIDDEN_OUTSIDE_PERSON_EVENT_TYPES
    )
