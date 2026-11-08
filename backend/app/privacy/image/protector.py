def fill_region(image, x: int, y: int, width: int, height: int):

    image_height, image_width = image.shape[:2]

    x1 = max(0, min(x, image_width))
    y1 = max(0, min(y, image_height))
    x2 = max(x1, min(x + width, image_width))
    y2 = max(y1, min(y + height, image_height))

    if x2 <= x1 or y2 <= y1:
        return image

    # Solid fill. Unlike blur, this cannot be reversed or
    # sharpened back into readable content.
    image[y1:y2, x1:x2] = (0, 0, 0)

    return image


def protect_image(image, regions, selected_ids):

    protected = image.copy()
    selected = set(selected_ids)

    for region in regions:

        # BLOCK regions (secrets) are always redacted.
        forced = region.recommended_action == "BLOCK"

        if region.id not in selected and not forced:
            continue

        protected = fill_region(
            protected, region.x, region.y, region.width, region.height
        )

    return protected
