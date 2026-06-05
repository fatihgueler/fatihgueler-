import AnimatedNumber from "./AnimatedNumber";

export default function StatCard({
  label,
  value,
  accent = "text-slate-100",
  icon,
}: {
  label: string;
  value: string | number;
  accent?: string;
  icon?: string;
}) {
  return (
    <div className="glass animate-fadeUp rounded-2xl p-4 transition hover:border-white/20">
      <div className="flex items-center justify-between">
        <div className={`text-2xl font-bold sm:text-3xl ${accent}`}>
          {typeof value === "number" ? <AnimatedNumber value={value} /> : value}
        </div>
        {icon && <span className="text-lg opacity-70">{icon}</span>}
      </div>
      <div className="mt-1 text-xs text-slate-400">{label}</div>
    </div>
  );
}
