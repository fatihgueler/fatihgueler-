export default function ProgressBar({
  current,
  total,
  phase,
}: {
  current: number;
  total: number;
  phase: string;
}) {
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-slate-300">{phase || "Arbeite …"}</span>
        {total > 0 && <span className="text-slate-500">{pct}%</span>}
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-brand transition-all duration-500"
          style={{ width: `${total > 0 ? pct : 100}%` }}
        />
      </div>
    </div>
  );
}
