"""
Orchestrates the NLP stage of the AI workflow pipeline:
clean -> NER -> classify -> embed -> duplicate check.

Each sub-step's actual logic lives in ai_models/nlp (kept dependency-free
from the web app); this module is the boundary that wires those pure
functions into the ORM, applies configured thresholds, and commits
results.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ai_models.nlp import classifier, duplicate_detection, ner, preprocessing
from app.config import get_settings
from app.database import SessionLocal
from app.models.complaint import Complaint, ComplaintStatus, ComplaintType
from app.services import gis_service
from app.services.complaint_service import ComplaintNotFoundError, get_complaint

settings = get_settings()
logger = logging.getLogger(__name__)


def _find_best_duplicate(
    db: Session, complaint: Complaint, embedding: List[float]
) -> Tuple[Optional[uuid.UUID], Optional[float]]:
    """Compares `embedding` against other recent, non-duplicate complaints
    and returns the best match if it clears the configured threshold.

    Scoped to `NLP_DUPLICATE_LOOKBACK_DAYS` for two reasons: it keeps the
    candidate set small as complaint volume grows, and a similarly-worded
    complaint from six months ago is much less likely to be the *same*
    incident than one from yesterday.
    """
    if not embedding:
        return None, None

    cutoff = datetime.utcnow() - timedelta(days=settings.NLP_DUPLICATE_LOOKBACK_DAYS)
    candidates = (
        db.query(Complaint)
        .filter(Complaint.id != complaint.id)
        .filter(Complaint.embedding.isnot(None))
        .filter(Complaint.submitted_at >= cutoff)
        .filter(Complaint.is_duplicate.is_(False))
        .all()
    )

    best_id, best_score = None, 0.0
    for candidate in candidates:
        score = duplicate_detection.cosine_similarity(embedding, candidate.embedding)
        if score > best_score:
            best_score, best_id = score, candidate.id

    if best_id is not None and best_score >= settings.NLP_DUPLICATE_THRESHOLD:
        return best_id, best_score
    return None, None


def process_complaint(db: Session, complaint: Complaint) -> Complaint:
    """Runs the full NLP stage against an already-loaded Complaint and
    commits the results. Split out from process_complaint_by_id so tests
    (or callers that already hold a session/complaint) can invoke it
    directly without opening a new session."""

    cleaned = preprocessing.clean_text(complaint.raw_text)
    complaint.cleaned_text = cleaned
    complaint.extracted_location_entity = ner.extract_location_entity(complaint.raw_text)

    label, confidence = classifier.classify_complaint_type(
        cleaned, use_transformer=settings.NLP_USE_TRANSFORMER_CLASSIFIER
    )
    complaint.complaint_type = ComplaintType(label)
    complaint.classification_confidence = confidence

    embedding = duplicate_detection.compute_embedding(cleaned, settings.SENTENCE_TRANSFORMER_MODEL)
    complaint.embedding = embedding

    duplicate_id, score = _find_best_duplicate(db, complaint, embedding)
    if duplicate_id is not None:
        complaint.is_duplicate = True
        complaint.duplicate_of_id = duplicate_id
        complaint.duplicate_similarity_score = score
        complaint.status = ComplaintStatus.DUPLICATE

    # Only geocode if the complaint doesn't already have coordinates (e.g.
    # from GPS capture on the frontend). Re-geocoding via Nominatim would
    # overwrite the precise GPS location with a less accurate text match.
    if complaint.geom is None:
        try:
            # Best-effort: by now we have the best available location signal
            # (location_text if the citizen gave one, extracted_location_entity
            # otherwise), so this is where geocoding naturally belongs in the
            # pipeline. A missing location, an unreachable Nominatim, or no
            # match shouldn't fail the whole NLP stage — it can be retried via
            # POST /api/gis/geocode/{complaint_id}.
            gis_service.geocode_complaint_in_place(complaint)
        except Exception as exc:
            logger.warning(
                "Geocoding failed for complaint %s (location_text=%r): %s",
                complaint.id, complaint.location_text, exc,
            )

    db.commit()
    db.refresh(complaint)
    return complaint


def process_complaint_by_id(complaint_id: uuid.UUID) -> None:
    """Entry point for background tasks / the manual re-run endpoint.
    Opens and closes its own DB session, since the request-scoped session
    from `get_db` closes as soon as the HTTP response is sent — long
    before a background task actually runs."""
    db = SessionLocal()
    try:
        complaint = get_complaint(db, complaint_id)
        process_complaint(db, complaint)
    except ComplaintNotFoundError:
        pass  # complaint may have been deleted between scheduling and running
    finally:
        db.close()
