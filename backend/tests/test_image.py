import numpy as np

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
