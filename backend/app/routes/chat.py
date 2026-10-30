from fastapi import APIRouter, HTTPException

from app.models import (
    SendRequest,
    SendResponse,
)

from app.ai.gemini import generate_text

from app.privacy.pseudonymizer import (
    restore_text,
)

from app.privacy.vault import (
    get_session,
    delete_session,
)

from app.privacy.response_guard import (
    verify_response,
)


router = APIRouter()


@router.post(
    "/send",
    response_model=SendResponse,
)
def send_to_ai(
    request: SendRequest,
):

    # ========================================================
    # GET PRIVACY SESSION
    # ========================================================

    session = get_session(
        request.session_id
    )

    if not session:

        raise HTTPException(
            status_code=404,
            detail=(
                "Privacy session expired "
                "or does not exist. "
                "Please create the protected "
                "preview again."
            ),
        )


    # ========================================================
    # SHOW EXACT PROTECTED REQUEST
    # ========================================================
    #
    # This is ONLY printed in the local development
    # terminal.
    #
    # This lets us verify that the original private
    # information is NOT being sent to Gemini.
    #
    # ========================================================

    print(
        "\n========== OBSCURA → AI =========="
    )

    print(
        session.sanitized_text
    )

    print(
        "===================================\n"
    )


    try:

        # ====================================================
        # GEMINI RECEIVES ONLY SANITIZED TEXT
        # ====================================================

        ai_response = generate_text(
            session.sanitized_text
        )


        # ====================================================
        # RESPONSE PRIVACY CHECK
        # ====================================================
        #
        # Check whether Gemini accidentally included
        # any original private values in its response.
        #
        # Example:
        #
        # Original:
        # xhari@gmail.com
        #
        # Protected:
        # <OBSCURA_EMAIL_001>
        #
        # If Gemini somehow returns:
        #
        # xhari@gmail.com
        #
        # the response guard will detect it.
        #
        # ====================================================

        guard_result = verify_response(
            ai_response,
            session.aliases,
        )


        if not guard_result["safe"]:

            print(
                "\n[OBSCURA SECURITY] "
                "Potential private-data leak detected."
            )

            print(
                "[OBSCURA SECURITY] "
                "Potential leaks:"
            )

            print(
                guard_result[
                    "potential_leaks"
                ]
            )

            # ------------------------------------------------
            # Delete the temporary privacy session.
            #
            # We don't want to keep the original-to-alias
            # mapping after a security failure.
            # ------------------------------------------------

            delete_session(
                request.session_id
            )


            raise HTTPException(
                status_code=502,
                detail=(
                    "The AI response appeared to "
                    "contain original private "
                    "information. OBSCURA blocked "
                    "the response."
                ),
            )


        # ====================================================
        # RESTORE ORIGINAL VALUES
        # ====================================================
        #
        # Example:
        #
        # Gemini:
        #
        # Please contact
        # <OBSCURA_EMAIL_001>
        #
        # OBSCURA:
        #
        # Please contact
        # xhari@gmail.com
        #
        # ====================================================

        restored_response = restore_text(
            ai_response,
            session.aliases,
        )


        # ====================================================
        # DELETE TEMPORARY PRIVACY SESSION
        # ====================================================
        #
        # The mapping is no longer required after the
        # response has been restored.
        #
        # ====================================================

        delete_session(
            request.session_id
        )


        # ====================================================
        # RETURN RESTORED RESPONSE
        # ====================================================

        return SendResponse(
            response=restored_response
        )


    # ========================================================
    # HTTP EXCEPTIONS
    # ========================================================

    except HTTPException:
        # Don't convert our intentional HTTPException
        # into another 502.

        raise


    # ========================================================
    # UNEXPECTED ERRORS
    # ========================================================

    except Exception as error:

        print(
            "\n========== GEMINI ERROR =========="
        )

        print(
            repr(error)
        )

        print(
            "==================================\n"
        )


        raise HTTPException(
            status_code=502,
            detail=(
                f"Gemini request failed: {error}"
            ),
        )