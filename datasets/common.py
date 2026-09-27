"""
Shared helpers for the historical dataset import scripts
(import_nyc_parking_violations.py, import_sf_parking_citations.py,
import_chicago_parking_violations.py).

These scripts are meant to be run manually/offline by an operator with
network access and DB credentials — they are NOT wired into the FastAPI
app or triggered by any endpoint, since bulk-loading potentially hundreds
of thousands of historical rows has very different operational
characteristics (long-running, resumable, rate-limit-aware) than a
request/response API call.
"""

import os
import sys
import time
from typing import Iterable, List, Optional

import httpx

# Let these scripts import the backend's app.* modules without being
# installed as a package.
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.database import SessionLocal  # noqa: E402
from app.models.complaint import Complaint, ComplaintSource, ComplaintStatus  # noqa: E402


def fetch_socrata_records(
    domain: str,
    dataset_id: str,
    *,
    page_size: int = 1000,
    max_records: Optional[int] = None,
    where: Optional[str] = None,
    app_token: Optional[str] = None,
) -> Iterable[dict]:
    """Pages through a Socrata (SODA) dataset and yields records as
    dicts. Socrata's default rate limit without an app token is fairly
    low and shared across all unauthenticated callers — request a free
    app token at https://evergreen.data.socrata.com/login for anything
    beyond a small sample, and pass it via `app_token` (or the
    SOCRATA_APP_TOKEN env var, which each import_*.py script reads)."""
    base_url = f"https://{domain}/resource/{dataset_id}.json"
    offset = 0
    fetched = 0
    headers = {"X-App-Token": app_token} if app_token else {}

    with httpx.Client(timeout=30.0, headers=headers) as client:
        while True:
            params = {"$limit": page_size, "$offset": offset}
            if where:
                params["$where"] = where

            response = client.get(base_url, params=params)
            response.raise_for_status()
            batch = response.json()

            if not batch:
                return

            for record in batch:
                yield record
                fetched += 1
                if max_records is not None and fetched >= max_records:
                    return

            offset += page_size
            time.sleep(0.2)  # a little courtesy delay between pages


def insert_historical_complaints(records: List[dict], *, batch_size: int = 500) -> int:
    """
    Bulk-inserts already-cleaned records (see each script's
    `clean_record`) as Complaint rows with source=HISTORICAL_IMPORT,
    status=APPROVED (these are already-issued citations, not pending
    reports awaiting triage).

    Each record dict is expected to have: raw_text, submitted_at, and
    at least one of location_text / geom_wkt (records with neither are
    skipped — there'd be nothing for the GIS module to plot). geom_wkt,
    if present, should look like "SRID=4326;POINT(lon lat)".

    Uses bulk_save_objects (not the ORM's normal add/commit-per-row) since
    this is meant for potentially tens of thousands of rows at once;
    that trades some ORM conveniences (no auto-populated `id` on the
    Python objects afterward) for materially better insert performance.
    """
    db = SessionLocal()
    inserted = 0
    try:
        batch = []
        for record in records:
            if not record.get("location_text") and not record.get("geom_wkt"):
                continue

            batch.append(
                Complaint(
                    source=ComplaintSource.HISTORICAL_IMPORT,
                    raw_text=record["raw_text"],
                    location_text=record.get("location_text"),
                    complaint_type=record.get("complaint_type"),
                    status=ComplaintStatus.APPROVED,
                    submitted_at=record["submitted_at"],
                    address=record.get("address"),
                    geom=record.get("geom_wkt"),
                )
            )

            if len(batch) >= batch_size:
                db.bulk_save_objects(batch)
                db.commit()
                inserted += len(batch)
                batch = []

        if batch:
            db.bulk_save_objects(batch)
            db.commit()
            inserted += len(batch)

        return inserted
    finally:
        db.close()
