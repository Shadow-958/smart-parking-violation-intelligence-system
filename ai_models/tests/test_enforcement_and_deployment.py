"""
Tests for the fully dependency-free parts of ai_models/ml_prediction/:
enforcement_time.py and officer_deployment.py. Neither needs pandas,
xgboost, or a database.
"""

from datetime import datetime

from ai_models.ml_prediction.enforcement_time import hour_to_time, recommend_enforcement_windows
from ai_models.ml_prediction.officer_deployment import rank_deployment_locations


def test_recommends_peak_hour_window():
    timestamps = [
        datetime(2026, 1, 5, 8, 15),
        datetime(2026, 1, 5, 8, 45),
        datetime(2026, 1, 5, 9, 5),
        datetime(2026, 1, 6, 20, 0),
    ]
    windows = recommend_enforcement_windows(timestamps, top_n=1, window_hours=2)
    assert len(windows) == 1
    assert windows[0]["start_hour"] == 8
    assert windows[0]["violation_count"] == 3


def test_empty_timestamps_returns_empty_list():
    assert recommend_enforcement_windows([]) == []


def test_hour_to_time_wraps_correctly():
    assert hour_to_time(23).hour == 23
    assert hour_to_time(25).hour == 1


def test_rank_deployment_locations_by_risk_only():
    hotspots = [
        {"id": "a", "risk_score": 0.5},
        {"id": "b", "risk_score": 0.9},
        {"id": "c", "risk_score": 0.2},
    ]
    ranked = rank_deployment_locations(hotspots, top_n=2)
    assert [h["id"] for h in ranked] == ["b", "a"]


def test_rank_deployment_locations_blends_forecast():
    hotspots = [{"id": "a", "risk_score": 0.3}, {"id": "b", "risk_score": 0.3}]
    forecasts = {"a": 100.0, "b": 10.0}
    ranked = rank_deployment_locations(hotspots, forecasts, forecast_weight=0.8)
    assert ranked[0]["id"] == "a"  # same risk, but much higher forecast tips it


def test_rank_deployment_locations_caps_to_top_n():
    hotspots = [{"id": str(i), "risk_score": i / 10} for i in range(20)]
    ranked = rank_deployment_locations(hotspots, top_n=5)
    assert len(ranked) == 5
