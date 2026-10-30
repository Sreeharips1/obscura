import cv2


# ============================================================
# BLUR REGION
# ============================================================

def blur_region(
    image,
    x: int,
    y: int,
    width: int,
    height: int,
):

    image_height, image_width = image.shape[:2]


    # --------------------------------------------------------
    # Clamp coordinates
    # --------------------------------------------------------

    x1 = max(
        0,
        min(x, image_width),
    )

    y1 = max(
        0,
        min(y, image_height),
    )

    x2 = max(
        x1,
        min(
            x + width,
            image_width,
        ),
    )

    y2 = max(
        y1,
        min(
            y + height,
            image_height,
        ),
    )


    if x2 <= x1 or y2 <= y1:

        return image


    roi = image[
        y1:y2,
        x1:x2,
    ]


    if roi.size == 0:

        return image


    # --------------------------------------------------------
    # Gaussian blur
    # --------------------------------------------------------

    blurred = cv2.GaussianBlur(
        roi,
        (51, 51),
        0,
    )


    image[
        y1:y2,
        x1:x2
    ] = blurred


    return image


# ============================================================
# PROTECT IMAGE
# ============================================================

def protect_image(
    image,
    regions,
    selected_ids,
):

    protected = image.copy()


    for region in regions:

        if region.id not in selected_ids:

            continue


        protected = blur_region(
            protected,

            region.x,
            region.y,

            region.width,
            region.height,
        )


    return protected