import base64

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.ai.gemini import generate_with_image
from app.debug import debug
from app.privacy.image.service import analyze_image, prepare_image
from app.privacy.pseudonymizer import restore_text
from app.privacy.response_guard import verify_response
from app.privacy.service import analyze, sanitize
from app.privacy.vault import create_session, delete_session, get_session


router = APIRouter()

MAX_BYTES = 8 * 1024 * 1024
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _read_upload(file: UploadFile) -> bytes:

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Only PNG, JPEG or WebP images are supported.")

    data = file.file.read(MAX_BYTES + 1)

    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image is larger than 8 MB.")

    if not data:
        raise HTTPException(400, "The uploaded file is empty.")

    return data


@router.post("/analyze")
def analyze_endpoint(file: UploadFile = File(...)):

    data = _read_upload(file)

    try:
        return analyze_image(data)
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.post("/prepare")
def prepare_endpoint(
    file: UploadFile = File(...),
    selected_ids: str = Form(""),
):

    data = _read_upload(file)

    ids = [item for item in selected_ids.split(",") if item]

    try:
        # Detection is deterministic, so region IDs match /analyze.
        result = analyze_image(data)
        protected = prepare_image(data, result.regions, ids)
    except ValueError as error:
        raise HTTPException(400, str(error))

    session_id = create_session(
        original_text="",
        sanitized_text="",
        aliases=[],
        image_bytes=protected,
    )

    forced = sum(1 for r in result.regions if r.recommended_action == "BLOCK")

    return {
        "session_id": session_id,
        "image_base64": base64.b64encode(protected).decode("ascii"),
        "width": result.width,
        "height": result.height,
        "forced_redactions": forced,
    }


class ImageSendRequest(BaseModel):
    session_id: str
    prompt: str = ""


@router.post("/send")
def send_endpoint(request: ImageSendRequest):

    session = get_session(request.session_id)

    if not session or not session.image_bytes:
        raise HTTPException(
            404,
            "Image session expired or does not exist. "
            "Please create the protected preview again.",
        )

    prompt = request.prompt.strip() or "Describe this image."

    # The question is protected by the same text pipeline.
    detections = analyze(prompt)

    if any(d.recommended_action == "BLOCK" for d in detections):
        raise HTTPException(
            400,
            "Your question contains a secret or credential. "
            "Remove it and try again.",
        )

    sanitized_prompt, aliases = sanitize(
        prompt, detections, [d.id for d in detections]
    )

    debug("[OBSCURA] image prompt sent:", sanitized_prompt)

    try:
        ai_response = generate_with_image(sanitized_prompt, session.image_bytes)

        guard = verify_response(ai_response, aliases)

        if not guard["safe"]:
            delete_session(request.session_id)
            raise HTTPException(
                502,
                "The AI response appeared to contain original private "
                "information. OBSCURA blocked the response.",
            )

        restored = restore_text(ai_response, aliases)

        delete_session(request.session_id)

        return {"response": restored}

    except HTTPException:
        raise

    except Exception as error:
        print(f"[OBSCURA] Gemini image request failed: {type(error).__name__}")
        raise HTTPException(502, f"Gemini request failed: {error}")
