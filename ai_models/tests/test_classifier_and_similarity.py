"""
Tests for the parts of ai_models/nlp that need no downloaded model:
the rule-based classifier and the cosine-similarity helper. The spaCy/
NLTK/transformers/sentence-transformers paths need real model downloads
and are exercised via integration testing once those are available in
your environment, not here.
"""

from ai_models.nlp.classifier import classify_complaint_type, rule_based_classify
from ai_models.nlp.duplicate_detection import cosine_similarity


def test_classifies_emergency_exit_blocking():
    label, confidence = rule_based_classify("Car is blocking the fire exit at the mall entrance")
    assert label == "emergency_exit_blocking"
    assert confidence > 0.5


def test_classifies_footpath_parking():
    label, confidence = rule_based_classify("Motorbike parked right on the sidewalk again")
    assert label == "footpath_parking"
    assert confidence > 0.5


def test_classifies_double_parking():
    label, _ = rule_based_classify("Someone double parked and now I'm completely boxed in")
    assert label == "double_parking"


def test_no_keyword_match_defaults_to_illegal_parking_low_confidence():
    label, confidence = rule_based_classify("There is a strange smell near my building")
    assert label == "illegal_parking"
    assert confidence == 0.3


def test_empty_text_is_unclassified():
    label, confidence = classify_complaint_type("")
    assert label == "unclassified"
    assert confidence == 0.0


def test_cosine_similarity_identical_vectors():
    vec = [0.6, 0.8]  # already unit-length
    assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_mismatched_lengths_returns_zero():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0


def test_cosine_similarity_empty_vector_returns_zero():
    assert cosine_similarity([], [1.0, 0.0]) == 0.0
