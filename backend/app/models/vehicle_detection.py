import uuid
from datetime import datetime

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class VehicleDetection(Base):
    """
    A single detected vehicle (one row per bounding box) produced by the
    YOLOv8 computer-vision pipeline for a given complaint image.
    """

    __tablename__ = "vehicle_detections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    complaint_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaint_images.id"), nullable=False
    )

    vehicle_class: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "car", "truck", "motorcycle"
    detection_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Bounding box in pixel coordinates, normalized to the original image
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)

    is_illegal_parking: Mapped[bool] = mapped_column(Boolean, nullable=True)
    illegal_parking_reason: Mapped[str] = mapped_column(String(255), nullable=True)

    model_name: Mapped[str] = mapped_column(String(100), default="yolov8n")
    model_version: Mapped[str] = mapped_column(String(50), nullable=True)

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    complaint_image = relationship("ComplaintImage", back_populates="vehicle_detections")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<VehicleDetection id={self.id} class={self.vehicle_class} illegal={self.is_illegal_parking}>"
