import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import apiClient from "../lib/apiClient";
import PageHeader from "../components/PageHeader";
import CurbStatus from "../components/CurbStatus";

const CURB_HEX = { pending: "#F2B705", approved: "#1B7A43", rejected: "#C8102E", duplicate: "#2B4C7E", resolved: "#1B7A43" };

// Default center: a reasonable world-ish fallback if there's no data yet
// to derive a center from. Real deployments should set this to the
// city's own coordinates.
const DEFAULT_CENTER = [19.076, 72.8777];

export default function MapViewPage() {
  const [features, setFeatures] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    function fetchFeatures() {
      apiClient
        .get("/api/gis/complaints/geojson")
        .then((res) => setFeatures(res.data.features || []))
        .finally(() => setLoading(false));
    }
    fetchFeatures();
    const interval = setInterval(fetchFeatures, 15_000);
    return () => clearInterval(interval);
  }, []);

  const center =
    features.length > 0
      ? [features[0].geometry.coordinates[1], features[0].geometry.coordinates[0]]
      : DEFAULT_CENTER;

  return (
    <div>
      <PageHeader title="Map View" subtitle={`${features.length} geocoded complaints`} />
      <div className="p-8">
        {loading ? (
          <p className="font-display uppercase text-ink/40">Loading map…</p>
        ) : (
          <div className="h-[600px] border border-ink/10">
            <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }}>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {features.map((f) => (
                <CircleMarker
                  key={f.properties.id}
                  center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
                  radius={7}
                  pathOptions={{
                    color: CURB_HEX[f.properties.status] || "#23262B",
                    fillColor: CURB_HEX[f.properties.status] || "#23262B",
                    fillOpacity: 0.8,
                  }}
                >
                  <Popup>
                    <div className="font-body text-sm">
                      <div className="mb-1 font-medium">{f.properties.complaint_type.replace(/_/g, " ")}</div>
                      <CurbStatus status={f.properties.status} />
                      <div className="mt-1 text-xs text-ink/60">{f.properties.address}</div>
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        )}
      </div>
    </div>
  );
}
