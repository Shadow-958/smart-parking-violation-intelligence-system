# Datasets

Scripts for backfilling the `complaints` table with historical parking
violation data, so Module 7's ML models have enough volume to train on
before real complaints accumulate. Records are inserted with
`source=historical_import`, `status=approved` (they're already-issued
citations, not pending reports), and are otherwise ordinary rows —
they'll be picked up by hotspot clustering, ML training, and enforcement
recommendations like any other complaint.

**These scripts are standalone command-line tools, not wired into the
API.** Bulk-loading tens of thousands of historical rows is a different
operation than the request/response app — run them manually with network
access and your `DATABASE_URL` set (they import `app.database` directly).

## Scripts

| Script | Source | Coordinates included? |
|---|---|---|
| `import_nyc_parking_violations.py` | NYC Open Data (`pvqr-7yc4`, verified live July 2026) | No — address only. See the script's docstring on why bulk-geocoding this isn't practical via the free Nominatim API used elsewhere in this project. |
| `import_sf_parking_citations.py` | DataSF (`ab4h-6ztd`, verified live July 2026) | Yes — DataSF geocodes on load. Field name for the coordinate wasn't verifiable offline; the script checks a few plausible shapes and documents how to confirm the real one. |
| `import_chicago_parking_violations.py` | Chicago Data Portal | **Dataset id not hardcoded** — I couldn't confirm a current, live Socrata id for Chicago parking tickets from this offline sandbox (most references found were one-off historical bulk extracts, not a maintained API endpoint). Pass `--dataset-id` yourself once you've found the current one; see the script's docstring. |

```bash
cd datasets
python import_nyc_parking_violations.py --max-records 5000
python import_sf_parking_citations.py --max-records 5000
python import_chicago_parking_violations.py --dataset-id <id-you-found> --max-records 5000
```

Set `SOCRATA_APP_TOKEN` (a free token from
https://evergreen.data.socrata.com/login) for anything beyond a small
sample — Socrata's unauthenticated rate limit is shared across every
caller worldwide and gets throttled quickly.

## Kaggle

The spec also mentions Kaggle as a source. I didn't write a Kaggle import
script: unlike the city portals above (which share the Socrata API and a
roughly consistent schema), Kaggle doesn't have one canonical "parking
violations" dataset — schemas vary widely between uploads, and Kaggle's
API requires a personal API key I have no way to obtain or verify
against here. If you pick a specific Kaggle dataset, the pattern in
`common.py` (a `clean_record()` function + `insert_historical_complaints()`)
should adapt easily: swap `fetch_socrata_records` for the Kaggle CLI
(`kaggle datasets download`) plus `pandas.read_csv`, and map that
dataset's columns into the same record shape (`raw_text`, `location_text`
or `geom_wkt`, `complaint_type`, `submitted_at`, `address`).

## OpenStreetMap

Already used live (not as a bulk import) — see
`backend/app/services/geocoding_service.py`, which geocodes individual
complaint locations against the public Nominatim API as part of the GIS
module's pipeline.

