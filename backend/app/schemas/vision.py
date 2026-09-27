import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class VehicleDetectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_class: str
    detection_confidence: float
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    is_illegal_parking: Optional[bool] = None
    illegal_parking_reason: Optional[str] = None
    model_name: str
    model_version: Optional[str] = None
    detected_at: datetime


class ComplaintImageDetections(BaseModel):
    """Field name `vehicle_detections` matches the ORM relationship name
    on ComplaintImage so `from_attributes` can populate it directly."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    processed: bool
    vehicle_detections: List[VehicleDetectionResponse] = []
