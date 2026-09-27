"""
Duplicate-complaint detection: embed cleaned complaint text with a
Sentence-BERT model, then compare via cosine similarity.

Embeddings are computed once per complaint and stored
(`Complaint.embedding`), so detecting duplicates for a new complaint only
requires embedding *that one* complaint and comparing it against
already-embedded candidates — see app/services/nlp_service.py for the
candidate-selection and thresholding logic (lookback window, similarity
threshold), which is a policy decision that belongs in the backend, not
here.
"""

from functools import lru_cache
from typing import List

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache
def _get_model(model_name: str):
    from sentence_transformers import SentenceTransformer  # heavy import, loaded lazily

    return SentenceTransformer(model_name)


def compute_embedding(text: str, model_name: str = DEFAULT_MODEL_NAME) -> List[float]:
    """Returns an L2-normalized embedding vector, or [] for empty input."""
    if not text or not text.strip():
        return []

    model = _get_model(model_name)
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Cosine similarity between two embeddings. Since compute_embedding
    normalizes its output, this reduces to a plain dot product — kept
    dependency-free (no numpy) since it's only ever comparing two modest
    (384-dim) vectors at a time."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    return float(sum(a * b for a, b in zip(vec_a, vec_b)))
