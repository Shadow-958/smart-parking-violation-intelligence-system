"""
Violation-probability estimation: given a grid cell + time bucket,
estimate the probability that at least one violation occurs there.

Same XGBoost-over-plain-features approach as hotspot_forecast.py, but
framed as binary classification (had_violation) rather than count
regression — useful for an "is this worth a patrol right now" yes/no-ish
signal rather than an expected-count number.
"""

from typing import Any, List

FEATURE_COLUMNS = ["grid_lat", "grid_lon", "day_of_week", "hour_of_day"]
TARGET_COLUMN = "had_violation"


def train(training_df, n_estimators: int = 200, max_depth: int = 6):
    from xgboost import XGBClassifier

    model = XGBClassifier(n_estimators=n_estimators, max_depth=max_depth, eval_metric="logloss")
    model.fit(training_df[FEATURE_COLUMNS], training_df[TARGET_COLUMN])
    return model


def predict_proba(model, features_df) -> List[float]:
    """Returns the probability of >=1 violation for each row, in [0, 1]."""
    probabilities = model.predict_proba(features_df[FEATURE_COLUMNS])
    return [float(row[1]) for row in probabilities]  # row[1] = P(had_violation=1)


def save(model, path: str) -> None:
    import joblib

    joblib.dump(model, path)


def load(path: str) -> Any:
    import joblib

    return joblib.load(path)
