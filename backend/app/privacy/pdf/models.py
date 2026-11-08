from typing import Literal

from pydantic import BaseModel


class PdfRegion(BaseModel):

    id: str
    page: int          # 0-based

    type: str
    label: str
    confidence: float

    # Position in points, in the page as displayed (rotation applied).
    x: float
    y: float
    width: float
    height: float

    source: str

    # The detected text. Shown only in the local UI.
    text: str | None = None

    # BLOCK regions (secrets) are ALWAYS redacted.
    recommended_action: Literal["REDACT", "BLOCK"] = "REDACT"


class PdfPage(BaseModel):

    page: int
    width: float
    height: float
    scanned: bool
    image_base64: str


class PdfAnalysis(BaseModel):

    page_count: int
    pages: list[PdfPage]
    regions: list[PdfRegion]

    metadata: dict[str, str]
    notes: list[str]
