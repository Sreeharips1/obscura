from app.privacy.image.ocr import repair_spacing


def test_missing_spaces_are_restored():
    fixed = repair_spacing("MynameisAaronsmith")
    assert fixed.count(" ") >= 2


def test_emails_and_numbers_are_untouched():
    assert repair_spacing("john.doe@example.com") == "john.doe@example.com"
    assert repair_spacing("9876543210") == "9876543210"


def test_normal_text_is_untouched():
    assert repair_spacing("Hello world") == "Hello world"
