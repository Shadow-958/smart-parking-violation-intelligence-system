import enum
import uuid
from datetime import datetime, time

from sqlalchemy import Float, DateTime, Time, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from app.database import Base


class RecommendationStatus(str, enum.Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    COMPLETED = "completed"


class OfficerRecommendation(Base):
    """
    A suggested enforcement action: patrol this location, during this time
    window, at this priority — generated from Hotspot + Prediction data and
    optionally assigned to a specific officer (User with role=OFFICER).
    """

    __tablename__ = "officer_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    hotspot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hotspots.id"), nullable=True
    )
    officer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    recommended_time_start: Mapped[time] = mapped_column(Time, nullable=True)
    recommended_time_end: Mapped[time] = mapped_column(Time, nullable=True)

    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(
            RecommendationStatus,
            name="recommendation_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=RecommendationStatus.SUGGESTED,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    hotspot = relationship("Hotspot", back_populates="officer_recommendations")
    officer = relationship("User", back_populates="officer_recommendations", foreign_keys=[officer_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OfficerRecommendation id={self.id} priority={self.priority_score} status={self.status}>"
