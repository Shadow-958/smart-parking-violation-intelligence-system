"""
Imports Chicago parking-violation data via the Socrata API and loads it
into the `complaints` table as historical records
(source=historical_import, status=approved).

**Dataset id intentionally NOT hardcoded.** Unlike the NYC and SF
scripts in this folder, I could not confirm a single, current, live
Socrata dataset id for Chicago parking tickets from this offline
sandbox — most public references found point to one-off historical bulk
CSV extracts (e.g. ProPublica's il-ticket-loader, covering 2007-2018)
rather than a maintained live SODA endpoint, and Chicago's own data
portal may only surface current parking-ticket data via bulk
download/FOIA rather than a queryable dataset. Rather than hardcode an
unverified guess, this script requires you to supply the id yourself:

    1. Search https://data.cityofchicago.org/browse?q=parking (or a web
       search) for the current dataset, and copy its 4x4 id from the URL
       (the part that looks like "xxxx-xxxx").
    2. python datasets/import_chicago_parking_violations.py \\
           --dataset-id <the-id-you-found> --max-records 5000

If the schema you find uses different field names than assumed in
clean_record() below, adjust that function to match.

Usage:
    python datasets/import_chicago_parking_violations.py --dataset-id xxxx-xxxx
"""

import argparse
import os
from datetime import datetime
from typing import Optional

from common import fetch_socrata_records, insert_historical_complaints
from app.models.complaint import ComplaintType  # noqa: E402 - path set up by importing common above

DOMAIN = "data.cityofchicago.org"
DEFAULT_COMPLAINT_TYPE = ComplaintType.ILLEGAL_PARKING


def clean_record(raw: dict) -> Optional[dict]:
    issue_date = raw.get("issue_date") or raw.get("ticket_issue_date")
    if not issue_date:
        return None

    submitted_at = None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y"):
        try:
            submitted_at = datetime.strptime(issue_date, fmt)
            break
        except ValueError:
            continue
    if submitted_at is None:
        return None

    location_text = raw.get("violation_location") or raw.get("location") or raw.get("address")
    if not location_text:
        return None
    location_text = f"{location_text}, Chicago, IL"

    violation_desc = raw.get("violation_description") or raw.get("violation_code") or "unspecified violation"

    return {
        "raw_text": f"Historical Chicago parking violation: {violation_desc} at {location_text}",
        "location_text": location_text,
        "complaint_type": DEFAULT_COMPLAINT_TYPE,
        "submitted_at": submitted_at,
        "address": location_text,
        "geom_wkt": None,  # Chicago's raw ticket data isn't geocoded either, per available sources
    }


def main(dataset_id: str, max_records: int) -> None:
    app_token = os.environ.get("SOCRATA_APP_TOKEN")
    records = fetch_socrata_records(DOMAIN, dataset_id, max_records=max_records, app_token=app_token)
    cleaned = [r for r in (clean_record(raw) for raw in records) if r is not None]
    inserted = insert_historical_complaints(cleaned)
    print(f"Inserted {inserted} historical complaints from Chicago dataset {dataset_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-id", required=True, help="Socrata 4x4 dataset id (see module docstring)")
    parser.add_argument("--max-records", type=int, default=5000)
    args = parser.parse_args()
    main(args.dataset_id, args.max_records)
