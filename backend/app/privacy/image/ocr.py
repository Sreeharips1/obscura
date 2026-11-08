from functools import lru_cache

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


def repair_spacing(text: str) -> str:
    """OCR sometimes drops spaces ("MynameisAaronsmith").
    Split only long, letters-only strings so emails, numbers and
    IDs are never altered."""

    if " " in text or len(text) < 10 or not text.isalpha():
        return text

    try:
        import wordninja
    except ImportError:
        return text

    parts = wordninja.split(text)

    return " ".join(parts) if parts else text


def run_ocr(image) -> list[OcrLine]:

    engine = get_engine()

    if engine is None:
        return []

    result, _ = engine(image)

    lines = []

    for box, text, score in result or []:

        text = repair_spacing(str(text).strip())

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
