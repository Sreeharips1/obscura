import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)


# ============================================================
# OBSCURA AI INSTRUCTION
# ============================================================
#
# IMPORTANT:
#
# The external AI must ONLY receive the protected text.
#
# The instruction below contains NO original private values.
#
# OBSCURA tokens represent private information that exists
# only inside the OBSCURA backend.
#
# ============================================================

OBSCURA_INSTRUCTION = """
You are operating behind OBSCURA, a privacy-preserving AI
gateway.

The user message below may contain placeholders such as:

<OBSCURA_NAME_001>
<OBSCURA_EMAIL_001>
<OBSCURA_PHONE_001>
<OBSCURA_ADDRESS_001>
<OBSCURA_ORG_001>
<OBSCURA_LOCATION_001>

These placeholders represent private information that has
been removed from the request before it reached you.

IMPORTANT RULES:

1. Treat every OBSCURA placeholder as a meaningful entity.

2. Do NOT interpret the placeholder literally as a person's
   name, organization name, email address, phone number, etc.

3. Preserve every OBSCURA placeholder exactly.

4. Never rename, modify, split, combine, or delete an
   OBSCURA placeholder.

5. If a placeholder represents a person's name, use it
   naturally wherever the person's name belongs.

6. If a placeholder represents an email address, use it
   naturally wherever an email address belongs.

7. If a placeholder represents a phone number, use it
   naturally wherever a phone number belongs.

8. If a placeholder represents an organization, use it
   naturally wherever the organization name belongs.

9. Do not attempt to guess or reconstruct the original
   private information.

10. Do not mention these privacy instructions in your answer.

11. Do not explain that placeholders are being used unless
    the user explicitly asks about them.

12. Complete the user's requested task normally.

13. Keep placeholders exactly as written so OBSCURA can
    safely restore the original private information after
    your response.

USER REQUEST:

"""


def generate_text(
    prompt: str,
) -> str:

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )


    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Put it in backend/.env."
        )


    client = genai.Client(
        api_key=api_key
    )


    protected_prompt = (
        OBSCURA_INSTRUCTION
        + prompt
    )


    response = client.models.generate_content(
        model=MODEL,
        contents=protected_prompt,
    )


    return response.text or ""