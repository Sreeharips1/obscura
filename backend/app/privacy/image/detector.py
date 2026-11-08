import hashlib
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
    faces = detect_faces(image)
    regions.extend(faces)

    # Imported here to avoid a circular import.
    from app.privacy.image.devices import detect_devices, detect_extra_faces

    regions.extend(detect_extra_faces(image, faces))
    regions.extend(detect_devices(image))
    regions.extend(detect_text_regions(image))

    unique = {}

    for region in regions:
        existing = unique.get(region.id)

        # If a BLOCK and a REDACT region collide, BLOCK wins.
        if existing is None or region.recommended_action == "BLOCK":
            unique[region.id] = region

    ordered = sorted(unique.values(), key=lambda r: (r.y, r.x))

    return ImageDetectionResult(width=width, height=height, regions=ordered)
