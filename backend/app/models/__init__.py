"""
Import every model here so that `Base.metadata` is fully populated in one
place. Alembic's env.py imports this module (via app.database.Base) to
support --autogenerate.
"""

from app.models.user import User, UserRole  # noqa: F401
from app.models.complaint import (  # noqa: F401
    Complaint,
    ComplaintSource,
    ComplaintType,
    ComplaintStatus,
)
from app.models.complaint_image import ComplaintImage  # noqa: F401
from app.models.vehicle_detection import VehicleDetection  # noqa: F401
from app.models.prediction import Prediction, PredictionType  # noqa: F401
from app.models.hotspot import Hotspot  # noqa: F401
from app.models.officer_recommendation import (  # noqa: F401
    OfficerRecommendation,
    RecommendationStatus,
)
