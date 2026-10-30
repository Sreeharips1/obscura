import cv2

from app.privacy.image.detector import (
    detect_image,
)


IMAGE_PATH = "test1.webp"


image = cv2.imread(
    IMAGE_PATH
)


if image is None:

    raise RuntimeError(
        f"Could not open {IMAGE_PATH}"
    )


result = detect_image(
    image
)


print("\n========== OBSCURA IMAGE TEST ==========")

print(
    f"Image size: "
    f"{result.width} x {result.height}"
)


for region in result.regions:

    print(
        f"{region.type:15} | "
        f"{region.label:15} | "
        f"{region.confidence:.2f} | "
        f"({region.x}, {region.y}) "
        f"{region.width}x{region.height}"
    )


print(
    "========================================\n"
)