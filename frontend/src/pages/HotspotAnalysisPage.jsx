import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Circle, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import apiClient from "../lib/apiClient";
import PageHeader from "../components/PageHeader";
import { RiskDot } from "../components/CurbStatus";
import { useAuth } from "../context/AuthContext";

const DEFAULT_CENTER = [19.076, 72.8777];

export default function HotspotAnalysisPage() {
  const { isStaff } = useAuth();
  const [hotspots, setHotspots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recomputing, setRecomputing] = useState(false);

  function load() {
    setLoading(true);
    apiClient
      .get("/api/gis/hotspots")
      .then((res) => setHotspots(res.data))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function recompute() {
    setRecomputing(true);
    try {
      await apiClient.post("/api/gis/hotspots/recompute", null, {
        params: { period_days: 0, eps_meters: 150, min_points: 3 },
      });
      load();
    } finally {
      setRecomputing(false);
    }
  }

  const center = hotspots.length > 0 ? [hotspots[0].lat, hotspots[0].lng] : DEFAULT_CENTER;

  return (
    <div>
      <PageHeader
        title="Hotspot Analysis"
        subtitle={`${hotspots.length} active hotspots${hotspots.length > 0 ? ` (${hotspots.reduce((sum, h) => sum + h.violation_count, 0)} violations clustered)` : ""}`}
        action={
          isStaff && (
            <button
              onClick={recompute}
              disabled={recomputing}
              className="bg-asphalt px-4 py-2 text-sm uppercase tracking-wide text-paper disabled:opacity-50"
            >
              {recomputing ? "Recomputing…" : "Recompute hotspots"}
            </button>
          )
        }
      />

      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="h-[500px] border border-ink/10">
            {!loading && (
              <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }}>
                <TileLayer
                  attribution='&copy; OpenStreetMap contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {hotspots.map((h) => (
                  <Circle
                    key={h.id}
                    center={[h.lat, h.lng]}
                    radius={h.radius_meters}
                    pathOptions={{
                      color: h.risk_score >= 0.66 ? "#C8102E" : h.risk_score >= 0.33 ? "#F2B705" : "#1B7A43",
                      fillOpacity: 0.25,
                    }}
                  >
                    <Popup>
                      <div className="text-sm">
                        <div>{h.violation_count} violations</div>
                        <RiskDot score={h.risk_score} />
                      </div>
                    </Popup>
                  </Circle>
                ))}
              </MapContainer>
            )}
          </div>
        </div>

        <div className="border border-ink/10 bg-white p-4">
          <h2 className="mb-3 text-sm">Ranked hotspots</h2>
          {loading ? (
            <p className="text-ink/40">Loading…</p>
          ) : hotspots.length === 0 ? (
            <p className="text-sm text-ink/50">
              No hotspots computed yet.{" "}
              {isStaff ? "Click Recompute once there's enough geocoded complaint data." : ""}
            </p>
          ) : (
            <ul className="divide-y divide-ink/5 text-sm">
              {hotspots.map((h) => (
                <li key={h.id} className="flex items-center justify-between py-2">
                  <div>
                    <div className="font-mono text-xs text-ink/50">
                      {h.lat.toFixed(4)}, {h.lng.toFixed(4)}
                    </div>
                    <div>{h.violation_count} violations</div>
                  </div>
                  <RiskDot score={h.risk_score} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
