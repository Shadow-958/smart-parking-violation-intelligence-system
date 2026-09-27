import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Float, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from app.database import Base


class PredictionType(str, enum.Enum):
    HOTSPOT_FORECAST = "hotspot_forecast"
    VIOLATION_PROBABILITY = "violation_probability"
    ENFORCEMENT_TIME = "enforcement_time"
    OFFICER_DEPLOYMENT = "officer_deployment"


class Prediction(Base):
    """
    Generic table for storing ML model outputs (XGBoost / Random Forest).
    `payload` holds prediction-type-specific structured detail (e.g. a
    recommended time window, or a ranked list of deployment locations)
    without needing a separate table per prediction type.
    """

    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    prediction_type: Mapped[PredictionType] = mapped_column(
    Enum(
        PredictionType,
        name="prediction_type",
        values_callable=lambda enum_cls: [member.value for member in enum_cls],
    ),
    nullable=False,
)
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    predicted_value: Mapped[float] = mapped_column(Float, nullable=True)  # e.g. probability 0-1
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=True)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "xgboost_hotspot_v1"
    model_version: Mapped[str] = mapped_column(String(50), nullable=True)

    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Prediction id={self.id} type={self.prediction_type} value={self.predicted_value}>"
