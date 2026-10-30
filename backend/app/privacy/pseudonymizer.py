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


# ============================================================
# TOKEN GENERATOR
# ============================================================

def generate_token(
    detection_type: str,
    number: int,
) -> str:

    prefix = TOKEN_PREFIXES.get(
        detection_type,
        "OBSCURA_PRIVATE",
    )

    return f"<{prefix}_{number:03d}>"


# ============================================================
# NORMALIZE ENTITY
# ============================================================
#
# Used ONLY for deciding whether two detections represent
# the same underlying value.
#
# Example:
#
# Sreehari
# sreehari
#
# become the same canonical identity.
#
# We do NOT modify the original value stored in AliasItem.
# ============================================================

def normalize_entity_value(
    value: str,
) -> str:

    return " ".join(
        value.strip().lower().split()
    )


# ============================================================
# BUILD ALIAS MAP
# ============================================================

def build_aliases(
    detections: list[Detection],
    selected_ids: list[str],
) -> list[AliasItem]:

    aliases = []

    counters = defaultdict(int)

    # --------------------------------------------------------
    # Maps:
    #
    # (TYPE, NORMALIZED_VALUE)
    #
    # to:
    #
    # AliasItem
    #
    # This is the key part that allows repeated occurrences
    # to share the same alias.
    # --------------------------------------------------------

    entity_aliases = {}


    # --------------------------------------------------------
    # Process in original text order.
    # --------------------------------------------------------

    selected_detections = [
        detection
        for detection in detections
        if detection.id in selected_ids
    ]

    selected_detections.sort(
        key=lambda detection: (
            detection.start,
            detection.end,
        )
    )


    for detection in selected_detections:

        # ----------------------------------------------------
        # BLOCK items must never be sent externally.
        # ----------------------------------------------------

        if (
            detection.recommended_action
            == "BLOCK"
        ):
            continue


        # ----------------------------------------------------
        # Canonical identity.
        #
        # Type is included deliberately.
        #
        # Example:
        #
        # "123456"
        # PHONE
        #
        # and
        #
        # "123456"
        # ACCOUNT_NUMBER
        #
        # must NOT automatically become the same entity.
        # ----------------------------------------------------

        key = (
            detection.type,
            normalize_entity_value(
                detection.value
            ),
        )


        # ----------------------------------------------------
        # Existing entity?
        # ----------------------------------------------------

        existing_alias = entity_aliases.get(
            key
        )


        if existing_alias is not None:

            # ------------------------------------------------
            # Same underlying entity.
            #
            # No new alias is created.
            #
            # The caller can still use the existing alias
            # because the detection ID is mapped separately
            # during sanitization.
            # ------------------------------------------------

            continue


        # ----------------------------------------------------
        # New entity.
        # ----------------------------------------------------

        counters[
            detection.type
        ] += 1


        token = generate_token(
            detection.type,
            counters[detection.type],
        )


        alias = AliasItem(
            detection_id=detection.id,
            original=detection.value,
            alias=token,
            type=detection.type,
        )


        aliases.append(
            alias
        )


        entity_aliases[
            key
        ] = alias


    return aliases


# ============================================================
# SANITIZE TEXT
# ============================================================

def sanitize_text(
    text: str,
    detections: list[Detection],
    selected_ids: list[str],
):

    aliases = build_aliases(
        detections,
        selected_ids,
    )


    # --------------------------------------------------------
    # Build alias lookup by detection ID.
    #
    # The first occurrence owns the AliasItem.
    # Repeated occurrences need to find that same alias.
    # --------------------------------------------------------

    alias_by_detection = {}


    # Canonical entity lookup.

    alias_by_entity = {
        (
            alias.type,
            normalize_entity_value(
                alias.original
            ),
        ): alias
        for alias in aliases
    }


    # --------------------------------------------------------
    # Associate EVERY selected detection with its canonical
    # alias.
    # --------------------------------------------------------

    for detection in detections:

        if detection.id not in selected_ids:
            continue


        if (
            detection.recommended_action
            == "BLOCK"
        ):
            continue


        key = (
            detection.type,
            normalize_entity_value(
                detection.value
            ),
        )


        alias = alias_by_entity.get(
            key
        )


        if alias is not None:

            alias_by_detection[
                detection.id
            ] = alias


    # --------------------------------------------------------
    # Build character-position replacements.
    # --------------------------------------------------------

    replacements = []


    for detection in detections:

        if detection.id not in selected_ids:
            continue


        alias = alias_by_detection.get(
            detection.id
        )


        if alias is None:
            continue


        replacements.append(
            (
                detection.start,
                detection.end,
                alias.alias,
            )
        )


    # --------------------------------------------------------
    # RIGHT → LEFT
    #
    # This preserves original character positions.
    # --------------------------------------------------------

    replacements.sort(
        key=lambda item: item[0],
        reverse=True,
    )


    sanitized = text


    for (
        start,
        end,
        replacement,
    ) in replacements:

        sanitized = (
            sanitized[:start]
            + replacement
            + sanitized[end:]
        )


    return sanitized, aliases


# ============================================================
# RESTORE AI RESPONSE
# ============================================================

def restore_text(
    text: str,
    aliases: list[AliasItem],
) -> str:

    restored = text


    # --------------------------------------------------------
    # Longest aliases first.
    # --------------------------------------------------------

    ordered_aliases = sorted(
        aliases,
        key=lambda alias: len(
            alias.alias
        ),
        reverse=True,
    )


    for alias in ordered_aliases:

        restored = restored.replace(
            alias.alias,
            alias.original,
        )


    return restored