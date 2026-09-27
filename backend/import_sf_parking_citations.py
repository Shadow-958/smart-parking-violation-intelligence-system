"""
Imports SF "SFMTA - Parking Citations" data via the Socrata API and
loads it into the `complaints` table as historical records
(source=historical_import, status=approved).

DATASET_ID (`ab4h-6ztd`, "SFMTA - Parking Citations" on data.sfgov.org)
was confirmed live as of July 2026.

Unlike NYC's dataset, SF's parking-citation data is already geocoded on
DataSF's end — per the dataset's own description, it includes "citation,
violation and location details" with "geolocation... based on a
geocoding process upon load" — so this script populates `geom` directly,
no separate bulk-geocoding pass needed. That said, I could not confirm
the *exact* field name for the coordinate by querying the live API from
this environment (Socrata schemas vary by dataset and I'm working
offline) — `_extract_latlon` below checks a few plausible shapes, but
run this yourself first and adjust if needed:

    curl "https://data.sfgov.org/resource/ab4h-6ztd.json?\\$limit=1"

Usage:
    python datasets/import_sf_parking_citations.py --max-records 5000
"""

import argparse
import os
from datetime import datetime
from typing import Optional, Tuple

from common import fetch_socrata_records, insert_historical_complaints
from app.models.complaint import ComplaintType  # noqa: E402 - path set up by importing common above

DOMAIN = "data.sf.gov"
DATASET_ID = "ab4h-6ztd"  # "SFMTA - Parking Citations" — see note above

# SF's violation codes/descriptions (e.g. "street cleaning", "meter
# expired") don't map cleanly onto this project's 5 complaint types
# either — same reasoning as the NYC script, defaulting to the general
# low-confidence bucket rather than guessing a mapping.
DEFAULT_COMPLAINT_TYPE = ComplaintType.ILLEGAL_PARKING


def _extract_latlon(raw: dict) -> Optional[Tuple[float, float]]:
    # Socrata Point/Location columns can appear as a GeoJSON-style dict
    # under various field names, or as separate lat/lon fields —
    # unverified against the live schema, see module docstring.
    for key in ("the_geom", "point", "geocoded_column", "location"):
        val = raw.get(key)
        if isinstance(val, dict) and "coordinates" in val:
            lon, lat = val["coordinates"][0], val["coordinates"][1]
            return float(lat), float(lon)

    lat = raw.get("latitude") or raw.get("lat")
    lon = raw.get("longitude") or raw.get("lon") or raw.get("lng")
    if lat and lon:
        return float(lat), float(lon)

    return None


def clean_record(raw: dict) -> Optional[dict]:
    issue_date = raw.get("citation_issued_datetime") or raw.get("issue_date")
    if not issue_date:
        return None
    try:
        submitted_at = datetime.fromisoformat(issue_date.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None

    location_text = raw.get("citation_location") or raw.get("location")
    latlon = _extract_latlon(raw)
    geom_wkt = f"SRID=4326;POINT({latlon[1]} {latlon[0]})" if latlon else None

    if not location_text and not geom_wkt:
        return None

    violation_desc = raw.get("violation_desc") or raw.get("violation") or "unspecified violation"

    return {
        "raw_text": f"Historical SF parking citation: {violation_desc} at {location_text or 'unknown location'}",
        "location_text": location_text,
        "complaint_type": DEFAULT_COMPLAINT_TYPE,
        "submitted_at": submitted_at,
        "address": location_text,
        "geom_wkt": geom_wkt,
    }


def main(max_records: int) -> None:
    app_token = os.environ.get("SOCRATA_APP_TOKEN")
    records = fetch_socrata_records(DOMAIN, DATASET_ID, max_records=max_records, app_token=app_token)
    cleaned = [r for r in (clean_record(raw) for raw in records) if r is not None]
    inserted = insert_historical_complaints(cleaned)
    geocoded = sum(1 for r in cleaned if r.get("geom_wkt"))
    print(f"Inserted {inserted} historical complaints from SF dataset {DATASET_ID} "
          f"({geocoded} with coordinates, {len(cleaned) - geocoded} location-text-only)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-records", type=int, default=5000)
    args = parser.parse_args()
    main(args.max_records)
