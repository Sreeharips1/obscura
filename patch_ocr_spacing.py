# patch_ocr_spacing.py  -- run from the repo root
import os, sys

ocr = "backend/app/privacy/image/ocr.py"
if not os.path.exists(ocr):
    sys.exit("Run this from the repo root.")

with open(ocr, "r", encoding="utf-8") as f:
    data = f.read()

if "repair_spacing" not in data:
    helper = '''

def repair_spacing(text: str) -> str:
    """OCR sometimes drops spaces ("MynameisAaronsmith").
    Split only long, letters-only strings so emails, numbers and
    IDs are never altered."""

    if " " in text or len(text) < 10 or not text.isalpha():
        return text

    try:
        import wordninja
    except ImportError:
        return text

    parts = wordninja.split(text)

    return " ".join(parts) if parts else text
'''
    data = data.replace("def run_ocr(image)", helper.lstrip("\n") + "\n\ndef run_ocr(image)", 1)

    old = "        text = str(text).strip()\n"
    new = "        text = repair_spacing(str(text).strip())\n"
    if old not in data:
        sys.exit("Could not find the OCR text line; ocr.py was changed.")
    data = data.replace(old, new, 1)

    with open(ocr, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    print("patched", ocr)

test = "backend/tests/test_ocr_spacing.py"
with open(test, "w", encoding="utf-8", newline="\n") as f:
    f.write('''from app.privacy.image.ocr import repair_spacing


def test_missing_spaces_are_restored():
    fixed = repair_spacing("MynameisAaronsmith")
    assert fixed.count(" ") >= 2


def test_emails_and_numbers_are_untouched():
    assert repair_spacing("john.doe@example.com") == "john.doe@example.com"
    assert repair_spacing("9876543210") == "9876543210"


def test_normal_text_is_untouched():
    assert repair_spacing("Hello world") == "Hello world"
''')
print("wrote", test)

req = "backend/requirements.txt"
with open(req, "r", encoding="utf-8") as f:
    have = f.read().split()
if "wordninja" not in have:
    with open(req, "a", encoding="utf-8", newline="\n") as f:
        f.write("wordninja\\n".replace("\\\\n", "\\n"))
    print("added wordninja to requirements.txt")

print("Done. Now: cd backend ; pip install wordninja ; pytest -v")