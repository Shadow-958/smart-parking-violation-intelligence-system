"""
Geocoding via the public Nominatim API (OpenStreetMap).

Nominatim's usage policy caps public-instance usage at roughly 1
request/second and requires a descriptive User-Agent — this module
enforces a minimum delay between calls and sends that header
(NOMINATIM_USER_AGENT in config). For production volume beyond
occasional per-complaint geocoding, self-host Nominatim or use a
commercial geocoding provider instead of the shared public instance; this
implementation is sized for interactive/per-complaint use, not for
bulk-geocoding historical data (that's a Module 7 dataset-import concern
and would need its own throttling strategy either way).
"""

import time
from typing import Tuple

import httpx

from app.config import get_settings

settings = get_settings()

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org/search"
_MIN_SECONDS_BETWEEN_REQUESTS = 1.0
_last_request_time: float = 0.0


class GeocodingError(Exception):
    """Raised when Nominatim can't be reached, times out, or has no match."""


def _throttle() -> None:
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _MIN_SECONDS_BETWEEN_REQUESTS:
        time.sleep(_MIN_SECONDS_BETWEEN_REQUESTS - elapsed)
    _last_request_time = time.monotonic()


def geocode(query: str, timeout: float = 5.0) -> Tuple[float, float, str]:
    """Returns (latitude, longitude, display_name) for the best match.
    Raises GeocodingError if the query is empty, the request fails, or
    there's no match.

    Tries a bounded search first (within the configured viewbox) for
    precision, then falls back to an unbounded search with just country
    codes if the bounded one returns nothing — handles colloquial names
    and locations just outside the viewbox."""
    if not query or not query.strip():
        raise GeocodingError("Empty location query")

    base_params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": settings.NOMINATIM_COUNTRY_CODES,
    }

    # Try bounded search first (precise), then unbounded fallback
    attempts = [
        {**base_params, "viewbox": settings.NOMINATIM_VIEWBOX, "bounded": 1},
        base_params,  # fallback: country-only, no viewbox
    ]

    last_error = None
    for params in attempts:
        _throttle()
        try:
            response = httpx.get(
                NOMINATIM_BASE_URL,
                params=params,
                headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                timeout=timeout,
            )
            response.raise_for_status()
            results = response.json()
        except httpx.HTTPError as exc:
            raise GeocodingError(f"Nominatim request failed: {exc}") from exc

        if results:
            top = results[0]
            return float(top["lat"]), float(top["lon"]), top.get("display_name", query)

    raise GeocodingError(f"No geocoding match for '{query}'")
