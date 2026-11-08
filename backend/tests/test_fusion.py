from app.privacy.entity_fusion import fuse_detections
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
