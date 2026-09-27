import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from app.database import Base


class ComplaintSource(str, enum.Enum):
    PORTAL = "portal"
    MOBILE_APP = "mobile_app"
    EMAIL = "email"
    SOCIAL_MEDIA = "social_media"
    HISTORICAL_IMPORT = "historical_import"  # bulk-loaded from open-data sources, see datasets/


class ComplaintType(str, enum.Enum):
    ILLEGAL_PARKING = "illegal_parking"
    DOUBLE_PARKING = "double_parking"
    NO_PARKING_ZONE = "no_parking_zone"
    FOOTPATH_PARKING = "footpath_parking"
    EMERGENCY_EXIT_BLOCKING = "emergency_exit_blocking"
    UNCLASSIFIED = "unclassified"


class ComplaintStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    RESOLVED = "resolved"


class Complaint(Base):
    """
    A single parking-violation complaint, from raw submission through the
    full AI pipeline (NLP cleaning -> classification -> duplicate check ->
    geocoding). Fields populated later in the pipeline start out NULL.
    """

    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Submitter may be null for anonymous / email / social-media complaints
    # that aren't tied to a registered account.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    source: Mapped[ComplaintSource] = mapped_column(
        Enum(
            ComplaintSource,
            name="complaint_source",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    # --- Raw input ---
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    location_text: Mapped[str] = mapped_column(Text, nullable=True)  # free-text location as submitted
    contact_name: Mapped[str] = mapped_column(String(150), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)

    # --- NLP pipeline outputs (populated by NLP module) ---
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=True)
    extracted_location_entity: Mapped[str] = mapped_column(Text, nullable=True)  # NER output
    complaint_type: Mapped[ComplaintType] = mapped_column(
        Enum(
            ComplaintType,
            name="complaint_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=ComplaintType.UNCLASSIFIED,
    )
    classification_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    # --- Duplicate detection (Sentence-BERT + cosine similarity) ---
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id"), nullable=True
    )
    duplicate_similarity_score: Mapped[float] = mapped_column(Float, nullable=True)
    # Sentence-BERT embedding of `cleaned_text`, stored so duplicate checks
    # against future complaints don't require re-embedding this one.
    embedding: Mapped[list] = mapped_column(JSON, nullable=True)

    # --- GIS: geocoded point, stored as PostGIS geography for accurate
    # distance/heatmap queries (SRID 4326 = WGS84 lat/lng) ---
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)  # resolved/normalized address

    status: Mapped[ComplaintStatus] = mapped_column(
    Enum(
        ComplaintStatus,
        name="complaint_status",
        values_callable=lambda enum_cls: [member.value for member in enum_cls],
    ),
    default=ComplaintStatus.PENDING,
    nullable=False,
)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # --- Relationships ---
    submitted_by = relationship("User", back_populates="complaints", foreign_keys=[user_id])
    duplicate_of = relationship("Complaint", remote_side=[id])
    images = relationship("ComplaintImage", back_populates="complaint", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Complaint id={self.id} type={self.complaint_type} status={self.status}>"
