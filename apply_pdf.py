# apply_pdf.py  -- run from the repo root
import os, sys

if not (os.path.isdir("backend/app") and os.path.isdir("frontend/src")):
    sys.exit("Run this from the repo root (the folder containing backend/ and frontend/).")

FILES = {}

# ----------------------------------------------------------------------
FILES["backend/app/privacy/pdf/__init__.py"] = ""

# ----------------------------------------------------------------------
FILES["backend/app/privacy/pdf/models.py"] = r'''from typing import Literal

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
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/pdf/service.py"] = r'''import base64
import hashlib
import os
import re

import cv2
import numpy as np
import pymupdf

from app.privacy.detector import detect_text
from app.privacy.detectors.patterns import make_detection
from app.privacy.pdf.models import PdfAnalysis, PdfPage, PdfRegion


MAX_PAGES = 25
CHUNK_CHARS = 1200       # keeps each model call small
PREVIEW_ZOOM = 1.2
OCR_ZOOM = 2.0

PROPAGATE_TYPES = {
    "PERSON_NAME": "PERSONAL_IDENTITY",
    "ORGANIZATION": "ORGANIZATIONAL_INFORMATION",
}

METADATA_FIELDS = ("title", "author", "subject", "keywords", "creator", "producer")


# ============================================================
# OPEN
# ============================================================

def open_pdf(data: bytes):

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise ValueError("Unable to read this PDF.")

    if doc.needs_pass:
        doc.close()
        raise ValueError(
            "Password-protected PDFs are not supported. "
            "Remove the password first."
        )

    if doc.page_count == 0:
        doc.close()
        raise ValueError("This PDF has no pages.")

    if doc.page_count > MAX_PAGES:
        count = doc.page_count
        doc.close()
        raise ValueError(
            f"This PDF has {count} pages. The limit is {MAX_PAGES}."
        )

    return doc


# ============================================================
# TEXT LAYOUT HELPERS
# ============================================================

def _lines(page):
    """Group the page's words into lines, in reading order."""

    lines = {}
    order = []

    for word in page.get_text("words"):

        key = (word[5], word[6])      # block, line

        if key not in lines:
            lines[key] = []
            order.append(key)

        lines[key].append(word)

    return [sorted(lines[key], key=lambda w: w[7]) for key in order]


def _chunks(lines):

    chunk = []
    size = 0

    for line in lines:

        length = sum(len(word[4]) + 1 for word in line)

        if chunk and size + length > CHUNK_CHARS:
            yield chunk
            chunk = []
            size = 0

        chunk.append(line)
        size += length

    if chunk:
        yield chunk


def _build(chunk):
    """Join a chunk into text and remember where every word sits."""

    parts = []
    entries = []
    position = 0

    for line_index, line in enumerate(chunk):

        for word_index, word in enumerate(line):

            if word_index:
                parts.append(" ")
                position += 1

            text = word[4]

            entries.append(
                (
                    position,
                    position + len(text),
                    line_index,
                    pymupdf.Rect(word[:4]),
                )
            )

            parts.append(text)
            position += len(text)

        parts.append("\n")
        position += 1

    return "".join(parts), entries


def _boxes(entries, start, end):
    """One box per line covered by the character range."""

    by_line = {}

    for word_start, word_end, line_index, rect in entries:

        if word_start < end and start < word_end:

            if line_index in by_line:
                by_line[line_index].include_rect(rect)
            else:
                by_line[line_index] = pymupdf.Rect(rect)

    return list(by_line.values())


# ============================================================
# REGION HELPERS
# ============================================================

def _region_id(page_no, kind, raw) -> str:

    key = (
        f"{page_no}:{kind}:"
        f"{raw.x0:.1f}:{raw.y0:.1f}:{raw.x1:.1f}:{raw.y1:.1f}"
    )

    return hashlib.sha256(key.encode()).hexdigest()[:20]


def _make_item(page, page_no, kind, label, confidence, raw, display,
               source, text, action):

    region = PdfRegion(
        id=_region_id(page_no, kind, raw),
        page=page_no,
        type=kind,
        label=label,
        confidence=round(float(confidence), 2),
        x=round(display.x0, 2),
        y=round(display.y0, 2),
        width=round(display.width, 2),
        height=round(display.height, 2),
        source=source,
        text=text,
        recommended_action=action,
    )

    return region, raw


def _to_display(page, raw):

    display = pymupdf.Rect(raw) * page.rotation_matrix
    display.normalize()

    return display


def _pad(raw):

    rect = pymupdf.Rect(raw)

    return pymupdf.Rect(rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 1)


# ============================================================
# A NAME FOUND ONCE IS PROTECTED EVERYWHERE
# ============================================================

def _propagate(text, detections, names):

    extra = []

    for lowered, (kind, original) in names.items():

        pattern = re.compile(
            r"(?i)(?<![\w@])" + re.escape(original) + r"(?![\w@])"
        )

        for match in pattern.finditer(text):

            start, end = match.span()

            if any(
                d.start < end and start < d.end
                for d in list(detections) + extra
            ):
                continue

            extra.append(
                make_detection(
                    kind=kind,
                    value=match.group(),
                    category=PROPAGATE_TYPES[kind],
                    confidence=0.85,
                    risk="MEDIUM",
                    reason=(
                        "This value matches one that was identified "
                        "elsewhere in the document."
                    ),
                    start=start,
                    end=end,
                    action="PSEUDONYMIZE",
                    source="CONTEXT",
                )
            )

    return extra


# ============================================================
# OCR FOR SCANNED PAGES
# ============================================================

def _ocr_items(page, page_no):

    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(OCR_ZOOM, OCR_ZOOM),
        colorspace=pymupdf.csRGB,
        alpha=False,
    )

    array = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width, pixmap.n
    )

    image = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)

    # Imported here so the OCR model only loads when needed.
    from app.privacy.image.detector import detect_text_regions

    items = []

    for region in detect_text_regions(image):

        display = pymupdf.Rect(
            region.x / OCR_ZOOM,
            region.y / OCR_ZOOM,
            (region.x + region.width) / OCR_ZOOM,
            (region.y + region.height) / OCR_ZOOM,
        )

        raw = display * page.derotation_matrix
        raw.normalize()

        items.append(
            _make_item(
                page, page_no, region.type, region.label,
                region.confidence, raw, display,
                region.source, region.text, region.recommended_action,
            )
        )

    return items


# ============================================================
# SCAN
# ============================================================

def _scan(data: bytes):
    """Returns (open document, [(region, raw_rect)], scanned page numbers)."""

    doc = open_pdf(data)

    try:
        chunks = []
        ocr_pages = set()
        ocr_all_images = os.getenv("OBSCURA_PDF_OCR_IMAGES", "0") == "1"
        words_per_page = {}

        for page_no in range(doc.page_count):

            page = doc[page_no]

            lines = _lines(page)

            words_per_page[page_no] = sum(len(line) for line in lines)

            for chunk in _chunks(lines):

                text, entries = _build(chunk)

                chunks.append(
                    [page_no, text, entries, list(detect_text(text))]
                )

        # Names found anywhere are looked for everywhere.
        names = {}

        for _p, _t, _e, detections in chunks:
            for d in detections:
                value = d.value.strip()

                if d.type in PROPAGATE_TYPES and len(value) >= 3:
                    names.setdefault(value.lower(), (d.type, value))

        items = []

        for page_no, text, entries, detections in chunks:

            page = doc[page_no]

            detections = detections + _propagate(text, detections, names)

            for d in detections:

                action = "BLOCK" if d.recommended_action == "BLOCK" else "REDACT"

                label = d.type.replace("_", " ").title()

                for raw in _boxes(entries, d.start, d.end):

                    items.append(
                        _make_item(
                            page, page_no, d.type, label, d.confidence,
                            raw, _to_display(page, raw),
                            d.source, d.value, action,
                        )
                    )

        # Scanned pages (and optionally pages with embedded images).
        for page_no in range(doc.page_count):

            page = doc[page_no]

            if not page.get_images():
                continue

            if words_per_page[page_no] < 3 or ocr_all_images:

                try:
                    items.extend(_ocr_items(page, page_no))
                    ocr_pages.add(page_no)
                except Exception as error:
                    print(
                        f"[OBSCURA PDF] OCR failed on page {page_no + 1} "
                        f"({type(error).__name__}): {error}"
                    )

        items.sort(key=lambda item: (item[0].page, item[0].y, item[0].x))

        return doc, items, ocr_pages

    except Exception:
        doc.close()
        raise


# ============================================================
# PREVIEWS / INSPECTION
# ============================================================

def _render(page, zoom=PREVIEW_ZOOM) -> str:

    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(zoom, zoom),
        colorspace=pymupdf.csRGB,
        alpha=False,
    )

    return base64.b64encode(pixmap.tobytes("png")).decode("ascii")


def _page_info(page, scanned: bool) -> PdfPage:

    return PdfPage(
        page=page.number,
        width=round(page.rect.width, 2),
        height=round(page.rect.height, 2),
        scanned=scanned,
        image_base64=_render(page),
    )


def _inspect(doc):
    """Hidden privacy risks that are not visible text."""

    metadata = {
        key: str(value)
        for key, value in (doc.metadata or {}).items()
        if key in METADATA_FIELDS and value
    }

    notes = []

    try:
        count = doc.embfile_count()
        if count:
            notes.append(f"{count} embedded file(s) inside the PDF.")
    except Exception:
        pass

    try:
        comments = sum(
            1 for page in doc for _ in (page.annots() or [])
        )
        if comments:
            notes.append(f"{comments} annotation(s) or comment(s).")
    except Exception:
        pass

    try:
        if doc.xref_xml_metadata():
            notes.append("XMP metadata is present.")
    except Exception:
        pass

    if metadata:
        notes.append(
            "Document properties (author, title, software) are removed "
            "from the protected copy."
        )

    return metadata, notes


# ============================================================
# ANALYZE
# ============================================================

def analyze_pdf(data: bytes) -> PdfAnalysis:

    doc, items, ocr_pages = _scan(data)

    try:
        pages = [_page_info(page, page.number in ocr_pages) for page in doc]

        metadata, notes = _inspect(doc)

        return PdfAnalysis(
            page_count=doc.page_count,
            pages=pages,
            regions=[region for region, _raw in items],
            metadata=metadata,
            notes=notes,
        )

    finally:
        doc.close()


# ============================================================
# PREPARE (REDACT)
# ============================================================

def prepare_pdf(data: bytes, selected_ids) -> dict:

    doc, items, ocr_pages = _scan(data)

    try:
        selected = set(selected_ids)

        chosen = [
            (region, raw)
            for region, raw in items
            if region.id in selected or region.recommended_action == "BLOCK"
        ]

        touched = set()
        values = set()

        for region, raw in chosen:

            page = doc[region.page]

            page.add_redact_annot(_pad(raw), fill=(0, 0, 0))

            touched.add(region.page)

            text = (region.text or "").strip()

            if len(text) >= 3 and "\n" not in text:
                values.add(text)

        # Safety net: wherever else a protected value appears
        # in the text layer, redact it too.
        for page in doc:

            for value in values:

                for rect in page.search_for(value):

                    page.add_redact_annot(_pad(rect), fill=(0, 0, 0))

                    touched.add(page.number)

        image_mode = getattr(pymupdf, "PDF_REDACT_IMAGE_PIXELS", 2)

        for page_no in touched:
            doc[page_no].apply_redactions(images=image_mode)

        # Strip hidden data.
        try:
            doc.set_metadata({})
        except Exception:
            pass

        try:
            doc.del_xml_metadata()
        except Exception:
            pass

        try:
            doc.scrub()
        except Exception as error:
            print(f"[OBSCURA PDF] scrub skipped: {type(error).__name__}")

        pdf_bytes = doc.tobytes(garbage=4, deflate=True)

    finally:
        doc.close()

    # Re-read the OUTPUT and verify.
    protected = pymupdf.open(stream=pdf_bytes, filetype="pdf")

    try:
        full_text = " ".join(
            " ".join(page.get_text().split()) for page in protected
        ).lower()

        still_visible = sorted(
            {
                region.type
                for region, _raw in chosen
                if region.text
                and len(" ".join(region.text.split())) >= 3
                and " ".join(region.text.split()).lower() in full_text
            }
        )

        previews = [
            _page_info(page, page.number in ocr_pages) for page in protected
        ]

    finally:
        protected.close()

    return {
        "pdf_bytes": pdf_bytes,
        "pages": previews,
        "redacted": len(chosen),
        "forced": sum(
            1 for region, _raw in chosen
            if region.recommended_action == "BLOCK"
        ),
        "still_visible": still_visible,
    }
'''

# ----------------------------------------------------------------------
FILES["backend/app/routes/pdf.py"] = r'''import base64

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
'''

# ----------------------------------------------------------------------
FILES["backend/tests/test_pdf.py"] = r'''import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.privacy.detectors.patterns import detect_patterns
from app.privacy.detectors.secrets import detect_secrets
from app.privacy.pdf import service


client = TestClient(app)


def light_detect(text):
    return detect_patterns(text) + detect_secrets(text)


@pytest.fixture(autouse=True)
def light_detector(monkeypatch):
    # Skip the heavy NER / GLiNER models in these tests.
    monkeypatch.setattr(service, "detect_text", light_detect)


def make_pdf(lines, author=None):
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line)
        y += 20
    if author:
        doc.set_metadata({"author": author})
    data = doc.tobytes()
    doc.close()
    return data


def extract(pdf_bytes):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = " ".join(page.get_text() for page in doc)
    meta = doc.metadata
    doc.close()
    return text, meta


def ids_of(analysis, include_block=False):
    return [
        r.id for r in analysis.regions
        if include_block or r.recommended_action != "BLOCK"
    ]


def test_analyze_finds_email_and_phone():
    data = make_pdf(["Contact john.doe@example.com or call 9876543210."])
    analysis = service.analyze_pdf(data)
    found = {r.type for r in analysis.regions}
    assert {"EMAIL", "PHONE"} <= found
    assert analysis.page_count == 1
    assert analysis.pages[0].image_base64


def test_selected_values_are_removed_from_the_file():
    data = make_pdf(["Mail john.doe@example.com", "Plain harmless line"])
    analysis = service.analyze_pdf(data)

    result = service.prepare_pdf(data, ids_of(analysis))
    text, _ = extract(result["pdf_bytes"])

    assert "john.doe@example.com" not in text
    assert "Plain harmless line" in text
    assert result["still_visible"] == []


def test_unselected_values_stay():
    data = make_pdf(["Mail john.doe@example.com"])
    result = service.prepare_pdf(data, [])
    text, _ = extract(result["pdf_bytes"])
    assert "john.doe@example.com" in text


def test_secrets_are_always_redacted():
    data = make_pdf(["password: hunter2xyz"])
    result = service.prepare_pdf(data, [])
    text, _ = extract(result["pdf_bytes"])
    assert "hunter2xyz" not in text
    assert result["forced"] >= 1


def test_metadata_is_stripped():
    data = make_pdf(["Hello"], author="Jane Roe")
    analysis = service.analyze_pdf(data)
    assert analysis.metadata.get("author") == "Jane Roe"

    result = service.prepare_pdf(data, [])
    _, meta = extract(result["pdf_bytes"])
    assert not meta.get("author")


def test_other_occurrences_are_redacted_too(monkeypatch):
    # The detector only reports the FIRST occurrence.
    monkeypatch.setattr(
        service, "detect_text", lambda t: detect_patterns(t)[:1]
    )
    data = make_pdf(["Mail a.b@example.com", "Again a.b@example.com"])
    analysis = service.analyze_pdf(data)
    assert len(analysis.regions) == 1

    result = service.prepare_pdf(data, ids_of(analysis))
    text, _ = extract(result["pdf_bytes"])
    assert "a.b@example.com" not in text


def test_garbage_is_rejected():
    with pytest.raises(ValueError):
        service.analyze_pdf(b"%PDF-not really")


def test_route_rejects_non_pdf():
    response = client.post(
        "/api/pdf/analyze",
        files={"file": ("a.pdf", b"hello", "application/pdf")},
    )
    assert response.status_code == 415


def test_route_flow_sends_only_the_redacted_pdf(monkeypatch):
    sent = {}

    def fake_generate(prompt, data, mime_type=None):
        sent["data"] = data
        sent["mime"] = mime_type
        return "ok"

    monkeypatch.setattr("app.routes.pdf.generate_with_image", fake_generate)

    data = make_pdf(["Mail john.doe@example.com"])
    files = {"file": ("t.pdf", data, "application/pdf")}

    analysis = client.post("/api/pdf/analyze", files=files).json()
    ids = ",".join(r["id"] for r in analysis["regions"])

    prepared = client.post(
        "/api/pdf/prepare",
        files={"file": ("t.pdf", data, "application/pdf")},
        data={"selected_ids": ids},
    ).json()

    response = client.post(
        "/api/pdf/send",
        json={"session_id": prepared["session_id"], "prompt": "Summarize"},
    )

    assert response.status_code == 200
    assert response.json()["response"] == "ok"
    assert sent["mime"] == "application/pdf"

    text, _ = extract(sent["data"])
    assert "john.doe@example.com" not in text
'''

# ----------------------------------------------------------------------
FILES["frontend/src/PdfPanel.jsx"] = r'''import { useState } from "react";

const API = "http://localhost:8000/api";

function PageView({ page, regions, selected, onToggle }) {
  return (
    <div className="pdfPage">
      <div className="pageLabel">Page {page.page + 1}</div>

      <div className="pdfPageStage">
        <img src={`data:image/png;base64,${page.image_base64}`} alt="" />

        {onToggle &&
          regions.map((region) => {
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
                onClick={() => onToggle(region)}
                style={{
                  left: `${(region.x / page.width) * 100}%`,
                  top: `${(region.y / page.height) * 100}%`,
                  width: `${(region.width / page.width) * 100}%`,
                  height: `${(region.height / page.height) * 100}%`,
                }}
              />
            );
          })}
      </div>
    </div>
  );
}

export default function PdfPanel() {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [selected, setSelected] = useState(new Set());

  const [prepared, setPrepared] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");

  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  function reset() {
    setAnalysis(null);
    setSelected(new Set());
    setPrepared(null);
    setResponse("");
  }

  async function onFile(event) {
    const chosen = event.target.files?.[0];
    if (!chosen) return;

    reset();
    setFile(chosen);

    try {
      setBusy(true);
      setStatus("Scanning the PDF (scanned pages need OCR and can be slow)...");

      const form = new FormData();
      form.append("file", chosen);

      const res = await fetch(`${API}/pdf/analyze`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "PDF analysis failed.");

      setAnalysis(data);

      // Everything except secrets (always hidden) and generic
      // "confidential" wording is selected by default.
      setSelected(
        new Set(
          data.regions
            .filter(
              (r) =>
                r.recommended_action !== "BLOCK" &&
                r.type !== "CONFIDENTIAL_CONTEXT",
            )
            .map((r) => r.id),
        ),
      );

      setStatus(
        data.regions.length
          ? `${data.regions.length} sensitive region${
              data.regions.length === 1 ? "" : "s"
            } found. Click a box to protect or unprotect it.`
          : "Nothing sensitive was detected. Detection is automatic, so please still review the document yourself.",
      );
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Unable to analyze the PDF.");
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

  async function createProtected() {
    try {
      setBusy(true);
      setStatus("Redacting the PDF...");

      const form = new FormData();
      form.append("file", file);
      form.append("selected_ids", [...selected].join(","));

      const res = await fetch(`${API}/pdf/prepare`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "Unable to protect the PDF.");

      setPrepared(data);
      setStatus("Protected PDF ready. Gemini will receive only this version.");
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Unable to protect the PDF.");
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    try {
      setBusy(true);
      setStatus("Sending the protected PDF to Gemini...");

      const res = await fetch(`${API}/pdf/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: prepared.session_id, prompt }),
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "AI request failed.");

      setResponse(data.response);
      setPrepared({ ...prepared, session_id: "" });
      setStatus("Response received.");
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Unable to communicate with Gemini.");
    } finally {
      setBusy(false);
    }
  }

  const regionsByPage = (pageNo) =>
    analysis.regions.filter((r) => r.page === pageNo);

  const hasForced = analysis?.regions.some(
    (r) => r.recommended_action === "BLOCK",
  );

  return (
    <section className="card pdfPanel">
      <div className="sectionTitle">
        <div>
          <h2>PDF Privacy</h2>
          <p>
            Upload a PDF. Personal data, secrets, hidden metadata and scanned
            text are detected locally. Selected content is permanently removed
            from the file before anything is sent.
          </p>
        </div>
      </div>

      <input
        type="file"
        accept="application/pdf"
        onChange={onFile}
        disabled={busy}
      />

      {status && <div className="status">{status}</div>}

      {analysis && (analysis.notes.length > 0 || Object.keys(analysis.metadata).length > 0) && (
        <div className="previewNotice">
          <strong>Hidden information in this file</strong>
          <ul>
            {Object.entries(analysis.metadata).map(([key, value]) => (
              <li key={key}>
                {key}: {value}
              </li>
            ))}
            {analysis.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      )}

      {hasForced && (
        <div className="blockedMessage">
          🔒 A secret or credential was found. It will always be removed.
        </div>
      )}

      {analysis && !prepared && (
        <>
          <div className="pdfPages">
            {analysis.pages.map((page) => (
              <PageView
                key={page.page}
                page={page}
                regions={regionsByPage(page.page)}
                selected={selected}
                onToggle={toggle}
              />
            ))}
          </div>

          {analysis.regions.length > 0 && (
            <div className="detections">
              {analysis.regions.map((region) => {
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
                        Page {region.page + 1} · {region.source} ·{" "}
                        {Math.round(region.confidence * 100)}%
                        {forced ? " · always removed" : ""}
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}

          <button onClick={createProtected} disabled={busy}>
            Create Protected PDF
          </button>
        </>
      )}

      {prepared && (
        <div className="preview">
          {prepared.still_visible.length > 0 && (
            <div className="blockedMessage">
              ⚠️ Some protected values may still be extractable from the
              output ({prepared.still_visible.join(", ")}). Do not send this
              file. Review it manually.
            </div>
          )}

          <div className="label">
            AI WILL RECEIVE ({prepared.redacted} region
            {prepared.redacted === 1 ? "" : "s"} removed)
          </div>

          <div className="pdfPages">
            {prepared.pages.map((page) => (
              <PageView
                key={page.page}
                page={page}
                regions={[]}
                selected={selected}
              />
            ))}
          </div>

          <a
            className="downloadLink"
            href={`data:application/pdf;base64,${prepared.pdf_base64}`}
            download="protected.pdf"
          >
            Download protected PDF
          </a>

          <textarea
            className="imagePrompt"
            placeholder="Ask something about the document (your question is also checked for private data)"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />

          <div className="actions">
            <button className="secondary" onClick={() => setPrepared(null)}>
              Back
            </button>
            <button
              onClick={send}
              disabled={!prepared.session_id || busy}
            >
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


def patch(path, edits):
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    changed = False
    for marker, old, new in edits:
        if marker in data:
            continue
        if old not in data:
            sys.exit(f"{path}: expected text not found ({old[:40]!r}). Patch it manually.")
        data = data.replace(old, new, 1)
        changed = True
    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
        print("patched", path)


# main.py: register the router
patch("backend/app/main.py", [
    (
        "pdf_router",
        "from app.routes.image import router as image_router",
        "from app.routes.image import router as image_router\n"
        "from app.routes.pdf import router as pdf_router",
    ),
    (
        'prefix="/api/pdf"',
        'app.include_router(image_router, prefix="/api/image", tags=["image"])',
        'app.include_router(image_router, prefix="/api/image", tags=["image"])\n'
        'app.include_router(pdf_router, prefix="/api/pdf", tags=["pdf"])',
    ),
])

# App.jsx: mount the panel
patch("frontend/src/App.jsx", [
    (
        'import PdfPanel',
        'import ImagePanel from "./ImagePanel";',
        'import ImagePanel from "./ImagePanel";\nimport PdfPanel from "./PdfPanel";',
    ),
    (
        "<PdfPanel />",
        "<ImagePanel />",
        "<ImagePanel />\n        <PdfPanel />",
    ),
])

# requirements
req = "backend/requirements.txt"
with open(req, "r", encoding="utf-8") as f:
    have = f.read().split()
with open(req, "a", encoding="utf-8", newline="\n") as f:
    if "pymupdf" not in have:
        f.write("pymupdf\n")
        print("added pymupdf to requirements.txt")

# styles
css = "frontend/src/styles.css"
with open(css, "r", encoding="utf-8") as f:
    c = f.read()

if ".pdfPages" not in c:
    c += '''

/* ============================================================
   PDF PANEL
   ============================================================ */

.pdfPages {
  display: grid;
  gap: 16px;
  margin: 16px 0;
  max-height: 900px;
  overflow: auto;
}

.pdfPage {
  max-width: 760px;
}

.pageLabel {
  font-size: 11px;
  font-weight: 800;
  color: #667085;
  margin-bottom: 6px;
}

.pdfPageStage {
  position: relative;
  border: 1px solid #e3e8ef;
  border-radius: 6px;
  overflow: hidden;
}

.pdfPageStage img {
  display: block;
  width: 100%;
}

.downloadLink {
  display: inline-block;
  margin: 8px 0;
  font-weight: 700;
  color: #3155d9;
}
'''
    with open(css, "w", encoding="utf-8", newline="\n") as f:
        f.write(c)
    print("patched", css)

print("\nDone.")