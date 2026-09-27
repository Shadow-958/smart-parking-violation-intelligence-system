import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import apiClient from "../lib/apiClient";
import PageHeader from "../components/PageHeader";
import CurbStatus from "../components/CurbStatus";
import { useAuth } from "../context/AuthContext";

const STATUS_OPTIONS = ["pending", "approved", "rejected", "duplicate", "resolved"];
const TYPE_OPTIONS = [
  "illegal_parking",
  "double_parking",
  "no_parking_zone",
  "footpath_parking",
  "emergency_exit_blocking",
  "unclassified",
];

export default function ComplaintsPage() {
  const { isStaff } = useAuth();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const limit = 20;
  const [filters, setFilters] = useState({ status: "", complaint_type: "", search: "" });
  const [loading, setLoading] = useState(true);

  const endpoint = isStaff ? "/api/complaints" : "/api/complaints/me";

  useEffect(() => {
    setLoading(true);
    const params = { skip, limit };
    if (isStaff) {
      if (filters.status) params.status = filters.status;
      if (filters.complaint_type) params.complaint_type = filters.complaint_type;
      if (filters.search) params.search = filters.search;
    }
    apiClient
      .get(endpoint, { params })
      .then((res) => {
        setItems(res.data.items);
        setTotal(res.data.total);
      })
      .finally(() => setLoading(false));
  }, [endpoint, skip, filters, isStaff]);

  async function updateStatus(id, newStatus) {
    await apiClient.patch(`/api/complaints/${id}/status`, { status: newStatus });
    setItems((prev) => prev.map((c) => (c.id === id ? { ...c, status: newStatus } : c)));
  }

  return (
    <div>
      <PageHeader
        title={isStaff ? "Complaints — Admin Panel" : "My Complaints"}
        subtitle={`${total} total`}
      />

      {isStaff && (
        <div className="flex flex-wrap gap-3 border-b border-ink/10 px-8 py-4">
          <input
            placeholder="Search text, location, address…"
            value={filters.search}
            onChange={(e) => {
              setSkip(0);
              setFilters((f) => ({ ...f, search: e.target.value }));
            }}
            className="w-64 border border-ink/20 bg-white px-3 py-1.5 text-sm"
          />
          <select
            value={filters.status}
            onChange={(e) => {
              setSkip(0);
              setFilters((f) => ({ ...f, status: e.target.value }));
            }}
            className="border border-ink/20 bg-white px-3 py-1.5 text-sm"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            value={filters.complaint_type}
            onChange={(e) => {
              setSkip(0);
              setFilters((f) => ({ ...f, complaint_type: e.target.value }));
            }}
            className="border border-ink/20 bg-white px-3 py-1.5 text-sm"
          >
            <option value="">All violation types</option>
            {TYPE_OPTIONS.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="p-8">
        {loading ? (
          <p className="font-display uppercase text-ink/40">Loading…</p>
        ) : items.length === 0 ? (
          <p className="text-ink/50">No complaints to show yet.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-ink/20 text-left font-mono text-xs uppercase text-ink/50">
                <th className="py-2">Type</th>
                <th className="py-2">Status</th>
                <th className="py-2">Location</th>
                <th className="py-2">Submitted</th>
                {isStaff && <th className="py-2">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="border-b border-ink/5 hover:bg-ink/[0.02]">
                  <td className="py-2">
                    <Link to={`/complaints/${c.id}`} className="hover:underline">
                      {c.complaint_type.replace(/_/g, " ")}
                    </Link>
                    {c.is_duplicate && (
                      <span className="ml-2 font-mono text-xs text-curb-blue">dup</span>
                    )}
                  </td>
                  <td className="py-2">
                    <CurbStatus status={c.status} />
                  </td>
                  <td className="py-2 text-ink/70">{c.address || c.location_text || "—"}</td>
                  <td className="py-2 font-mono text-xs text-ink/50">
                    {new Date(c.submitted_at).toLocaleString()}
                  </td>
                  {isStaff && (
                    <td className="py-2">
                      <select
                        value={c.status}
                        onChange={(e) => updateStatus(c.id, e.target.value)}
                        className="border border-ink/20 bg-white px-2 py-1 text-xs"
                      >
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="mt-4 flex items-center gap-3 font-mono text-xs">
          <button
            disabled={skip === 0}
            onClick={() => setSkip((s) => Math.max(0, s - limit))}
            className="border border-ink/20 px-3 py-1 disabled:opacity-30"
          >
            Prev
          </button>
          <span>
            {skip + 1}–{Math.min(skip + limit, total)} of {total}
          </span>
          <button
            disabled={skip + limit >= total}
            onClick={() => setSkip((s) => s + limit)}
            className="border border-ink/20 px-3 py-1 disabled:opacity-30"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
