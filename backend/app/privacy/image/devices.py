import cv2

from app.privacy.image.detector import make_region


# Objects whose SCREEN can show private content. The whole object is
# covered, so it works even when the screen text is unreadable.
DEVICE_NAMES = {"cell phone", "laptop", "tv"}

_model = None
_failed = False


def _get_model():
    global _model, _failed

    if _model is not None or _failed:
        return _model

    try:
        from ultralytics import YOLO
        print("[OBSCURA IMAGE] Loading device detector (first run downloads ~6 MB)")
        _model = YOLO("yolov8n.pt")
    except Exception as error:
        _failed = True
        print(
            "[OBSCURA IMAGE] Device detection unavailable "
            f"({type(error).__name__}). Run: pip install ultralytics"
        )

    return _model


def detect_devices(image):

    model = _get_model()

    if model is None:
        return []

    try:
        result = model.predict(image, conf=0.25, verbose=False)[0]
        names = result.names
        height, width = image.shape[:2]

        regions = []

        for box, cls, conf in zip(
            result.boxes.xyxy.tolist(),
            result.boxes.cls.tolist(),
            result.boxes.conf.tolist(),
        ):
            name = names[int(cls)]

            if name not in DEVICE_NAMES:
                continue

            x1, y1, x2, y2 = box
            pad_x = (x2 - x1) * 0.05
            pad_y = (y2 - y1) * 0.05

            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(width, x2 + pad_x)
            y2 = min(height, y2 + pad_y)

            regions.append(
                make_region(
                    "DEVICE_SCREEN",
                    f"Screen device ({name})",
                    conf,
                    x1, y1, x2 - x1, y2 - y1,
                    "YOLO",
                )
            )

        return regions

    except Exception as error:
        print(f"[OBSCURA IMAGE] Device detection error: {type(error).__name__}: {error}")
        return []


def _iou(a, b):
    ax2, ay2 = a.x + a.width, a.y + a.height
    bx2, by2 = b.x + b.width, b.y + b.height

    ix = max(0, min(ax2, bx2) - max(a.x, b.x))
    iy = max(0, min(ay2, by2) - max(a.y, b.y))
    inter = ix * iy

    union = a.width * a.height + b.width * b.height - inter

    return inter / union if union else 0


def detect_extra_faces(image, existing):
    """Tilted and side-profile faces, skipping ones already found."""

    try:
        gray = cv2.equalizeHist(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        width = gray.shape[1]

        found = []

        for name, flip in (
            ("haarcascade_frontalface_alt2.xml", False),
            ("haarcascade_profileface.xml", False),
            ("haarcascade_profileface.xml", True),
        ):
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + name)

            if cascade.empty():
                continue

            source = cv2.flip(gray, 1) if flip else gray

            for (x, y, w, h) in cascade.detectMultiScale(
                source, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40)
            ):
                if flip:
                    x = width - x - w

                pad_x, pad_y = int(w * 0.15), int(h * 0.20)

                region = make_region(
                    "FACE", "Face", 0.70,
                    max(0, x - pad_x), max(0, y - pad_y),
                    w + 2 * pad_x, h + 2 * pad_y,
                    "OPENCV",
                )

                if any(_iou(region, other) > 0.3 for other in list(existing) + found):
                    continue

                found.append(region)

        return found

    except Exception as error:
        print(f"[OBSCURA IMAGE] Extra face detection error: {error}")
        return []
