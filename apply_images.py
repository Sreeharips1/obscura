# apply_images.py  -- run from the repo root
import os, sys

if not (os.path.isdir("backend/app") and os.path.isdir("frontend/src")):
    sys.exit("Run this from the repo root (the folder containing backend/ and frontend/).")

FILES = {}

# ----------------------------------------------------------------------
FILES["backend/app/privacy/vault.py"] = r'''import time
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class VaultSession:
    original_text: str
    sanitized_text: str
    aliases: list[Any]
    created_at: float
    image_bytes: bytes | None = None


# Temporary in-memory storage for the prototype.
_SESSIONS: dict[str, VaultSession] = {}

TTL_SECONDS = 15 * 60


def create_session(
    original_text: str,
    sanitized_text: str,
    aliases: list[Any],
    image_bytes: bytes | None = None,
) -> str:

    session_id = str(uuid.uuid4())

    _SESSIONS[session_id] = VaultSession(
        original_text=original_text,
        sanitized_text=sanitized_text,
        aliases=aliases,
        created_at=time.time(),
        image_bytes=image_bytes,
    )

    return session_id


def get_session(session_id: str):

    cleanup()

    return _SESSIONS.get(session_id)


def delete_session(session_id: str):

    _SESSIONS.pop(session_id, None)


def cleanup():

    now = time.time()

    expired = [
        sid for sid, s in _SESSIONS.items()
        if now - s.created_at > TTL_SECONDS
    ]

    for sid in expired:
        _SESSIONS.pop(sid, None)
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/image/models.py"] = r'''from pydantic import BaseModel
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
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/image/mapping.py"] = r'''from dataclasses import dataclass


@dataclass
class OcrLine:
    text: str
    x: int
    y: int
    width: int
    height: int
    score: float = 1.0


def build_text(lines: list[OcrLine]):
    """Join OCR lines with newlines and remember each line's span."""

    parts = []
    spans = []
    position = 0

    for line in lines:
        spans.append((position, position + len(line.text), line))
        parts.append(line.text)
        position += len(line.text) + 1

    return "\n".join(parts), spans


def span_boxes(spans, start: int, end: int):
    """
    Map a character range of the joined text back to boxes.

    Character positions are spread evenly across each line's width.
    That is approximate for proportional fonts, so each box is padded.
    """

    boxes = []

    for line_start, line_end, line in spans:

        if end <= line_start or start >= line_end:
            continue

        length = max(len(line.text), 1)

        local_start = max(start, line_start) - line_start
        local_end = min(end, line_end) - line_start

        char_width = line.width / length
        pad_x = max(4, int(char_width * 0.6))
        pad_y = 3

        x1 = line.x + int(line.width * local_start / length) - pad_x
        x2 = line.x + int(line.width * local_end / length) + pad_x

        x1 = max(0, x1)
        y1 = max(0, line.y - pad_y)

        boxes.append((x1, y1, x2 - x1, line.height + 2 * pad_y))

    return boxes
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/image/ocr.py"] = r'''from functools import lru_cache

import numpy as np

from app.privacy.image.mapping import OcrLine


@lru_cache(maxsize=1)
def get_engine():

    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        print(
            "[OBSCURA IMAGE] RapidOCR is not installed. "
            "Run: pip install rapidocr-onnxruntime"
        )
        return None

    print("[OBSCURA IMAGE] Loading OCR engine")
    return RapidOCR()


def run_ocr(image) -> list[OcrLine]:

    engine = get_engine()

    if engine is None:
        return []

    result, _ = engine(image)

    lines = []

    for box, text, score in result or []:

        text = str(text).strip()

        if not text:
            continue

        points = np.array(box, dtype=float)
        x1, y1 = points.min(axis=0)
        x2, y2 = points.max(axis=0)

        lines.append(
            OcrLine(
                text=text,
                x=int(x1),
                y=int(y1),
                width=max(1, int(x2 - x1)),
                height=max(1, int(y2 - y1)),
                score=float(score),
            )
        )

    return lines
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/image/detector.py"] = r'''import hashlib
import re

import cv2

from app.privacy.image.mapping import build_text, span_boxes
from app.privacy.image.models import ImageRegion, ImageDetectionResult
from app.privacy.image.ocr import run_ocr


# Indian-style plate, e.g. KL 07 AB 1234 / MH12DE1433
PLATE_RE = re.compile(
    r"\b[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}\b"
)


def generate_region_id(region_type, x, y, width, height) -> str:

    raw = f"{region_type}:{x}:{y}:{width}:{height}"

    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def make_region(region_type, label, confidence, x, y, width, height,
                source, action="REDACT", text=None) -> ImageRegion:

    return ImageRegion(
        id=generate_region_id(region_type, x, y, width, height),
        type=region_type,
        label=label,
        confidence=round(float(confidence), 2),
        x=int(x),
        y=int(y),
        width=int(width),
        height=int(height),
        source=source,
        text=text,
        recommended_action=action,
    )


def _polygons_to_regions(points, region_type, label, confidence):

    regions = []

    if points is None or len(points) == 0:
        return regions

    for polygon in points:

        if polygon is None:
            continue

        polygon = polygon.astype(int).reshape(-1, 2)

        x = int(polygon[:, 0].min())
        y = int(polygon[:, 1].min())
        width = int(polygon[:, 0].max()) - x
        height = int(polygon[:, 1].max()) - y

        if width <= 0 or height <= 0:
            continue

        regions.append(
            make_region(region_type, label, confidence,
                        x, y, width, height, "OPENCV")
        )

    return regions


# ============================================================
# QR / BARCODE
# ============================================================

def detect_qr_codes(image):

    try:
        ok, points = cv2.QRCodeDetector().detectMulti(image)

        if not ok:
            return []

        return _polygons_to_regions(points, "QR_CODE", "QR code", 0.98)

    except Exception as error:
        print(f"[OBSCURA IMAGE] QR detection error: {error}")
        return []


def _make_barcode_detector():

    module = getattr(cv2, "barcode", None)

    if module is not None and hasattr(module, "BarcodeDetector"):
        return module.BarcodeDetector()

    if hasattr(cv2, "barcode_BarcodeDetector"):
        return cv2.barcode_BarcodeDetector()

    return None


def detect_barcodes(image):

    try:
        detector = _make_barcode_detector()

        if detector is None:
            return []

        result = detector.detect(image)

        if not (isinstance(result, tuple) and len(result) == 2):
            return []

        ok, points = result

        if not ok:
            return []

        return _polygons_to_regions(points, "BARCODE", "Barcode", 0.96)

    except Exception as error:
        print(f"[OBSCURA IMAGE] Barcode detection error: {error}")
        return []


# ============================================================
# FACES (OpenCV Haar cascade: bundled, no download needed)
# ============================================================

def detect_faces(image):

    try:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(path)

        if cascade.empty():
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
        )

        regions = []

        for (x, y, w, h) in faces:

            pad_x = int(w * 0.15)
            pad_y = int(h * 0.20)

            regions.append(
                make_region(
                    "FACE", "Face", 0.80,
                    max(0, x - pad_x), max(0, y - pad_y),
                    w + 2 * pad_x, h + 2 * pad_y,
                    "OPENCV",
                )
            )

        return regions

    except Exception as error:
        print(f"[OBSCURA IMAGE] Face detection error: {error}")
        return []


# ============================================================
# TEXT IN IMAGE (OCR -> text detectors -> boxes)
# ============================================================

def detect_text_regions(image):

    try:
        lines = run_ocr(image)

        if not lines:
            return []

        # Imported here so the heavy models only load when needed.
        from app.privacy.detector import detect_text

        full_text, spans = build_text(lines)

        regions = []

        for detection in detect_text(full_text):

            action = (
                "BLOCK"
                if detection.recommended_action == "BLOCK"
                else "REDACT"
            )

            label = detection.type.replace("_", " ").title()

            for x, y, w, h in span_boxes(spans, detection.start, detection.end):
                regions.append(
                    make_region(
                        detection.type, label, detection.confidence,
                        x, y, w, h,
                        "OCR+" + detection.source,
                        action, detection.value,
                    )
                )

        for line_start, _line_end, line in spans:

            for match in PLATE_RE.finditer(line.text.upper()):

                for x, y, w, h in span_boxes(
                    spans,
                    line_start + match.start(),
                    line_start + match.end(),
                ):
                    regions.append(
                        make_region(
                            "LICENSE_PLATE", "License plate", 0.85,
                            x, y, w, h, "OCR", "REDACT", match.group(),
                        )
                    )

        return regions

    except Exception as error:
        print(
            f"[OBSCURA IMAGE] OCR detection error "
            f"({type(error).__name__}): {error}"
        )
        return []


# ============================================================
# MAIN
# ============================================================

def detect_image(image) -> ImageDetectionResult:

    height, width = image.shape[:2]

    regions = []

    regions.extend(detect_qr_codes(image))
    regions.extend(detect_barcodes(image))
    regions.extend(detect_faces(image))
    regions.extend(detect_text_regions(image))

    unique = {}

    for region in regions:
        existing = unique.get(region.id)

        # If a BLOCK and a REDACT region collide, BLOCK wins.
        if existing is None or region.recommended_action == "BLOCK":
            unique[region.id] = region

    ordered = sorted(unique.values(), key=lambda r: (r.y, r.x))

    return ImageDetectionResult(width=width, height=height, regions=ordered)
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/image/protector.py"] = r'''def fill_region(image, x: int, y: int, width: int, height: int):

    image_height, image_width = image.shape[:2]

    x1 = max(0, min(x, image_width))
    y1 = max(0, min(y, image_height))
    x2 = max(x1, min(x + width, image_width))
    y2 = max(y1, min(y + height, image_height))

    if x2 <= x1 or y2 <= y1:
        return image

    # Solid fill. Unlike blur, this cannot be reversed or
    # sharpened back into readable content.
    image[y1:y2, x1:x2] = (0, 0, 0)

    return image


def protect_image(image, regions, selected_ids):

    protected = image.copy()
    selected = set(selected_ids)

    for region in regions:

        # BLOCK regions (secrets) are always redacted.
        forced = region.recommended_action == "BLOCK"

        if region.id not in selected and not forced:
            continue

        protected = fill_region(
            protected, region.x, region.y, region.width, region.height
        )

    return protected
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/image/service.py"] = r'''import cv2
import numpy as np

from app.privacy.image.detector import detect_image
from app.privacy.image.protector import protect_image


MAX_SIDE = 2000


def decode_image(image_bytes: bytes):

    array = np.frombuffer(image_bytes, dtype=np.uint8)

    image = cv2.imdecode(array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Unable to decode the uploaded image.")

    # Keep OCR fast and memory bounded. Analyze and prepare both go
    # through this function, so region coordinates always match.
    height, width = image.shape[:2]
    longest = max(height, width)

    if longest > MAX_SIDE:
        scale = MAX_SIDE / longest
        image = cv2.resize(
            image,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_AREA,
        )

    return image


def analyze_image(image_bytes: bytes):

    return detect_image(decode_image(image_bytes))


def prepare_image(image_bytes: bytes, regions, selected_ids):

    image = decode_image(image_bytes)

    protected = protect_image(image, regions, selected_ids)

    # Re-encoding to PNG also drops EXIF / GPS metadata.
    success, encoded = cv2.imencode(".png", protected)

    if not success:
        raise ValueError("Unable to encode protected image.")

    return encoded.tobytes()
'''

# ----------------------------------------------------------------------
FILES["backend/app/routes/image.py"] = r'''import base64

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
'''

# ----------------------------------------------------------------------
FILES["backend/app/main.py"] = r'''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.privacy import router as privacy_router
from app.routes.chat import router as chat_router
from app.routes.image import router as image_router

app = FastAPI(
    title="OBSCURA API",
    version="0.2.0",
    description="Privacy-preserving AI gateway",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(privacy_router, prefix="/api/privacy", tags=["privacy"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(image_router, prefix="/api/image", tags=["image"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "obscura"}
'''

# ----------------------------------------------------------------------
FILES["backend/tests/test_image.py"] = r'''import numpy as np

from app.privacy.image.detector import PLATE_RE
from app.privacy.image.mapping import OcrLine, build_text, span_boxes
from app.privacy.image.models import ImageRegion
from app.privacy.image.protector import protect_image


def region(region_id, action="REDACT"):
    return ImageRegion(
        id=region_id, type="T", label="t", confidence=0.9,
        x=10, y=10, width=20, height=20,
        source="TEST", recommended_action=action,
    )


def white():
    return np.full((60, 60, 3), 255, dtype=np.uint8)


def test_unselected_region_is_untouched():
    out = protect_image(white(), [region("a")], [])
    assert (out == 255).all()


def test_selected_region_is_filled_and_original_kept():
    original = white()
    out = protect_image(original, [region("a")], ["a"])
    assert out[15, 15].sum() == 0
    assert (original == 255).all()


def test_block_region_is_always_filled():
    out = protect_image(white(), [region("a", "BLOCK")], [])
    assert out[15, 15].sum() == 0


def test_span_boxes_cover_the_matched_part_of_a_line():
    line = OcrLine("hello world", 100, 50, 110, 20)
    _full, spans = build_text([line])

    x, y, w, h = span_boxes(spans, 6, 11)[0]

    assert x <= 100 + 110 * 6 // 11
    assert x + w >= 210
    assert y <= 50 and y + h >= 70


def test_build_text_offsets():
    a = OcrLine("abc", 0, 0, 30, 10)
    b = OcrLine("def", 0, 20, 30, 10)
    full, spans = build_text([a, b])
    assert full == "abc\ndef"
    assert spans[1][0] == 4


def test_plate_regex():
    assert PLATE_RE.search("KL 07 AB 1234")
    assert PLATE_RE.search("MH12DE1433")
    assert not PLATE_RE.search("hello world")
'''

# ----------------------------------------------------------------------
FILES["frontend/src/ImagePanel.jsx"] = r'''import { useEffect, useState } from "react";

const API = "http://localhost:8000/api";

export default function ImagePanel() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(new Set());

  const [protectedUrl, setProtectedUrl] = useState("");
  const [sessionId, setSessionId] = useState("");

  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");

  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function reset() {
    setResult(null);
    setSelected(new Set());
    setProtectedUrl("");
    setSessionId("");
    setResponse("");
  }

  async function onFile(event) {
    const chosen = event.target.files?.[0];
    if (!chosen) return;

    reset();
    setFile(chosen);
    setPreviewUrl(URL.createObjectURL(chosen));

    try {
      setBusy(true);
      setStatus("Scanning the image (first run loads the OCR model)...");

      const form = new FormData();
      form.append("file", chosen);

      const res = await fetch(`${API}/image/analyze`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "Image analysis failed.");

      setResult(data);
      setSelected(
        new Set(
          data.regions
            .filter((r) => r.recommended_action !== "BLOCK")
            .map((r) => r.id),
        ),
      );

      setStatus(
        data.regions.length
          ? `${data.regions.length} sensitive region${
              data.regions.length === 1 ? "" : "s"
            } found. Click a box to protect or unprotect it.`
          : "Nothing sensitive was detected. Detection is automatic, so please still check the image yourself.",
      );
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Unable to analyze the image.");
    } finally {
      setBusy(false);
    }
  }

  function toggle(region) {
    if (region.recommended_action === "BLOCK") return;

    setSelected((old) => {
      const next = new Set(old);
      if (next.has(region.id)) next.delete(region.id);
      else next.add(region.id);
      return next;
    });
  }

  async function createPreview() {
    try {
      setBusy(true);
      setStatus("Creating protected image...");

      const form = new FormData();
      form.append("file", file);
      form.append("selected_ids", [...selected].join(","));

      const res = await fetch(`${API}/image/prepare`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "Unable to protect image.");

      setSessionId(data.session_id);
      setProtectedUrl(`data:image/png;base64,${data.image_base64}`);
      setStatus("Protected image ready. Gemini will receive only this version.");
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Unable to create protected image.");
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    try {
      setBusy(true);
      setStatus("Sending the protected image to Gemini...");

      const res = await fetch(`${API}/image/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, prompt }),
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "AI request failed.");

      setResponse(data.response);
      setSessionId("");
      setStatus("Response received.");
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Unable to communicate with Gemini.");
    } finally {
      setBusy(false);
    }
  }

  const hasForced = result?.regions.some(
    (r) => r.recommended_action === "BLOCK",
  );

  return (
    <section className="card imagePanel">
      <div className="sectionTitle">
        <div>
          <h2>Image Privacy</h2>
          <p>
            Upload an image. Text, QR codes, barcodes, faces and license plates
            are detected locally. Selected areas are covered with solid black
            before anything is sent.
          </p>
        </div>
      </div>

      <input
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={onFile}
        disabled={busy}
      />

      {status && <div className="status">{status}</div>}

      {previewUrl && (
        <div className="imageStage">
          <img src={previewUrl} alt="Uploaded" />

          {result &&
            result.regions.map((region) => {
              const forced = region.recommended_action === "BLOCK";
              const on = forced || selected.has(region.id);

              return (
                <div
                  key={region.id}
                  className={`regionBox ${on ? "on" : "off"} ${
                    forced ? "forced" : ""
                  }`}
                  title={`${region.label}${
                    region.text ? `: ${region.text}` : ""
                  }${forced ? " (always hidden)" : ""}`}
                  onClick={() => toggle(region)}
                  style={{
                    left: `${(region.x / result.width) * 100}%`,
                    top: `${(region.y / result.height) * 100}%`,
                    width: `${(region.width / result.width) * 100}%`,
                    height: `${(region.height / result.height) * 100}%`,
                  }}
                />
              );
            })}
        </div>
      )}

      {hasForced && (
        <div className="blockedMessage">
          🔒 A secret or credential was found in the image. It will always be
          hidden.
        </div>
      )}

      {result && result.regions.length > 0 && (
        <div className="detections">
          {result.regions.map((region) => {
            const forced = region.recommended_action === "BLOCK";

            return (
              <label className="detection medium" key={region.id}>
                <input
                  type="checkbox"
                  checked={forced || selected.has(region.id)}
                  disabled={forced}
                  onChange={() => toggle(region)}
                />
                <div className="detectionBody">
                  <strong>{region.label}</strong>
                  {region.text && <span> · {region.text}</span>}
                  <div className="meta">
                    {region.source} · {Math.round(region.confidence * 100)}%
                    {forced ? " · always hidden" : ""}
                  </div>
                </div>
              </label>
            );
          })}
        </div>
      )}

      {result && !protectedUrl && (
        <button onClick={createPreview} disabled={busy}>
          Create Protected Image
        </button>
      )}

      {protectedUrl && (
        <div className="preview">
          <div className="compare">
            <div>
              <div className="label">ORIGINAL</div>
              <img className="thumb" src={previewUrl} alt="Original" />
            </div>
            <div>
              <div className="label">AI WILL RECEIVE</div>
              <img className="thumb" src={protectedUrl} alt="Protected" />
            </div>
          </div>

          <textarea
            className="imagePrompt"
            placeholder="Ask something about the image (your question is also checked for private data)"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />

          <div className="actions">
            <button
              className="secondary"
              onClick={() => {
                setProtectedUrl("");
                setSessionId("");
              }}
            >
              Back
            </button>
            <button onClick={send} disabled={!sessionId || busy}>
              {busy ? "Sending..." : "Confirm & Send to Gemini"}
            </button>
          </div>
        </div>
      )}

      {response && (
        <div className="response">
          <div className="label">AI RESPONSE</div>
          <div className="responseText">{response}</div>
        </div>
      )}
    </section>
  );
}
'''

# ----------------------------------------------------------------------
for path, content in FILES.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("wrote", path)

# ----------------------------------------------------------------------
# gemini.py: add generate_with_image
# ----------------------------------------------------------------------
gem = "backend/app/ai/gemini.py"
with open(gem, "r", encoding="utf-8") as f:
    g = f.read()

if "def generate_with_image" not in g:
    g += '''

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
'''
    with open(gem, "w", encoding="utf-8", newline="\n") as f:
        f.write(g)
    print("patched", gem)

# ----------------------------------------------------------------------
# requirements
# ----------------------------------------------------------------------
req = "backend/requirements.txt"
with open(req, "r", encoding="utf-8") as f:
    have = f.read().split()
with open(req, "a", encoding="utf-8", newline="\n") as f:
    for pkg in ["rapidocr-onnxruntime", "httpx"]:
        if pkg not in have:
            f.write(pkg + "\n")
            print("added", pkg, "to requirements.txt")

# ----------------------------------------------------------------------
# App.jsx: mount ImagePanel
# ----------------------------------------------------------------------
app = "frontend/src/App.jsx"
with open(app, "r", encoding="utf-8") as f:
    a = f.read()

if "ImagePanel" not in a:
    first = 'import { useMemo, useState } from "react";'
    if first not in a or "</main>" not in a:
        sys.exit("App.jsx has unexpected content; add ImagePanel manually.")
    a = a.replace(first, first + '\nimport ImagePanel from "./ImagePanel";', 1)
    a = a.replace("</main>", "  <ImagePanel />\n      </main>", 1)
    with open(app, "w", encoding="utf-8", newline="\n") as f:
        f.write(a)
    print("patched", app)

# ----------------------------------------------------------------------
# styles
# ----------------------------------------------------------------------
css = "frontend/src/styles.css"
with open(css, "r", encoding="utf-8") as f:
    c = f.read()

if ".imageStage" not in c:
    c += '''

/* ============================================================
   IMAGE PANEL
   ============================================================ */

.imageStage {
  position: relative;
  display: inline-block;
  max-width: 100%;
  margin: 16px 0;
}

.imageStage img {
  display: block;
  max-width: 100%;
  border-radius: 10px;
}

.regionBox {
  position: absolute;
  cursor: pointer;
  border: 2px solid #2563eb;
  background: rgba(37, 99, 235, 0.12);
  box-sizing: border-box;
}

.regionBox.on {
  border-color: #16a34a;
  background: rgba(22, 163, 74, 0.28);
}

.regionBox.off {
  border-style: dashed;
  border-color: #d97706;
  background: rgba(217, 119, 6, 0.1);
}

.regionBox.forced {
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.35);
  cursor: not-allowed;
}

.thumb {
  display: block;
  width: 100%;
  border-radius: 10px;
}

.imagePrompt {
  width: 100%;
  min-height: 80px;
  margin: 16px 0;
  padding: 12px;
  border: 1px solid #e3e8ef;
  border-radius: 10px;
  resize: vertical;
}
'''
    with open(css, "w", encoding="utf-8", newline="\n") as f:
        f.write(c)
    print("patched", css)

print("\nDone.")