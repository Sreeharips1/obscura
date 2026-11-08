from pydantic import BaseModel
from typing import Literal


class ImageRegion(BaseModel):

    id: str
    type: str
    label: str
    confidence: float

    x: int
    y: int
    width: int
    height: int

    source: str

    # Text found in the region (OCR hits only). Shown locally in the UI.
    text: str | None = None

    # BLOCK regions are ALWAYS redacted, whatever the user selects.
    recommended_action: Literal[
        "REDACT",
        "BLUR",
        "PSEUDONYMIZE",
        "BLOCK",
        "ASK_USER",
    ] = "ASK_USER"


class ImageDetectionResult(BaseModel):

    width: int
    height: int
    regions: list[ImageRegion]
