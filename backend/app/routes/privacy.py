from fastapi import APIRouter

from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    PrepareRequest,
    PrepareResponse,
    AliasPreview,
    ClearRequest,
)

from app.privacy.service import analyze, sanitize

from app.privacy.vault import (
    create_session,
    delete_session,
)


router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalyzeResponse
)
def analyze_text(request: AnalyzeRequest):

    detections = analyze(request.text)

    return AnalyzeResponse(
        text=request.text,
        detections=detections
    )


@router.post(
    "/prepare",
    response_model=PrepareResponse
)
def prepare_text(request: PrepareRequest):

    detections = analyze(
        request.text
    )

    selected = [
        detection
        for detection in detections
        if detection.id in request.selected_detection_ids
    ]

    # --------------------------------------------------------
    # DEBUG / SAFETY CHECK
    # --------------------------------------------------------

    missing_ids = [
        detection_id
        for detection_id in request.selected_detection_ids
        if detection_id not in {
            detection.id
            for detection in detections
        }
    ]

    if missing_ids:

        print(
            "WARNING: Some selected detection IDs "
            "were not found:",
            missing_ids
        )

    # --------------------------------------------------------
    # BLOCK SECRETS
    # --------------------------------------------------------

    blocked = [
        detection
        for detection in selected
        if detection.recommended_action == "BLOCK"
    ]

    if blocked:

        return PrepareResponse(
            session_id="",
            original_text=request.text,
            sanitized_text="",
            aliases=[],
            blocked=True,
            warning=(
                "A credential or secret was detected. "
                "Remove it before sending this request "
                "to an external AI."
            ),
        )

    # --------------------------------------------------------
    # SANITIZE
    # --------------------------------------------------------

    sanitized_text, aliases = sanitize(
        request.text,
        detections,
        request.selected_detection_ids,
    )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print("\n========== OBSCURA PREPARE ==========")

    print("Original:")
    print(request.text)

    print("\nSelected IDs:")
    print(request.selected_detection_ids)

    print("\nDetected:")
    for detection in detections:
        print(
            detection.id,
            "|",
            detection.type,
            "|",
            detection.value
        )

    print("\nAliases:")
    for alias in aliases:
        print(
            alias.original,
            "->",
            alias.alias
        )

    print("\nSanitized:")
    print(sanitized_text)

    print("=====================================\n")

    # --------------------------------------------------------
    # CREATE PRIVACY VAULT SESSION
    # --------------------------------------------------------

    session_id = create_session(
        original_text=request.text,
        sanitized_text=sanitized_text,
        aliases=aliases,
    )

    previews = [
        AliasPreview(
            type=alias.type,
            original=alias.original,
            alias=alias.alias,
        )
        for alias in aliases
    ]

    return PrepareResponse(
        session_id=session_id,
        original_text=request.text,
        sanitized_text=sanitized_text,
        aliases=previews,
    )


@router.post("/clear")
def clear_session(request: ClearRequest):

    delete_session(request.session_id)

    return {
        "cleared": True
    }