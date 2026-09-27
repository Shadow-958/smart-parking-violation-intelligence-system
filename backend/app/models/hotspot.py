import uuid
from datetime import datetime

from sqlalchemy import Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from app.database import Base


class Hotspot(Base):
    """
    A geographic cluster of parking violations for a given time window,
    used to render heatmaps and drive officer-deployment recommendations.
    Computed periodically (e.g. nightly job) from approved complaints.
    """

    __tablename__ = "hotspots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Center point of the cluster; radius_meters approximates its extent
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    radius_meters: Mapped[float] = mapped_column(Float, default=200.0)

    violation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)  # normalized 0-1 severity

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    officer_recommendations = relationship("OfficerRecommendation", back_populates="hotspot")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Hotspot id={self.id} count={self.violation_count} risk={self.risk_score}>"
