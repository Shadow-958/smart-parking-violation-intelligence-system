"""
Tests for the pure-Python parts of ai_models/ml_prediction/features.py.
to_training_frame (which needs pandas) is exercised in your environment,
not here.
"""

from datetime import datetime

from ai_models.ml_prediction.features import assign_grid_cell, build_grid_time_counts


def test_assign_grid_cell_snaps_to_grid():
    lat, lon = assign_grid_cell(19.0763, 72.8777, grid_size=0.005)
    assert lat == round(19.0763 / 0.005) * 0.005
    assert lon == round(72.8777 / 0.005) * 0.005


def test_nearby_points_land_in_same_cell():
    a = assign_grid_cell(19.07600, 72.87770)
    b = assign_grid_cell(19.07610, 72.87765)  # a few meters away
    assert a == b


def test_build_grid_time_counts_aggregates_correctly():
    records = [
        {"lat": 19.0760, "lon": 72.8777, "submitted_at": datetime(2026, 1, 5, 14, 30)},
        {"lat": 19.0761, "lon": 72.8778, "submitted_at": datetime(2026, 1, 5, 14, 45)},  # same cell/hour
        {"lat": 19.0900, "lon": 72.9000, "submitted_at": datetime(2026, 1, 5, 9, 0)},  # different cell
    ]
    buckets = build_grid_time_counts(records)
    assert sum(b["count"] for b in buckets) == 3
    assert any(b["count"] == 2 for b in buckets)


def test_empty_input_returns_empty_list():
    assert build_grid_time_counts([]) == []
