"""
Dashboard endpoint: one aggregate summary call for the frontend's stat
strip, status/type breakdowns, and daily trend chart.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import dashboard_service

router = APIRouter()


@router.get("/summary", summary="Aggregate stats for the dashboard")
def summary(
    trend_days: int = Query(30, ge=1, le=10000),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return dashboard_service.get_summary(db, trend_days=trend_days)
