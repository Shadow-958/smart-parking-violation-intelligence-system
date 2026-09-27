export default function PageHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between border-b border-ink/10 px-8 py-6">
      <div>
        <h1 className="text-2xl text-asphalt">{title}</h1>
        {subtitle && <p className="mt-1 font-mono text-xs text-ink/50">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
