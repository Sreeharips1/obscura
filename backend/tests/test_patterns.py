from app.privacy.detectors.patterns import detect_patterns
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
