"""
Officer deployment ranking: combines hotspot risk with (optional)
forecasted violation counts into a single priority ranking of where to
send patrols.

Plain arithmetic over already-computed hotspot/forecast data — not a
trained model. The actual prediction work happens upstream
(hotspot_forecast.py); this module's job is just to turn "here are N
hotspots, each with a risk score and maybe a forecast" into a ranked,
capped list suitable for OfficerRecommendation rows.
"""

from typing import Dict, List, Optional


def rank_deployment_locations(
    hotspots: List[dict],
    forecasts_by_hotspot_id: Optional[Dict[str, float]] = None,
    top_n: int = 10,
    forecast_weight: float = 0.4,
) -> List[dict]:
    """
    `hotspots`: list of dicts with at least {id, risk_score}.
    `forecasts_by_hotspot_id`: optional {hotspot_id: predicted_count},
    normalized internally against the max value present.

    Returns the input hotspots augmented with a `priority_score` (a blend
    of risk_score and normalized forecast, or risk_score alone if no
    forecast is available), sorted descending and capped to `top_n`.
    """
    forecasts_by_hotspot_id = forecasts_by_hotspot_id or {}
    max_forecast = max(forecasts_by_hotspot_id.values(), default=0.0)

    ranked = []
    for hotspot in hotspots:
        risk_score = hotspot.get("risk_score", 0.0)
        forecast = forecasts_by_hotspot_id.get(hotspot["id"])

        if forecast is not None and max_forecast > 0:
            normalized_forecast = forecast / max_forecast
            priority_score = (1 - forecast_weight) * risk_score + forecast_weight * normalized_forecast
        else:
            priority_score = risk_score

        ranked.append({**hotspot, "priority_score": round(priority_score, 4)})

    ranked.sort(key=lambda h: h["priority_score"], reverse=True)
    return ranked[:top_n]
