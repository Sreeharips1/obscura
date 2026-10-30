from functools import lru_cache

from gliner import GLiNER

from app.models import Detection
from app.privacy.detectors.patterns import make_detection


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "urchade/gliner_small-v2.1"


# ============================================================
# PII LABELS
# ============================================================

PII_LABELS = [
    "person name",
    "organization",
    "location",
    "address",
    "phone number",
    "email address",
    "username",
    "password",
    "credit card number",
    "bank account number",
    "national id",
    "passport number",
    "driver license number",
    "ip address",
    "url",
    "date",
]


# ============================================================
# LOAD MODEL
# ============================================================

@lru_cache(maxsize=1)
def get_model():

    print(
        f"[OBSCURA] Loading GLiNER model: {MODEL_NAME}"
    )

    model = GLiNER.from_pretrained(
        MODEL_NAME
    )

    print(
        "[OBSCURA] GLiNER model loaded."
    )

    return model


# ============================================================
# RISK MAPPING
# ============================================================

def get_risk(
    label: str,
) -> str:

    label = label.lower()

    if label in {
        "password",
        "credit card number",
        "bank account number",
        "national id",
        "passport number",
        "driver license number",
    }:
        return "CRITICAL"

    if label in {
        "email address",
        "phone number",
        "address",
        "username",
    }:
        return "HIGH"

    if label in {
        "person name",
        "location",
    }:
        return "MEDIUM"

    if label == "organization":
        return "MEDIUM"

    return "LOW"


# ============================================================
# DETECT PII
# ============================================================

def detect_pii(
    text: str,
) -> list[Detection]:

    if not text.strip():
        return []


    model = get_model()


    # --------------------------------------------------------
    # GLiNER expects natural-language entity labels.
    # --------------------------------------------------------

    entities = model.predict_entities(
        text,
        PII_LABELS,
        threshold=0.35,
    )


    detections = []


    for entity in entities:

        value = entity["text"]

        label = entity["label"]

        start = entity["start"]

        end = entity["end"]

        score = float(
            entity["score"]
        )


        # ----------------------------------------------------
        # Normalize model labels to OBSCURA types
        # ----------------------------------------------------

        type_mapping = {

            "person name":
                "PERSON_NAME",

            "organization":
                "ORGANIZATION",

            "location":
                "LOCATION",

            "address":
                "ADDRESS",

            "phone number":
                "PHONE",

            "email address":
                "EMAIL",

            "username":
                "USERNAME",

            "password":
                "PASSWORD",

            "credit card number":
                "CARD_NUMBER_LIKE",

            "bank account number":
                "BANK_ACCOUNT",

            "national id":
                "NATIONAL_ID",

            "passport number":
                "PASSPORT_NUMBER",

            "driver license number":
                "DRIVER_LICENSE",

            "ip address":
                "IP_ADDRESS",

            "url":
                "SENSITIVE_URL",

            "date":
                "DATE",
        }


        detection_type = type_mapping.get(
            label.lower(),
            "UNKNOWN_PII",
        )


        risk = get_risk(
            label
        )


        # ----------------------------------------------------
        # Don't create unknown detections.
        # ----------------------------------------------------

        if detection_type == "UNKNOWN_PII":
            continue


        # ----------------------------------------------------
        # Create normal OBSCURA detection.
        # ----------------------------------------------------

        detections.append(
            make_detection(

                kind=detection_type,

                value=value,

                category="PERSONALLY_IDENTIFIABLE_INFORMATION",

                confidence=round(
                    score,
                    2,
                ),

                risk=risk,

                reason=(
                    "A local pretrained PII model "
                    "identified this text as "
                    f"{label}."
                ),

                start=start,

                end=end,

                action="PSEUDONYMIZE",

                source="PII_MODEL",
            )
        )


    return detections