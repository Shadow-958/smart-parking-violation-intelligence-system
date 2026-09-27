"""
NLP endpoints.

Analysis normally runs automatically as a background task immediately
after complaint submission (see the background_tasks.add_task call in
app/api/routes/complaints.py). This router exposes a manual re-run for
officers/admins — useful after correcting a misclassification, changing
NLP_USE_TRANSFORMER_CLASSIFIER, or updating a model.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.complaint import ComplaintResponse
from app.services import complaint_service, nlp_service

router = APIRouter()


@router.post(
    "/analyze/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Re-run the NLP pipeline on a complaint (officer/admin only)",
)
def analyze_complaint(
    complaint_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    try:
        complaint = complaint_service.get_complaint(db, complaint_id)
    except complaint_service.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return nlp_service.process_complaint(db, complaint)
