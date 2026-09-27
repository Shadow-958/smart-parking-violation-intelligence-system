export default function StatCard({ label, value, accent }) {
  return (
    <div className="border border-ink/10 bg-white p-4">
      <div className="font-mono text-xs uppercase tracking-widest text-ink/50">{label}</div>
      <div className={`mt-1 font-display text-4xl ${accent || "text-asphalt"}`}>{value}</div>
    </div>
  );
}
