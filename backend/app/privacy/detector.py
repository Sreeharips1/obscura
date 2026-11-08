from app.debug import debug
from app.models import Detection

from app.privacy.detectors.patterns import detect_patterns
from app.privacy.detectors.secrets import detect_secrets
from app.privacy.detectors.context import detect_context
from app.privacy.detectors.contextual import detect_contextual
from app.privacy.detectors.ner import detect_ner
from app.privacy.detectors.pii_model import detect_pii

from app.privacy.entity_fusion import fuse_detections
from app.privacy.overlap_resolver import resolve_overlaps


def _run(name: str, function, text: str) -> list[Detection]:
    # One broken optional detector (for example a missing model)
    # must not take the whole pipeline down. The warning is always
    # printed so you notice that protection is reduced.
    try:
        return function(text)
    except Exception as error:
        print(
            f"[OBSCURA WARNING] {name} detector failed "
            f"({type(error).__name__}). Continuing without it."
        )
        debug(repr(error))
        return []


def _dump(title: str, detections: list[Detection]) -> None:
    # Values are intentionally NOT printed.
    debug(f"\n========== {title} ==========")
    for d in detections:
        debug(
            f"{d.type:20} | {d.source:15} | "
            f"{d.confidence:.2f} | {d.start}:{d.end}"
        )
    debug("===================================\n")


def detect_text(text: str) -> list[Detection]:

    detections: list[Detection] = []

    detections.extend(_run("pattern", detect_patterns, text))
    detections.extend(_run("secret", detect_secrets, text))
    detections.extend(_run("confidential-context", detect_context, text))
    detections.extend(_run("contextual", detect_contextual, text))
    detections.extend(_run("ner", detect_ner, text))
    detections.extend(_run("pii-model", detect_pii, text))

    _dump("BEFORE FUSION", detections)

    detections = fuse_detections(detections)

    _dump("AFTER FUSION", detections)

    detections = resolve_overlaps(detections)

    return detections
