"""
Standalone scheduler process for periodic jobs: hotspot recomputation
(+ officer recommendation regeneration) and ML model retraining. Both
were manual-only (POST endpoints) through Modules 6-7; this is what
actually runs them on a schedule in production.

**Deliberately NOT embedded in the API server's lifespan.** An
in-process APScheduler running inside a Gunicorn deployment with
multiple workers (see entrypoint.sh, GUNICORN_WORKERS) would start one
scheduler *per worker*, each independently deciding it's time to run the
job — silently duplicating every run. Instead, this runs as its own
single-replica process sharing the same image and code but never
handling HTTP traffic (see the `scheduler` service in
docker-compose.prod.yml, which overrides the container command to run
this module instead of the API server).

If you need this to survive scheduler-process restarts without missing
or double-running jobs, or need to run more than one replica of it,
look at APScheduler's persistent jobstores (e.g. SQLAlchemyJobStore) —
not implemented here since a single always-on replica is enough for this
project's expected job frequency (daily/weekly).
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import get_settings
from app.database import SessionLocal
from app.services import gis_service, ml_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scheduler")

settings = get_settings()


def recompute_hotspots_job() -> None:
    db = SessionLocal()
    try:
        hotspots = gis_service.recompute_hotspots(
            db,
            period_days=settings.HOTSPOT_PERIOD_DAYS,
            eps_meters=settings.HOTSPOT_EPS_METERS,
            min_points=settings.HOTSPOT_MIN_POINTS,
        )
        logger.info("Recomputed %d hotspots", len(hotspots))

        recommendations = ml_service.generate_officer_recommendations(
            db, lookback_days=settings.ENFORCEMENT_LOOKBACK_DAYS, top_n=settings.DEPLOYMENT_TOP_N
        )
        logger.info("Generated %d officer recommendations", len(recommendations))
    except Exception:
        logger.exception("Hotspot recompute job failed")
    finally:
        db.close()


def retrain_models_job() -> None:
    db = SessionLocal()
    try:
        result = ml_service.train_models(db, min_records=settings.MIN_TRAINING_RECORDS)
        logger.info("Retrained models: %s", result)

        forecasts = ml_service.forecast_hotspots(db)
        logger.info("Refreshed %d hotspot forecasts", len(forecasts))
    except ml_service.InsufficientTrainingDataError as exc:
        logger.info("Skipping this retrain cycle: %s", exc)
    except Exception:
        logger.exception("Model retraining job failed")
    finally:
        db.close()


def main() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        recompute_hotspots_job,
        "interval",
        hours=settings.HOTSPOT_RECOMPUTE_INTERVAL_HOURS,
        id="recompute_hotspots",
    )
    scheduler.add_job(
        retrain_models_job,
        "interval",
        hours=settings.MODEL_RETRAIN_INTERVAL_HOURS,
        id="retrain_models",
    )
    logger.info(
        "Scheduler started: hotspots every %dh, retraining every %dh",
        settings.HOTSPOT_RECOMPUTE_INTERVAL_HOURS,
        settings.MODEL_RETRAIN_INTERVAL_HOURS,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
