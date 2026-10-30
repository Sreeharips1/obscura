import re

import spacy

from app.models import Detection
from app.privacy.detectors.patterns import make_detection


# ============================================================
# LOAD MODEL ONCE
# ============================================================

try:
    nlp = spacy.load("en_core_web_sm")

except OSError:
    nlp = None


# ============================================================
# ENTITY CONFIGURATION
# ============================================================

ENTITY_CONFIG = {

    "PERSON": {
        "type": "PERSON_NAME",
        "category": "PERSONAL_IDENTITY",
        "risk": "MEDIUM",
        "confidence": 0.82,
        "action": "PSEUDONYMIZE",
        "reason": (
            "A local language model identified "
            "this text as a person's name."
        ),
    },

    "GPE": {
        "type": "LOCATION",
        "category": "LOCATION_INFORMATION",
        "risk": "HIGH",
        "confidence": 0.82,
        "action": "ASK_USER",
        "reason": (
            "A local language model identified "
            "this text as a geographic location."
        ),
    },

    "LOC": {
        "type": "LOCATION",
        "category": "LOCATION_INFORMATION",
        "risk": "HIGH",
        "confidence": 0.78,
        "action": "ASK_USER",
        "reason": (
            "A local language model identified "
            "this text as a location."
        ),
    },

    "ORG": {
        "type": "ORGANIZATION",
        "category": "ORGANIZATIONAL_INFORMATION",
        "risk": "MEDIUM",
        "confidence": 0.80,
        "action": "ASK_USER",
        "reason": (
            "A local language model identified "
            "this text as an organization."
        ),
    },

    "FAC": {
        "type": "FACILITY",
        "category": "LOCATION_INFORMATION",
        "risk": "MEDIUM",
        "confidence": 0.70,
        "action": "ASK_USER",
        "reason": (
            "A local language model identified "
            "this text as a facility or location."
        ),
    },
}


# ============================================================
# PERSON-SIGNAL PHRASES
# ============================================================

# These are not enough by themselves.
# They are used together with the entity's position.
#
# Example:
#
# Sreehari joined the team
# ^^^^^^^^
# person is BEFORE "joined"
#
# ABC Technologies joined the partnership
# ^^^^^^^^^^^^^^^^^
# this could be an organization, so we do NOT blindly
# convert ORG -> PERSON.
# ============================================================

PERSON_BEFORE_VERB = [
    "joined",
    "works",
    "worked",
    "studies",
    "studied",
    "graduated",
    "applied",
    "applies",
    "interviewed",
    "attended",
    "moved",
    "lives",
    "stays",
    "resides",
]


PERSON_EXPLICIT_PATTERNS = [
    r"\bmy\s+name\s+is\s+",
    r"\bmy\s+full\s+name\s+is\s+",
    r"\bi\s+am\s+",
    r"\bi'm\s+",
    r"\bmr\.?\s+",
    r"\bms\.?\s+",
    r"\bmiss\s+",
]


# ============================================================
# TEXT UTILITIES
# ============================================================

def _sentence_for_entity(
    text: str,
    start: int,
    end: int,
) -> str:

    """
    Return only the sentence containing the entity.

    We deliberately DO NOT inspect a huge surrounding
    window because that caused the previous false positive.
    """

    sentence_start = text.rfind(
        ".",
        0,
        start,
    )

    sentence_start = max(
        sentence_start,
        text.rfind(
            "!",
            0,
            start,
        ),
        text.rfind(
            "?",
            0,
            start,
        ),
    )

    sentence_start += 1


    sentence_end_candidates = [
        position
        for position in [
            text.find(
                ".",
                end,
            ),
            text.find(
                "!",
                end,
            ),
            text.find(
                "?",
                end,
            ),
        ]
        if position != -1
    ]


    if sentence_end_candidates:

        sentence_end = min(
            sentence_end_candidates
        )

    else:

        sentence_end = len(text)


    return text[
        sentence_start:sentence_end
    ]


# ============================================================
# EXPLICIT PERSON CONTEXT
# ============================================================

def has_explicit_person_context(
    sentence: str,
    entity_start_in_sentence: int,
) -> bool:

    before_entity = sentence[
        :entity_start_in_sentence
    ].lower()


    for pattern in PERSON_EXPLICIT_PATTERNS:

        if re.search(
            pattern,
            before_entity,
        ):

            return True


    return False


# ============================================================
# SUBJECT-LIKE PERSON CONTEXT
# ============================================================

def is_person_subject(
    sentence: str,
    entity_start_in_sentence: int,
    entity_end_in_sentence: int,
) -> bool:

    """
    Determine whether the entity appears to be the person
    performing an action.

    Example:

        Sreehari joined ABC Technologies

        Sreehari
        ^^^^^^^^
        BEFORE "joined" → likely person

    But:

        Sreehari joined ABC Technologies

        ABC Technologies
                       ^^^^^^^^^^^^^^^^^
                       AFTER "joined" → don't convert ORG
    """

    before = sentence[
        :entity_start_in_sentence
    ]

    after = sentence[
        entity_end_in_sentence:
    ]


    before_lower = before.lower()
    after_lower = after.lower()


    # --------------------------------------------------------
    # Explicit person declaration
    # --------------------------------------------------------

    if has_explicit_person_context(
        sentence,
        entity_start_in_sentence,
    ):

        return True


    # --------------------------------------------------------
    # Check whether a person-like action verb occurs
    # immediately after the entity.
    #
    # We only inspect a small amount of text.
    # --------------------------------------------------------

    after_words = after_lower.strip()


    for verb in PERSON_BEFORE_VERB:

        pattern = rf"^{re.escape(verb)}\b"

        if re.search(
            pattern,
            after_words,
        ):

            return True


    # --------------------------------------------------------
    # Another common structure:
    #
    # "Sreehari is an engineer"
    # "Sreehari is working..."
    # "Sreehari is applying..."
    # --------------------------------------------------------

    if re.match(
        r"^is\s+(?:an?\s+)?"
        r"(?:engineer|developer|student|manager|"
        r"employee|applicant|candidate|working|"
        r"applying|studying|living|staying)\b",
        after_words,
    ):

        return True


    return False


# ============================================================
# SHOULD CONVERT ORG → PERSON?
# ============================================================

def should_correct_org_to_person(
    text: str,
    entity,
) -> bool:

    """
    We only correct an ORG prediction when there is strong
    evidence that THIS SPECIFIC ENTITY is a person.

    We do NOT use a large context window.
    """

    sentence = _sentence_for_entity(
        text,
        entity.start_char,
        entity.end_char,
    )


    # Calculate the entity position inside the sentence.

    sentence_start = text.rfind(
        ".",
        0,
        entity.start_char,
    )

    sentence_start = max(
        sentence_start,
        text.rfind(
            "!",
            0,
            entity.start_char,
        ),
        text.rfind(
            "?",
            0,
            entity.start_char,
        ),
    )

    sentence_start += 1


    entity_start = (
        entity.start_char
        - sentence_start
    )

    entity_end = (
        entity.end_char
        - sentence_start
    )


    return is_person_subject(
        sentence,
        entity_start,
        entity_end,
    )


# ============================================================
# DETECT NER ENTITIES
# ============================================================

def detect_ner(
    text: str,
) -> list[Detection]:

    if not text.strip():

        return []


    if nlp is None:

        print(
            "[OBSCURA NER] "
            "spaCy model is not installed."
        )

        return []


    document = nlp(text)

    detections = []


    for entity in document.ents:

        original_label = entity.label_

        config = ENTITY_CONFIG.get(
            original_label
        )


        if not config:

            continue


        value = entity.text.strip()


        if not value:

            continue


        # ====================================================
        # CAREFUL ORG → PERSON CORRECTION
        # ====================================================

        if (
            original_label == "ORG"
            and should_correct_org_to_person(
                text,
                entity,
            )
        ):

            config = ENTITY_CONFIG[
                "PERSON"
            ]

            final_type = "PERSON"


        else:

            final_type = original_label


        # ====================================================
        # CREATE DETECTION
        # ====================================================

        detections.append(
            make_detection(
                kind=config["type"],
                value=value,
                category=config["category"],
                confidence=config["confidence"],
                risk=config["risk"],
                reason=config["reason"],
                start=entity.start_char,
                end=entity.end_char,
                action=config["action"],
                source="NER",
            )
        )


    return detections