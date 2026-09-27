"""
Orchestrates the Computer Vision stage of the AI workflow pipeline: run
YOLOv8 on a complaint image, assess each detected vehicle, and persist
VehicleDetection rows. Mirrors the structure of nlp_service.py — actual
model logic lives in ai_models/computer_vision (dependency-free from the
web app); this is the boundary that wires it into the ORM and config.
"""

import uuid

from sqlalchemy.orm import Session

from ai_models.computer_vision import detector, illegal_parking
from app.config import get_settings
from app.database import SessionLocal
from app.models.complaint_image import ComplaintImage
from app.models.vehicle_detection import VehicleDetection

settings = get_settings()


class ComplaintImageNotFoundError(Exception):
    """Raised when an image_id doesn't exist."""


def _get_image(db: Session, image_id: uuid.UUID) -> ComplaintImage:
    image = db.get(ComplaintImage, image_id)
    if image is None:
        raise ComplaintImageNotFoundError(f"Complaint image {image_id} not found")
    return image


def process_image(db: Session, image: ComplaintImage) -> ComplaintImage:
    """Runs vehicle detection against an already-loaded ComplaintImage and
    persists results. Safe to re-run (e.g. after a model upgrade): any
    prior VehicleDetection rows for this image are cleared first, so
    reprocessing doesn't accumulate duplicates."""

    db.query(VehicleDetection).filter(VehicleDetection.complaint_image_id == image.id).delete()

    detections = detector.detect_vehicles(
        image.file_path,
        weights=settings.YOLO_WEIGHTS,
        confidence_threshold=settings.YOLO_CONFIDENCE_THRESHOLD,
    )

    for det in detections:
        is_illegal, reason = illegal_parking.assess_detection(
            det.vehicle_class, det.confidence, settings.VISION_HIGH_CONFIDENCE_THRESHOLD
        )
        db.add(
            VehicleDetection(
                complaint_image_id=image.id,
                vehicle_class=det.vehicle_class,
                detection_confidence=det.confidence,
                bbox_x=det.bbox_x,
                bbox_y=det.bbox_y,
                bbox_width=det.bbox_width,
                bbox_height=det.bbox_height,
                is_illegal_parking=is_illegal,
                illegal_parking_reason=reason,
                model_name=settings.YOLO_WEIGHTS.replace(".pt", ""),
            )
        )

    image.processed = True
    db.commit()
    db.refresh(image)
    return image


def process_image_by_id(image_id: uuid.UUID) -> None:
    """Entry point for background tasks / the manual re-run endpoint —
    opens and closes its own DB session, same reasoning as
    nlp_service.process_complaint_by_id."""
    db = SessionLocal()
    try:
        image = _get_image(db, image_id)
        process_image(db, image)
    except ComplaintImageNotFoundError:
        pass  # image may have been deleted between scheduling and running
    finally:
        db.close()
