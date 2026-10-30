import cv2
import hashlib

from app.privacy.image.models import (
    ImageRegion,
    ImageDetectionResult,
)


# ============================================================
# DETECTION ID
# ============================================================

def generate_region_id(
    region_type: str,
    x: int,
    y: int,
    width: int,
    height: int,
) -> str:

    raw = (
        f"{region_type}:"
        f"{x}:{y}:{width}:{height}"
    )

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()[:20]


# ============================================================
# QR CODE DETECTION
# ============================================================

def detect_qr_codes(
    image,
) -> list[ImageRegion]:

    regions = []

    detector = cv2.QRCodeDetector()

    try:

        result = detector.detectAndDecodeMulti(
            image
        )

        # OpenCV versions return slightly different
        # structures, therefore we handle both cases.

        if len(result) == 4:

            success, decoded_info, points, _ = result

        else:

            success = False
            decoded_info = []
            points = None


        if not success or points is None:

            return regions


        for index, polygon in enumerate(points):

            if polygon is None:
                continue

            polygon = polygon.astype(int)

            x_values = polygon[:, 0]
            y_values = polygon[:, 1]

            x = int(x_values.min())
            y = int(y_values.min())

            right = int(x_values.max())
            bottom = int(y_values.max())

            width = right - x
            height = bottom - y

            if width <= 0 or height <= 0:
                continue


            regions.append(
                ImageRegion(
                    id=generate_region_id(
                        "QR_CODE",
                        x,
                        y,
                        width,
                        height,
                    ),

                    type="QR_CODE",

                    label="QR code",

                    confidence=0.98,

                    x=x,
                    y=y,
                    width=width,
                    height=height,

                    source="OPENCV",

                    recommended_action="BLUR",
                )
            )

    except Exception as error:

        print(
            "[OBSCURA IMAGE] "
            f"QR detection error: {error}"
        )


    return regions


# ============================================================
# BARCODE DETECTION
# ============================================================

def detect_barcodes(
    image,
) -> list[ImageRegion]:

    regions = []

    detector = cv2.barcode_BarcodeDetector()

    try:

        result = detector.detectAndDecode(
            image
        )

        # OpenCV's exact return structure can vary
        # between versions.

        if len(result) == 3:

            ok, decoded_info, points = result

        else:

            return regions


        if points is None:

            return regions


        if len(points) == 0:

            return regions


        for polygon in points:

            if polygon is None:
                continue


            polygon = polygon.astype(int)

            x_values = polygon[:, 0]
            y_values = polygon[:, 1]

            x = int(x_values.min())
            y = int(y_values.min())

            right = int(x_values.max())
            bottom = int(y_values.max())

            width = right - x
            height = bottom - y


            if width <= 0 or height <= 0:
                continue


            regions.append(
                ImageRegion(
                    id=generate_region_id(
                        "BARCODE",
                        x,
                        y,
                        width,
                        height,
                    ),

                    type="BARCODE",

                    label="Barcode",

                    confidence=0.96,

                    x=x,
                    y=y,
                    width=width,
                    height=height,

                    source="OPENCV",

                    recommended_action="BLUR",
                )
            )

    except Exception as error:

        print(
            "[OBSCURA IMAGE] "
            f"Barcode detection error: {error}"
        )


    return regions


# ============================================================
# MAIN IMAGE DETECTOR
# ============================================================

def detect_image(
    image,
) -> ImageDetectionResult:

    height, width = image.shape[:2]

    regions = []


    # --------------------------------------------------------
    # QR
    # --------------------------------------------------------

    regions.extend(
        detect_qr_codes(
            image
        )
    )


    # --------------------------------------------------------
    # Barcode
    # --------------------------------------------------------

    regions.extend(
        detect_barcodes(
            image
        )
    )


    # --------------------------------------------------------
    # Remove duplicate regions
    # --------------------------------------------------------

    unique = {}

    for region in regions:

        unique[region.id] = region


    regions = list(
        unique.values()
    )


    return ImageDetectionResult(
        width=width,
        height=height,
        regions=regions,
    )