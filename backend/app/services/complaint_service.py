"""
Complaint business logic, kept separate from route handlers so it's
reusable (e.g. by a future email/social-media ingestion worker that
creates complaints outside of an HTTP request) and independently
testable without spinning up FastAPI.
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models.complaint import Complaint, ComplaintStatus, ComplaintType, ComplaintSource
from app.models.complaint_image import ComplaintImage
from app.schemas.complaint import ComplaintCreate

settings = get_settings()

# Kept intentionally small/conservative; expand as real-world formats require.
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ComplaintNotFoundError(Exception):
    """Raised when a complaint_id doesn't exist."""


class InvalidImageError(Exception):
    """Raised for an unsupported content type or an over-size upload."""


def create_complaint(
    db: Session, complaint_in: ComplaintCreate, user_id: Optional[uuid.UUID]
) -> Complaint:
    complaint = Complaint(
        user_id=user_id,
        source=complaint_in.source,
        raw_text=complaint_in.raw_text,
        location_text=complaint_in.location_text,
        contact_name=complaint_in.contact_name,
        contact_phone=complaint_in.contact_phone,
        contact_email=complaint_in.contact_email,
    )
    # If the frontend captured GPS coordinates, set geometry immediately so
    # the complaint appears on the map without waiting for async Nominatim
    # geocoding (which may fail or take several seconds).
    if complaint_in.latitude is not None and complaint_in.longitude is not None:
        complaint.geom = f"SRID=4326;POINT({complaint_in.longitude} {complaint_in.latitude})"
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def get_complaint(db: Session, complaint_id: uuid.UUID) -> Complaint:
    complaint = (
        db.query(Complaint)
        .options(selectinload(Complaint.images))
        .filter(Complaint.id == complaint_id)
        .first()
    )
    if complaint is None:
        raise ComplaintNotFoundError(f"Complaint {complaint_id} not found")
    return complaint


def list_complaints(
    db: Session,
    *,
    status_filter: Optional[ComplaintStatus] = None,
    complaint_type: Optional[ComplaintType] = None,
    source: Optional[ComplaintSource] = None,
    is_duplicate: Optional[bool] = None,
    search: Optional[str] = None,
    submitted_from: Optional[datetime] = None,
    submitted_to: Optional[datetime] = None,
    user_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Complaint], int]:
    """Filtered, paginated complaint listing. Powers both the citizen
    "my complaints" view and the officer/admin triage view — the caller
    decides which filters to apply (e.g. user_id is set for "my
    complaints", left None for the admin-wide view)."""

    query = db.query(Complaint).options(selectinload(Complaint.images))

    if status_filter is not None:
        query = query.filter(Complaint.status == status_filter)
    if complaint_type is not None:
        query = query.filter(Complaint.complaint_type == complaint_type)
    if source is not None:
        query = query.filter(Complaint.source == source)
    if is_duplicate is not None:
        query = query.filter(Complaint.is_duplicate == is_duplicate)
    if user_id is not None:
        query = query.filter(Complaint.user_id == user_id)
    if submitted_from is not None:
        query = query.filter(Complaint.submitted_at >= submitted_from)
    if submitted_to is not None:
        query = query.filter(Complaint.submitted_at <= submitted_to)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Complaint.raw_text.ilike(like),
                Complaint.location_text.ilike(like),
                Complaint.address.ilike(like),
            )
        )

    total = query.count()
    items = query.order_by(Complaint.submitted_at.desc()).offset(skip).limit(limit).all()
    return items, total


def update_status(db: Session, complaint_id: uuid.UUID, new_status: ComplaintStatus) -> Complaint:
    complaint = get_complaint(db, complaint_id)
    complaint.status = new_status
    db.commit()
    db.refresh(complaint)
    return complaint


def save_complaint_image(db: Session, complaint_id: uuid.UUID, file: UploadFile) -> ComplaintImage:
    """Validate and persist an uploaded image to disk, then record it.
    Raises ComplaintNotFoundError / InvalidImageError on failure — no
    partial state is left behind (the file is only written after
    validation passes)."""

    complaint = get_complaint(db, complaint_id)  # raises ComplaintNotFoundError if missing

    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise InvalidImageError(
            f"Unsupported image type '{file.content_type}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_CONTENT_TYPES))}"
        )

    contents = file.file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise InvalidImageError(f"Image exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    stored_filename = f"{uuid.uuid4()}{ext}"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_filename)

    with open(stored_path, "wb") as f:
        f.write(contents)

    image = ComplaintImage(
        complaint_id=complaint.id,
        file_path=stored_path,
        original_filename=file.filename,
        content_type=file.content_type,
        file_size_bytes=len(contents),
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image
