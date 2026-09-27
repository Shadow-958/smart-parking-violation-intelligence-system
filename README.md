# Smart Parking Violation Intelligence and Decision Support System

An AI-powered platform that ingests parking-violation complaints from a
citizen portal, mobile app, email, and social media, then runs them through
an NLP → computer vision → GIS → machine-learning pipeline to surface
violation hotspots and recommend enforcement action.

**Stack:** FastAPI (Python) · React (Vite) · PostgreSQL + PostGIS · Docker

---

## Build status

This project is being built **incrementally, module by module**, per the
original spec. Each module is fully explained before moving to the next.

| # | Module | Status |
|---|--------|--------|
| 1 | Project setup & database design | ✅ Done |
| 2 | Authentication (JWT) | ✅ Done |
| 3 | Complaint management API | ✅ Done |
| 4 | NLP pipeline (cleaning, NER, classification, duplicate detection) | ✅ Done |
| 5 | Computer vision (YOLOv8 vehicle detection) | ✅ Done |
| 6 | GIS module (geocoding, PostGIS queries, heatmaps) | ✅ Done |
| 7 | Machine learning (hotspot forecasting, deployment recommendations) | ✅ Done |
| 8 | Dashboard & Admin Panel (full React UI) | ✅ Done |
| 9 | Deployment (production Docker, docs, diagrams) | ✅ Done (this delivery) |


## Getting started

```bash
# 1. Copy the environment template and fill in real secrets
cp .env.example .env

# 2. Start the stack
docker compose up --build

# 3. Check the API
curl http://localhost:8000/health

# 4. Open the frontend
open http://localhost:5173
```

### Running database migrations

```bash
docker compose exec backend alembic upgrade head
```

> **Note on this delivery:** most of this was written and syntax-checked
> in an offline sandbox (no internet access, so no `pip install`/`docker
> compose up`/model downloads), so it hasn't been run end-to-end against
> a live Postgres+PostGIS instance yet. Please run it in your own
> environment as the first step, and flag anything that doesn't come up
> cleanly. One thing to double check: **the backend's Docker build
> context changed in Module 4** from `./backend` to the project root, so
> its Dockerfile can also pull in `ai_models/` — if you had the old
> compose file cached, `docker compose build backend` to pick this up.
>
> Seven test files are genuinely dependency-free and were actually
> executed (not just compiled) in this sandbox, all passing:
> `tests/test_security.py`, `tests/test_complaint_service.py` (mocked DB),
> `tests/test_geo_math.py`,
> `ai_models/tests/test_classifier_and_similarity.py`,
> `ai_models/tests/test_illegal_parking_heuristic.py`,
> `ai_models/tests/test_features.py`, and
> `ai_models/tests/test_enforcement_and_deployment.py`. Everything
> touching spaCy/NLTK/transformers/sentence-transformers/ultralytics/
> xgboost/pandas/Postgres/Nominatim still needs your environment to
> verify. One difference from earlier modules: geocoding needs network
> access at **runtime** (every request that geocodes a new location), not
> just at Docker build time — if your deployment has no outbound internet
> access, geocoding will fail (harmlessly — see the best-effort handling
> in `nlp_service.py`) until that's addressed.
>
> **Module 9 specifically:** `docker-compose.prod.yml`, `Caddyfile`,
> `entrypoint.sh`, and `scheduler.py` are all syntax/logic-reviewed but
> **not** run end-to-end — I have no Docker daemon in this sandbox, so
> the production compose stack has never actually been brought up. The
> most likely things to need a real fix on first try: the Caddy domain
> placeholder (you must edit this — Caddy can't get a cert for
> `parking.example.com`), and whatever `GUNICORN_WORKERS` value is
> actually right for your hardware. Test the production stack in a
> staging environment before pointing real traffic at it.

## Project structure

```
smart-parking-violation-system/
├── backend/                # FastAPI app
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM models (7 tables)
│   │   ├── schemas/          # Pydantic request/response schemas (Module 2+)
│   │   ├── api/routes/       # Route handlers (Module 2+)
│   │   ├── core/             # Security, dependencies (Module 2+)
│   │   ├── services/         # Business logic (Module 3+)
│   │   ├── config.py         # Environment-driven settings
│   │   ├── database.py       # Engine/session/Base
│   │   └── main.py           # App entrypoint
│   ├── migrations/          # Alembic migrations
│   ├── tests/
│   ├── requirements.txt      # Core API/DB dependencies
│   ├── requirements-ai.txt   # Heavy NLP deps (Module 4)
│   ├── requirements-cv.txt   # Heavy computer vision deps (Module 5)
│   ├── requirements-ml.txt   # Heavy ML deps (Module 7)
│   └── Dockerfile            # Builds from the project root (see docker-compose.yml)
├── frontend/                # React (Vite) app — Module 8
│   └── src/
│       ├── components/       # Layout, ProtectedRoute, CurbStatus, StatCard,
│       │                     # PageHeader, AuthenticatedImage
│       ├── context/          # AuthContext (JWT, current user, role)
│       ├── lib/               # apiClient (axios + interceptors)
│       ├── pages/             # Login, Register, Dashboard, SubmitComplaint,
│       │                     # Complaints, ComplaintDetail, MapView,
│       │                     # HotspotAnalysis, Predictions, Reports
│       └── App.jsx           # Routes
├── ai_models/                # NLP / computer vision / ML model code (Modules 4-7)
│   ├── nlp/                  # preprocessing, NER, classification, duplicate detection
│   ├── computer_vision/      # YOLOv8 vehicle detection, illegal-parking heuristic
│   ├── ml_prediction/        # feature engineering, hotspot forecast, violation probability,
│   │                         # enforcement time, officer deployment
│   └── tests/
├── datasets/                 # Historical data import scripts (Module 7): NYC/SF/Chicago
├── docs/                    # Installation, architecture, schema, UML, API, deployment docs
├── scripts/
├── .github/workflows/ci.yml  # Runs all dependency-free tests + syntax check (Module 9)
├── docker-compose.yml         # Local dev stack
├── docker-compose.prod.yml    # Production stack — gunicorn, nginx, Caddy, scheduler (Module 9)
├── Caddyfile                  # Reverse proxy + automatic HTTPS (Module 9)
├── .env.example                # Dev environment template
└── .env.prod.example           # Production environment template (Module 9)
```

## Documentation

* [`docs/installation_guide.md`](docs/installation_guide.md) — prerequisites through first run, troubleshooting
* [`docs/architecture.md`](docs/architecture.md) — system architecture & AI workflow
* [`docs/database_schema.md`](docs/database_schema.md) — ER diagram & schema notes
* [`docs/uml_diagrams.md`](docs/uml_diagrams.md) — class diagram & complaint-pipeline sequence diagram
* [`docs/api_documentation.md`](docs/api_documentation.md) — API reference (every endpoint, all 9 modules)
* [`docs/deployment_guide.md`](docs/deployment_guide.md) — dev + production Docker deployment, secrets, scheduling
