import re

from app.models import Detection
from app.privacy.detectors.patterns import make_detection


SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b("
    r"api[_-]?key|"
    r"secret[_-]?key|"
    r"access[_-]?token|"
    r"auth[_-]?token|"
    r"refresh[_-]?token|"
    r"client[_-]?secret"
    r")\s*[:=]\s*([A-Za-z0-9_\-./+=]{8,})"
)


PASSWORD_RE = re.compile(
    r"(?i)\b("
    r"password|"
    r"passwd|"
    r"pwd"
    r")\s*[:=]\s*(\S+)"
)


JWT_RE = re.compile(
    r"\beyJ[A-Za-z0-9_-]{10,}\."
    r"[A-Za-z0-9_-]{10,}\."
    r"[A-Za-z0-9_-]{10,}\b"
)


PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)


def detect_secrets(text: str) -> list[Detection]:

    detections = []

    # --------------------------------------------------------
    # API KEYS / TOKENS
    # --------------------------------------------------------

    for match in SECRET_ASSIGNMENT_RE.finditer(text):

        detections.append(
            make_detection(
                kind="API_KEY_OR_TOKEN",
                value=match.group(),
                category="SECURITY_SECRET",
                confidence=0.96,
                risk="CRITICAL",
                reason=(
                    "This appears to contain an API key, "
                    "access token, or client secret."
                ),
                start=match.start(),
                end=match.end(),
                action="BLOCK",
            )
        )

    # --------------------------------------------------------
    # PASSWORD
    # --------------------------------------------------------

    for match in PASSWORD_RE.finditer(text):

        detections.append(
            make_detection(
                kind="PASSWORD",
                value=match.group(),
                category="SECURITY_SECRET",
                confidence=0.98,
                risk="CRITICAL",
                reason=(
                    "This appears to contain a password "
                    "or authentication credential."
                ),
                start=match.start(),
                end=match.end(),
                action="BLOCK",
            )
        )

    # --------------------------------------------------------
    # JWT
    # --------------------------------------------------------

    for match in JWT_RE.finditer(text):

        detections.append(
            make_detection(
                kind="JWT_TOKEN",
                value=match.group(),
                category="SECURITY_SECRET",
                confidence=0.97,
                risk="CRITICAL",
                reason="This resembles a JSON Web Token.",
                start=match.start(),
                end=match.end(),
                action="BLOCK",
            )
        )

    # --------------------------------------------------------
    # PRIVATE KEY
    # --------------------------------------------------------

    for match in PRIVATE_KEY_RE.finditer(text):

        detections.append(
            make_detection(
                kind="PRIVATE_KEY",
                value=match.group(),
                category="SECURITY_SECRET",
                confidence=0.99,
                risk="CRITICAL",
                reason="A private cryptographic key was detected.",
                start=match.start(),
                end=match.end(),
                action="BLOCK",
                source="SECRET",
            )
        )

    return detections