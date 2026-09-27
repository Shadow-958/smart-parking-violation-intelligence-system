"""
Computer vision endpoints.

Detection normally runs automatically as a background task right after a
photo is uploaded (see the background_tasks.add_task call in
app/api/routes/complaints.py's upload_complaint_image). This router
exposes viewing results and a manual re-run for officers/admins.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.complaint_image import ComplaintImage
from app.models.user import User, UserRole
from app.schemas.vision import ComplaintImageDetections
from app.services import vision_service
from app.services.complaint_service import get_complaint

router = APIRouter()


def _get_image_or_404(db: Session, image_id: uuid.UUID) -> ComplaintImage:
    image = db.get(ComplaintImage, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint image not found")
    return image


@router.get(
    "/detections/{image_id}",
    response_model=ComplaintImageDetections,
    summary="Get vehicle detection results for a complaint image",
)
def get_detections(
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image = _get_image_or_404(db, image_id)
    complaint = get_complaint(db, image.complaint_id)

    is_owner = complaint.user_id == current_user.id
    is_staff = current_user.role in (UserRole.OFFICER, UserRole.ADMIN)
    if not is_owner and not is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this image"
        )

    return image


@router.post(
    "/analyze/{image_id}",
    response_model=ComplaintImageDetections,
    summary="Re-run vehicle detection on a complaint image (officer/admin only)",
)
def analyze_image(
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    image = _get_image_or_404(db, image_id)
    return vision_service.process_image(db, image)
