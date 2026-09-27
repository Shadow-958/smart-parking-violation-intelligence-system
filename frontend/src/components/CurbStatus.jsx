/**
 * Renders a status/priority value as a small "painted curb stub" — the
 * design's signature device, echoing real curb color-coding (red = no
 * stopping, yellow = limited/loading, green = time-limited/permitted).
 * Used consistently for complaint status, hotspot risk, and
 * recommendation priority so the color system means the same thing
 * everywhere in the app.
 */
const CURB_STYLES = {
  // complaint status
  pending: { color: "bg-curb-yellow", label: "Pending" },
  approved: { color: "bg-curb-green", label: "Approved" },
  rejected: { color: "bg-curb-red", label: "Rejected" },
  duplicate: { color: "bg-curb-blue", label: "Duplicate" },
  resolved: { color: "bg-curb-green", label: "Resolved" },
  // recommendation status
  suggested: { color: "bg-curb-yellow", label: "Suggested" },
  accepted: { color: "bg-curb-green", label: "Accepted" },
  dismissed: { color: "bg-asphalt/40", label: "Dismissed" },
  completed: { color: "bg-curb-blue", label: "Completed" },
};

export default function CurbStatus({ status, label }) {
  const style = CURB_STYLES[status] || { color: "bg-asphalt/30", label: status };
  return (
    <span className="inline-flex items-center gap-2 text-sm font-medium">
      <span className={`h-3 w-6 rounded-sm ${style.color}`} aria-hidden="true" />
      {label || style.label}
    </span>
  );
}

/** Small numeric severity dot for risk_score / confidence values (0-1),
 * using the same red/yellow/green curb logic rather than a separate
 * color language. */
export function RiskDot({ score }) {
  const color = score >= 0.66 ? "bg-curb-red" : score >= 0.33 ? "bg-curb-yellow" : "bg-curb-green";
  return (
    <span className="inline-flex items-center gap-2 text-sm">
      <span className={`h-3 w-6 rounded-sm ${color}`} aria-hidden="true" />
      <span className="font-mono">{(score ?? 0).toFixed(2)}</span>
    </span>
  );
}
