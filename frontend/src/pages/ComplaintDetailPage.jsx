import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import apiClient from "../lib/apiClient";
import PageHeader from "../components/PageHeader";
import CurbStatus, { RiskDot } from "../components/CurbStatus";
import AuthenticatedImage from "../components/AuthenticatedImage";
import { useAuth } from "../context/AuthContext";

function DetectionOverlay({ imageId }) {
  const [detections, setDetections] = useState(null);
  const [naturalSize, setNaturalSize] = useState(null);

  useEffect(() => {
    apiClient
      .get(`/api/vision/detections/${imageId}`)
      .then((res) => setDetections(res.data.vehicle_detections || []))
      .catch(() => setDetections([]));
  }, [imageId]);

  return (
    <div className="relative inline-block">
      <AuthenticatedImage
        imageId={imageId}
        alt="Complaint evidence"
        className="max-h-96 w-auto border border-ink/10"
        onLoad={(e) =>
          setNaturalSize({ width: e.target.naturalWidth, height: e.target.naturalHeight })
        }
      />
      {naturalSize &&
        detections?.map((d) => (
          <div
            key={d.id}
            title={`${d.vehicle_class} — ${(d.detection_confidence * 100).toFixed(0)}%`}
            className={`absolute border-2 ${d.is_illegal_parking ? "border-curb-red" : "border-curb-yellow"}`}
            style={{
              left: `${(d.bbox_x / naturalSize.width) * 100}%`,
              top: `${(d.bbox_y / naturalSize.height) * 100}%`,
              width: `${(d.bbox_width / naturalSize.width) * 100}%`,
              height: `${(d.bbox_height / naturalSize.height) * 100}%`,
            }}
          >
            <span className="absolute -top-5 left-0 bg-asphalt px-1 font-mono text-[10px] text-paper">
              {d.vehicle_class} {(d.detection_confidence * 100).toFixed(0)}%
            </span>
          </div>
        ))}
    </div>
  );
}

export default function ComplaintDetailPage() {
  const { id } = useParams();
  const { isStaff } = useAuth();
  const [complaint, setComplaint] = useState(null);
  const [error, setError] = useState(null);

  function load() {
    apiClient
      .get(`/api/complaints/${id}`)
      .then((res) => setComplaint(res.data))
      .catch(() => setError("Complaint not found, or you don't have access to it."));
  }

  useEffect(load, [id]);

  async function updateStatus(newStatus) {
    const { data } = await apiClient.patch(`/api/complaints/${id}/status`, { status: newStatus });
    setComplaint(data);
  }

  async function rerunNlp() {
    const { data } = await apiClient.post(`/api/nlp/analyze/${id}`);
    setComplaint(data);
  }

  if (error) return <div className="p-8 text-curb-red">{error}</div>;
  if (!complaint) return <div className="p-8 font-display uppercase text-ink/40">Loading…</div>;

  return (
    <div>
      <PageHeader
        title="Complaint Detail"
        subtitle={complaint.id}
        action={<CurbStatus status={complaint.status} />}
      />

      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <section className="border border-ink/10 bg-white p-5">
            <h2 className="mb-3 text-sm">Report text</h2>
            <p className="whitespace-pre-wrap text-ink/80">{complaint.raw_text}</p>
          </section>

          {complaint.images?.length > 0 && (
            <section className="border border-ink/10 bg-white p-5">
              <h2 className="mb-3 text-sm">Photos &amp; vehicle detection</h2>
              <div className="flex flex-wrap gap-4">
                {complaint.images.map((img) => (
                  <DetectionOverlay key={img.id} imageId={img.id} />
                ))}
              </div>
              <p className="mt-2 font-mono text-xs text-ink/40">
                Red border = high-confidence detection worth review. Yellow = low confidence.
              </p>
            </section>
          )}

          <section className="border border-ink/10 bg-white p-5">
            <h2 className="mb-3 text-sm">NLP analysis</h2>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="font-mono text-xs uppercase text-ink/40">Violation type</dt>
                <dd>{complaint.complaint_type.replace(/_/g, " ")}</dd>
              </div>
              <div>
                <dt className="font-mono text-xs uppercase text-ink/40">Classification confidence</dt>
                <dd>{complaint.classification_confidence != null ? <RiskDot score={complaint.classification_confidence} /> : "—"}</dd>
              </div>
              <div>
                <dt className="font-mono text-xs uppercase text-ink/40">Extracted location</dt>
                <dd>{complaint.extracted_location_entity || "—"}</dd>
              </div>
              <div>
                <dt className="font-mono text-xs uppercase text-ink/40">Duplicate of</dt>
                <dd>
                  {complaint.is_duplicate ? (
                    <span className="text-curb-blue">
                      {complaint.duplicate_of_id} ({(complaint.duplicate_similarity_score * 100).toFixed(0)}% match)
                    </span>
                  ) : (
                    "No"
                  )}
                </dd>
              </div>
            </dl>
            {isStaff && (
              <button
                onClick={rerunNlp}
                className="mt-4 border border-ink/20 px-3 py-1.5 text-xs uppercase tracking-wide hover:bg-ink/5"
              >
                Re-run NLP analysis
              </button>
            )}
          </section>
        </div>

        <div className="space-y-6">
          <section className="border border-ink/10 bg-white p-5">
            <h2 className="mb-3 text-sm">Details</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-ink/50">Source</dt>
                <dd>{complaint.source.replace(/_/g, " ")}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink/50">Submitted</dt>
                <dd className="font-mono text-xs">{new Date(complaint.submitted_at).toLocaleString()}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink/50">Address</dt>
                <dd className="text-right">{complaint.address || complaint.location_text || "Not geocoded yet"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink/50">Contact</dt>
                <dd className="text-right">{complaint.contact_name || "Anonymous"}</dd>
              </div>
            </dl>
          </section>

          {isStaff && (
            <section className="border border-ink/10 bg-white p-5">
              <h2 className="mb-3 text-sm">Change status</h2>
              <div className="flex flex-wrap gap-2">
                {["approved", "rejected", "resolved"].map((s) => (
                  <button
                    key={s}
                    onClick={() => updateStatus(s)}
                    disabled={complaint.status === s}
                    className="border border-ink/20 px-3 py-1.5 text-xs uppercase tracking-wide disabled:opacity-30"
                  >
                    Mark {s}
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
