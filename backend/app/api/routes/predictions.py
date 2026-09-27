"""
ML prediction endpoints: train models from historical data, forecast
hotspots, estimate violation probability at a point, get recommended
enforcement time windows, and generate/list officer deployment
recommendations.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.officer_recommendation import OfficerRecommendation, RecommendationStatus
from app.models.user import User, UserRole
from app.services import gis_service, ml_service

router = APIRouter()
settings = get_settings()


@router.post(
    "/train",
    summary="Train the hotspot-forecast and violation-probability models (officer/admin only)",
)
def train(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    try:
        return ml_service.train_models(db, min_records=settings.MIN_TRAINING_RECORDS)
    except ml_service.InsufficientTrainingDataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/hotspots/forecast",
    summary="Generate 7-day-ahead hotspot forecasts (officer/admin only)",
)
def forecast_hotspots(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    predictions = ml_service.forecast_hotspots(db)
    return {"created": len(predictions)}


@router.get(
    "/violation-probability",
    summary="Estimate violation probability at a point in time/space",
)
def violation_probability(
    lat: float = Query(...),
    lng: float = Query(...),
    timestamp: Optional[datetime] = Query(None, description="Defaults to now"),
    _current_user: User = Depends(get_current_user),
):
    return ml_service.estimate_violation_probability(lat, lng, timestamp or datetime.utcnow())


@router.get("/enforcement-times", summary="Recommended enforcement time windows per hotspot")
def enforcement_times(
    lookback_days: int = Query(settings.ENFORCEMENT_LOOKBACK_DAYS, ge=0, le=10000),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return ml_service.get_enforcement_recommendations(db, lookback_days=lookback_days)


@router.post(
    "/recommendations/generate",
    summary="Generate officer deployment recommendations from current hotspots (officer/admin only)",
)
def generate_recommendations(
    lookback_days: int = Query(settings.ENFORCEMENT_LOOKBACK_DAYS, ge=0, le=10000),
    top_n: int = Query(settings.DEPLOYMENT_TOP_N, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    recommendations = ml_service.generate_officer_recommendations(db, lookback_days=lookback_days, top_n=top_n)
    return {"created": len(recommendations)}


@router.get("/recommendations", summary="List officer deployment recommendations (officer/admin only)")
def list_recommendations(
    status_filter: Optional[RecommendationStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    query = db.query(OfficerRecommendation)
    if status_filter is not None:
        query = query.filter(OfficerRecommendation.status == status_filter)

    results = []
    for rec in query.order_by(OfficerRecommendation.priority_score.desc()).all():
        lat, lng = gis_service.point_to_latlng(rec.geom)
        results.append(
            {
                "id": str(rec.id),
                "hotspot_id": str(rec.hotspot_id) if rec.hotspot_id else None,
                "officer_id": str(rec.officer_id) if rec.officer_id else None,
                "lat": lat,
                "lng": lng,
                "recommended_time_start": rec.recommended_time_start.isoformat() if rec.recommended_time_start else None,
                "recommended_time_end": rec.recommended_time_end.isoformat() if rec.recommended_time_end else None,
                "priority_score": rec.priority_score,
                "status": rec.status.value,
                "created_at": rec.created_at.isoformat(),
            }
        )
    return results
