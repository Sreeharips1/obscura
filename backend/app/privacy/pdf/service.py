import base64
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
