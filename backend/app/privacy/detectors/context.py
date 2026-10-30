import re

from app.models import Detection
from app.privacy.detectors.patterns import make_detection


# ============================================================
# CONFIDENTIAL CONTEXT PATTERNS
# ============================================================

CONFIDENTIAL_PATTERNS = [
    r"\bconfidential\b",
    r"\binternal\s+use\s+only\b",
    r"\bnot\s+for\s+distribution\b",
    r"\bdo\s+not\s+share\b",
    r"\bprivate\s+information\b",
    r"\bsecret\s+project\b",
    r"\bunreleased\s+product\b",
    r"\btrade\s+secret\b",
]


# ============================================================
# CONTEXTUAL ORGANIZATION PATTERN
# ============================================================

ORGANIZATION_CONTEXT_PATTERN = re.compile(
    r"""
    \b
    (?:
        join
        |joined
        |joining
        |work\s+at
        |working\s+at
        |work\s+for
        |working\s+for
        |employed\s+at
        |application\s+to
        |application\s+for
        |offer\s+from
        |interview\s+at
        |position\s+at
    )
    \s+
    (
        [A-Za-z0-9][A-Za-z0-9&.,'_-]*
        (?:
            \s+
            [A-Za-z0-9][A-Za-z0-9&.,'_-]*
        ){0,4}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# WORDS THAT END ORGANIZATION PHRASES
# ============================================================

ORGANIZATION_STOP_WORDS = {
    "and",
    "but",
    "or",
    "then",
    "while",
    "where",
    "which",
    "that",
    "with",
    "from",
    "to",
    "in",
    "on",
    "at",
    "my",
    "i",
    "he",
    "she",
    "they",
    "we",
}


# ============================================================
# CONFIDENTIAL CONTEXT DETECTION
# ============================================================

def detect_context(
    text: str,
) -> list[Detection]:

    detections = []


    for pattern in CONFIDENTIAL_PATTERNS:

        for match in re.finditer(
            pattern,
            text,
            re.IGNORECASE,
        ):

            detections.append(
                make_detection(
                    kind="CONFIDENTIAL_CONTEXT",

                    value=match.group(),

                    category="CONFIDENTIAL_INFORMATION",

                    confidence=0.72,

                    risk="HIGH",

                    reason=(
                        "The surrounding language suggests "
                        "that this information may be confidential."
                    ),

                    start=match.start(),

                    end=match.end(),

                    action="ASK_USER",

                    source="CONTEXT",
                )
            )


    return detections


# ============================================================
# CONTEXTUAL ORGANIZATION DETECTION
# ============================================================

def detect_contextual_organizations(
    text: str,
) -> list[Detection]:

    detections = []


    for match in ORGANIZATION_CONTEXT_PATTERN.finditer(
        text
    ):

        # ----------------------------------------------------
        # Extract candidate organization
        # ----------------------------------------------------

        raw_value = match.group(1).strip()


        words = raw_value.split()


        cleaned_words = []


        for word in words:

            normalized = word.lower().strip(
                ".,;:!?()[]{}"
            )


            if normalized in ORGANIZATION_STOP_WORDS:

                break


            cleaned_words.append(
                word
            )


        if not cleaned_words:
            continue


        value = " ".join(
            cleaned_words
        ).strip()


        if not value:
            continue


        # ----------------------------------------------------
        # Ignore extremely short candidates
        # ----------------------------------------------------

        if len(value) < 2:
            continue


        # ----------------------------------------------------
        # Calculate exact character positions
        # ----------------------------------------------------

        start = match.start(1)

        end = start + len(value)


        # ----------------------------------------------------
        # Create detection using the project's standard
        # detection factory.
        # ----------------------------------------------------

        detections.append(
            make_detection(
                kind="ORGANIZATION",

                value=value,

                category="ORGANIZATIONAL_INFORMATION",

                confidence=0.88,

                risk="MEDIUM",

                reason=(
                    "The surrounding language indicates "
                    "that this text refers to an organization."
                ),

                start=start,

                end=end,

                action="Pseudonymize",

                source="CONTEXT",
            )
        )


    return detections