import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ComplaintImage(Base):
    """
    An image uploaded alongside a complaint. YOLOv8 vehicle-detection
    results for this image live in the separate VehicleDetection table
    (one image can contain multiple detected vehicles).
    """

    __tablename__ = "complaint_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id"), nullable=False
    )

    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)

    # Whether this image has been through the CV pipeline yet
    processed: Mapped[bool] = mapped_column(default=False)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="images")
    vehicle_detections = relationship(
        "VehicleDetection", back_populates="complaint_image", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ComplaintImage id={self.id} complaint_id={self.complaint_id}>"
