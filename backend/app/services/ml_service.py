"""
Orchestrates the Machine Learning stage of the AI workflow pipeline:
train forecasting/probability models from historical complaint data, and
turn the results (plus current hotspots) into concrete enforcement-time
and officer-deployment recommendations.

Actual model logic lives in ai_models/ml_prediction (dependency-free from
the web app, same pattern as ai_models/nlp and ai_models/computer_vision);
this module is the boundary that pulls data out of Postgres, engineers
features, and persists results.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from ai_models.ml_prediction import enforcement_time, features, hotspot_forecast, officer_deployment, violation_probability
from app.config import get_settings
from app.models.complaint import Complaint, ComplaintStatus
from app.models.officer_recommendation import OfficerRecommendation, RecommendationStatus
from app.models.prediction import Prediction, PredictionType
from app.services import gis_service

settings = get_settings()


class InsufficientTrainingDataError(Exception):
    """Raised when there aren't enough geocoded complaints to train on."""


def _forecast_model_path() -> str:
    return os.path.join(settings.ML_MODEL_DIR, "hotspot_forecast_xgboost.joblib")


def _probability_model_path() -> str:
    return os.path.join(settings.ML_MODEL_DIR, "violation_probability_xgboost.joblib")


def _load_forecast_model():
    path = _forecast_model_path()
    return hotspot_forecast.load(path) if os.path.exists(path) else None


def _load_probability_model():
    path = _probability_model_path()
    return violation_probability.load(path) if os.path.exists(path) else None


def _extract_training_records(db: Session) -> List[dict]:
    rows = (
        db.query(Complaint.geom, Complaint.submitted_at)
        .filter(Complaint.geom.isnot(None))
        .filter(Complaint.status != ComplaintStatus.DUPLICATE)
        .all()
    )
    records = []
    for geom, submitted_at in rows:
        lat, lon = gis_service.point_to_latlng(geom)
        records.append({"lat": lat, "lon": lon, "submitted_at": submitted_at})
    return records


def train_models(db: Session, min_records: int = 30) -> dict:
    """Trains both the hotspot-forecast and violation-probability models
    from all geocoded, non-duplicate complaints, and saves them to disk.

    Raises InsufficientTrainingDataError below `min_records` — training
    an XGBoost model on a handful of points produces something that
    *looks* like a real model without being one; better to say so plainly
    than silently ship an undertrained model (see hotspot_forecast.py's
    docstring)."""
    records = _extract_training_records(db)
    if len(records) < min_records:
        raise InsufficientTrainingDataError(
            f"Only {len(records)} geocoded complaints available; need at least {min_records}. "
            "Import historical data (see datasets/) or wait for more real complaints to accumulate."
        )

    bucketed = features.build_grid_time_counts(records)
    training_df = features.to_training_frame(bucketed)
    probability_training_df = features.to_probability_training_frame(records)

    os.makedirs(settings.ML_MODEL_DIR, exist_ok=True)

    forecast_model = hotspot_forecast.train(training_df)
    hotspot_forecast.save(forecast_model, _forecast_model_path())

    probability_model = violation_probability.train(probability_training_df)
    violation_probability.save(probability_model, _probability_model_path())

    return {
        "trained_at": datetime.utcnow().isoformat(),
        "training_records": len(records),
        "training_buckets": len(bucketed),
    }


def _forecast_for_hotspot(model, lat: float, lon: float) -> float:
    """Sums predicted counts across the next 7 days x 24 hours for this
    location's grid cell — a rough "expected violations next week"
    figure. `model` is assumed not None; callers handle the no-model
    fallback themselves."""
    import pandas as pd

    grid_lat, grid_lon = features.assign_grid_cell(lat, lon)
    rows = [
        {"grid_lat": grid_lat, "grid_lon": grid_lon, "day_of_week": day, "hour_of_day": hour}
        for day in range(7)
        for hour in range(24)
    ]
    features_df = pd.DataFrame(rows)
    return sum(hotspot_forecast.predict(model, features_df))


def forecast_hotspots(db: Session) -> List[Prediction]:
    """Produces a 7-day-ahead violation-count forecast for each current
    hotspot. Falls back to the hotspot's own observed violation_count
    (treat "next week" as "like the period just observed") if no model
    has been trained yet, so this degrades gracefully rather than
    hard-failing before anyone's called POST /api/predictions/train.

    Fully replaces prior HOTSPOT_FORECAST predictions — same
    snapshot-not-history reasoning as gis_service.recompute_hotspots."""
    model = _load_forecast_model()
    hotspots = gis_service.get_hotspots(db)

    db.query(Prediction).filter(Prediction.prediction_type == PredictionType.HOTSPOT_FORECAST).delete()

    now = datetime.utcnow()
    created: List[Prediction] = []
    for hotspot in hotspots:
        if model is not None:
            predicted_value = _forecast_for_hotspot(model, hotspot["lat"], hotspot["lng"])
            model_name, confidence = "xgboost_hotspot_forecast_v1", 0.6
        else:
            predicted_value = float(hotspot["violation_count"])
            model_name, confidence = "naive_baseline", 0.3

        prediction = Prediction(
            prediction_type=PredictionType.HOTSPOT_FORECAST,
            geom=f"SRID=4326;POINT({hotspot['lng']} {hotspot['lat']})",
            predicted_value=round(predicted_value, 2),
            confidence=confidence,
            model_name=model_name,
            valid_from=now,
            valid_to=now + timedelta(days=7),
        )
        db.add(prediction)
        created.append(prediction)

    db.commit()
    for p in created:
        db.refresh(p)
    return created


def estimate_violation_probability(lat: float, lon: float, timestamp: datetime) -> dict:
    """On-demand single-point estimate (spec item: "estimate violation
    probability") — naturally an interactive query ("should I patrol this
    corner right now?") rather than something to precompute for every
    possible location/time combination."""
    model = _load_probability_model()
    if model is None:
        return {
            "probability": None,
            "model_name": None,
            "note": "No trained model yet — run POST /api/predictions/train first.",
        }

    import pandas as pd

    grid_lat, grid_lon = features.assign_grid_cell(lat, lon)
    features_df = pd.DataFrame(
        [{"grid_lat": grid_lat, "grid_lon": grid_lon, "day_of_week": timestamp.weekday(), "hour_of_day": timestamp.hour}]
    )
    probability = violation_probability.predict_proba(model, features_df)[0]
    return {"probability": round(probability, 4), "model_name": "xgboost_violation_probability_v1"}


def _nearby_complaint_timestamps(
    db: Session, lat: float, lon: float, radius_meters: float, lookback_days: int
) -> List[datetime]:
    cutoff = (
        datetime.utcnow() - timedelta(days=lookback_days)
        if lookback_days > 0
        else datetime(1970, 1, 1)
    )
    rows = db.execute(
        text(
            """
            SELECT submitted_at
            FROM complaints
            WHERE geom IS NOT NULL
              AND submitted_at >= :cutoff
              AND status NOT IN ('duplicate', 'rejected')
              AND ST_DWithin(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    :radius
                  )
            """
        ),
        {"cutoff": cutoff, "lon": lon, "lat": lat, "radius": radius_meters},
    ).fetchall()
    return [row[0] for row in rows]


def get_enforcement_recommendations(db: Session, lookback_days: int = 0) -> List[dict]:
    """Per-hotspot recommended enforcement time windows — read-only, does
    not persist anything (OfficerRecommendation rows are a separate,
    explicit step via generate_officer_recommendations)."""
    hotspots = gis_service.get_hotspots(db)
    results = []
    for hotspot in hotspots:
        timestamps = _nearby_complaint_timestamps(
            db, hotspot["lat"], hotspot["lng"], hotspot["radius_meters"], lookback_days
        )
        windows = enforcement_time.recommend_enforcement_windows(timestamps)
        results.append({
            "hotspot_id": hotspot["id"],
            "lat": hotspot["lat"],
            "lng": hotspot["lng"],
            "violation_count": hotspot["violation_count"],
            "risk_score": hotspot["risk_score"],
            "windows": windows,
        })
    return results


def generate_officer_recommendations(
    db: Session, lookback_days: int = 0, top_n: int = 10
) -> List[OfficerRecommendation]:
    """
    For each current hotspot: pulls nearby historical complaint
    timestamps, recommends peak enforcement hours, blends hotspot risk
    with a forecast into a priority score, and writes
    OfficerRecommendation rows for the top-ranked locations.

    Only clears previously *suggested* (not yet accepted/completed)
    recommendations before inserting fresh ones — an officer's decision
    on an existing recommendation isn't silently discarded just because
    hotspots were recomputed.
    """
    hotspots = gis_service.get_hotspots(db)
    if not hotspots:
        return []

    model = _load_forecast_model()
    forecasts_by_id: Dict[str, float] = {
        h["id"]: (_forecast_for_hotspot(model, h["lat"], h["lng"]) if model is not None else h["violation_count"])
        for h in hotspots
    }

    ranked = officer_deployment.rank_deployment_locations(hotspots, forecasts_by_id, top_n=top_n)

    db.query(OfficerRecommendation).filter(OfficerRecommendation.status == RecommendationStatus.SUGGESTED).delete()

    created: List[OfficerRecommendation] = []
    for hotspot in ranked:
        timestamps = _nearby_complaint_timestamps(
            db, hotspot["lat"], hotspot["lng"], hotspot["radius_meters"], lookback_days
        )
        windows = enforcement_time.recommend_enforcement_windows(timestamps, top_n=1)
        start_time = enforcement_time.hour_to_time(windows[0]["start_hour"]) if windows else None
        end_time = enforcement_time.hour_to_time(windows[0]["end_hour"]) if windows else None

        recommendation = OfficerRecommendation(
            hotspot_id=uuid.UUID(hotspot["id"]),
            geom=f"SRID=4326;POINT({hotspot['lng']} {hotspot['lat']})",
            recommended_time_start=start_time,
            recommended_time_end=end_time,
            priority_score=hotspot["priority_score"],
            status=RecommendationStatus.SUGGESTED,
        )
        db.add(recommendation)
        created.append(recommendation)

    db.commit()
    for r in created:
        db.refresh(r)
    return created
