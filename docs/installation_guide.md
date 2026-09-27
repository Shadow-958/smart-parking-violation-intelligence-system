# Installation Guide

For a two-command quick start, see the README. This guide covers
prerequisites, what each step actually does, and what to check if
something doesn't come up cleanly — worth reading in full the first time
you run this stack, since (per the honesty notes throughout this
project's README) most of it has been syntax-checked and reviewed but not
execution-tested end-to-end in the sandbox it was built in.

## Prerequisites

* **Docker** and **Docker Compose** (v2 — the `docker compose` subcommand,
  not the standalone `docker-compose` v1 binary the compose files here
  weren't tested against).
* **Network access** during the first build: the backend image downloads
  spaCy's English model, NLTK data, and a YOLOv8 checkpoint
  (Modules 4-5), and geocoding needs live network access at *runtime*
  too (Module 6, via the public Nominatim API) — this isn't a
  one-time download.
* A few GB of free disk space — the combined spaCy/transformers/torch/
  ultralytics/xgboost dependency set is large (see `backend/
  requirements-ai.txt`, `requirements-cv.txt`, `requirements-ml.txt`).

## Step 1: Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and at minimum set a real `SECRET_KEY` (`openssl rand -hex
32`) and `POSTGRES_PASSWORD` — the committed defaults are placeholders,
not even meant for local dev security, just to make the file runnable
out of the box.

## Step 2: Build and start the stack

```bash
docker compose up --build
```

This starts three services (see `docker-compose.yml`):

| Service | What it is | Port |
|---|---|---|
| `db` | PostgreSQL 16 + PostGIS 3.4 | 5432 |
| `backend` | FastAPI app (dev mode: `uvicorn --reload`) | 8000 |
| `frontend` | Vite dev server (React, hot reload) | 5173 |

The first build takes a while (see the network-access note above);
subsequent builds are much faster since each `requirements-*.txt` is its
own Docker layer.

## Step 3: Run database migrations

The app doesn't create tables automatically — migrations are explicit:

```bash
docker compose exec backend alembic upgrade head
```

This runs all three migrations in order (`0001` initial schema, `0002`
adds the embedding column, `0003` adds the historical-import source) and
enables the PostGIS extension. If this fails, it's usually either a
`DATABASE_URL` mismatch between `.env` and what `db` was actually
initialized with, or the `db` container not being fully healthy yet — a
few seconds' retry usually resolves the latter.

## Step 4: Verify

```bash
curl http://localhost:8000/health
# {"api":"ok","database":"ok"}
```

Then open http://localhost:5173 and http://localhost:8000/docs (FastAPI's
interactive Swagger UI — useful for exploring every endpoint directly,
independent of the frontend).

## Step 5: Create your first account

Register through the frontend (http://localhost:5173/register), or
directly:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin1","email":"admin@example.com","password":"changeme123","role":"admin"}'
```

Note: `POST /api/auth/register` always creates a `citizen` account
regardless of what `role` you pass (see `app/api/routes/auth.py`) —
that's deliberate, not a bug. To get an `officer`/`admin` account for
testing officer-only endpoints (status changes, hotspot recompute, ML
training, reports), update the row directly for now:

```sql
UPDATE users SET role = 'admin' WHERE username = 'admin1';
```

(A proper "admin promotes another user" endpoint is a reasonable Module
9+ addition once there's a UI reason to need one beyond local testing.)

## Getting real data flowing

The system works with zero data, but hotspots/ML predictions need
volume to be meaningful (see `MIN_TRAINING_RECORDS` in `app/config.py`).
Two ways to get there:

1. **Submit complaints through the app** — the full pipeline (NLP →
   geocoding → hotspot clustering) runs automatically.
2. **Backfill historical data** — see `datasets/README.md` for the NYC/
   SF/Chicago import scripts.

Once there's data with coordinates:

```bash
# Compute hotspots from geocoded complaints
curl -X POST http://localhost:8000/api/gis/hotspots/recompute \
  -H "Authorization: Bearer <admin-token>"

# Train the forecasting models (needs MIN_TRAINING_RECORDS geocoded complaints)
curl -X POST http://localhost:8000/api/predictions/train \
  -H "Authorization: Bearer <admin-token>"
```

In production, both of these run automatically — see
`backend/app/core/scheduler.py` and `docs/deployment_guide.md`.

## Troubleshooting

* **`docker compose build` fails downloading spaCy/YOLOv8/etc.** — check
  network access from the build environment; these downloads are not
  optional even for a minimal setup, since Modules 4-5 bake them into
  the image at build time.
* **`alembic upgrade head` errors on `CREATE EXTENSION postgis`** — the
  `db` container needs to be the `postgis/postgis` image (already set in
  `docker-compose.yml`), not plain `postgres`; if you've swapped it,
  swap it back.
* **Geocoding never populates `complaints.geom`** — confirm the backend
  container has outbound internet access; Nominatim is a live external
  dependency, not bundled (see `app/services/geocoding_service.py`).
* **Frontend shows a blank page / console errors about missing
  modules** — this frontend was built in an offline sandbox with no way
  to run `npm install` or a bundler (see the Module 8 notes in the
  README); if something doesn't compile, it's the most likely place for
  a real bug to be hiding relative to the backend.
