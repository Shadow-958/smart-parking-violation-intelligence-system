# API Documentation

FastAPI auto-generates interactive docs once the server is running:

* Swagger UI: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc

This file tracks endpoints in prose as each module adds them, for anyone
browsing the repo without running the server.

## Module 1 — Health & bootstrap

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | none | Service metadata (name, status, environment) |
| GET | `/health` | none | Confirms the API process is up and the database is reachable |

## Module 2 — Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | none | Create a citizen account. 400 if username/email already taken. |
| POST | `/api/auth/login` | none | OAuth2 password grant (form fields `username`, `password`). Returns a bearer JWT. |
| GET | `/api/auth/me` | Bearer token | Returns the authenticated user's profile. |

**Roles:** `citizen`, `officer`, `admin` (see `UserRole` in `app/models/user.py`).
Registration always creates a `citizen` account; officer/admin
provisioning is an admin-only action to be added in the Admin Panel
module, not something a user can self-select at signup.

**Using the token:** send `Authorization: Bearer <access_token>` on
subsequent requests. Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES`
(default 8 hours, configurable via environment variable).

## Module 3 — Complaint management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/complaints` | optional | Submit a complaint. Attaches to the logged-in user if a token is sent; otherwise anonymous (relies on `contact_*` fields). |
| GET | `/api/complaints/me` | Bearer token | The caller's own complaints, paginated. |
| GET | `/api/complaints` | officer/admin | All complaints, with `status`, `complaint_type`, `source`, `is_duplicate`, `search`, `submitted_from`/`submitted_to` filters, pagination. |
| GET | `/api/complaints/{id}` | owner or officer/admin | Full complaint detail, including attached images. |
| PATCH | `/api/complaints/{id}/status` | officer/admin | Transition status (`pending`/`approved`/`rejected`/`duplicate`/`resolved`). |
| POST | `/api/complaints/{id}/images` | owner or officer/admin | Upload a photo (jpeg/png/webp, size-capped by `MAX_UPLOAD_SIZE_MB`). |

**Note:** `complaint_type`, `cleaned_text`, `duplicate_of_id`, and `address`
all come back `null`/`unclassified` until the corresponding AI module runs
— this module only handles storage and retrieval, not analysis.

## Module 4 — NLP

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/nlp/analyze/{id}` | officer/admin | Manually re-run the NLP pipeline on a complaint. Runs automatically as a background task on submission already — this is for re-processing (e.g. after a correction). |

Automatic pipeline (triggered by `POST /api/complaints`, no separate call
needed): clean text → extract location entity → classify complaint type
→ compute embedding → check for duplicates. Configurable via
`NLP_USE_TRANSFORMER_CLASSIFIER`, `NLP_DUPLICATE_THRESHOLD`,
`NLP_DUPLICATE_LOOKBACK_DAYS`, `SENTENCE_TRANSFORMER_MODEL` (see
`.env.example`).

## Module 5 — Computer Vision

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/vision/detections/{image_id}` | owner or officer/admin | Vehicle detections for a complaint image. |
| POST | `/api/vision/analyze/{image_id}` | officer/admin | Manually re-run YOLOv8 detection. Runs automatically as a background task on upload already. |

Automatic pipeline (triggered by `POST /api/complaints/{id}/images`):
detect vehicles (car/motorcycle/bus/truck, filtered from the full COCO
class set) → confidence-gate each detection into
`is_illegal_parking`/`illegal_parking_reason`. Configurable via
`YOLO_WEIGHTS`, `YOLO_CONFIDENCE_THRESHOLD`,
`VISION_HIGH_CONFIDENCE_THRESHOLD` (see `.env.example`). **Note:**
`is_illegal_parking=True` means "worth an officer's attention", not an
independently confirmed violation — see the docstring in
`ai_models/computer_vision/illegal_parking.py` for why.

## Module 6 — GIS

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/gis/complaints/geojson` | any authenticated user | GeoJSON `FeatureCollection` of geocoded complaints, filterable by `status`, `complaint_type`, `submitted_from`/`submitted_to`. Properties exclude `raw_text`/`contact_*`. |
| GET | `/api/gis/heatmap` | any authenticated user | `[{lat, lng, weight}]` for a Leaflet.heat layer, filterable by `lookback_days`. |
| GET | `/api/gis/hotspots` | any authenticated user | Currently computed hotspots (centroid, radius, violation count, risk score). |
| POST | `/api/gis/hotspots/recompute` | officer/admin | Re-clusters recent complaints via PostGIS `ST_ClusterDBSCAN` and replaces the hotspots table. Params: `period_days`, `eps_meters`, `min_points`. |
| POST | `/api/gis/geocode/{id}` | officer/admin | Manually retry geocoding a complaint (e.g. after Nominatim was briefly unreachable). |

Automatic pipeline (chained onto the end of the NLP stage, no separate
call needed): geocode using `location_text` or, failing that,
`extracted_location_entity`, via the public Nominatim API. Best-effort —
failures don't block the rest of the NLP results and can be retried
manually. Configurable via `HOTSPOT_PERIOD_DAYS`, `HOTSPOT_EPS_METERS`,
`HOTSPOT_MIN_POINTS`, `HEATMAP_LOOKBACK_DAYS` (see `.env.example`).
Hotspot recomputation isn't scheduled automatically yet — run it
periodically (e.g. a cron hitting the recompute endpoint) or wire it into
the Deployment module's job scheduler.

## Module 7 — Machine Learning

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/predictions/train` | officer/admin | Trains hotspot-forecast + violation-probability models from all geocoded, non-duplicate complaints. 400 if fewer than `MIN_TRAINING_RECORDS` are available. |
| POST | `/api/predictions/hotspots/forecast` | officer/admin | Writes a 7-day-ahead forecast (`Prediction`, type `hotspot_forecast`) for each current hotspot. Falls back to a naive baseline if no model is trained yet. |
| GET | `/api/predictions/violation-probability` | any authenticated user | On-demand estimate for a given `lat`, `lng`, optional `timestamp` (defaults to now). |
| GET | `/api/predictions/enforcement-times` | any authenticated user | Recommended peak-hour enforcement windows per hotspot, from nearby complaint timestamps. |
| POST | `/api/predictions/recommendations/generate` | officer/admin | Ranks hotspots (risk + forecast blend) and writes `OfficerRecommendation` rows for the top `top_n`. Preserves recommendations already accepted/completed. |
| GET | `/api/predictions/recommendations` | officer/admin | Lists current recommendations, filterable by `status`. |

This completes the full NLP → CV → GIS → ML pipeline described in the
original spec. Configurable via `ML_MODEL_DIR`, `MIN_TRAINING_RECORDS`,
`ENFORCEMENT_LOOKBACK_DAYS`, `DEPLOYMENT_TOP_N` (see `.env.example`).

## Module 8 — Dashboard, image serving & reports

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/dashboard/summary` | any authenticated user | Total/pending/resolved/duplicate counts, hotspot count, open recommendation count, status/type breakdowns, daily trend (`trend_days`, default 30) and monthly trend (last 12 months). Powers the Dashboard page's stat strip and charts. |
| GET | `/api/complaints/images/{image_id}/file` | owner or officer/admin | Streams the actual image bytes — added because earlier modules only ever returned image *metadata*; the frontend needs this to render `<img>` tags. |
| GET | `/api/reports/complaints/csv` | officer/admin | CSV export of complaints, same filters as `GET /api/complaints` (`status`, `complaint_type`, `submitted_from`/`submitted_to`), capped at 50,000 rows. |

This completes every endpoint group named in the original spec's REST API
section. The React frontend (`frontend/src`) consumes all of the above,
plus every endpoint from Modules 2-7.
