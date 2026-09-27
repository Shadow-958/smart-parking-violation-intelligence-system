"""
Hotspot forecasting: given historical grid-cell/time-bucket violation
counts, train a model that predicts expected violation count for a given
cell/time going forward.

Uses XGBoost's regressor (per the spec's preference for XGBoost/Random
Forest) over day/hour/grid-cell features. This is a genuinely supervised,
historical-data-dependent model — unlike the CV/NLP modules' defaults,
there's no reasonable rule-based substitute for "how many violations will
this grid cell see next Tuesday at 3pm". Training data volume matters a
lot here: with only a handful of complaints, don't expect useful
predictions — this needs real historical volume (see datasets/) to be
worth deploying, which is why app/services/ml_service.py enforces a
minimum record count before training at all.
"""

from typing import Any, List

FEATURE_COLUMNS = ["grid_lat", "grid_lon", "day_of_week", "hour_of_day"]
TARGET_COLUMN = "count"


def train(training_df, n_estimators: int = 200, max_depth: int = 6):
    """training_df: output of ai_models.ml_prediction.features.to_training_frame.
    Returns a fitted XGBRegressor."""
    from xgboost import XGBRegressor

    model = XGBRegressor(n_estimators=n_estimators, max_depth=max_depth, objective="reg:squarederror")
    model.fit(training_df[FEATURE_COLUMNS], training_df[TARGET_COLUMN])
    return model


def predict(model, features_df) -> List[float]:
    """features_df: same columns as FEATURE_COLUMNS, one row per
    (grid_cell, time_bucket) to forecast. Returns predicted counts,
    clipped at 0 (a negative forecasted violation count isn't
    meaningful)."""
    predictions = model.predict(features_df[FEATURE_COLUMNS])
    return [max(0.0, float(p)) for p in predictions]


def save(model, path: str) -> None:
    import joblib

    joblib.dump(model, path)


def load(path: str) -> Any:
    import joblib

    return joblib.load(path)
