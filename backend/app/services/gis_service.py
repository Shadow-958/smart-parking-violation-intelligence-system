"""
GIS service: geocoding orchestration, GeoJSON export for the Leaflet map,
heatmap point export, and hotspot clustering via PostGIS's ST_ClusterDBSCAN.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from geoalchemy2.shape import to_shape
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models.complaint import Complaint, ComplaintStatus, ComplaintType
from app.models.hotspot import Hotspot
from app.models.officer_recommendation import OfficerRecommendation
from app.services import complaint_service, geocoding_service
from app.services.geo_math import haversine_meters

settings = get_settings()


class GeocodingSkippedError(Exception):
    """Raised when a complaint has neither location_text nor
    extracted_location_entity to geocode from."""


def point_to_latlng(geom) -> Tuple[float, float]:
    point = to_shape(geom)
    return point.y, point.x  # shapely Point: .x = lon, .y = lat


def geocode_complaint_in_place(complaint: Complaint) -> None:
    """Resolves this complaint's location to coordinates and sets
    complaint.geom/address — does NOT commit; the caller controls the
    transaction (this is what lets nlp_service chain this into the same
    commit as the rest of the NLP stage).

    Prefers `location_text` (what the citizen typed) over
    `extracted_location_entity` (the NLP module's NER guess), since a
    person describing where they are is usually more precise/reliable
    than an entity span pulled out of free text.
    """
    query = complaint.location_text or complaint.extracted_location_entity
    if not query:
        raise GeocodingSkippedError("No location_text or extracted_location_entity to geocode")

    lat, lon, display_name = geocoding_service.geocode(query)
    complaint.geom = f"SRID=4326;POINT({lon} {lat})"
    complaint.address = display_name


def geocode_complaint(db: Session, complaint: Complaint) -> Complaint:
    """Public entrypoint for standalone geocoding (the manual retry
    endpoint): geocodes and commits in one step."""
    geocode_complaint_in_place(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def geocode_complaint_by_id(complaint_id: uuid.UUID) -> None:
    """Background-task entrypoint — opens/closes its own session."""
    db = SessionLocal()
    try:
        complaint = complaint_service.get_complaint(db, complaint_id)
        geocode_complaint(db, complaint)
    except (complaint_service.ComplaintNotFoundError, GeocodingSkippedError, geocoding_service.GeocodingError):
        pass
    finally:
        db.close()


def get_complaints_geojson(
    db: Session,
    *,
    status_filter: Optional[ComplaintStatus] = None,
    complaint_type: Optional[ComplaintType] = None,
    submitted_from: Optional[datetime] = None,
    submitted_to: Optional[datetime] = None,
) -> dict:
    """Returns a GeoJSON FeatureCollection of geocoded complaints for the
    map. Only non-sensitive fields are exposed as properties — raw_text
    and contact_* deliberately stay out of this layer; use
    GET /api/complaints/{id} for full detail once you have a feature's id."""
    query = db.query(Complaint).filter(Complaint.geom.isnot(None))
    if status_filter is not None:
        query = query.filter(Complaint.status == status_filter)
    if complaint_type is not None:
        query = query.filter(Complaint.complaint_type == complaint_type)
    if submitted_from is not None:
        query = query.filter(Complaint.submitted_at >= submitted_from)
    if submitted_to is not None:
        query = query.filter(Complaint.submitted_at <= submitted_to)

    features = []
    for complaint in query.all():
        lat, lng = point_to_latlng(complaint.geom)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": {
                    "id": str(complaint.id),
                    "complaint_type": complaint.complaint_type.value,
                    "status": complaint.status.value,
                    "submitted_at": complaint.submitted_at.isoformat(),
                    "address": complaint.address,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


def get_heatmap_points(db: Session, lookback_days: int = 0) -> List[dict]:
    """Returns [{lat, lng, weight}] for geocoded, non-duplicate complaints.
    `lookback_days=0` means all dates (imported datasets can be years old)."""
    query = (
        db.query(Complaint)
        .filter(Complaint.geom.isnot(None))
        .filter(Complaint.status != ComplaintStatus.DUPLICATE)
    )
    if lookback_days > 0:
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        query = query.filter(Complaint.submitted_at >= cutoff)

    points = []
    for complaint in query.all():
        lat, lng = point_to_latlng(complaint.geom)
        points.append({"lat": lat, "lng": lng, "weight": 1.0})
    return points


def recompute_hotspots(
    db: Session,
    period_days: int = 0,
    eps_meters: float = 150.0,
    min_points: int = 3,
) -> List[Hotspot]:
    """
    Clusters geocoded, non-duplicate/non-rejected complaints using PostGIS
    ST_ClusterDBSCAN, then replaces the entire `hotspots` table.

    `period_days=0` includes all dates. A rolling window still drops this
    project's 2020 import, which is most of the map points.
    """
    period_end = datetime.utcnow()
    period_start = (
        period_end - timedelta(days=period_days)
        if period_days > 0
        else datetime(1970, 1, 1)
    )
    date_filter = "AND submitted_at >= :period_start" if period_days > 0 else ""

    rows = (
        db.execute(
            text(
                f"""
                SELECT
                    ST_Y(geom::geometry) AS lat,
                    ST_X(geom::geometry) AS lng,
                    ST_ClusterDBSCAN(ST_Transform(geom::geometry, 3857), eps := :eps, minpoints := :minpoints)
                        OVER () AS cluster_id
                FROM complaints
                WHERE geom IS NOT NULL
                  {date_filter}
                  AND status NOT IN ('duplicate', 'rejected')
                """
            ),
            {"eps": eps_meters, "minpoints": min_points, "period_start": period_start},
        )
        .mappings()
        .all()
    )

    clusters: Dict[int, List[Tuple[float, float]]] = {}
    for row in rows:
        cluster_id = row["cluster_id"]
        if cluster_id is None:
            continue  # noise point — PostGIS's DBSCAN convention for unclustered rows
        clusters.setdefault(cluster_id, []).append((row["lat"], row["lng"]))

    db.query(OfficerRecommendation).update({OfficerRecommendation.hotspot_id: None})
    db.query(Hotspot).delete()

    if not clusters:
        db.commit()
        return []

    max_count = max(len(points) for points in clusters.values())
    created: List[Hotspot] = []

    for points in clusters.values():
        count = len(points)
        centroid_lat = sum(p[0] for p in points) / count
        centroid_lng = sum(p[1] for p in points) / count
        radius = max(
            (haversine_meters(centroid_lat, centroid_lng, lat, lng) for lat, lng in points),
            default=0.0,
        )

        hotspot = Hotspot(
            geom=f"SRID=4326;POINT({centroid_lng} {centroid_lat})",
            radius_meters=max(radius, 50.0),  # floor so tight clusters still render visibly
            violation_count=count,
            risk_score=round(count / max_count, 3),
            period_start=period_start,
            period_end=period_end,
        )
        db.add(hotspot)
        created.append(hotspot)

    db.commit()
    for hotspot in created:
        db.refresh(hotspot)
    return created


def get_hotspots(db: Session) -> List[dict]:
    """Returns current hotspots as plain dicts with lat/lng extracted from
    their PostGIS geometry, ready for JSON serialization."""
    hotspots = db.query(Hotspot).order_by(Hotspot.risk_score.desc()).all()
    result = []
    for h in hotspots:
        lat, lng = point_to_latlng(h.geom)
        result.append(
            {
                "id": str(h.id),
                "lat": lat,
                "lng": lng,
                "radius_meters": h.radius_meters,
                "violation_count": h.violation_count,
                "risk_score": h.risk_score,
                "period_start": h.period_start.isoformat(),
                "period_end": h.period_end.isoformat(),
                "created_at": h.created_at.isoformat(),
            }
        )
    return result
