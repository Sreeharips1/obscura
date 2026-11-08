import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.privacy.detectors.patterns import detect_patterns
from app.privacy.detectors.secrets import detect_secrets
from app.privacy.pdf import service


client = TestClient(app)


def light_detect(text):
    return detect_patterns(text) + detect_secrets(text)


@pytest.fixture(autouse=True)
def light_detector(monkeypatch):
    # Skip the heavy NER / GLiNER models in these tests.
    monkeypatch.setattr(service, "detect_text", light_detect)


def make_pdf(lines, author=None):
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line)
        y += 20
    if author:
        doc.set_metadata({"author": author})
    data = doc.tobytes()
    doc.close()
    return data


def extract(pdf_bytes):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = " ".join(page.get_text() for page in doc)
    meta = doc.metadata
    doc.close()
    return text, meta


def ids_of(analysis, include_block=False):
    return [
        r.id for r in analysis.regions
        if include_block or r.recommended_action != "BLOCK"
    ]


def test_analyze_finds_email_and_phone():
    data = make_pdf(["Contact john.doe@example.com or call 9876543210."])
    analysis = service.analyze_pdf(data)
    found = {r.type for r in analysis.regions}
    assert {"EMAIL", "PHONE"} <= found
    assert analysis.page_count == 1
    assert analysis.pages[0].image_base64


def test_selected_values_are_removed_from_the_file():
    data = make_pdf(["Mail john.doe@example.com", "Plain harmless line"])
    analysis = service.analyze_pdf(data)

    result = service.prepare_pdf(data, ids_of(analysis))
    text, _ = extract(result["pdf_bytes"])

    assert "john.doe@example.com" not in text
    assert "Plain harmless line" in text
    assert result["still_visible"] == []


def test_unselected_values_stay():
    data = make_pdf(["Mail john.doe@example.com"])
    result = service.prepare_pdf(data, [])
    text, _ = extract(result["pdf_bytes"])
    assert "john.doe@example.com" in text


def test_secrets_are_always_redacted():
    data = make_pdf(["password: hunter2xyz"])
    result = service.prepare_pdf(data, [])
    text, _ = extract(result["pdf_bytes"])
    assert "hunter2xyz" not in text
    assert result["forced"] >= 1


def test_metadata_is_stripped():
    data = make_pdf(["Hello"], author="Jane Roe")
    analysis = service.analyze_pdf(data)
    assert analysis.metadata.get("author") == "Jane Roe"

    result = service.prepare_pdf(data, [])
    _, meta = extract(result["pdf_bytes"])
    assert not meta.get("author")


def test_other_occurrences_are_redacted_too(monkeypatch):
    # The detector only reports the FIRST occurrence.
    monkeypatch.setattr(
        service, "detect_text", lambda t: detect_patterns(t)[:1]
    )
    data = make_pdf(["Mail a.b@example.com", "Again a.b@example.com"])
    analysis = service.analyze_pdf(data)
    assert len(analysis.regions) == 1

    result = service.prepare_pdf(data, ids_of(analysis))
    text, _ = extract(result["pdf_bytes"])
    assert "a.b@example.com" not in text


def test_garbage_is_rejected():
    with pytest.raises(ValueError):
        service.analyze_pdf(b"%PDF-not really")


def test_route_rejects_non_pdf():
    response = client.post(
        "/api/pdf/analyze",
        files={"file": ("a.pdf", b"hello", "application/pdf")},
    )
    assert response.status_code == 415


def test_route_flow_sends_only_the_redacted_pdf(monkeypatch):
    sent = {}

    def fake_generate(prompt, data, mime_type=None):
        sent["data"] = data
        sent["mime"] = mime_type
        return "ok"

    monkeypatch.setattr("app.routes.pdf.generate_with_image", fake_generate)

    data = make_pdf(["Mail john.doe@example.com"])
    files = {"file": ("t.pdf", data, "application/pdf")}

    analysis = client.post("/api/pdf/analyze", files=files).json()
    ids = ",".join(r["id"] for r in analysis["regions"])

    prepared = client.post(
        "/api/pdf/prepare",
        files={"file": ("t.pdf", data, "application/pdf")},
        data={"selected_ids": ids},
    ).json()

    response = client.post(
        "/api/pdf/send",
        json={"session_id": prepared["session_id"], "prompt": "Summarize"},
    )

    assert response.status_code == 200
    assert response.json()["response"] == "ok"
    assert sent["mime"] == "application/pdf"

    text, _ = extract(sent["data"])
    assert "john.doe@example.com" not in text
