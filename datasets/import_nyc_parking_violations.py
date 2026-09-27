"""
Imports NYC "Parking Violations Issued" data via the Socrata API and
loads it into the `complaints` table as historical records
(source=historical_import, status=approved).

**Dataset note:** NYC publishes a new "Parking Violations Issued -
Fiscal Year YYYY" dataset every year rather than maintaining one
evergreen id. DATASET_ID below (`pvqr-7yc4`, Fiscal Year 2026) was
confirmed live on data.cityofnewyork.us as of July 2026 — update it to
whichever fiscal year(s) you want; browse
https://data.cityofnewyork.us/browse?q=parking+violations+issued for
the current list.

**No coordinates in this dataset.** NYC's parking-violation records
carry House Number/Street Name/Violation County, not lat/lon — so
importing this data does NOT geocode it for you. At import volume
(potentially millions of rows/year), the free public Nominatim API used
elsewhere in this project (rate-limited to ~1 req/sec, see
app/services/geocoding_service.py) is not practical for bulk geocoding.
This script leaves `geom` NULL for these rows: they still contribute to
NLP/ML text-based analysis and enforcement-time aggregation once
geocoded, but won't appear on the map/heatmap until geocoded (via a
self-hosted Nominatim / commercial bulk geocoder, or the existing manual
POST /api/gis/geocode/{id} run in bulk — impractically slowly, at this
volume — via a script of your own).

Usage:
    python datasets/import_nyc_parking_violations.py --max-records 5000
    SOCRATA_APP_TOKEN=xxx python datasets/import_nyc_parking_violations.py --max-records 50000
"""

import argparse
import os
from datetime import datetime
from typing import Optional

from common import fetch_socrata_records, insert_historical_complaints
from app.models.complaint import ComplaintType  # noqa: E402 - path set up by importing common above

DOMAIN = "data.cityofnewyork.us"
DATASET_ID = "pvqr-7yc4"  # "Parking Violations Issued - Fiscal Year 2026" — see note above

# NYC's violation codes are numeric (see the separate "DOF Parking
# Violation Codes" dataset, ncbg-6agr) and don't map cleanly onto this
# project's 5 complaint types without cross-referencing that code table.
# Rather than guess a mapping I can't verify, everything imports as
# ILLEGAL_PARKING — the same low-confidence general default the NLP
# classifier itself falls back to (see ai_models/nlp/classifier.py).
# Refine this once you've cross-referenced ncbg-6agr against the codes
# you actually care about.
DEFAULT_COMPLAINT_TYPE = ComplaintType.ILLEGAL_PARKING


def clean_record(raw: dict) -> Optional[dict]:
    issue_date = raw.get("issue_date")
    if not issue_date:
        return None

    submitted_at = None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            submitted_at = datetime.strptime(issue_date, fmt)
            break
        except ValueError:
            continue
    if submitted_at is None:
        return None

    house_number = (raw.get("house_number") or "").strip()
    street_name = (raw.get("street_name") or "").strip()
    county = (raw.get("violation_county") or "").strip()
    if not street_name:
        return None

    location_text = f"{house_number} {street_name}, {county}, New York, NY".strip()
    violation_desc = raw.get("violation_description") or raw.get("violation") or "unspecified violation"

    return {
        "raw_text": f"Historical NYC parking violation: {violation_desc} at {location_text}",
        "location_text": location_text,
        "complaint_type": DEFAULT_COMPLAINT_TYPE,
        "submitted_at": submitted_at,
        "address": location_text,
        "geom_wkt": None,  # see module docstring
    }


def main(max_records: int) -> None:
    app_token = os.environ.get("SOCRATA_APP_TOKEN")
    records = fetch_socrata_records(DOMAIN, DATASET_ID, max_records=max_records, app_token=app_token)
    cleaned = [r for r in (clean_record(raw) for raw in records) if r is not None]
    inserted = insert_historical_complaints(cleaned)
    print(f"Inserted {inserted} historical complaints from NYC dataset {DATASET_ID} "
          f"({len(cleaned)} cleaned of the records fetched)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-records", type=int, default=5000, help="Cap on records to fetch (default 5000)")
    args = parser.parse_args()
    main(args.max_records)
