"""
GIS endpoints: GeoJSON export for the Leaflet map, heatmap points, hotspot
listing/recomputation, and a manual geocode retry.

Map/heatmap/hotspot views are readable by any authenticated user (they
only expose aggregate/non-sensitive fields — see gis_service's docstrings
for exactly what's excluded); recomputing hotspots and retrying a failed
geocode are officer/admin actions.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.complaint import ComplaintStatus, ComplaintType
from app.models.user import User, UserRole
from app.services import complaint_service, gis_service

router = APIRouter()
settings = get_settings()


@router.get(
    "/complaints/geojson",
    summary="GeoJSON FeatureCollection of geocoded complaints, for the map",
)
def complaints_geojson(
    status_filter: Optional[ComplaintStatus] = Query(None, alias="status"),
    complaint_type: Optional[ComplaintType] = None,
    submitted_from: Optional[datetime] = None,
    submitted_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return gis_service.get_complaints_geojson(
        db,
        status_filter=status_filter,
        complaint_type=complaint_type,
        submitted_from=submitted_from,
        submitted_to=submitted_to,
    )


@router.get("/heatmap", summary="Weighted lat/lng points for a Leaflet.heat layer")
def heatmap(
    lookback_days: int = Query(settings.HEATMAP_LOOKBACK_DAYS, ge=0, le=10000),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return gis_service.get_heatmap_points(db, lookback_days=lookback_days)


@router.get("/hotspots", summary="Current computed hotspots")
def list_hotspots(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return gis_service.get_hotspots(db)


@router.post(
    "/hotspots/recompute",
    summary="Recompute hotspots from recent complaints (officer/admin only)",
)
def recompute_hotspots(
    period_days: int = Query(settings.HOTSPOT_PERIOD_DAYS, ge=0, le=10000),
    eps_meters: float = Query(settings.HOTSPOT_EPS_METERS, gt=0),
    min_points: int = Query(settings.HOTSPOT_MIN_POINTS, ge=2),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    hotspots = gis_service.recompute_hotspots(
        db, period_days=period_days, eps_meters=eps_meters, min_points=min_points
    )
    return {"created": len(hotspots), "hotspots": gis_service.get_hotspots(db)}


@router.post(
    "/geocode/{complaint_id}",
    summary="Manually retry geocoding for a complaint (officer/admin only)",
)
def retry_geocode(
    complaint_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    try:
        complaint = complaint_service.get_complaint(db, complaint_id)
    except complaint_service.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    try:
        gis_service.geocode_complaint(db, complaint)
    except gis_service.GeocodingSkippedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # geocoding_service.GeocodingError, network issues, etc.
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return {"id": str(complaint.id), "address": complaint.address}
