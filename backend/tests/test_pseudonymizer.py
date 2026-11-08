from app.privacy.pseudonymizer import sanitize_text, restore_text
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
