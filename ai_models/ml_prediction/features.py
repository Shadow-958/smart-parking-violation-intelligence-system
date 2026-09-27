"""
Feature engineering for hotspot forecasting / violation probability
models: turns raw (lat, lon, timestamp) records into a spatiotemporal
grid of violation counts a model can train on.

Deliberately takes plain dicts/lists rather than a SQLAlchemy query
result, so the aggregation logic stays testable without a database (see
ai_models/tests/test_features.py) — the backend service layer
(app/services/ml_service.py) is responsible for pulling rows out of
Postgres and handing them to this module as plain data.
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

# ~0.005 degrees is roughly 500m at mid-latitudes — coarse enough to
# aggregate meaningfully, fine enough to distinguish different streets.
DEFAULT_GRID_SIZE_DEGREES = 0.005


def assign_grid_cell(
    lat: float, lon: float, grid_size: float = DEFAULT_GRID_SIZE_DEGREES
) -> Tuple[float, float]:
    """Snaps a coordinate to the center of its grid cell."""
    grid_lat = round(lat / grid_size) * grid_size
    grid_lon = round(lon / grid_size) * grid_size
    return round(grid_lat, 6), round(grid_lon, 6)


def build_grid_time_counts(
    records: List[dict], grid_size: float = DEFAULT_GRID_SIZE_DEGREES
) -> List[dict]:
    """
    Aggregates raw records (each a dict with at least `lat`, `lon`,
    `submitted_at`) into (grid_cell, day_of_week, hour_of_day) buckets
    with violation counts — the training target for the hotspot forecast
    and violation probability models.

    Returns a list of dicts, one per non-empty bucket:
    {grid_lat, grid_lon, day_of_week, hour_of_day, count}

    Pure Python (no pandas) so this step alone is testable without any
    of this module's heavier dependencies installed.
    """
    buckets: Dict[tuple, int] = defaultdict(int)

    for record in records:
        lat, lon = record["lat"], record["lon"]
        timestamp: datetime = record["submitted_at"]
        grid_lat, grid_lon = assign_grid_cell(lat, lon, grid_size)
        key = (grid_lat, grid_lon, timestamp.weekday(), timestamp.hour)
        buckets[key] += 1

    return [
        {
            "grid_lat": grid_lat,
            "grid_lon": grid_lon,
            "day_of_week": day_of_week,
            "hour_of_day": hour_of_day,
            "count": count,
        }
        for (grid_lat, grid_lon, day_of_week, hour_of_day), count in buckets.items()
    ]


def to_training_frame(bucketed_records: List[dict]):
    """Converts bucketed count records into a pandas DataFrame with a
    binary `had_violation` target added, ready for training. Split out
    from build_grid_time_counts specifically so the pandas dependency
    only applies to this step, not the aggregation logic above."""
    import pandas as pd

    df = pd.DataFrame(bucketed_records)
    if df.empty:
        return df

    df["had_violation"] = (df["count"] > 0).astype(int)
    return df

def to_probability_training_frame(
    records: List[dict],
    grid_size: float = DEFAULT_GRID_SIZE_DEGREES,
):
    """
    Creates a binary training dataset for violation-probability prediction.

    Positive samples:
        grid cell + day + hour where a violation occurred.

    Negative samples:
        grid cell + day + hour combinations where no violation occurred.
    """
    import pandas as pd

    if not records:
        return pd.DataFrame()

    # Collect observed grid cells and the positive combinations.
    grid_cells = set()
    positive_buckets = set()

    for record in records:
        grid_lat, grid_lon = assign_grid_cell(
            record["lat"], record["lon"], grid_size
        )
        timestamp = record["submitted_at"]

        grid_cells.add((grid_lat, grid_lon))

        positive_buckets.add(
            (
                grid_lat,
                grid_lon,
                timestamp.weekday(),
                timestamp.hour,
            )
        )

    # Generate all 7 days × 24 hours for every observed grid cell.
    rows = []

    for grid_lat, grid_lon in grid_cells:
        for day_of_week in range(7):
            for hour_of_day in range(24):
                key = (
                    grid_lat,
                    grid_lon,
                    day_of_week,
                    hour_of_day,
                )

                rows.append(
                    {
                        "grid_lat": grid_lat,
                        "grid_lon": grid_lon,
                        "day_of_week": day_of_week,
                        "hour_of_day": hour_of_day,
                        "had_violation": int(key in positive_buckets),
                    }
                )

    return pd.DataFrame(rows)