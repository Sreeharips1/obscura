from fastapi import APIRouter

from app.debug import debug
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    PrepareRequest,
    PrepareResponse,
    AliasPreview,
    ClearRequest,
)
from app.privacy.service import analyze, sanitize
from app.privacy.vault import create_session, delete_session


router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_text(request: AnalyzeRequest):

    detections = analyze(request.text)

    return AnalyzeResponse(
        text=request.text,
        detections=detections,
    )


@router.post("/prepare", response_model=PrepareResponse)
def prepare_text(request: PrepareRequest):

    detections = analyze(request.text)

    # --------------------------------------------------------
    # BLOCK SECRETS
    #
    # IMPORTANT: check ALL detections, not only the selected
    # ones. The UI never lets the user select BLOCK items, so
    # checking only the selection would let secrets through.
    # --------------------------------------------------------

    blocked = [
        detection
        for detection in detections
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
    # Only keep selected IDs that really exist.
    # --------------------------------------------------------

    known_ids = {detection.id for detection in detections}

    selected_ids = [
        detection_id
        for detection_id in request.selected_detection_ids
        if detection_id in known_ids
    ]

    ignored = len(request.selected_detection_ids) - len(selected_ids)

    if ignored:
        debug(f"[OBSCURA] {ignored} selected detection IDs were not found.")

    # --------------------------------------------------------
    # SANITIZE
    # --------------------------------------------------------

    sanitized_text, aliases = sanitize(
        request.text,
        detections,
        selected_ids,
    )

    debug(
        "[OBSCURA] prepare:",
        f"{len(detections)} detections,",
        f"{len(aliases)} aliases",
    )

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

    return {"cleared": True}
