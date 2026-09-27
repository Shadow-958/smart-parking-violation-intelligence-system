import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../lib/apiClient";
import PageHeader from "../components/PageHeader";

const COMPLAINT_SOURCES = [
  { value: "portal", label: "Citizen portal" },
  { value: "mobile_app", label: "Mobile app" },
  { value: "email", label: "Email" },
  { value: "social_media", label: "Social media" },
];

export default function SubmitComplaintPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    raw_text: "",
    source: "portal",
    location_text: "",
    latitude: null,
    longitude: null,
    contact_name: "",
    contact_phone: "",
    contact_email: "",
  });
  const [geoStatus, setGeoStatus] = useState(null); // "locating" | "done" | "error"
  const [image, setImage] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submittedId, setSubmittedId] = useState(null);

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  function captureGPS() {
    if (!navigator.geolocation) {
      setGeoStatus("error");
      return;
    }
    setGeoStatus("locating");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm((f) => ({
          ...f,
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
        }));
        setGeoStatus("done");
      },
      () => setGeoStatus("error"),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { data: complaint } = await apiClient.post("/api/complaints", form);

      if (image) {
        const body = new FormData();
        body.append("file", image);
        await apiClient.post(`/api/complaints/${complaint.id}/images`, body, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      setSubmittedId(complaint.id);
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't submit the complaint. Check the form and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  // --- Live analysis view after submission ---
  const [analysis, setAnalysis] = useState(null);
  const [analysisReady, setAnalysisReady] = useState(false);

  useEffect(() => {
    if (!submittedId) return;
    let cancelled = false;

    function poll() {
      apiClient
        .get(`/api/complaints/${submittedId}`)
        .then((res) => {
          if (cancelled) return;
          setAnalysis(res.data);
          // NLP pipeline is done when cleaned_text exists
          if (res.data.cleaned_text) {
            setAnalysisReady(true);
          }
        })
        .catch(() => {});
    }

    poll(); // immediate first fetch
    const interval = setInterval(poll, 2000);

    // Stop polling once analysis is ready (give a few extra polls for geocoding)
    const timeout = setTimeout(() => clearInterval(interval), 30000);

    return () => {
      cancelled = true;
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [submittedId]);

  if (submittedId) {
    const stages = [
      {
        name: "Text Preprocessing",
        desc: "Cleaning, tokenizing, lemmatizing, removing stopwords",
        done: !!analysis?.cleaned_text,
        result: analysis?.cleaned_text,
        icon: "🧹",
      },
      {
        name: "Location Extraction (NER)",
        desc: "Extracting location entities using spaCy NER (GPE, LOC, FAC)",
        done: !!analysis?.cleaned_text, // runs at same time as preprocessing
        result: analysis?.extracted_location_entity || (analysis?.cleaned_text ? "No location entity found" : null),
        icon: "📍",
      },
      {
        name: "Violation Classification",
        desc: "Rule-based keyword matching / Zero-shot transformer classification",
        done: analysis?.complaint_type && analysis.complaint_type !== "unclassified",
        result: analysis?.complaint_type
          ? `${analysis.complaint_type.replace(/_/g, " ")} (${((analysis.classification_confidence ?? 0) * 100).toFixed(0)}% confidence)`
          : null,
        icon: "🏷️",
      },
      {
        name: "Duplicate Detection",
        desc: "Sentence-BERT embedding (all-MiniLM-L6-v2) + cosine similarity",
        done: !!analysis?.cleaned_text,
        result: analysis?.is_duplicate
          ? `Duplicate found (${((analysis.duplicate_similarity_score ?? 0) * 100).toFixed(0)}% match)`
          : analysis?.cleaned_text
          ? "No duplicates found"
          : null,
        icon: "🔍",
        highlight: analysis?.is_duplicate,
      },
      {
        name: "Geocoding",
        desc: "Resolving location to coordinates via Nominatim (OpenStreetMap)",
        done: !!analysis?.address,
        result: analysis?.address || (analysisReady && !analysis?.address ? "Geocoding pending or failed" : null),
        icon: "🗺️",
      },
    ];

    const completedCount = stages.filter((s) => s.done).length;
    const progress = (completedCount / stages.length) * 100;

    return (
      <div>
        <PageHeader title="Complaint Analysis" subtitle="AI pipeline processing your complaint" />

        <div className="mx-auto max-w-2xl space-y-6 p-8">
          {/* Progress bar */}
          <div className="border border-ink/10 bg-white p-5">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-display uppercase tracking-wide">
                {analysisReady ? "✅ Analysis Complete" : "⏳ Processing…"}
              </span>
              <span className="font-mono text-xs text-ink/50">
                {completedCount}/{stages.length} stages
              </span>
            </div>
            <div className="h-2 w-full rounded bg-ink/10">
              <div
                className="h-2 rounded bg-curb-green transition-all duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="mt-2 font-mono text-xs text-ink/40">Reference: {submittedId}</div>
          </div>

          {/* Pipeline stages */}
          <div className="space-y-3">
            {stages.map((stage, i) => (
              <div
                key={i}
                className={`border bg-white p-4 transition-all duration-500 ${
                  stage.done ? "border-curb-green/30" : "border-ink/10"
                }`}
                style={{
                  borderLeft: `4px solid ${stage.done ? "#1B7A43" : "#E5E5E5"}`,
                }}
              >
                <div className="flex items-start gap-3">
                  <span className="text-lg">{stage.icon}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{stage.name}</span>
                      {stage.done ? (
                        <span className="rounded bg-curb-green/10 px-1.5 py-0.5 font-mono text-[10px] uppercase text-curb-green">
                          Done
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded bg-curb-yellow/10 px-1.5 py-0.5 font-mono text-[10px] uppercase text-curb-yellow">
                          <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-curb-yellow" />
                          Processing
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-ink/40">{stage.desc}</p>
                    {stage.result && (
                      <div
                        className={`mt-2 rounded px-3 py-2 font-mono text-xs ${
                          stage.highlight
                            ? "border border-curb-red/20 bg-curb-red/5 text-curb-red"
                            : "bg-ink/5 text-ink/70"
                        }`}
                      >
                        {stage.result}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Original text card */}
          {analysis && (
            <div className="border border-ink/10 bg-white p-5">
              <h3 className="mb-2 font-mono text-xs uppercase text-ink/40">Original report text</h3>
              <p className="whitespace-pre-wrap text-sm text-ink/80">{analysis.raw_text}</p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex justify-center gap-3 pt-2">
            <button
              onClick={() => navigate(`/complaints/${submittedId}`)}
              className="bg-asphalt px-4 py-2 text-sm uppercase tracking-wide text-paper"
            >
              Full detail
            </button>
            <button
              onClick={() => navigate("/map")}
              className="bg-curb-blue px-4 py-2 text-sm uppercase tracking-wide text-paper"
            >
              View on map
            </button>
            <button
              onClick={() => {
                setSubmittedId(null);
                setAnalysis(null);
                setAnalysisReady(false);
                setForm({ raw_text: "", source: "portal", location_text: "", latitude: null, longitude: null, contact_name: "", contact_phone: "", contact_email: "" });
                setImage(null);
                setGeoStatus(null);
              }}
              className="border border-ink/20 px-4 py-2 text-sm uppercase tracking-wide"
            >
              File another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Submit Complaint" subtitle="Report a parking violation" />

      <form onSubmit={handleSubmit} className="mx-auto max-w-xl space-y-5 p-8">
        <div>
          <label className="mb-1 block font-mono text-xs uppercase text-ink/50">
            What did you see? *
          </label>
          <textarea
            value={form.raw_text}
            onChange={update("raw_text")}
            required
            minLength={10}
            rows={4}
            placeholder="e.g. A white sedan is parked across the sidewalk outside 42 Elm Street, blocking the wheelchair ramp."
            className="w-full border border-ink/20 bg-white px-3 py-2 focus-visible:outline-curb-blue"
          />
        </div>

        <div>
          <label className="mb-1 block font-mono text-xs uppercase text-ink/50">Where?</label>
          <input
            value={form.location_text}
            onChange={update("location_text")}
            placeholder="Street address or nearby landmark"
            className="w-full border border-ink/20 bg-white px-3 py-2 focus-visible:outline-curb-blue"
          />
          <div className="mt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={captureGPS}
              disabled={geoStatus === "locating"}
              className="text-xs uppercase tracking-wide text-curb-blue underline disabled:opacity-50"
            >
              {geoStatus === "locating" ? "Locating…" : "📍 Use my current location"}
            </button>
            {geoStatus === "done" && (
              <span className="text-xs text-curb-green">
                ✓ GPS captured ({form.latitude?.toFixed(5)}, {form.longitude?.toFixed(5)})
              </span>
            )}
            {geoStatus === "error" && (
              <span className="text-xs text-curb-red">Could not get location — enter address above instead</span>
            )}
          </div>
        </div>

        <div>
          <label className="mb-1 block font-mono text-xs uppercase text-ink/50">How are you reporting this?</label>
          <select
            value={form.source}
            onChange={update("source")}
            className="w-full border border-ink/20 bg-white px-3 py-2 focus-visible:outline-curb-blue"
          >
            {COMPLAINT_SOURCES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-ink/50">Your name</label>
            <input
              value={form.contact_name}
              onChange={update("contact_name")}
              className="w-full border border-ink/20 bg-white px-3 py-2 focus-visible:outline-curb-blue"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-ink/50">Phone</label>
            <input
              value={form.contact_phone}
              onChange={update("contact_phone")}
              className="w-full border border-ink/20 bg-white px-3 py-2 focus-visible:outline-curb-blue"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-ink/50">Email</label>
            <input
              type="email"
              value={form.contact_email}
              onChange={update("contact_email")}
              className="w-full border border-ink/20 bg-white px-3 py-2 focus-visible:outline-curb-blue"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block font-mono text-xs uppercase text-ink/50">Photo (optional)</label>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setImage(e.target.files?.[0] || null)}
            className="w-full border border-ink/20 bg-white px-3 py-2 text-sm"
          />
        </div>

        {error && <p className="text-sm text-curb-red">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="bg-curb-yellow px-6 py-2 font-display uppercase tracking-wide text-asphalt-dark disabled:opacity-50"
        >
          {submitting ? "Submitting…" : "Submit complaint"}
        </button>
      </form>
    </div>
  );
}
