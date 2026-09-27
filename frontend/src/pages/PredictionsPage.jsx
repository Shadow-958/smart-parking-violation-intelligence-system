import { useEffect, useState } from "react";
import apiClient from "../lib/apiClient";
import PageHeader from "../components/PageHeader";
import { RiskDot } from "../components/CurbStatus";
import { useAuth } from "../context/AuthContext";

export default function PredictionsPage() {
  const { isStaff } = useAuth();
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState(null);
  const [trainError, setTrainError] = useState(null);

  const [probeForm, setProbeForm] = useState({ lat: "19.076", lng: "72.8777" });
  const [probeResult, setProbeResult] = useState(null);
  const [probing, setProbing] = useState(false);

  const [enforcementWindows, setEnforcementWindows] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  function loadEnforcementWindows() {
  apiClient
    .get("/api/predictions/enforcement-times", {
      params: { lookback_days: 0 },
    })
    .then((res) => setEnforcementWindows(res.data));
}

  function loadRecommendations() {
    if (!isStaff) return;
    apiClient.get("/api/predictions/recommendations").then((res) => setRecommendations(res.data));
  }

  useEffect(() => {
    loadEnforcementWindows();
    loadRecommendations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isStaff]);

  async function handleTrain() {
    setTraining(true);
    setTrainError(null);
    setTrainResult(null);
    try {
      const { data } = await apiClient.post("/api/predictions/train");
      setTrainResult(data);
    } catch (err) {
      setTrainError(err.response?.data?.detail || "Training failed.");
    } finally {
      setTraining(false);
    }
  }

  async function handleForecast() {
    await apiClient.post("/api/predictions/hotspots/forecast");
  }

  async function handleGenerateRecommendations() {
  await apiClient.post("/api/predictions/recommendations/generate", null, {
    params: { lookback_days: 0 },
  });
  loadRecommendations();
  loadEnforcementWindows();
}

  async function handleProbe(e) {
    e.preventDefault();
    setProbing(true);
    try {
      const { data } = await apiClient.get("/api/predictions/violation-probability", {
        params: { lat: probeForm.lat, lng: probeForm.lng },
      });
      setProbeResult(data);
    } finally {
      setProbing(false);
    }
  }

  return (
    <div>
      <PageHeader title="AI Predictions" subtitle="Hotspot forecasts, enforcement timing, deployment" />

      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-2">
        {isStaff && (
          <section className="border border-ink/10 bg-white p-5">
            <h2 className="mb-3 text-sm">Model training</h2>
            <p className="mb-3 text-sm text-ink/60">
              Trains the hotspot-forecast and violation-probability models from all geocoded complaints
              (real + imported historical data). Requires a minimum record count — see the backend's
              MIN_TRAINING_RECORDS setting.
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleTrain}
                disabled={training}
                className="bg-asphalt px-4 py-2 text-sm uppercase tracking-wide text-paper disabled:opacity-50"
              >
                {training ? "Training…" : "Train models"}
              </button>
              <button
                onClick={handleForecast}
                className="border border-ink/20 px-4 py-2 text-sm uppercase tracking-wide"
              >
                Forecast hotspots
              </button>
              <button
                onClick={handleGenerateRecommendations}
                className="border border-ink/20 px-4 py-2 text-sm uppercase tracking-wide"
              >
                Generate recommendations
              </button>
            </div>
            {trainResult && (
              <p className="mt-3 font-mono text-xs text-curb-green">
                Trained on {trainResult.training_records} records ({trainResult.training_buckets} grid/time buckets).
              </p>
            )}
            {trainError && <p className="mt-3 text-sm text-curb-red">{trainError}</p>}
          </section>
        )}

        <section className="border border-ink/10 bg-white p-5">
          <h2 className="mb-3 text-sm">Violation probability estimator</h2>
          <form onSubmit={handleProbe} className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block font-mono text-xs uppercase text-ink/50">Latitude</label>
              <input
                value={probeForm.lat}
                onChange={(e) => setProbeForm((f) => ({ ...f, lat: e.target.value }))}
                className="w-32 border border-ink/20 bg-white px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block font-mono text-xs uppercase text-ink/50">Longitude</label>
              <input
                value={probeForm.lng}
                onChange={(e) => setProbeForm((f) => ({ ...f, lng: e.target.value }))}
                className="w-32 border border-ink/20 bg-white px-2 py-1.5 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={probing}
              className="bg-curb-yellow px-4 py-1.5 text-sm uppercase tracking-wide text-asphalt-dark disabled:opacity-50"
            >
              Estimate
            </button>
          </form>
          {probeResult && (
            <div className="mt-4 text-sm">
              {probeResult.probability != null ? (
                <RiskDot score={probeResult.probability} />
              ) : (
                <p className="text-ink/50">{probeResult.note}</p>
              )}
            </div>
          )}
        </section>

        <section className="border border-ink/10 bg-white p-5 lg:col-span-2">
          <h2 className="mb-4 text-sm">Recommended enforcement windows</h2>
          {enforcementWindows.length === 0 ? (
            <p className="text-sm text-ink/50">No hotspots to analyze yet.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {enforcementWindows.map((entry) => {
                const riskColor =
                  entry.risk_score >= 0.66 ? "#C8102E" : entry.risk_score >= 0.33 ? "#F2B705" : "#1B7A43";
                return (
                  <div
                    key={entry.hotspot_id}
                    className="rounded border border-ink/10 bg-paper p-3"
                    style={{ borderLeft: `4px solid ${riskColor}` }}
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs font-medium">
                        📍 {entry.lat?.toFixed(4)}, {entry.lng?.toFixed(4)}
                      </span>
                      <RiskDot score={entry.risk_score} />
                    </div>
                    <div className="mb-2 text-xs text-ink/50">
                      {entry.violation_count} violations in cluster
                    </div>
                    {entry.windows.length === 0 ? (
                      <span className="text-xs text-ink/40">No historical pattern yet</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {entry.windows.map((w, i) => (
                          <span
                            key={i}
                            className="inline-block rounded bg-ink/5 px-2 py-0.5 font-mono text-xs"
                          >
                            {String(w.start_hour).padStart(2, "0")}:00–
                            {String(w.end_hour).padStart(2, "0")}:00
                            <span className="text-ink/40"> ({w.violation_count})</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {isStaff && (
          <section className="border border-ink/10 bg-white p-5 lg:col-span-2">
            <h2 className="mb-4 text-sm">Officer deployment recommendations</h2>
            {recommendations.length === 0 ? (
              <p className="text-sm text-ink/50">
                No recommendations yet — click "Generate recommendations" above.
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {recommendations.map((r) => {
                  const prioColor =
                    r.priority_score >= 0.66 ? "#C8102E" : r.priority_score >= 0.33 ? "#F2B705" : "#1B7A43";
                  return (
                    <div
                      key={r.id}
                      className="rounded border border-ink/10 bg-paper p-3"
                      style={{ borderLeft: `4px solid ${prioColor}` }}
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <span className="text-xs font-medium">
                          📍 {r.lat.toFixed(4)}, {r.lng.toFixed(4)}
                        </span>
                        <RiskDot score={r.priority_score} />
                      </div>
                      {r.recommended_time_start && (
                        <div className="mb-1">
                          <span className="inline-block rounded bg-ink/5 px-2 py-0.5 font-mono text-xs">
                            🕐 {r.recommended_time_start.slice(0, 5)}–{r.recommended_time_end?.slice(0, 5)}
                          </span>
                        </div>
                      )}
                      <div className="text-xs text-ink/40">
                        Priority: {(r.priority_score * 100).toFixed(0)}%
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
