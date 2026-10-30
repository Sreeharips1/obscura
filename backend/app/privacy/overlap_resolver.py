from app.models import Detection


# ============================================================
# TYPE PRIORITY
# ============================================================
#
# Higher number = stronger semantic type when two detections
# compete for the same text span.
#
# Structured identifiers are given the highest priority.
# Contextual semantic entities come next.
# ============================================================

TYPE_PRIORITY = {

    # --------------------------------------------------------
    # Secrets / credentials
    # --------------------------------------------------------

    "PRIVATE_KEY": 110,
    "API_KEY_OR_TOKEN": 109,
    "PASSWORD": 108,
    "JWT_TOKEN": 107,

    # --------------------------------------------------------
    # Government / financial identifiers
    # --------------------------------------------------------

    "AADHAAR_LIKE": 105,
    "PAN_LIKE": 104,
    "CARD_NUMBER_LIKE": 103,
    "BANK_ACCOUNT": 102,

    # --------------------------------------------------------
    # Direct contact information
    # --------------------------------------------------------

    "EMAIL": 100,
    "PHONE": 99,

    # --------------------------------------------------------
    # Digital identifiers
    # --------------------------------------------------------

    "IMEI": 95,
    "MAC_ADDRESS": 94,
    "IFSC_CODE": 93,
    "UPI_ID": 92,
    "IP_ADDRESS": 91,

    # --------------------------------------------------------
    # Web / URL
    # --------------------------------------------------------

    "SENSITIVE_URL": 90,

    # --------------------------------------------------------
    # Contextual private information
    # --------------------------------------------------------

    "ADDRESS": 85,
    "LOCATION": 84,
    "PERSON_NAME": 83,
    "ORGANIZATION": 82,
    "EMPLOYER": 80,
    "PROJECT_NAME": 79,

    # --------------------------------------------------------
    # General confidential context
    # --------------------------------------------------------

    "CONFIDENTIAL_CONTEXT": 40,
}


# ============================================================
# RISK PRIORITY
# ============================================================

RISK_PRIORITY = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


# ============================================================
# SOURCE PRIORITY
# ============================================================
#
# This is used only when two detections have essentially
# the same semantic strength.
#
# Deterministic pattern matching is extremely reliable for
# structured values.
#
# Context detection is important for semantic entities such
# as organizations.
#
# PII_MODEL provides additional evidence.
# ============================================================

SOURCE_PRIORITY = {
    "PATTERN": 6,
    "SECRET": 6,
    "CONTEXT": 5,
    "NER": 4,
    "PII_MODEL": 3,
    "UNKNOWN": 1,
}


# ============================================================
# CONTEXTUAL TYPE PREFERENCE
# ============================================================
#
# Some contextual relationships are especially strong.
#
# Example:
#
# "join cisco"
#
# strongly suggests:
#
# cisco → ORGANIZATION
#
# rather than:
#
# cisco → LOCATION
# ============================================================

CONTEXT_TYPE_PREFERENCE = {
    "ORGANIZATION": 4,
    "EMPLOYER": 3,
    "PERSON_NAME": 3,
    "ADDRESS": 3,
    "LOCATION": 2,
    "PROJECT_NAME": 2,
}


# ============================================================
# HELPERS
# ============================================================

def _source_score(
    detection: Detection,
) -> int:

    sources = (
        detection.evidence
        or [detection.source]
    )

    return max(
        SOURCE_PRIORITY.get(
            source,
            SOURCE_PRIORITY["UNKNOWN"],
        )
        for source in sources
    )


def _priority(
    detection: Detection,
) -> tuple:

    return (
        TYPE_PRIORITY.get(
            detection.type,
            0,
        ),

        RISK_PRIORITY.get(
            detection.risk,
            0,
        ),

        CONTEXT_TYPE_PREFERENCE.get(
            detection.type,
            0,
        ),

        _source_score(
            detection
        ),

        detection.confidence,

        detection.end - detection.start,
    )


def _overlaps(
    first: Detection,
    second: Detection,
) -> bool:

    return (
        first.start < second.end
        and second.start < first.end
    )


def _same_span(
    first: Detection,
    second: Detection,
) -> bool:

    return (
        first.start == second.start
        and first.end == second.end
    )


def _same_value(
    first: Detection,
    second: Detection,
) -> bool:

    return (
        first.value.strip().lower()
        == second.value.strip().lower()
    )


# ============================================================
# SEMANTIC CONFLICT
# ============================================================

def _is_semantic_conflict(
    first: Detection,
    second: Detection,
) -> bool:

    if not _same_span(
        first,
        second,
    ):
        return False

    return (
        first.type
        != second.type
    )


# ============================================================
# RESOLVER
# ============================================================

def resolve_overlaps(
    detections: list[Detection],
) -> list[Detection]:

    if not detections:
        return []


    # --------------------------------------------------------
    # Process strongest detections first.
    # --------------------------------------------------------

    ordered = sorted(
        detections,
        key=_priority,
        reverse=True,
    )


    accepted: list[Detection] = []


    for candidate in ordered:

        conflict = False


        for existing in accepted:

            if not _overlaps(
                candidate,
                existing,
            ):
                continue


            # =================================================
            # EXACT SAME SPAN
            # =================================================

            if _same_span(
                candidate,
                existing,
            ):

                # ------------------------------------------------
                # Same semantic type:
                #
                # Fusion should normally already have combined
                # these. Keep the stronger fused detection.
                # ------------------------------------------------

                if (
                    candidate.type
                    == existing.type
                ):

                    conflict = True
                    break


                # ------------------------------------------------
                # Different semantic type:
                #
                # Example:
                #
                # cisco → LOCATION
                # cisco → ORGANIZATION
                #
                # Keep the stronger semantic interpretation.
                # ------------------------------------------------

                if _is_semantic_conflict(
                    candidate,
                    existing,
                ):

                    if (
                        _priority(candidate)
                        <= _priority(existing)
                    ):

                        conflict = True
                        break


            # =================================================
            # PARTIAL OVERLAP
            # =================================================

            else:

                # ------------------------------------------------
                # If the existing detection is stronger, discard
                # the weaker overlapping candidate.
                # ------------------------------------------------

                if (
                    _priority(candidate)
                    <= _priority(existing)
                ):

                    conflict = True
                    break


        if not conflict:

            accepted.append(
                candidate
            )


    # --------------------------------------------------------
    # Restore natural text order.
    # --------------------------------------------------------

    accepted.sort(
        key=lambda detection: (
            detection.start,
            detection.end,
        )
    )


    return accepted