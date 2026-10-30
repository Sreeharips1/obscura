from app.privacy.detector import detect_text
from app.privacy.pseudonymizer import (
    sanitize_text,
    restore_text,
)


def analyze(text: str):

    return detect_text(text)


def sanitize(
    text,
    detections,
    selected_ids,
):

    return sanitize_text(
        text,
        detections,
        selected_ids,
    )


def restore(
    text,
    aliases,
):

    return restore_text(
        text,
        aliases,
    )