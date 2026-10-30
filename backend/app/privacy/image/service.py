import cv2
import numpy as np

from app.privacy.image.detector import (
    detect_image,
)

from app.privacy.image.protector import (
    protect_image,
)


# ============================================================
# DECODE IMAGE
# ============================================================

def decode_image(
    image_bytes: bytes,
):

    array = np.frombuffer(
        image_bytes,
        dtype=np.uint8,
    )


    image = cv2.imdecode(
        array,
        cv2.IMREAD_COLOR,
    )


    if image is None:

        raise ValueError(
            "Unable to decode the uploaded image."
        )


    return image


# ============================================================
# ANALYZE IMAGE
# ============================================================

def analyze_image(
    image_bytes: bytes,
):

    image = decode_image(
        image_bytes
    )

    return detect_image(
        image
    )


# ============================================================
# PROTECT IMAGE
# ============================================================

def prepare_image(
    image_bytes: bytes,
    regions,
    selected_ids,
):

    image = decode_image(
        image_bytes
    )


    protected = protect_image(
        image,
        regions,
        selected_ids,
    )


    success, encoded = cv2.imencode(
        ".png",
        protected,
    )


    if not success:

        raise ValueError(
            "Unable to encode protected image."
        )


    return encoded.tobytes()