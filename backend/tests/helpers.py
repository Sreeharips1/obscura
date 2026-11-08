from app.privacy.detectors.patterns import make_detection


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
