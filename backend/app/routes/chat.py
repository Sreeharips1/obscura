from fastapi import APIRouter, HTTPException

from app.ai.gemini import generate_text
from app.debug import debug
from app.models import SendRequest, SendResponse
from app.privacy.pseudonymizer import restore_text
from app.privacy.response_guard import verify_response
from app.privacy.vault import get_session, delete_session


router = APIRouter()


@router.post("/send", response_model=SendResponse)
def send_to_ai(request: SendRequest):

    session = get_session(request.session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=(
                "Privacy session expired or does not exist. "
                "Please create the protected preview again."
            ),
        )

    # Only visible when OBSCURA_DEBUG=1. This is the sanitized
    # text, which is what Gemini receives.
    debug("\n========== OBSCURA -> AI ==========")
    debug(session.sanitized_text)
    debug("===================================\n")

    try:

        ai_response = generate_text(session.sanitized_text)

        # ----------------------------------------------------
        # RESPONSE PRIVACY CHECK
        # ----------------------------------------------------

        guard_result = verify_response(ai_response, session.aliases)

        if not guard_result["safe"]:

            leaked_types = [
                leak["type"] for leak in guard_result["potential_leaks"]
            ]

            # Log only the TYPES, never the original values.
            print(
                "[OBSCURA SECURITY] Potential private-data leak "
                f"detected in AI response. Types: {leaked_types}"
            )

            delete_session(request.session_id)

            raise HTTPException(
                status_code=502,
                detail=(
                    "The AI response appeared to contain original "
                    "private information. OBSCURA blocked the response."
                ),
            )

        # ----------------------------------------------------
        # RESTORE ORIGINAL VALUES
        # ----------------------------------------------------

        restored_response = restore_text(ai_response, session.aliases)

        delete_session(request.session_id)

        return SendResponse(response=restored_response)

    except HTTPException:
        raise

    except Exception as error:

        print(f"[OBSCURA] Gemini request failed: {type(error).__name__}")
        debug(repr(error))

        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed: {error}",
        )
