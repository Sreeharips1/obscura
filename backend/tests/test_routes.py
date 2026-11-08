import pytest
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
