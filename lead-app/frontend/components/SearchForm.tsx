"use client";

import { useState } from "react";
import { SearchParams } from "@/lib/types";

const PRESETS: Record<string, string[] | null> = {
  "Alle KMUs": null,
  Gastronomie: [
    "amenity=restaurant", "amenity=cafe", "amenity=bar", "amenity=pub",
    "amenity=fast_food", "amenity=biergarten", "amenity=ice_cream",
  ],
  Einzelhandel: ["shop"],
  Handwerk: ["craft"],
  Dienstleister: [
    "office=lawyer", "office=tax_advisor", "office=insurance",
    "office=estate_agent", "amenity=pharmacy", "amenity=driving_school",
  ],
};

export default function SearchForm({
  onSearch,
  disabled,
}: {
  onSearch: (p: SearchParams, label: string) => void;
  disabled: boolean;
}) {
  const [stadt, setStadt] = useState("Hannover");
  const [region, setRegion] = useState(false);
  const [preset, setPreset] = useState("Alle KMUs");
  const [nurTel, setNurTel] = useState(true);

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const ort = stadt.trim() || "Hannover";
    onSearch(
      { stadt: ort, level: region ? "6" : "8", kategorien: PRESETS[preset], nur_mit_telefon: nurTel },
      `${ort}${region ? " · Umland" : ""} · ${preset}`,
    );
  }

  return (
    <form onSubmit={submit} className="glass-strong rounded-2xl p-4 sm:p-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-slate-400">Stadt / Gebiet</label>
          <input
            value={stadt}
            onChange={(e) => setStadt(e.target.value)}
            placeholder="z. B. Hannover"
            className="rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-slate-400">Branche</label>
          <select
            value={preset}
            onChange={(e) => setPreset(e.target.value)}
            className="rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
          >
            {Object.keys(PRESETS).map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-4">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" checked={region} onChange={(e) => setRegion(e.target.checked)} className="h-4 w-4 accent-indigo-500" />
            Umland (Region)
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" checked={nurTel} onChange={(e) => setNurTel(e.target.checked)} className="h-4 w-4 accent-indigo-500" />
            nur mit Telefon
          </label>
        </div>

        <button type="submit" disabled={disabled} className="btn-primary w-full sm:w-auto">
          {disabled ? "Suche läuft …" : "✨ Leads finden"}
        </button>
      </div>

      {region && (
        <p className="mt-3 text-xs text-slate-500">
          Tipp: Für das Umland den OSM-Regionsnamen eingeben, z. B.{" "}
          <span className="text-slate-300">„Region Hannover&quot;</span>.
        </p>
      )}
    </form>
  );
}
