from dataclasses import dataclass


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
