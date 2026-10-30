from pydantic import BaseModel, Field
from typing import Literal


class Detection(BaseModel):
    id: str

    type: str
    value: str
    category: str

    confidence: float
    risk: str

    reason: str

    start: int
    end: int

    recommended_action: str

    source: str = "UNKNOWN"

    evidence: list[str] = Field(
        default_factory=list
    )

    entity_key: str | None = None

    occurrences: list[tuple[int, int]] = Field(
        default_factory=list
    )


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    text: str
    detections: list[Detection]


class PrepareRequest(BaseModel):
    text: str
    selected_detection_ids: list[str]


class AliasItem(BaseModel):
    detection_id: str
    original: str
    alias: str
    type: str


class AliasPreview(BaseModel):
    type: str
    original: str
    alias: str


class PrepareResponse(BaseModel):
    session_id: str
    original_text: str
    sanitized_text: str
    aliases: list[AliasPreview]

    blocked: bool = False

    warning: str | None = None


class SendRequest(BaseModel):
    session_id: str


class SendResponse(BaseModel):
    response: str


class ClearRequest(BaseModel):
    session_id: str