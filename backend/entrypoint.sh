#!/bin/sh
# Switches between dev and production server modes based on ENVIRONMENT.
# Used by both docker-compose.yml (dev, ENVIRONMENT defaults to
# "development") and docker-compose.prod.yml (ENVIRONMENT=production).
set -e

if [ "$ENVIRONMENT" = "production" ]; then
  echo "Starting in production mode (gunicorn + uvicorn workers)"
  exec gunicorn app.main:app \
    --workers "${GUNICORN_WORKERS:-4}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
else
  echo "Starting in development mode (uvicorn --reload)"
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
