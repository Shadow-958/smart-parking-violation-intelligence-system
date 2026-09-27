"""
Location extraction via spaCy Named Entity Recognition.

GPE (countries/cities/states), LOC (non-GPE locations), and FAC
(buildings, roads, other facilities) are treated as location candidates —
street names and landmarks ("outside City Mall", "on 5th Avenue") are
usually tagged FAC or LOC rather than GPE, so all three are needed to
catch how people actually describe where a violation happened.

This is a *fallback/enrichment* signal for geocoding, not a replacement
for the `location_text` field the user fills in directly — the GIS module
prefers `location_text` when present and falls back to this extracted
entity otherwise.
"""

from typing import Optional

from ai_models.nlp.preprocessing import get_spacy_model

_LOCATION_LABELS = {"GPE", "LOC", "FAC"}


def extract_location_entity(raw_text: Optional[str]) -> Optional[str]:
    """Returns the longest location-like entity span found in the raw
    complaint text, or None if none was found (including when the spaCy
    model isn't installed — NLTK has no NER equivalent, so there's no
    fallback here the way there is for cleaning)."""
    if not raw_text:
        return None

    nlp = get_spacy_model()
    if nlp is None:
        return None

    doc = nlp(raw_text)
    candidates = [ent.text.strip() for ent in doc.ents if ent.label_ in _LOCATION_LABELS]
    if not candidates:
        return None

    return max(candidates, key=len)
