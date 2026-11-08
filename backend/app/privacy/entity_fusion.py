from app.models import Detection


# ============================================================
# WEIGHTS
# ============================================================

SOURCE_WEIGHT = {
    "PATTERN": 1.00,
    "SECRET": 1.00,
    "CONTEXT": 0.92,
    "NER": 0.82,
    "PII_MODEL": 0.78,
    "UNKNOWN": 0.50,
}

RISK_WEIGHT = {
    "CRITICAL": 1.00,
    "HIGH": 0.85,
    "MEDIUM": 0.65,
    "LOW": 0.40,
}

TYPE_PRIORITY = {
    "PASSWORD": 110,
    "API_KEY_OR_TOKEN": 110,
    "PRIVATE_KEY": 110,
    "JWT_TOKEN": 109,

    "AADHAAR_LIKE": 105,
    "PAN_LIKE": 105,
    "CARD_NUMBER_LIKE": 104,
    "BANK_ACCOUNT": 103,

    "EMAIL": 100,
    "PHONE": 99,

    "IMEI": 95,
    "MAC_ADDRESS": 94,
    "IFSC_CODE": 93,
    "UPI_ID": 92,
    "IP_ADDRESS": 91,

    "SENSITIVE_URL": 90,

    "ADDRESS": 85,
    "LOCATION": 84,
    "PERSON_NAME": 83,
    "ORGANIZATION": 82,
    "EMPLOYER": 80,
    "PROJECT_NAME": 79,

    "CONFIDENTIAL_CONTEXT": 40,
}

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

def overlaps(first: Detection, second: Detection) -> bool:
    return first.start < second.end and second.start < first.end


def normalized_value(detection: Detection) -> str:
    return detection.value.strip().lower()


def same_entity(first: Detection, second: Detection) -> bool:
    # ------------------------------------------------------------
    # Two detections are the "same candidate" ONLY when they are
    # about the same piece of text.
    #
    # The old rule "same type + same value anywhere in the text"
    # was removed on purpose: it merged every occurrence of a
    # repeated value (e.g. "Sreehari" twice) into ONE detection,
    # so only one span was kept and the others stayed in plaintext.
    # Repeated occurrences must stay separate detections; the
    # pseudonymizer gives them the same alias.
    # ------------------------------------------------------------

    # Exact same span (even if detectors disagree about the type).
    if first.start == second.start and first.end == second.end:
        return True

    # Same value AND overlapping span.
    if normalized_value(first) == normalized_value(second) and overlaps(first, second):
        return True

    return False


def source_score(detection: Detection) -> float:
    sources = detection.evidence or [detection.source]

    if not sources:
        return SOURCE_WEIGHT["UNKNOWN"]

    return max(
        SOURCE_WEIGHT.get(source, SOURCE_WEIGHT["UNKNOWN"])
        for source in sources
    )


def choose_best(detections: list[Detection]) -> Detection:

    def score(detection: Detection):

        base_type = TYPE_PRIORITY.get(detection.type, 0)

        has_context = (
            detection.source == "CONTEXT"
            or "CONTEXT" in (detection.evidence or [])
        )

        context_bonus = 0

        if has_context:
            context_bonus = CONTEXT_TYPE_PREFERENCE.get(detection.type, 0)

        if detection.type == "PERSON_NAME" and has_context:
            base_type += 10

        if detection.type == "ORGANIZATION" and has_context:
            base_type += 8

        return (
            base_type,
            context_bonus,
            source_score(detection),
            detection.confidence,
            RISK_WEIGHT.get(detection.risk, 0.0),
            detection.end - detection.start,
        )

    return max(detections, key=score)


def calculate_confidence(detections: list[Detection]) -> float:

    if not detections:
        return 0.0

    probability_not_detected = 1.0

    for detection in detections:

        base = max(0.0, min(detection.confidence, 1.0))

        effective = max(0.0, min(base * source_score(detection), 0.99))

        probability_not_detected *= 1.0 - effective

    combined = 1.0 - probability_not_detected

    return round(min(combined, 0.99), 2)


# ============================================================
# FUSE
# ============================================================

def fuse_detections(detections: list[Detection]) -> list[Detection]:

    if not detections:
        return []

    ordered = sorted(detections, key=lambda d: (d.start, d.end))

    groups: list[list[Detection]] = []

    for detection in ordered:

        matched_group = None

        for group in groups:
            if any(same_entity(detection, existing) for existing in group):
                matched_group = group
                break

        if matched_group is not None:
            matched_group.append(detection)
        else:
            groups.append([detection])

    fused = []

    for group in groups:

        best = choose_best(group)

        evidence = []

        for detection in group:
            for source in (detection.evidence or [detection.source]):
                if source not in evidence:
                    evidence.append(source)

        confidence = calculate_confidence(group)

        if len(group) == 1:
            reason = best.reason
        else:
            reason = (
                f"{best.reason} "
                "Multiple detection methods supported this finding."
            )

        fused.append(
            best.model_copy(
                update={
                    "confidence": confidence,
                    "source": "+".join(evidence),
                    "evidence": evidence,
                    "reason": reason,
                }
            )
        )

    fused.sort(key=lambda d: (d.start, d.end))

    return fused
