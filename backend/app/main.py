"""
Application entrypoint.

Module 1 scope: app bootstrap, CORS, health check, and DB connectivity
check only. Feature routers (auth, complaints, NLP, CV, GIS, predictions,
dashboard, reports) are added incrementally in later modules and wired in
via `app.api.router` — see app/api/__init__.py.
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import auth, complaints, dashboard, gis, nlp, predictions, reports, vision
from app.config import get_settings
from app.database import get_db

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered platform for ingesting, analyzing, and acting on parking violation complaints.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
def root():
    return {
        "service": settings.APP_NAME,
        "status": "running",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["health"])
def health_check(db: Session = Depends(get_db)):
    """Verifies the API process is up AND the database is reachable."""
    db.execute(text("SELECT 1"))
    return {"api": "ok", "database": "ok"}


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(complaints.router, prefix="/api/complaints", tags=["complaints"])
app.include_router(nlp.router, prefix="/api/nlp", tags=["nlp"])
app.include_router(vision.router, prefix="/api/vision", tags=["vision"])
app.include_router(gis.router, prefix="/api/gis", tags=["gis"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
