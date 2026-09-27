"""
Tests for ai_models/computer_vision/illegal_parking.py's confidence-gate
heuristic. detector.py itself needs a real YOLOv8 model/weights and is
exercised via integration testing once ultralytics is installed in your
environment, not here.
"""

from ai_models.computer_vision.illegal_parking import assess_detection


def test_high_confidence_detection_flagged_true():
    is_illegal, reason = assess_detection("car", 0.87)
    assert is_illegal is True
    assert "87%" in reason
    assert "Car" in reason


def test_low_confidence_detection_flagged_false():
    is_illegal, reason = assess_detection("motorcycle", 0.3)
    assert is_illegal is False
    assert "30%" in reason
    assert "manual review" in reason


def test_exactly_at_threshold_counts_as_high_confidence():
    is_illegal, _ = assess_detection("truck", 0.5, high_confidence_threshold=0.5)
    assert is_illegal is True


def test_custom_threshold_is_respected():
    # 0.6 would pass the default 0.5 threshold but not a stricter 0.75 one
    is_illegal, _ = assess_detection("bus", 0.6, high_confidence_threshold=0.75)
    assert is_illegal is False
