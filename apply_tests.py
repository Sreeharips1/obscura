# apply_tests.py  -- run from the repo root
import os, sys

if not os.path.isdir("backend/app"):
    sys.exit("Run this from the repo root (the folder containing backend/ and frontend/).")

FILES = {}

FILES["backend/pytest.ini"] = '''[pytest]
pythonpath = .
testpaths = tests
'''

FILES["backend/tests/__init__.py"] = ""

FILES["backend/tests/helpers.py"] = r'''from app.privacy.detectors.patterns import make_detection


def det(text, value, kind="PERSON_NAME", action="PSEUDONYMIZE",
        risk="MEDIUM", source="CONTEXT", occurrence=0):
    """Build a Detection for the Nth occurrence of `value` in `text`."""
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(value, start + 1)
    return make_detection(
        kind=kind,
        value=value,
        category="TEST",
        confidence=0.9,
        risk=risk,
        reason="test",
        start=start,
        end=start + len(value),
        action=action,
        source=source,
    )
'''

FILES["backend/tests/test_patterns.py"] = r'''from app.privacy.detectors.patterns import detect_patterns
from app.privacy.detectors.secrets import detect_secrets


def types(detections):
    return {d.type for d in detections}


def test_email_detected():
    found = detect_patterns("Contact me at john.doe@example.com today")
    assert "EMAIL" in types(found)


def test_phone_detected():
    found = detect_patterns("Call 9876543210 now")
    assert "PHONE" in types(found)


def test_pan_detected():
    found = detect_patterns("My PAN is ABCDE1234F")
    assert "PAN_LIKE" in types(found)


def test_aadhaar_detected():
    found = detect_patterns("Aadhaar 1234 5678 9012")
    assert "AADHAAR_LIKE" in types(found)


def test_plain_text_has_no_detections():
    assert detect_patterns("Write a poem about autumn") == []


def test_detection_ids_are_stable():
    a = detect_patterns("mail a@b.com")
    b = detect_patterns("mail a@b.com")
    assert [d.id for d in a] == [d.id for d in b]


def test_password_is_blocked():
    found = detect_secrets("my password: hunter2xyz")
    assert any(
        d.type == "PASSWORD" and d.recommended_action == "BLOCK" for d in found
    )


def test_api_key_is_blocked():
    found = detect_secrets("api_key = abcdef1234567890")
    assert any(d.type == "API_KEY_OR_TOKEN" for d in found)


def test_jwt_is_blocked():
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnop"
    found = detect_secrets(f"token {token}")
    assert any(d.type == "JWT_TOKEN" for d in found)
'''

FILES["backend/tests/test_fusion.py"] = r'''from app.privacy.entity_fusion import fuse_detections
from tests.helpers import det


def test_repeated_values_stay_separate():
    text = "My name is Sreehari. Sreehari wants a job."
    first = det(text, "Sreehari", occurrence=0)
    second = det(text, "Sreehari", occurrence=1)

    fused = fuse_detections([first, second])

    assert len(fused) == 2
    assert {d.start for d in fused} == {first.start, second.start}


def test_same_span_from_two_sources_is_merged():
    text = "Hello Sreehari"
    a = det(text, "Sreehari", source="CONTEXT")
    b = det(text, "Sreehari", source="NER")

    fused = fuse_detections([a, b])

    assert len(fused) == 1
    assert set(fused[0].evidence) == {"CONTEXT", "NER"}
    assert fused[0].confidence >= a.confidence
'''

FILES["backend/tests/test_pseudonymizer.py"] = r'''from app.privacy.pseudonymizer import sanitize_text, restore_text
from tests.helpers import det


TEXT = "My name is Sreehari. Sreehari can be reached at a@b.com."


def build():
    name1 = det(TEXT, "Sreehari", occurrence=0)
    name2 = det(TEXT, "Sreehari", occurrence=1)
    email = det(TEXT, "a@b.com", kind="EMAIL", risk="HIGH", source="PATTERN")
    return name1, name2, email


def test_selecting_one_occurrence_protects_all():
    name1, name2, email = build()

    sanitized, aliases = sanitize_text(TEXT, [name1, name2, email], [name1.id])

    assert "Sreehari" not in sanitized
    assert sanitized.count("<OBSCURA_NAME_001>") == 2
    assert "a@b.com" in sanitized  # not selected, so untouched
    assert len(aliases) == 1


def test_round_trip_restores_original():
    name1, name2, email = build()

    sanitized, aliases = sanitize_text(
        TEXT, [name1, name2, email], [name1.id, email.id]
    )

    assert "a@b.com" not in sanitized
    assert restore_text(sanitized, aliases) == TEXT


def test_case_variants_share_one_alias():
    text = "Ask Sreehari. Then ask sreehari again."
    a = det(text, "Sreehari")
    b = det(text, "sreehari")

    sanitized, aliases = sanitize_text(text, [a, b], [a.id, b.id])

    assert len(aliases) == 1
    assert sanitized.count("<OBSCURA_NAME_001>") == 2


def test_block_items_are_never_replaced():
    text = "password: hunter2xyz"
    secret = det(
        text, "password: hunter2xyz", kind="PASSWORD",
        action="BLOCK", risk="CRITICAL", source="SECRET",
    )

    sanitized, aliases = sanitize_text(text, [secret], [secret.id])

    assert sanitized == text
    assert aliases == []


def test_empty_selection_changes_nothing():
    name1, name2, email = build()

    sanitized, aliases = sanitize_text(TEXT, [name1, name2, email], [])

    assert sanitized == TEXT
    assert aliases == []
'''

FILES["backend/tests/test_response_guard.py"] = r'''from app.models import AliasItem
from app.privacy.response_guard import verify_response


ALIAS = AliasItem(
    detection_id="x",
    original="sreehari@gmail.com",
    alias="<OBSCURA_EMAIL_001>",
    type="EMAIL",
)


def test_safe_response():
    result = verify_response("Please contact <OBSCURA_EMAIL_001>", [ALIAS])
    assert result["safe"] is True


def test_leaked_original_is_flagged():
    result = verify_response("Please contact sreehari@gmail.com", [ALIAS])
    assert result["safe"] is False
    assert result["potential_leaks"][0]["type"] == "EMAIL"
'''

FILES["backend/tests/test_routes.py"] = r'''import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import AliasItem
from app.privacy.vault import create_session
from tests.helpers import det


client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_prepare_blocks_secret_even_when_not_selected(monkeypatch):
    text = "my password: hunter2xyz"
    secret = det(
        text, "password: hunter2xyz", kind="PASSWORD",
        action="BLOCK", risk="CRITICAL", source="SECRET",
    )
    monkeypatch.setattr("app.routes.privacy.analyze", lambda t: [secret])

    response = client.post(
        "/api/privacy/prepare",
        json={"text": text, "selected_detection_ids": []},
    )

    body = response.json()
    assert body["blocked"] is True
    assert body["session_id"] == ""
    assert body["sanitized_text"] == ""


def test_prepare_with_no_detections_still_creates_session(monkeypatch):
    monkeypatch.setattr("app.routes.privacy.analyze", lambda t: [])

    response = client.post(
        "/api/privacy/prepare",
        json={"text": "Write a poem", "selected_detection_ids": []},
    )

    body = response.json()
    assert body["blocked"] is False
    assert body["session_id"]
    assert body["sanitized_text"] == "Write a poem"


def make_session():
    alias = AliasItem(
        detection_id="x",
        original="sreehari@gmail.com",
        alias="<OBSCURA_EMAIL_001>",
        type="EMAIL",
    )
    return create_session(
        original_text="mail sreehari@gmail.com",
        sanitized_text="mail <OBSCURA_EMAIL_001>",
        aliases=[alias],
    )


def test_chat_restores_original_values(monkeypatch):
    monkeypatch.setattr(
        "app.routes.chat.generate_text",
        lambda prompt: "Contact <OBSCURA_EMAIL_001> soon",
    )

    response = client.post("/api/chat/send", json={"session_id": make_session()})

    assert response.status_code == 200
    assert response.json()["response"] == "Contact sreehari@gmail.com soon"


def test_chat_blocks_response_that_leaks_original(monkeypatch):
    monkeypatch.setattr(
        "app.routes.chat.generate_text",
        lambda prompt: "Contact sreehari@gmail.com soon",
    )

    response = client.post("/api/chat/send", json={"session_id": make_session()})

    assert response.status_code == 502


def test_chat_unknown_session_returns_404():
    response = client.post("/api/chat/send", json={"session_id": "does-not-exist"})
    assert response.status_code == 404
'''

for path, content in FILES.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("wrote", path)

# TestClient needs httpx
req = "backend/requirements.txt"
with open(req, "r", encoding="utf-8") as f:
    lines = f.read().split()
if "httpx" not in lines:
    with open(req, "a", encoding="utf-8", newline="\n") as f:
        f.write("httpx\n")
    print("added httpx to requirements.txt")

print("\nDone. Now run:  cd backend  then  pip install httpx  then  pytest -v")