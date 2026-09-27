# Deployment Guide

## Local development

```bash
cp .env.example .env      # fill in real secrets
docker compose up --build
docker compose exec backend alembic upgrade head
```

* Backend: http://localhost:8000 (docs at `/docs`)
* Frontend: http://localhost:5173
* Postgres/PostGIS: localhost:5432

See `docs/installation_guide.md` for the detailed walkthrough
(prerequisites, first-account setup, troubleshooting).

**First build is slow and needs network access**: the backend image
downloads spaCy's English model, NLTK data, and a YOLOv8 checkpoint
during `docker compose build` (Modules 4-5) — several minutes, close to
a GB combined. This isn't a one-time cost either: geocoding
(Module 6) needs live network access to the public Nominatim API at
*runtime*, every time a new location needs resolving.

## Production

```bash
cp .env.prod.example .env.prod   # fill in REAL secrets — see below
# edit Caddyfile: replace parking.example.com with your real domain
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

`docker-compose.prod.yml` is a standalone file, not a
`docker-compose.yml` override — Compose's merge semantics for list
fields (`ports`, `volumes`) aren't consistent enough across versions to
safely rely on for "which ports face the internet." It differs from the
dev compose file in several load-bearing ways:

| | Dev (`docker-compose.yml`) | Production (`docker-compose.prod.yml`) |
|---|---|---|
| Backend server | `uvicorn --reload` | Gunicorn + Uvicorn workers (`entrypoint.sh` switches on `ENVIRONMENT`) |
| Frontend | Vite dev server (HMR) | Static build served by nginx (`Dockerfile.prod`) |
| Code | Bind-mounted (live edits) | Baked into the image (rebuild to deploy a change) |
| Exposed ports | `db`/`backend`/`frontend` all on host | Only Caddy (80/443) — everything else is compose-network-internal |
| TLS | None | Automatic, via Caddy + Let's Encrypt |
| Scheduled jobs | None (manual `POST` only) | A dedicated `scheduler` container (see below) |

### Reverse proxy / TLS

Caddy (not nginx+certbot) fronts the whole stack — `/api/*`, `/docs`,
and `/openapi.json` route to the backend, everything else to the
frontend, with automatic HTTPS from about 10 lines of `Caddyfile`. You
must replace the placeholder domain in `Caddyfile` with a real,
DNS-resolvable one; Caddy won't (and shouldn't be able to) issue a
certificate otherwise.

### Secrets management

`.env.prod` as a plaintext file on the host is **better than committing
secrets to git, but still not what a real production deployment should
rely on long-term.** Before this handles real citizen data:

* Generate `SECRET_KEY` with `openssl rand -hex 32` — never reuse the
  dev default.
* Use a real secrets manager where you're hosting this — Docker Swarm
  secrets, AWS Secrets Manager / Parameter Store, GCP Secret Manager,
  Azure Key Vault, or at minimum a `.env.prod` with host filesystem
  permissions locked down (`chmod 600`) and excluded from any backup
  that isn't itself encrypted.
* Rotate `POSTGRES_PASSWORD` and `SECRET_KEY` on a schedule, and
  immediately if `.env.prod` is ever exposed (committed by accident,
  logged, etc.) — rotating `SECRET_KEY` invalidates every issued JWT,
  which is the correct behavior after a suspected leak, not a bug to
  route around.
* Use a least-privilege Postgres role for `POSTGRES_USER` rather than a
  superuser, once you're managing the database outside of what
  `postgis/postgis`'s init script sets up by default.

### Scheduled jobs

Hotspot recomputation and ML retraining were manual-`POST`-only through
Modules 6-7. In production, `docker-compose.prod.yml`'s `scheduler`
service runs `backend/app/core/scheduler.py` — the same image and code
as `backend`, just with its container command overridden to run the
scheduler module instead of the API server.

This is **deliberately a separate single-replica process**, not an
in-process `APScheduler` inside the API server's Gunicorn workers: with
`GUNICORN_WORKERS=4`, an in-process scheduler would start once per
worker and run every job four times. Don't try to "simplify" this by
merging it back into `backend` without also solving that duplication
problem (e.g. a Postgres advisory lock, or a persistent jobstore with
leader election) — the separate-process approach is simpler than either
of those and costs one extra (cheap, low-traffic) container.

Default intervals: hotspots recompute every `HOTSPOT_RECOMPUTE_INTERVAL_HOURS`
(24h) alongside officer recommendation regeneration, models retrain
every `MODEL_RETRAIN_INTERVAL_HOURS` (168h / weekly) — both configurable
via `.env.prod`.

### Database

`docker-compose.prod.yml`'s `db` service is still a local PostGIS
container with a named volume — adequate for getting a real deployment
running, but you should move to a managed, backed-up Postgres instance
(with PostGIS enabled) before this holds data you can't afford to lose:
RDS/Cloud SQL/Azure Database for PostgreSQL all support PostGIS. Point
`DATABASE_URL` at it and remove the `db` service from the compose file
once you do.

### CI

`.github/workflows/ci.yml` runs the dependency-free test suites built up
across Modules 2-7 (`backend/tests`, `ai_models/tests`) plus a full
`py_compile` syntax pass over every Python file, on every push/PR. It
does **not** run anything needing a live Postgres+PostGIS instance,
downloaded spaCy/NLTK models, or Nominatim network access — extending it
to cover those (e.g. a Postgres service container + Alembic migrate +
integration tests) is reasonable follow-on work once there's an
integration test suite to run; none exists yet; see the honesty notes on
testing scope throughout this project's README.

### Monitoring / logging

Not implemented. Gunicorn's `--access-logfile -` / `--error-logfile -`
(already set in `entrypoint.sh`) send logs to stdout, which is the right
starting point for most container log aggregators (CloudWatch, Stackdriver,
Loki, etc.) to pick up without further changes — but nothing here
currently ships metrics, traces, or alerting. Worth adding before relying
on this in a setting where downtime needs to be noticed quickly rather
than discovered by a citizen complaint about the complaint system.
