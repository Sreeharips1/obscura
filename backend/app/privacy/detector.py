from app.models import Detection

from app.privacy.detectors.patterns import (
    detect_patterns,
)

from app.privacy.detectors.secrets import (
    detect_secrets,
)

from app.privacy.detectors.context import (
    detect_context,
)

from app.privacy.detectors.contextual import (
    detect_contextual,
)

from app.privacy.detectors.ner import (
    detect_ner,
)

from app.privacy.detectors.pii_model import (
    detect_pii,
)

from app.privacy.entity_fusion import (
    fuse_detections,
)

from app.privacy.overlap_resolver import (
    resolve_overlaps,
)


def detect_text(
    text: str,
) -> list[Detection]:

    detections = []


    # ========================================================
    # LAYER 1
    # STRUCTURED PATTERNS
    # ========================================================

    detections.extend(
        detect_patterns(text)
    )


    # ========================================================
    # LAYER 2
    # SECURITY SECRETS
    # ========================================================

    detections.extend(
        detect_secrets(text)
    )


    # ========================================================
    # LAYER 3
    # CONFIDENTIAL LANGUAGE
    # ========================================================

    detections.extend(
        detect_context(text)
    )


    # ========================================================
    # LAYER 4
    # CONTEXTUAL INFORMATION
    # ========================================================

    detections.extend(
        detect_contextual(text)
    )


    # ========================================================
    # LAYER 5
    # EXISTING NER
    # ========================================================

    detections.extend(
        detect_ner(text)
    )


    # ========================================================
    # LAYER 6
    # PRETRAINED PII MODEL
    # ========================================================

    detections.extend(
        detect_pii(text)
    )


    # ========================================================
    # DEBUG: BEFORE FUSION
    # ========================================================

    print(
        "\n========== BEFORE FUSION =========="
    )

    for detection in detections:

        print(
            f"{detection.type:20} | "
            f"{detection.value:30} | "
            f"{detection.source:15} | "
            f"{detection.confidence:.2f} | "
            f"{detection.start}:{detection.end}"
        )

    print(
        "===================================\n"
    )


    # ========================================================
    # ENTITY FUSION
    # ========================================================

    detections = fuse_detections(
        detections
    )


    # ========================================================
    # DEBUG: AFTER FUSION
    # ========================================================

    print(
        "\n========== AFTER FUSION =========="
    )

    for detection in detections:

        print(
            f"{detection.type:20} | "
            f"{detection.value:30} | "
            f"{detection.source:15} | "
            f"{detection.confidence:.2f} | "
            f"{detection.start}:{detection.end} | "
            f"{detection.evidence}"
        )

    print(
        "==================================\n"
    )


    # ========================================================
    # OVERLAP RESOLUTION
    # ========================================================

    detections = resolve_overlaps(
        detections
    )


    # ========================================================
    # FINAL RESULT
    # ========================================================

    return detections