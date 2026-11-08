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


def detect_context(text: str) -> list[Detection]:

    detections = []

    for pattern in CONFIDENTIAL_PATTERNS:

        for match in re.finditer(pattern, text, re.IGNORECASE):

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
