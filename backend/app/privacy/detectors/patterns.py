import re
import hashlib

from app.models import Detection


# ============================================================
# BASIC PERSONAL / CONTACT INFORMATION
# ============================================================

EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)"
)


# ============================================================
# INDIAN IDENTIFIERS
# ============================================================

AADHAAR_RE = re.compile(
    r"(?<!\d)(?:\d{4}[\s-]\d{4}[\s-]\d{4})(?!\d)"
)

PAN_RE = re.compile(
    r"(?<![A-Z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Z0-9])",
    re.IGNORECASE
)


# ============================================================
# FINANCIAL
# ============================================================

IFSC_RE = re.compile(
    r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    re.IGNORECASE
)

UPI_RE = re.compile(
    r"\b[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}"
    r"(?!\.[A-Za-z]{2,})\b"
)

CARD_RE = re.compile(
    r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"
)


# ============================================================
# DIGITAL IDENTIFIERS
# ============================================================

IPV4_RE = re.compile(
    r"\b(?:"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\."
    r"){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"\b"
)

MAC_RE = re.compile(
    r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"
)

IMEI_RE = re.compile(
    r"(?<!\d)\d{15}(?!\d)"
)


# ============================================================
# URLS
# ============================================================

URL_RE = re.compile(
    r"\bhttps?://[^\s<>\"]+",
    re.IGNORECASE
)


# ============================================================
# CONTEXTUAL PERSON NAME
# ============================================================

NAME_CONTEXT_RE = re.compile(
    r"(?i)\b(?:my\s+name\s+is|name\s*[:=])\s*"
    r"([A-Z][A-Za-z]{2,}(?:\s+[A-Z][A-Za-z]{2,})*)"
)


# ============================================================
# ADDRESS CONTEXT
# ============================================================

ADDRESS_CONTEXT_RE = re.compile(
    r"(?i)\b(?:"
    r"address|home\s+address|residing\s+at|lives?\s+at"
    r")\s*[:=-]?\s*"
    r"([^.;\n]{8,})"
)


def make_detection(
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
    source: str = "PATTERN",
) -> Detection:
    
     # --------------------------------------------------------
    # IMPORTANT
    #
    # Detection IDs must remain stable.
    #
    # /analyze and /prepare both run detection.
    # If we generate a random UUID each time, the IDs from
    # /analyze won't match the IDs from /prepare.
    #
    # Therefore we generate the ID deterministically from:
    #
    # type + value + position
    # --------------------------------------------------------

    raw_id = (
        f"{kind}|"
        f"{value}|"
        f"{start}|"
        f"{end}"
    )

    detection_id = hashlib.sha256(
        raw_id.encode("utf-8")
    ).hexdigest()[:24]

    return Detection(
        id=detection_id,
        type=kind,
        value=value,
        category=category,
        confidence=confidence,
        risk=risk,
        reason=reason,
        start=start,
        end=end,
        recommended_action=action,
        source=source,
        evidence=[source],
    )


def detect_patterns(text: str) -> list[Detection]:

    detections = []

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    for match in EMAIL_RE.finditer(text):

        detections.append(
            make_detection(
                kind="EMAIL",
                value=match.group(),
                category="CONTACT_INFORMATION",
                confidence=0.99,
                risk="HIGH",
                reason=(
                    "Email addresses can directly identify "
                    "or contact a person."
                ),
                start=match.start(),
                end=match.end(),
                action="PSEUDONYMIZE",
            )
        )

    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    for match in PHONE_RE.finditer(text):

        value = match.group().strip()
        digits = re.sub(r"\D", "", value)

        if 9 <= len(digits) <= 15:

            detections.append(
                make_detection(
                    kind="PHONE",
                    value=value,
                    category="CONTACT_INFORMATION",
                    confidence=0.95,
                    risk="HIGH",
                    reason=(
                        "This appears to be a phone number "
                        "and may directly identify or contact someone."
                    ),
                    start=match.start(),
                    end=match.end(),
                    action="PSEUDONYMIZE",
                )
            )

    # --------------------------------------------------------
    # AADHAAR
    # --------------------------------------------------------

    for match in AADHAAR_RE.finditer(text):

        detections.append(
            make_detection(
                kind="AADHAAR_LIKE",
                value=match.group(),
                category="GOVERNMENT_IDENTIFIER",
                confidence=0.90,
                risk="CRITICAL",
                reason=(
                    "This matches an Aadhaar-like 12-digit "
                    "identifier format."
                ),
                start=match.start(),
                end=match.end(),
                action="REPLACE",
            )
        )

    # --------------------------------------------------------
    # PAN
    # --------------------------------------------------------

    for match in PAN_RE.finditer(text):

        detections.append(
            make_detection(
                kind="PAN_LIKE",
                value=match.group(),
                category="GOVERNMENT_IDENTIFIER",
                confidence=0.90,
                risk="CRITICAL",
                reason=(
                    "This matches an Indian PAN-like "
                    "identifier format."
                ),
                start=match.start(),
                end=match.end(),
                action="REPLACE",
            )
        )

    # --------------------------------------------------------
    # IFSC
    # --------------------------------------------------------

    for match in IFSC_RE.finditer(text):

        detections.append(
            make_detection(
                kind="IFSC_CODE",
                value=match.group(),
                category="FINANCIAL_INFORMATION",
                confidence=0.90,
                risk="HIGH",
                reason="This appears to be an Indian bank IFSC code.",
                start=match.start(),
                end=match.end(),
                action="PSEUDONYMIZE",
            )
        )

    # --------------------------------------------------------
    # UPI
    # --------------------------------------------------------

    for match in UPI_RE.finditer(text):

        value = match.group()

        # Don't classify ordinary email addresses twice.
        if EMAIL_RE.fullmatch(value):
            continue

        detections.append(
            make_detection(
                kind="UPI_ID",
                value=value,
                category="FINANCIAL_INFORMATION",
                confidence=0.70,
                risk="HIGH",
                reason=(
                    "This may be a UPI identifier. "
                    "Context is required to confirm it."
                ),
                start=match.start(),
                end=match.end(),
                action="PSEUDONYMIZE",
            )
        )

    # --------------------------------------------------------
    # CREDIT / DEBIT CARD
    # --------------------------------------------------------

    for match in CARD_RE.finditer(text):

        value = match.group()
        digits = re.sub(r"\D", "", value)

        if 13 <= len(digits) <= 19:

            detections.append(
                make_detection(
                    kind="CARD_NUMBER_LIKE",
                    value=value,
                    category="FINANCIAL_INFORMATION",
                    confidence=0.75,
                    risk="CRITICAL",
                    reason=(
                        "This resembles a payment card number."
                    ),
                    start=match.start(),
                    end=match.end(),
                    action="REPLACE",
                )
            )

    # --------------------------------------------------------
    # IPV4
    # --------------------------------------------------------

    for match in IPV4_RE.finditer(text):

        detections.append(
            make_detection(
                kind="IP_ADDRESS",
                value=match.group(),
                category="DIGITAL_IDENTIFIER",
                confidence=0.98,
                risk="MEDIUM",
                reason=(
                    "An IP address can reveal information "
                    "about a device or network."
                ),
                start=match.start(),
                end=match.end(),
                action="PSEUDONYMIZE",
            )
        )

    # --------------------------------------------------------
    # MAC ADDRESS
    # --------------------------------------------------------

    for match in MAC_RE.finditer(text):

        detections.append(
            make_detection(
                kind="MAC_ADDRESS",
                value=match.group(),
                category="DIGITAL_IDENTIFIER",
                confidence=0.98,
                risk="HIGH",
                reason="This appears to be a device MAC address.",
                start=match.start(),
                end=match.end(),
                action="REPLACE",
            )
        )

    # --------------------------------------------------------
    # IMEI
    # --------------------------------------------------------

    for match in IMEI_RE.finditer(text):

        value = match.group()

        # Avoid treating ordinary 15-digit numbers as IMEI
        # unless nearby context mentions IMEI/device.
        window = text[
            max(0, match.start() - 30):
            min(len(text), match.end() + 30)
        ].lower()

        if "imei" in window:

            detections.append(
                make_detection(
                    kind="IMEI",
                    value=value,
                    category="DIGITAL_IDENTIFIER",
                    confidence=0.95,
                    risk="HIGH",
                    reason="This appears to be an IMEI number.",
                    start=match.start(),
                    end=match.end(),
                    action="REPLACE",
                )
            )

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    for match in URL_RE.finditer(text):

        value = match.group()

        # Only flag URLs that look like they may contain
        # private tokens or query parameters.
        lower = value.lower()

        sensitive_terms = [
            "token=",
            "access_token=",
            "session=",
            "key=",
            "password=",
            "auth=",
            "code=",
        ]

        if any(term in lower for term in sensitive_terms):

            detections.append(
                make_detection(
                    kind="SENSITIVE_URL",
                    value=value,
                    category="DIGITAL_SECRET",
                    confidence=0.90,
                    risk="CRITICAL",
                    reason=(
                        "This URL appears to contain a token, "
                        "credential, or authentication parameter."
                    ),
                    start=match.start(),
                    end=match.end(),
                    action="BLOCK",
                )
            )

    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    for match in NAME_CONTEXT_RE.finditer(text):

        value = match.group(1)

        detections.append(
            make_detection(
                kind="PERSON_NAME",
                value=value,
                category="PERSONAL_IDENTITY",
                confidence=0.82,
                risk="MEDIUM",
                reason=(
                    "The text explicitly identifies this "
                    "value as a person's name."
                ),
                start=match.start(1),
                end=match.end(1),
                action="PSEUDONYMIZE",
            )
        )

    # --------------------------------------------------------
    # ADDRESS
    # --------------------------------------------------------

    for match in ADDRESS_CONTEXT_RE.finditer(text):

        value = match.group(1).strip()

        detections.append(
            make_detection(
                kind="ADDRESS",
                value=value,
                category="LOCATION_INFORMATION",
                confidence=0.82,
                risk="HIGH",
                reason=(
                    "The surrounding text indicates that "
                    "this may be a personal address."
                ),
                start=match.start(1),
                end=match.end(1),
                action="PSEUDONYMIZE",
            )
        )

    return detections