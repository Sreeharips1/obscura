import base64

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.ai.gemini import generate_with_image
from app.debug import debug
from app.privacy.pdf.service import analyze_pdf, prepare_pdf
from app.privacy.pseudonymizer import restore_text
from app.privacy.response_guard import verify_response
from app.privacy.service import analyze, sanitize
from app.privacy.vault import create_session, delete_session, get_session


router = APIRouter()

MAX_BYTES = 20 * 1024 * 1024


def _read_pdf(file: UploadFile) -> bytes:

    data = file.file.read(MAX_BYTES + 1)

    if len(data) > MAX_BYTES:
        raise HTTPException(413, "PDF is larger than 20 MB.")

    if not data.startswith(b"%PDF"):
        raise HTTPException(415, "Only PDF files are supported.")

    return data


@router.post("/analyze")
def analyze_endpoint(file: UploadFile = File(...)):

    data = _read_pdf(file)

    try:
        return analyze_pdf(data)
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.post("/prepare")
def prepare_endpoint(
    file: UploadFile = File(...),
    selected_ids: str = Form(""),
):

    data = _read_pdf(file)

    ids = [item for item in selected_ids.split(",") if item]

    try:
        result = prepare_pdf(data, ids)
    except ValueError as error:
        raise HTTPException(400, str(error))

    session_id = create_session(
        original_text="",
        sanitized_text="",
        aliases=[],
        image_bytes=result["pdf_bytes"],
    )

    return {
        "session_id": session_id,
        "pdf_base64": base64.b64encode(result["pdf_bytes"]).decode("ascii"),
        "pages": result["pages"],
        "redacted": result["redacted"],
        "forced_redactions": result["forced"],
        "still_visible": result["still_visible"],
    }


class PdfSendRequest(BaseModel):
    session_id: str
    prompt: str = ""


@router.post("/send")
def send_endpoint(request: PdfSendRequest):

    session = get_session(request.session_id)

    if not session or not session.image_bytes:
        raise HTTPException(
            404,
            "PDF session expired or does not exist. "
            "Please create the protected copy again.",
        )

    prompt = request.prompt.strip() or "Summarize this document."

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

    debug("[OBSCURA] pdf prompt sent:", sanitized_prompt)

    try:
        ai_response = generate_with_image(
            sanitized_prompt,
            session.image_bytes,
            mime_type="application/pdf",
        )

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
        print(f"[OBSCURA] Gemini PDF request failed: {type(error).__name__}")
        raise HTTPException(502, f"Gemini request failed: {error}")
