import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import apiClient from "../lib/apiClient";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import CurbStatus from "../components/CurbStatus";
import { useAuth } from "../context/AuthContext";

const CURB_HEX = { pending: "#F2B705", approved: "#1B7A43", rejected: "#C8102E", duplicate: "#2B4C7E", resolved: "#1B7A43" };
const RECENT_ACTIVITY_POLL_MS = 30_000;

export default function DashboardPage() {
  const { isStaff } = useAuth();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    apiClient
      .get("/api/dashboard/summary")
      .then((res) => setSummary(res.data))
      .catch(() => setError("Couldn't load dashboard data."));
  }, []);

  useEffect(() => {
    // "Real-time alerts" per the spec, implemented honestly as polling
    // rather than a websocket/SSE push channel — a simpler, more
    // reliable fit for a 30-second-freshness activity feed than the
    // infrastructure a true push channel would need.
    const endpoint = isStaff ? "/api/complaints" : "/api/complaints/me";
    function poll() {
      apiClient
        .get(endpoint, { params: { skip: 0, limit: 5 } })
        .then((res) => setRecent(res.data.items))
        .catch(() => {});
    }
    poll();
    const interval = setInterval(poll, RECENT_ACTIVITY_POLL_MS);
    return () => clearInterval(interval);
  }, [isStaff]);

  if (error) return <div className="p-8 text-curb-red">{error}</div>;
  if (!summary) return <div className="p-8 font-display uppercase text-ink/40">Loading…</div>;

  const statusData = Object.entries(summary.by_status).map(([status, count]) => ({ status, count }));
  const typeData = Object.entries(summary.by_type).map(([type, count]) => ({
    type: type.replace(/_/g, " "),
    count,
  }));

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="City-wide parking violation overview" />

      <div className="grid grid-cols-2 gap-4 p-8 md:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Total Complaints" value={summary.total_complaints} />
        <StatCard label="Pending" value={summary.pending_count} accent="text-curb-yellow" />
        <StatCard label="Resolved" value={summary.resolved_count} accent="text-curb-green" />
        <StatCard label="Duplicates" value={summary.duplicate_count} accent="text-curb-blue" />
        <StatCard label="Active Hotspots" value={summary.hotspot_count} accent="text-curb-red" />
        <StatCard label="Open Recommendations" value={summary.suggested_recommendations} />
      </div>

      <div className="grid grid-cols-1 gap-6 px-8 pb-8 lg:grid-cols-2">
        <div className="border border-ink/10 bg-white p-4">
          <h2 className="mb-4 text-sm">Complaints by status</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={statusData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#00000010" />
              <XAxis dataKey="status" tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count">
                {statusData.map((entry) => (
                  <Cell key={entry.status} fill={CURB_HEX[entry.status] || "#23262B"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="border border-ink/10 bg-white p-4">
          <h2 className="mb-4 text-sm">Complaints by violation type</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={typeData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#00000010" />
              <XAxis type="number" allowDecimals={false} tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="type"
                width={140}
                tick={{ fontFamily: "IBM Plex Mono", fontSize: 10 }}
              />
              <Tooltip />
              <Bar dataKey="count" fill="#2B4C7E" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="border border-ink/10 bg-white p-4">
          <h2 className="mb-4 text-sm">Daily complaint volume</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={summary.daily_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#00000010" />
              <XAxis dataKey="date" tick={{ fontFamily: "IBM Plex Mono", fontSize: 10 }} />
              <YAxis allowDecimals={false} tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#F2B705" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="border border-ink/10 bg-white p-4">
          <h2 className="mb-4 text-sm">Monthly complaint volume</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={summary.monthly_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#00000010" />
              <XAxis dataKey="month" tick={{ fontFamily: "IBM Plex Mono", fontSize: 10 }} />
              <YAxis allowDecimals={false} tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#2B4C7E" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="border border-ink/10 bg-white p-4 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm">Recent activity</h2>
            <span className="font-mono text-xs text-ink/40">refreshes every 30s</span>
          </div>
          {recent.length === 0 ? (
            <p className="text-sm text-ink/50">No complaints yet.</p>
          ) : (
            <ul className="divide-y divide-ink/5 text-sm">
              {recent.map((c) => (
                <li key={c.id} className="flex items-center justify-between py-2">
                  <div>
                    <span className="font-medium">{c.complaint_type.replace(/_/g, " ")}</span>
                    <span className="ml-2 text-ink/50">{c.address || c.location_text || ""}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-xs text-ink/40">
                      {new Date(c.submitted_at).toLocaleTimeString()}
                    </span>
                    <CurbStatus status={c.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
