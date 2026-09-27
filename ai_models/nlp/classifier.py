"""
Complaint-type classification.

Returns plain string labels (e.g. "double_parking") rather than the
backend's `ComplaintType` enum, deliberately — this package has no
dependency on the FastAPI app, so it stays reusable/testable on its own
and the backend (app/services/nlp_service.py) does the string -> enum
conversion at the boundary.

**Default: rule-based keyword classifier.** Fast (no model to load),
deterministic, always available. A reasonable baseline given there's no
labeled complaint-text training set yet (the historical datasets in
Module 7 are violation records for hotspot/ML prediction, not labeled
complaint text).

**Optional: Hugging Face zero-shot classification** (`facebook/bart-large-mnli`
by default). More accurate, but downloads a ~1.6GB model on first use and
is noticeably slower per request — call `classify_complaint_type(text,
use_transformer=True)` to opt in. Worth revisiting (a distilled model, or
a model fine-tuned on real complaint data once it exists) before relying
on this at production volume.
"""

from functools import lru_cache
from typing import List, Tuple

UNCLASSIFIED = "unclassified"

# Keyword lists match app.models.complaint.ComplaintType's string values,
# so the backend can do ComplaintType(label) directly.
_KEYWORD_RULES: dict = {
    "emergency_exit_blocking": [
        "emergency exit", "fire exit", "fire lane", "blocking exit",
        "ambulance access", "fire hydrant",
    ],
    "footpath_parking": [
        "footpath", "sidewalk", "pavement", "pedestrian path", "walkway",
    ],
    "double_parking": [
        "double park", "double-park", "blocking my car", "boxed in", "second row",
    ],
    "no_parking_zone": [
        "no parking zone", "no-parking sign", "no parking sign",
        "restricted zone", "tow zone",
    ],
    "illegal_parking": [
        "illegally parked", "illegal parking", "parked illegally",
        "wrong side", "disabled spot", "handicap spot",
    ],
}

_ZERO_SHOT_HYPOTHESES = {
    "a vehicle is illegally parked": "illegal_parking",
    "two vehicles are double parked next to each other": "double_parking",
    "a vehicle is parked in a no parking zone": "no_parking_zone",
    "a vehicle is parked on a footpath or sidewalk": "footpath_parking",
    "a vehicle is blocking an emergency exit or fire lane": "emergency_exit_blocking",
}


def rule_based_classify(text: str) -> Tuple[str, float]:
    lowered = text.lower()
    best_label, best_hits = None, 0

    for label, keywords in _KEYWORD_RULES.items():
        hits = sum(1 for kw in keywords if kw in lowered)
        if hits > best_hits:
            best_label, best_hits = label, hits

    if best_hits == 0:
        # No keyword signal at all. Defaulting to the most common
        # violation type with low confidence is more useful downstream
        # (dashboards/filters) than an "unclassified" bucket that just
        # accumulates unreviewed complaints — but the low confidence
        # score makes it easy to find and correct.
        return "illegal_parking", 0.3

    confidence = min(0.6 + 0.15 * best_hits, 0.95)
    return best_label, confidence


@lru_cache
def _get_zero_shot_pipeline(model_name: str):
    from transformers import pipeline  # heavy import, only loaded if actually used

    return pipeline("zero-shot-classification", model=model_name)


def transformer_classify(text: str, model_name: str = "facebook/bart-large-mnli") -> Tuple[str, float]:
    classifier = _get_zero_shot_pipeline(model_name)
    candidate_labels: List[str] = list(_ZERO_SHOT_HYPOTHESES.keys())
    result = classifier(text, candidate_labels)
    top_hypothesis = result["labels"][0]
    top_score = float(result["scores"][0])
    return _ZERO_SHOT_HYPOTHESES[top_hypothesis], top_score


def classify_complaint_type(
    cleaned_text: str,
    use_transformer: bool = False,
    transformer_model_name: str = "facebook/bart-large-mnli",
) -> Tuple[str, float]:
    """Returns (label, confidence in [0,1]). `label` matches
    app.models.complaint.ComplaintType's string values."""
    if not cleaned_text or not cleaned_text.strip():
        return UNCLASSIFIED, 0.0

    if use_transformer:
        try:
            return transformer_classify(cleaned_text, transformer_model_name)
        except Exception:
            # Model missing/failed to load — fall back rather than fail
            # the whole NLP stage over an optional accuracy upgrade.
            pass

    return rule_based_classify(cleaned_text)
