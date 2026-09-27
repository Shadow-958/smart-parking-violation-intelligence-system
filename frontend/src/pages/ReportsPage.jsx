import { useState } from "react";
import apiClient from "../lib/apiClient";
import PageHeader from "../components/PageHeader";

const STATUS_OPTIONS = ["pending", "approved", "rejected", "duplicate", "resolved"];

export default function ReportsPage() {
  const [filters, setFilters] = useState({ status: "", submitted_from: "", submitted_to: "" });
  const [downloading, setDownloading] = useState(false);

  async function handleDownload() {
    setDownloading(true);
    try {
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.submitted_from) params.submitted_from = filters.submitted_from;
      if (filters.submitted_to) params.submitted_to = filters.submitted_to;

      const response = await apiClient.get("/api/reports/complaints/csv", {
        params,
        responseType: "blob",
      });

      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "complaints_export.csv";
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div>
      <PageHeader title="Reports" subtitle="Export complaint data" />

      <div className="max-w-lg space-y-4 p-8">
        <div>
          <label className="mb-1 block font-mono text-xs uppercase text-ink/50">Status</label>
          <select
            value={filters.status}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
            className="w-full border border-ink/20 bg-white px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-ink/50">From</label>
            <input
              type="date"
              value={filters.submitted_from}
              onChange={(e) => setFilters((f) => ({ ...f, submitted_from: e.target.value }))}
              className="w-full border border-ink/20 bg-white px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-ink/50">To</label>
            <input
              type="date"
              value={filters.submitted_to}
              onChange={(e) => setFilters((f) => ({ ...f, submitted_to: e.target.value }))}
              className="w-full border border-ink/20 bg-white px-3 py-2 text-sm"
            />
          </div>
        </div>

        <button
          onClick={handleDownload}
          disabled={downloading}
          className="bg-curb-yellow px-6 py-2 font-display uppercase tracking-wide text-asphalt-dark disabled:opacity-50"
        >
          {downloading ? "Preparing…" : "Download CSV"}
        </button>
      </div>
    </div>
  );
}
