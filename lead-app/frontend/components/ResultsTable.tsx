import { Lead } from "@/lib/types";

function Badge({ pruefung }: { pruefung: string }) {
  if (pruefung === "hat Website")
    return <span className="rounded-full bg-red-500/15 px-2 py-0.5 text-xs text-red-400">hat Website</span>;
  if (pruefung.startsWith("ohne Website"))
    return <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-400">ohne Website ✓</span>;
  return <span className="text-xs text-slate-500">–</span>;
}

export default function ResultsTable({ leads }: { leads: Lead[] }) {
  return (
    <div className="max-h-[70vh] overflow-auto rounded-2xl border border-slate-800">
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 bg-slate-900 text-left text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th className="px-3 py-2">Name</th>
            <th className="px-3 py-2">Kategorie</th>
            <th className="px-3 py-2">Telefon</th>
            <th className="px-3 py-2">Adresse</th>
            <th className="px-3 py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((l, i) => (
            <tr key={i} className="border-t border-slate-800/70 hover:bg-slate-900/50">
              <td className="px-3 py-2">
                <div className="font-medium text-slate-100">{l.name}</div>
                {l.email && <div className="text-xs text-slate-500">{l.email}</div>}
              </td>
              <td className="px-3 py-2 text-slate-300">{l.kategorie}</td>
              <td className="px-3 py-2">
                <a href={`tel:${l.telefon.replace(/\s/g, "")}`} className="text-brand hover:underline">
                  {l.telefon}
                </a>
              </td>
              <td className="px-3 py-2 text-slate-400">{l.adresse || "–"}</td>
              <td className="px-3 py-2"><Badge pruefung={l.pruefung} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
