"""
Enforcement-time recommendation: given raw violation timestamps near a
hotspot, recommend which hours of the day see the most violations.

Deliberately a plain aggregation, not a trained model — "when do
violations peak here" is a descriptive-statistics question with a fully
interpretable answer (a count-by-hour histogram), and forcing a
black-box model onto it would trade transparency for no real accuracy
benefit. The spec's XGBoost/Random Forest guidance is best applied to
genuinely predictive tasks (hotspot_forecast.py, violation_probability.py)
rather than every ML-adjacent feature in this module — not everything
that sounds like "prediction" needs to be a trained model.
"""

from collections import Counter
from datetime import datetime, time
from typing import List, Tuple


def recommend_enforcement_windows(
    timestamps: List[datetime], top_n: int = 3, window_hours: int = 2
) -> List[dict]:
    """
    Returns up to `top_n` recommended enforcement windows, each
    `window_hours` wide, ranked by historical violation count within that
    window. Returns an empty list if there's no data.

    Example return value:
        [{"start_hour": 8, "end_hour": 10, "violation_count": 42}, ...]
    """
    if not timestamps:
        return []

    hour_counts = Counter(ts.hour for ts in timestamps)

    window_totals: List[Tuple[int, int]] = []
    for start_hour in range(24):
        total = sum(hour_counts.get((start_hour + offset) % 24, 0) for offset in range(window_hours))
        window_totals.append((start_hour, total))

    window_totals.sort(key=lambda item: item[1], reverse=True)

    recommendations = []
    for start_hour, total in window_totals[:top_n]:
        if total == 0:
            continue
        end_hour = (start_hour + window_hours) % 24
        recommendations.append({"start_hour": start_hour, "end_hour": end_hour, "violation_count": total})
    return recommendations


def hour_to_time(hour: int) -> time:
    """Converts a plain hour-of-day int to a datetime.time, for storing
    in OfficerRecommendation.recommended_time_start/end."""
    return time(hour=hour % 24, minute=0)
