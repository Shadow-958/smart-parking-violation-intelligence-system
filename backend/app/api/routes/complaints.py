"""
Complaint management endpoints.

Route order matters here: `/me` must be registered before `/{complaint_id}`
or FastAPI/Starlette would try to parse the literal string "me" as a UUID
path parameter and 422 before ever reaching the "my complaints" handler.
"""

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_user, get_current_user_optional, require_roles
from app.database import get_db, SessionLocal
from app.models.complaint import ComplaintSource, ComplaintStatus, ComplaintType
from app.models.complaint_image import ComplaintImage
from app.models.user import User, UserRole
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintImageResponse,
    ComplaintResponse,
    ComplaintStatusUpdate,
    PaginatedComplaints,
)
from app.services import complaint_service, gis_service, nlp_service, vision_service

router = APIRouter()

settings = get_settings()


def _recompute_hotspots_background() -> None:
    """Recompute hotspots in a background task with its own DB session.
    Runs after each new complaint so hotspot analysis stays current
    without relying solely on the 24h scheduler."""
    db = SessionLocal()
    try:
        gis_service.recompute_hotspots(
            db,
            period_days=settings.HOTSPOT_PERIOD_DAYS,
            eps_meters=settings.HOTSPOT_EPS_METERS,
            min_points=settings.HOTSPOT_MIN_POINTS,
        )
    except Exception:
        pass  # non-critical; the scheduler will retry on its next cycle
    finally:
        db.close()


def _assert_can_view(complaint, current_user: User) -> None:
    is_owner = complaint.user_id == current_user.id
    is_staff = current_user.role in (UserRole.OFFICER, UserRole.ADMIN)
    if not is_owner and not is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this complaint",
        )


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a parking complaint",
)
def submit_complaint(
    complaint_in: ComplaintCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Works both logged in and anonymously — the citizen portal and mobile
    app will typically send a bearer token, while email/social-media
    ingestion (added later) won't have one, relying instead on the
    contact_* fields to identify the submitter.
    """
    user_id = current_user.id if current_user else None
    complaint = complaint_service.create_complaint(db, complaint_in, user_id)

    # Runs after the response is sent, so submission stays fast even
    # though NLP (and, once wired in, CV/geocoding) is not instant.
    background_tasks.add_task(nlp_service.process_complaint_by_id, complaint.id)

    # Recompute hotspots after the NLP pipeline (which includes geocoding)
    # so new complaints are reflected in the hotspot analysis without
    # waiting for the 24h scheduler or a manual officer trigger.
    background_tasks.add_task(_recompute_hotspots_background)

    return complaint


@router.get("/me", response_model=PaginatedComplaints, summary="List my own complaints")
def list_my_complaints(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = complaint_service.list_complaints(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return PaginatedComplaints(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "",
    response_model=PaginatedComplaints,
    summary="List/filter/search all complaints (officer/admin only)",
)
def list_complaints(
    status_filter: Optional[ComplaintStatus] = Query(None, alias="status"),
    complaint_type: Optional[ComplaintType] = None,
    source: Optional[ComplaintSource] = None,
    is_duplicate: Optional[bool] = None,
    search: Optional[str] = Query(None, description="Matches complaint text, location, or address"),
    submitted_from: Optional[datetime] = None,
    submitted_to: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    items, total = complaint_service.list_complaints(
        db,
        status_filter=status_filter,
        complaint_type=complaint_type,
        source=source,
        is_duplicate=is_duplicate,
        search=search,
        submitted_from=submitted_from,
        submitted_to=submitted_to,
        skip=skip,
        limit=limit,
    )
    return PaginatedComplaints(items=items, total=total, skip=skip, limit=limit)


@router.get("/{complaint_id}", response_model=ComplaintResponse, summary="Get a single complaint")
def get_complaint_detail(
    complaint_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        complaint = complaint_service.get_complaint(db, complaint_id)
    except complaint_service.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    _assert_can_view(complaint, current_user)
    return complaint


@router.patch(
    "/{complaint_id}/status",
    response_model=ComplaintResponse,
    summary="Approve/reject/resolve a complaint (officer/admin only)",
)
def update_complaint_status(
    complaint_id: uuid.UUID,
    status_update: ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    try:
        return complaint_service.update_status(db, complaint_id, status_update.status)
    except complaint_service.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/{complaint_id}/images",
    response_model=ComplaintImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a photo to a complaint",
)
def upload_complaint_image(
    complaint_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        complaint = complaint_service.get_complaint(db, complaint_id)
    except complaint_service.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    _assert_can_view(complaint, current_user)

    try:
        image = complaint_service.save_complaint_image(db, complaint_id, file)
    except complaint_service.InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    background_tasks.add_task(vision_service.process_image_by_id, image.id)
    return image


# NOTE: uploading an image here stores the file, creates a ComplaintImage
# row (processed=False), and schedules YOLOv8 vehicle detection as a
# background task — by the time a client polls GET
# /api/vision/detections/{image_id}, `processed` should have flipped to
# True with VehicleDetection rows attached.


@router.get(
    "/images/{image_id}/file",
    summary="Fetch the actual image bytes for a complaint photo",
)
def get_complaint_image_file(
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Streams the stored image file — needed by the frontend to actually
    render `<img>` tags; the upload/detection endpoints only ever
    returned metadata, never the bytes themselves."""
    image = db.get(ComplaintImage, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    try:
        complaint = complaint_service.get_complaint(db, image.complaint_id)
    except complaint_service.ComplaintNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    _assert_can_view(complaint, current_user)

    if not os.path.exists(image.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file missing on disk")

    return FileResponse(image.file_path, media_type=image.content_type or "image/jpeg")
