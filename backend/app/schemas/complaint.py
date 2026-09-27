import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.complaint import ComplaintSource, ComplaintType, ComplaintStatus


class ComplaintCreate(BaseModel):
    """
    Submission payload. Fields populated later by the AI pipeline
    (cleaned_text, complaint_type, geom, etc.) are deliberately absent —
    those are set by the NLP/GIS modules, never by the client.

    Optional latitude/longitude allow the frontend to submit GPS coordinates
    directly, bypassing Nominatim geocoding for more reliable map placement.
    """

    raw_text: str = Field(min_length=10, max_length=5000)
    source: ComplaintSource = ComplaintSource.PORTAL
    location_text: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    contact_name: Optional[str] = Field(default=None, max_length=150)
    contact_phone: Optional[str] = Field(default=None, max_length=32)
    contact_email: Optional[EmailStr] = None


class ComplaintImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    processed: bool
    uploaded_at: datetime


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    source: ComplaintSource
    raw_text: str
    location_text: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None

    # NLP pipeline outputs — null until the NLP module processes this complaint
    cleaned_text: Optional[str] = None
    extracted_location_entity: Optional[str] = None
    complaint_type: ComplaintType
    classification_confidence: Optional[float] = None

    # Duplicate detection outputs — null until that stage runs
    is_duplicate: bool
    duplicate_of_id: Optional[uuid.UUID] = None
    duplicate_similarity_score: Optional[float] = None

    # GIS outputs — null until geocoding runs
    address: Optional[str] = None

    status: ComplaintStatus
    submitted_at: datetime
    updated_at: datetime

    images: List[ComplaintImageResponse] = []


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus


class PaginatedComplaints(BaseModel):
    items: List[ComplaintResponse]
    total: int
    skip: int
    limit: int
