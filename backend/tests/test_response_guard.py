from app.models import AliasItem
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
