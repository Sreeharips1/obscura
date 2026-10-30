import re

from app.models import Detection
from app.privacy.detectors.patterns import make_detection


# ============================================================
# CONTEXTUAL NAME DETECTION
# ============================================================

NAME_PATTERNS = [

    # My name is Sreehari
    # My name is Sreehari P Shaiju
    re.compile(
        r"(?i)\bmy\s+name\s+is\s+"
        r"([A-Z][A-Za-z'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z'-]{1,}){0,4})"
    ),

    # My full name is Sreehari P Shaiju
    re.compile(
        r"(?i)\bmy\s+full\s+name\s+is\s+"
        r"([A-Z][A-Za-z'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z'-]{1,}){0,4})"
    ),

    # I am Sreehari
    re.compile(
        r"(?i)\bI\s+am\s+"
        r"([A-Z][A-Za-z'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z'-]{1,}){0,3})"
    ),

    # I'm Sreehari
    re.compile(
        r"(?i)\bI'm\s+"
        r"([A-Z][A-Za-z'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z'-]{1,}){0,3})"
    ),

    # iam Sreehari
    # i am Sreehari
    re.compile(
        r"(?i)\b(?:i\s+am|iam)\s+"
        r"([A-Z][A-Za-z'-]{2,})"
    ),
]


# ============================================================
# LOCATION / ADDRESS CONTEXT
# ============================================================

LOCATION_PATTERNS = [

    # I live in Kochi
    re.compile(
        r"(?i)\bI\s+(?:live|stay|reside)\s+in\s+"
        r"([^.,;\n]{2,60})"
    ),

    # I live at ...
    re.compile(
        r"(?i)\bI\s+(?:live|stay|reside)\s+at\s+"
        r"([^.;\n]{5,100})"
    ),

    # My home address is ...
    re.compile(
        r"(?i)\bmy\s+(?:home|residential)\s+address\s+is\s+"
        r"([^.;\n]{5,120})"
    ),

    # My address is ...
    re.compile(
        r"(?i)\bmy\s+address\s+is\s+"
        r"([^.;\n]{5,120})"
    ),
]


# ============================================================
# EMPLOYMENT CONTEXT
# ============================================================

EMPLOYER_PATTERNS = [

    # I work at Cisco
    # I work for Cisco
    re.compile(
        r"(?i)\bI\s+work\s+(?:at|for)\s+"
        r"([A-Z][A-Za-z0-9&.,' -]{2,80})"
    ),

    # My company is Cisco
    # My employer is Cisco
    re.compile(
        r"(?i)\bmy\s+(?:company|employer)\s+is\s+"
        r"([A-Z][A-Za-z0-9&.,' -]{2,80})"
    ),

    # Working at Cisco
    re.compile(
        r"(?i)\bworking\s+(?:at|for)\s+"
        r"([A-Z][A-Za-z0-9&.,' -]{2,80})"
    ),
]


# ============================================================
# ORGANIZATION / COMPANY CONTEXT
# ============================================================

ORGANIZATION_PATTERNS = [

    # --------------------------------------------------------
    # Joining an organization
    #
    # join Cisco
    # joined Cisco
    # joining Cisco
    # wish to join Cisco
    # wishes to join Cisco
    # want to join Cisco
    # wants to join Cisco
    # --------------------------------------------------------

    re.compile(
        r"(?i)\b"
        r"(?:"
        r"join"
        r"|joined"
        r"|joining"
        r"|wish\s+to\s+join"
        r"|wishes\s+to\s+join"
        r"|want\s+to\s+join"
        r"|wants\s+to\s+join"
        r"|wanted\s+to\s+join"
        r")"
        r"\s+"
        r"("
        r"[A-Za-z0-9][A-Za-z0-9&'-]*"
        r"(?:"
        r"\s+"
        r"[A-Za-z0-9][A-Za-z0-9&'-]*"
        r"){0,4}"
        r")"
    ),

    # --------------------------------------------------------
    # Employment
    #
    # work at Cisco
    # work for ABC Technologies
    # working at Google
    # employed at Microsoft
    # --------------------------------------------------------

    re.compile(
        r"(?i)\b"
        r"(?:"
        r"work\s+at"
        r"|working\s+at"
        r"|work\s+for"
        r"|working\s+for"
        r"|employed\s+at"
        r")"
        r"\s+"
        r"("
        r"[A-Za-z0-9][A-Za-z0-9&'-]*"
        r"(?:"
        r"\s+"
        r"[A-Za-z0-9][A-Za-z0-9&'-]*"
        r"){0,4}"
        r")"
    ),

    # --------------------------------------------------------
    # Application / position
    #
    # application to Cisco
    # application for Cisco
    # position at Cisco
    # interview at Cisco
    # offer from Cisco
    # --------------------------------------------------------

    re.compile(
        r"(?i)\b"
        r"(?:"
        r"application\s+to"
        r"|application\s+for"
        r"|position\s+at"
        r"|interview\s+at"
        r"|offer\s+from"
        r")"
        r"\s+"
        r"("
        r"[A-Za-z0-9][A-Za-z0-9&'-]*"
        r"(?:"
        r"\s+"
        r"[A-Za-z0-9][A-Za-z0-9&'-]*"
        r"){0,4}"
        r")"
    ),

    # --------------------------------------------------------
    # Sending something to an organization
    #
    # send the email to Cisco
    # send this to ABC Technologies
    # send it to Google
    # --------------------------------------------------------

    re.compile(
        r"(?i)\b"
        r"(?:"
        r"send\s+(?:this\s+|it\s+|the\s+mail\s+|the\s+email\s+)?to"
        r"|sent\s+(?:this\s+|it\s+|the\s+mail\s+|the\s+email\s+)?to"
        r")"
        r"\s+"
        r"("
        r"[A-Za-z0-9][A-Za-z0-9&'-]*"
        r"(?:"
        r"\s+"
        r"[A-Za-z0-9][A-Za-z0-9&'-]*"
        r"){0,4}"
        r")"
    ),
]


# ============================================================
# ORGANIZATION STOP WORDS
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
    "moved",
    "move",
    "wish",
    "wishes",
    "want",
    "wants",
    "wanted",
    "would",
    "give",
    "send",
    "the",
    "please",
    "application",
}


# ============================================================
# PROJECT / CONFIDENTIAL WORK
# ============================================================

PROJECT_PATTERNS = [

    re.compile(
        r"(?i)\bproject\s+"
        r"([A-Z][A-Za-z0-9_-]{2,50})"
    ),

    re.compile(
        r"(?i)\b(?:internal|confidential)\s+project\s+"
        r"([A-Za-z0-9_-]{2,50})"
    ),
]


# ============================================================
# RECIPIENT / PERSON CONTEXT
# ============================================================

RECIPIENT_PATTERNS = [

    re.compile(
        r"(?i)\bsend\s+(?:this|it|the\s+mail|the\s+email)"
        r"\s+to\s+"
        r"([A-Z][A-Za-z'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z'-]{1,}){0,3})"
    ),

    re.compile(
        r"(?i)\bemail\s+"
        r"([A-Z][A-Za-z'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z'-]{1,}){0,3})"
    ),
]


# ============================================================
# HELPER
# ============================================================

def _add_detection(
    detections: list[Detection],
    *,
    kind: str,
    value: str,
    category: str,
    confidence: float,
    risk: str,
    reason: str,
    start: int,
    end: int,
    action: str,
    source: str = "CONTEXT",
):
    value = value.strip()

    if not value:
        return

    detections.append(
        make_detection(
            kind=kind,
            value=value,
            category=category,
            confidence=confidence,
            risk=risk,
            reason=reason,
            start=start,
            end=end,
            action=action,
            source=source,
        )
    )


# ============================================================
# CLEAN ORGANIZATION VALUE
# ============================================================

def _clean_organization_value(
    value: str,
) -> str:

    words = value.strip().split()

    cleaned_words = []

    for word in words:

        normalized = word.lower().strip(
            ".,;:!?()[]{}"
        )

        if normalized in ORGANIZATION_STOP_WORDS:
            break

        cleaned_words.append(word)

    return " ".join(
        cleaned_words
    ).strip()


# ============================================================
# REPEATED PERSON IDENTITY PROPAGATION
# ============================================================
#
# Example:
#
# My name is Sreehari.
# Sreehari wishes to join Cisco.
#
# First occurrence:
#     CONTEXT -> Sreehari
#
# Second occurrence:
#     automatically detected as PERSON_NAME
#
# This prevents the same person's name from being exposed
# simply because it appears again later in the text.
# ============================================================

def _propagate_person_names(
    text: str,
    detections: list[Detection],
) -> None:

    # --------------------------------------------------------
    # Find names that were strongly identified by context.
    # --------------------------------------------------------

    known_names = []

    for detection in detections:

        if detection.type != "PERSON_NAME":
            continue

        if detection.source != "CONTEXT":
            continue

        normalized = detection.value.strip().lower()

        if not normalized:
            continue

        if normalized not in known_names:
            known_names.append(normalized)


    # --------------------------------------------------------
    # Find every occurrence of those names.
    # --------------------------------------------------------

    for normalized_name in known_names:

        original_name = next(
            (
                detection.value
                for detection in detections
                if (
                    detection.type == "PERSON_NAME"
                    and detection.source == "CONTEXT"
                    and detection.value.strip().lower()
                    == normalized_name
                )
            ),
            normalized_name,
        )

        # ----------------------------------------------------
        # Case-insensitive exact-word matching.
        #
        # Prevent:
        #
        # Sreehari -> matching Sreeharian
        #
        # Also prevent matching inside emails/usernames.
        # ----------------------------------------------------

        pattern = re.compile(
            r"(?i)(?<![\w@])"
            + re.escape(original_name)
            + r"(?![\w@])"
        )


        for match in pattern.finditer(text):

            start = match.start()
            end = match.end()


            # ------------------------------------------------
            # Don't create another detection if this exact
            # span already has a contextual PERSON_NAME.
            # ------------------------------------------------

            already_exists = any(
                (
                    detection.type == "PERSON_NAME"
                    and detection.start == start
                    and detection.end == end
                )
                for detection in detections
            )

            if already_exists:
                continue


            detections.append(
                make_detection(
                    kind="PERSON_NAME",
                    value=match.group(),
                    category="PERSONAL_IDENTITY",
                    confidence=0.86,
                    risk="MEDIUM",
                    reason=(
                        "This value matches a person's name "
                        "previously identified from explicit "
                        "personal context."
                    ),
                    start=start,
                    end=end,
                    action="PSEUDONYMIZE",
                    source="CONTEXT",
                )
            )


# ============================================================
# CONTEXTUAL DETECTION
# ============================================================

def detect_contextual(
    text: str,
) -> list[Detection]:

    detections: list[Detection] = []


    # ========================================================
    # PERSON NAME
    # ========================================================

    for pattern in NAME_PATTERNS:

        for match in pattern.finditer(text):

            value = match.group(1).strip()

            ignored = {
                "looking",
                "applying",
                "working",
                "interested",
                "trying",
                "writing",
            }

            if value.lower() in ignored:
                continue

            _add_detection(
                detections,

                kind="PERSON_NAME",

                value=value,

                category="PERSONAL_IDENTITY",

                confidence=0.90,

                risk="MEDIUM",

                reason=(
                    "The surrounding language explicitly "
                    "identifies this as a person's name."
                ),

                start=match.start(1),

                end=match.end(1),

                action="PSEUDONYMIZE",
            )


    # ========================================================
    # LOCATION / ADDRESS
    # ========================================================

    for pattern in LOCATION_PATTERNS:

        for match in pattern.finditer(text):

            value = match.group(1).strip()

            _add_detection(
                detections,

                kind="LOCATION",

                value=value,

                category="LOCATION_INFORMATION",

                confidence=0.82,

                risk="HIGH",

                reason=(
                    "The surrounding language indicates "
                    "that this may be a person's residence "
                    "or private location."
                ),

                start=match.start(1),

                end=match.end(1),

                action="PSEUDONYMIZE",
            )


    # ========================================================
    # EMPLOYER
    # ========================================================

    for pattern in EMPLOYER_PATTERNS:

        for match in pattern.finditer(text):

            value = match.group(1)

            value = re.split(
                r"(?i)\s+(?:and|but|because|where|which|that)\s+",
                value,
                maxsplit=1,
            )[0].strip()

            if not value:
                continue

            _add_detection(
                detections,

                kind="EMPLOYER",

                value=value,

                category="EMPLOYMENT_INFORMATION",

                confidence=0.76,

                risk="MEDIUM",

                reason=(
                    "The surrounding language suggests "
                    "this is an employer or workplace."
                ),

                start=match.start(1),

                end=match.start(1) + len(value),

                action="ASK_USER",
            )


    # ========================================================
    # ORGANIZATION / COMPANY
    # ========================================================

    for pattern in ORGANIZATION_PATTERNS:

        for match in pattern.finditer(text):

            raw_value = match.group(1)

            value = _clean_organization_value(
                raw_value
            )

            if not value:
                continue

            if len(value) < 2:
                continue

            # ------------------------------------------------
            # Important:
            #
            # Use the actual cleaned value length to calculate
            # the span. This prevents:
            #
            # Cisco. Please
            #
            # from becoming the detected organization.
            # ------------------------------------------------

            start = match.start(1)
            end = start + len(value)

            _add_detection(
                detections,

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

                action="PSEUDONYMIZE",
            )


    # ========================================================
    # PROJECT
    # ========================================================

    for pattern in PROJECT_PATTERNS:

        for match in pattern.finditer(text):

            value = match.group(1).strip()

            _add_detection(
                detections,

                kind="PROJECT_NAME",

                value=value,

                category="CONFIDENTIAL_INFORMATION",

                confidence=0.74,

                risk="HIGH",

                reason=(
                    "A project name was detected. "
                    "Project names may contain confidential "
                    "business or development information."
                ),

                start=match.start(1),

                end=match.end(1),

                action="ASK_USER",
            )


    # ========================================================
    # RECIPIENT / PERSON
    # ========================================================

    for pattern in RECIPIENT_PATTERNS:

        for match in pattern.finditer(text):

            value = match.group(1).strip()

            _add_detection(
                detections,

                kind="PERSON_NAME",

                value=value,

                category="PERSONAL_IDENTITY",

                confidence=0.78,

                risk="MEDIUM",

                reason=(
                    "The surrounding language suggests "
                    "this is the name of another person."
                ),

                start=match.start(1),

                end=match.end(1),

                action="ASK_USER",
            )


    # ========================================================
    # REPEATED PERSON IDENTITY
    # ========================================================
    #
    # This MUST happen before returning.
    #
    # Example:
    #
    # My name is Sreehari.
    # Sreehari wishes to join Cisco.
    #
    # Both occurrences become PERSON_NAME.
    # ========================================================

    _propagate_person_names(
        text,
        detections,
    )


    return detections