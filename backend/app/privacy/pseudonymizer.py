from collections import defaultdict

from app.models import Detection, AliasItem


# ============================================================
# TOKEN PREFIXES
# ============================================================

TOKEN_PREFIXES = {
    "EMAIL": "OBSCURA_EMAIL",
    "PHONE": "OBSCURA_PHONE",
    "PERSON_NAME": "OBSCURA_NAME",
    "ORGANIZATION": "OBSCURA_ORG",
    "EMPLOYER": "OBSCURA_EMPLOYER",
    "ADDRESS": "OBSCURA_ADDRESS",
    "LOCATION": "OBSCURA_LOCATION",
    "PROJECT_NAME": "OBSCURA_PROJECT",

    "AADHAAR_LIKE": "OBSCURA_GOV_ID",
    "PAN_LIKE": "OBSCURA_GOV_ID",

    "IFSC_CODE": "OBSCURA_BANK_CODE",
    "UPI_ID": "OBSCURA_UPI",
    "CARD_NUMBER_LIKE": "OBSCURA_CARD",

    "IP_ADDRESS": "OBSCURA_IP",
    "MAC_ADDRESS": "OBSCURA_MAC",
    "IMEI": "OBSCURA_IMEI",

    "SENSITIVE_URL": "OBSCURA_URL",

    "USERNAME": "OBSCURA_USERNAME",
    "PASSWORD": "OBSCURA_PASSWORD",

    "BANK_ACCOUNT": "OBSCURA_BANK_ACCOUNT",
    "PASSPORT_NUMBER": "OBSCURA_PASSPORT",
    "DRIVER_LICENSE": "OBSCURA_LICENSE",

    "CONFIDENTIAL_CONTEXT": "OBSCURA_CONFIDENTIAL",
}


def generate_token(detection_type: str, number: int) -> str:

    prefix = TOKEN_PREFIXES.get(detection_type, "OBSCURA_PRIVATE")

    return f"<{prefix}_{number:03d}>"


def normalize_entity_value(value: str) -> str:

    return " ".join(value.strip().lower().split())


def _entity_key(detection: Detection) -> tuple[str, str]:

    return (detection.type, normalize_entity_value(detection.value))


# ============================================================
# EXPAND SELECTION
# ============================================================
#
# If the user protects ONE occurrence of a value (e.g. "Sreehari"),
# every other occurrence of the same type + value is protected too.
# Otherwise the name would still leak from the other occurrences.
# BLOCK items are never included here.
# ============================================================

def expand_selection(
    detections: list[Detection],
    selected_ids: list[str],
) -> list[str]:

    selected = set(selected_ids)

    chosen_entities = {
        _entity_key(detection)
        for detection in detections
        if detection.id in selected
        and detection.recommended_action != "BLOCK"
    }

    return [
        detection.id
        for detection in detections
        if detection.recommended_action != "BLOCK"
        and (
            detection.id in selected
            or _entity_key(detection) in chosen_entities
        )
    ]


# ============================================================
# BUILD ALIAS MAP
# ============================================================

def build_aliases(
    detections: list[Detection],
    selected_ids: list[str],
) -> list[AliasItem]:

    aliases = []
    counters = defaultdict(int)
    entity_aliases = {}

    selected = set(selected_ids)

    selected_detections = sorted(
        (
            detection
            for detection in detections
            if detection.id in selected
            and detection.recommended_action != "BLOCK"
        ),
        key=lambda detection: (detection.start, detection.end),
    )

    for detection in selected_detections:

        key = _entity_key(detection)

        if key in entity_aliases:
            continue

        counters[detection.type] += 1

        alias = AliasItem(
            detection_id=detection.id,
            original=detection.value,
            alias=generate_token(detection.type, counters[detection.type]),
            type=detection.type,
        )

        aliases.append(alias)
        entity_aliases[key] = alias

    return aliases


# ============================================================
# SANITIZE TEXT
# ============================================================

def sanitize_text(
    text: str,
    detections: list[Detection],
    selected_ids: list[str],
):

    selected_ids = expand_selection(detections, selected_ids)

    aliases = build_aliases(detections, selected_ids)

    alias_by_entity = {
        (alias.type, normalize_entity_value(alias.original)): alias
        for alias in aliases
    }

    selected = set(selected_ids)

    replacements = []

    for detection in detections:

        if detection.id not in selected:
            continue

        alias = alias_by_entity.get(_entity_key(detection))

        if alias is None:
            continue

        replacements.append((detection.start, detection.end, alias.alias))

    # Right -> left keeps earlier character positions valid.
    replacements.sort(key=lambda item: item[0], reverse=True)

    sanitized = text

    for start, end, replacement in replacements:
        sanitized = sanitized[:start] + replacement + sanitized[end:]

    return sanitized, aliases


# ============================================================
# RESTORE AI RESPONSE
# ============================================================

def restore_text(text: str, aliases: list[AliasItem]) -> str:

    restored = text

    for alias in sorted(aliases, key=lambda a: len(a.alias), reverse=True):
        restored = restored.replace(alias.alias, alias.original)

    return restored
