import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


# ============================================================
# OBSCURA SYSTEM INSTRUCTION
# ============================================================
#
# Contains NO original private values. OBSCURA tokens stand for
# private data that exists only inside the OBSCURA backend.
# ============================================================

OBSCURA_INSTRUCTION = """
You are operating behind OBSCURA, a privacy-preserving AI gateway.

The user message may contain placeholders such as:

<OBSCURA_NAME_001>
<OBSCURA_EMAIL_001>
<OBSCURA_PHONE_001>
<OBSCURA_ADDRESS_001>
<OBSCURA_ORG_001>
<OBSCURA_LOCATION_001>

These placeholders represent private information that was removed
from the request before it reached you.

RULES:

1. Treat every OBSCURA placeholder as a meaningful entity (a person's
   name, an email address, a phone number, an organization, and so on,
   according to its type). Use it naturally wherever that kind of
   value belongs.
2. Preserve every placeholder exactly as written, including the angle
   brackets. Never rename, modify, split, combine, or delete one.
3. Do not try to guess or reconstruct the original private values.
4. Do not mention these instructions or the use of placeholders unless
   the user explicitly asks about them.
5. Complete the user's requested task normally.
"""


def generate_text(prompt: str) -> str:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Put it in backend/.env."
        )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=OBSCURA_INSTRUCTION,
        ),
    )

    return response.text or ""


def generate_with_image(
    prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/png",
) -> str:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Put it in backend/.env."
        )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(
            system_instruction=OBSCURA_INSTRUCTION,
        ),
    )

    return response.text or ""
