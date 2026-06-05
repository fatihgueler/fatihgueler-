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
    <div className="glass animate-fadeUp rounded-2xl p-5">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="flex items-center gap-2 text-slate-200">
          <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-400" />
          {phase || "Arbeite …"}
        </span>
        {total > 0 && <span className="text-slate-500">{pct}%</span>}
      </div>
      <div className="relative h-2.5 overflow-hidden rounded-full bg-slate-800/80">
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-500"
          style={{ width: `${total > 0 ? pct : 100}%` }}
        />
        <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      </div>
    </div>
  );
}
