import { Lead } from "@/lib/types";

function Badge({ pruefung }: { pruefung: string }) {
  if (pruefung === "hat Website")
    return <span className="whitespace-nowrap rounded-full bg-red-500/15 px-2 py-0.5 text-xs text-red-400">hat Website</span>;
  if (pruefung.startsWith("ohne Website"))
    return <span className="whitespace-nowrap rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-400">ohne Website ✓</span>;
  if (pruefung === "ungeprüft")
    return <span className="whitespace-nowrap rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-400">ungeprüft</span>;
  return <span className="text-xs text-slate-600">–</span>;
}

export default function ResultsTable({ leads }: { leads: Lead[] }) {
  return (
    <div className="glass max-h-[68vh] overflow-auto rounded-2xl">
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 z-10 bg-slate-900/95 text-left text-xs uppercase tracking-wide text-slate-400 backdrop-blur">
          <tr>
            <th className="px-3 py-2.5">Name</th>
            <th className="hidden px-3 py-2.5 sm:table-cell">Kategorie</th>
            <th className="px-3 py-2.5">Telefon</th>
            <th className="hidden px-3 py-2.5 md:table-cell">Adresse</th>
            <th className="px-3 py-2.5">Status</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((l, i) => (
            <tr key={i} className="border-t border-white/5 transition hover:bg-white/5">
              <td className="px-3 py-2.5">
                <div className="font-medium text-slate-100">{l.name}</div>
                <div className="text-xs text-slate-500 sm:hidden">{l.kategorie}</div>
                {l.email && <div className="text-xs text-slate-500">{l.email}</div>}
              </td>
              <td className="hidden px-3 py-2.5 text-slate-300 sm:table-cell">{l.kategorie}</td>
              <td className="px-3 py-2.5">
                <a href={`tel:${l.telefon.replace(/\s/g, "")}`} className="text-indigo-400 hover:underline">
                  {l.telefon}
                </a>
              </td>
              <td className="hidden px-3 py-2.5 text-slate-400 md:table-cell">{l.adresse || "–"}</td>
              <td className="px-3 py-2.5"><Badge pruefung={l.pruefung} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
