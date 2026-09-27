"""
Application configuration.

All secrets and environment-specific values are loaded from environment
variables (see .env.example at the project root). Never hard-code secrets
here.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App metadata ---
    APP_NAME: str = "Smart Parking Violation Intelligence and Decision Support System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- Database ---
    # Example: postgresql+psycopg2://parking_user:parking_pass@db:5432/parking_db
    DATABASE_URL: str

    # --- Auth / JWT ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # --- File storage ---
    UPLOAD_DIR: str = "/app/uploads/complaint_images"
    MAX_UPLOAD_SIZE_MB: int = 10

    # --- Geocoding (GIS module) ---
    NOMINATIM_USER_AGENT: str = "smart-parking-violation-system"
    # Bounding box to constrain geocoding results (lon1,lat1,lon2,lat2).
    # Default covers the Mumbai metropolitan area. Set to an empty string
    # to disable viewbox filtering.
    NOMINATIM_VIEWBOX: str = "72.7,18.85,73.1,19.35"
    NOMINATIM_COUNTRY_CODES: str = "in"

    # --- NLP pipeline ---
    # Rule-based classification is the default (fast, no model download).
    # Flip this on to use Hugging Face zero-shot classification instead —
    # more accurate, but pulls in a ~1.6GB model and is much slower per
    # request. See ai_models/nlp/classifier.py for the tradeoff writeup.
    NLP_USE_TRANSFORMER_CLASSIFIER: bool = False
    NLP_DUPLICATE_THRESHOLD: float = 0.85
    NLP_DUPLICATE_LOOKBACK_DAYS: int = 30
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"

    # --- Computer Vision (YOLOv8) ---
    YOLO_WEIGHTS: str = "yolov8n.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.25
    VISION_HIGH_CONFIDENCE_THRESHOLD: float = 0.5

    # --- GIS / hotspots ---
    # 0 = all historical complaints (no date cutoff). Needed when
    # imported datasets are older than a rolling window (this project's
    # bulk is from 2020; a 1000-day window still drops it).
    HOTSPOT_PERIOD_DAYS: int = 0
    HOTSPOT_EPS_METERS: float = 300.0
    HOTSPOT_MIN_POINTS: int = 2
    HEATMAP_LOOKBACK_DAYS: int = 0

    # --- Machine Learning (Module 7) ---
    ML_MODEL_DIR: str = "/app/ai_models/ml_prediction/artifacts"
    MIN_TRAINING_RECORDS: int = 30
    ENFORCEMENT_LOOKBACK_DAYS: int = 0
    DEPLOYMENT_TOP_N: int = 10

    # --- Scheduler (Module 9) ---
    # Runs as its own single-replica process, not embedded in the API
    # server — see app/core/scheduler.py for why.
    HOTSPOT_RECOMPUTE_INTERVAL_HOURS: int = 24
    MODEL_RETRAIN_INTERVAL_HOURS: int = 168  # weekly

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so we only parse the environment once."""
    return Settings()
