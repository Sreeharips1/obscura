import cv2
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
