"""
Aggregate statistics for the dashboard's stat strip and charts. Kept as
plain dict-returning queries (not a heavy analytics layer) since this is
read-only summary data refreshed on every dashboard page load, not
something that needs precomputation.
"""

from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintStatus, ComplaintType
from app.models.hotspot import Hotspot
from app.models.officer_recommendation import OfficerRecommendation, RecommendationStatus


def get_summary(db: Session, trend_days: int = 30) -> dict:
    total_complaints = db.query(func.count(Complaint.id)).scalar() or 0
    duplicate_count = (
        db.query(func.count(Complaint.id)).filter(Complaint.is_duplicate.is_(True)).scalar() or 0
    )
    pending_count = (
        db.query(func.count(Complaint.id)).filter(Complaint.status == ComplaintStatus.PENDING).scalar() or 0
    )
    resolved_count = (
        db.query(func.count(Complaint.id)).filter(Complaint.status == ComplaintStatus.RESOLVED).scalar() or 0
    )

    by_status: Dict[str, int] = {
        row[0].value: row[1]
        for row in db.query(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status).all()
    }
    by_type: Dict[str, int] = {
        row[0].value: row[1]
        for row in db.query(Complaint.complaint_type, func.count(Complaint.id))
        .group_by(Complaint.complaint_type)
        .all()
    }

    cutoff = datetime.utcnow() - timedelta(days=trend_days)
    daily_rows = (
        db.query(func.date(Complaint.submitted_at), func.count(Complaint.id))
        .filter(Complaint.submitted_at >= cutoff)
        .group_by(func.date(Complaint.submitted_at))
        .order_by(func.date(Complaint.submitted_at))
        .all()
    )
    daily_trend: List[dict] = [{"date": str(day), "count": count} for day, count in daily_rows]

    monthly_cutoff = datetime.utcnow() - timedelta(days=365)
    monthly_rows = (
        db.query(func.to_char(Complaint.submitted_at, "YYYY-MM"), func.count(Complaint.id))
        .filter(Complaint.submitted_at >= monthly_cutoff)
        .group_by(func.to_char(Complaint.submitted_at, "YYYY-MM"))
        .order_by(func.to_char(Complaint.submitted_at, "YYYY-MM"))
        .all()
    )
    monthly_trend: List[dict] = [{"month": month, "count": count} for month, count in monthly_rows]

    hotspot_count = db.query(func.count(Hotspot.id)).scalar() or 0
    suggested_recommendations = (
        db.query(func.count(OfficerRecommendation.id))
        .filter(OfficerRecommendation.status == RecommendationStatus.SUGGESTED)
        .scalar()
        or 0
    )

    return {
        "total_complaints": total_complaints,
        "pending_count": pending_count,
        "resolved_count": resolved_count,
        "duplicate_count": duplicate_count,
        "hotspot_count": hotspot_count,
        "suggested_recommendations": suggested_recommendations,
        "by_status": by_status,
        "by_type": by_type,
        "daily_trend": daily_trend,
        "monthly_trend": monthly_trend,
    }
