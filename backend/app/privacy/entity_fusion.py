from app.models import Detection


# ============================================================
# SOURCE WEIGHTS
# ============================================================

SOURCE_WEIGHT = {

    # Extremely reliable deterministic detectors
    "PATTERN": 1.00,
    "SECRET": 1.00,

    # Context is strong for semantic relationships
    "CONTEXT": 0.92,

    # Traditional NER
    "NER": 0.82,

    # Pretrained PII model
    "PII_MODEL": 0.78,

    "UNKNOWN": 0.50,
}


# ============================================================
# TYPE PRIORITY
# ============================================================

TYPE_PRIORITY = {

    # --------------------------------------------------------
    # Secrets
    # --------------------------------------------------------

    "PASSWORD": 110,
    "API_KEY_OR_TOKEN": 110,
    "PRIVATE_KEY": 110,
    "JWT_TOKEN": 109,

    # --------------------------------------------------------
    # Government / financial
    # --------------------------------------------------------

    "AADHAAR_LIKE": 105,
    "PAN_LIKE": 105,
    "CARD_NUMBER_LIKE": 104,
    "BANK_ACCOUNT": 103,

    # --------------------------------------------------------
    # Contact
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
    # Contextual entities
    # --------------------------------------------------------

    "ADDRESS": 85,
    "LOCATION": 84,
    "PERSON_NAME": 83,
    "ORGANIZATION": 82,
    "EMPLOYER": 80,
    "PROJECT_NAME": 79,

    "SENSITIVE_URL": 90,

    "CONFIDENTIAL_CONTEXT": 40,
}


# ============================================================
# SEMANTIC CONTEXT PREFERENCE
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
# OVERLAP
# ============================================================

def overlaps(
    first: Detection,
    second: Detection,
) -> bool:

    return (
        first.start < second.end
        and second.start < first.end
    )


# ============================================================
# NORMALIZED VALUE
# ============================================================

def normalized_value(
    detection: Detection,
) -> str:

    return detection.value.strip().lower()


# ============================================================
# SAME ENTITY
# ============================================================

def same_entity(
    first: Detection,
    second: Detection,
) -> bool:

    # --------------------------------------------------------
    # Exact same span.
    #
    # IMPORTANT:
    #
    # We consider this the same underlying candidate even
    # when two detectors disagree about its type.
    #
    # Example:
    #
    # cisco → LOCATION
    # cisco → ORGANIZATION
    # --------------------------------------------------------

    if (
        first.start == second.start
        and first.end == second.end
    ):

        return True


    # --------------------------------------------------------
    # Same type + same normalized value.
    #
    # Example:
    #
    # Sreehari
    # Sreehari
    # --------------------------------------------------------

    if (
        first.type == second.type
        and normalized_value(first)
        == normalized_value(second)
    ):

        return True


    # --------------------------------------------------------
    # Same normalized value + overlapping span.
    # --------------------------------------------------------

    if (
        normalized_value(first)
        == normalized_value(second)
        and overlaps(
            first,
            second,
        )
    ):

        return True


    return False


# ============================================================
# SOURCE SCORE
# ============================================================

def source_score(
    detection: Detection,
) -> float:

    sources = (
        detection.evidence
        or [detection.source]
    )

    if not sources:
        return SOURCE_WEIGHT["UNKNOWN"]


    return max(
        SOURCE_WEIGHT.get(
            source,
            SOURCE_WEIGHT["UNKNOWN"],
        )
        for source in sources
    )


# ============================================================
# TYPE SCORE
# ============================================================

def type_score(
    detection: Detection,
) -> float:

    return (
        TYPE_PRIORITY.get(
            detection.type,
            0,
        )
        / 110.0
    )


# ============================================================
# CHOOSE BEST
# ============================================================

def choose_best(
    detections: list[Detection],
) -> Detection:

    def score(
        detection: Detection,
    ):

        base_type = TYPE_PRIORITY.get(
            detection.type,
            0,
        )

        has_context = (
            detection.source == "CONTEXT"
            or "CONTEXT" in (
                detection.evidence or []
            )
        )

        context_bonus = 0

        if has_context:

            context_bonus = CONTEXT_TYPE_PREFERENCE.get(
                detection.type,
                0,
            )

        # ----------------------------------------------------
        # Strong contextual identity evidence
        # ----------------------------------------------------

        if (
            detection.type == "PERSON_NAME"
            and has_context
        ):
            base_type += 10

        # ----------------------------------------------------
        # Strong contextual organization evidence
        # ----------------------------------------------------

        if (
            detection.type == "ORGANIZATION"
            and has_context
        ):
            base_type += 8

        return (
            base_type,
            context_bonus,
            source_score(detection),
            detection.confidence,
            RISK_WEIGHT.get(
                detection.risk,
                0.0,
            ),
            detection.end - detection.start,
        )

    return max(
        detections,
        key=score,
    )


# ============================================================
# RISK WEIGHT
# ============================================================

RISK_WEIGHT = {
    "CRITICAL": 1.00,
    "HIGH": 0.85,
    "MEDIUM": 0.65,
    "LOW": 0.40,
}


# ============================================================
# FUSION CONFIDENCE
# ============================================================

def calculate_confidence(
    detections: list[Detection],
) -> float:

    if not detections:
        return 0.0


    probability_not_detected = 1.0


    for detection in detections:

        base = max(
            0.0,
            min(
                detection.confidence,
                1.0,
            ),
        )


        source_weight = source_score(
            detection
        )


        effective = (
            base
            * source_weight
        )


        effective = max(
            0.0,
            min(
                effective,
                0.99,
            ),
        )


        probability_not_detected *= (
            1.0 - effective
        )


    combined = (
        1.0
        - probability_not_detected
    )


    return round(
        min(
            combined,
            0.99,
        ),
        2,
    )


# ============================================================
# FUSE
# ============================================================

def fuse_detections(
    detections: list[Detection],
) -> list[Detection]:

    if not detections:
        return []


    ordered = sorted(
        detections,
        key=lambda detection: (
            detection.start,
            detection.end,
        ),
    )


    groups: list[list[Detection]] = []


    # ========================================================
    # BUILD GROUPS
    # ========================================================

    for detection in ordered:

        matched_group = None


        for group in groups:

            if any(
                same_entity(
                    detection,
                    existing,
                )
                for existing in group
            ):

                matched_group = group
                break


        if matched_group is not None:

            matched_group.append(
                detection
            )

        else:

            groups.append(
                [detection]
            )


    # ========================================================
    # CREATE FUSED DETECTIONS
    # ========================================================

    fused = []


    for group in groups:

        best = choose_best(
            group
        )


        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        evidence = []


        for detection in group:

            for source in (
                detection.evidence
                or [detection.source]
            ):

                if source not in evidence:

                    evidence.append(
                        source
                    )


        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        confidence = calculate_confidence(
            group
        )


        # ----------------------------------------------------
        # Reason
        # ----------------------------------------------------

        if len(group) == 1:

            reason = best.reason

        else:

            reason = (
                f"{best.reason} "
                f"Multiple detection methods "
                f"supported this finding."
            )


        # ----------------------------------------------------
        # Create fused detection
        # ----------------------------------------------------

        fused_detection = best.model_copy(
            update={
                "confidence": confidence,

                "source": "+".join(
                    evidence
                ),

                "evidence": evidence,

                "reason": reason,
            }
        )


        fused.append(
            fused_detection
        )


    # ========================================================
    # FINAL ORDER
    # ========================================================

    fused.sort(
        key=lambda detection: (
            detection.start,
            detection.end,
        )
    )


    return fused