from pydantic import BaseModel
from typing import Literal


# ============================================================
# IMAGE REGION
# ============================================================

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

    recommended_action: Literal[
        "PSEUDONYMIZE",
        "BLUR",
        "BLOCK",
        "ASK_USER",
    ] = "ASK_USER"


# ============================================================
# IMAGE DETECTION RESULT
# ============================================================

class ImageDetectionResult(BaseModel):

    width: int

    height: int

    regions: list[ImageRegion]