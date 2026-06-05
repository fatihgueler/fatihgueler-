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
  onSearch: (p: SearchParams) => void;
  disabled: boolean;
}) {
  const [stadt, setStadt] = useState("Hannover");
  const [region, setRegion] = useState(false);
  const [preset, setPreset] = useState("Alle KMUs");
  const [nurTel, setNurTel] = useState(true);

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    onSearch({
      stadt: stadt.trim() || "Hannover",
      level: region ? "6" : "8",
      kategorien: PRESETS[preset],
      nur_mit_telefon: nurTel,
    });
  }

  return (
    <form
      onSubmit={submit}
      className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:grid-cols-2 lg:grid-cols-4"
    >
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-slate-400">Stadt / Gebiet</label>
        <input
          value={stadt}
          onChange={(e) => setStadt(e.target.value)}
          placeholder="z. B. Hannover"
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-brand"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-slate-400">Branche</label>
        <select
          value={preset}
          onChange={(e) => setPreset(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-brand"
        >
          {Object.keys(PRESETS).map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
      </div>

      <div className="flex flex-col justify-center gap-2 pt-2">
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input type="checkbox" checked={region} onChange={(e) => setRegion(e.target.checked)} className="accent-brand" />
          Umland einbeziehen (Region)
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input type="checkbox" checked={nurTel} onChange={(e) => setNurTel(e.target.checked)} className="accent-brand" />
          nur mit Telefonnummer
        </label>
      </div>

      <div className="flex items-end">
        <button
          type="submit"
          disabled={disabled}
          className="w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          {disabled ? "Suche läuft …" : "Leads finden"}
        </button>
      </div>

      {region && (
        <p className="text-xs text-slate-500 sm:col-span-2 lg:col-span-4">
          Tipp: Für das Umland den OSM-Regionsnamen eingeben, z. B.{" "}
          <span className="text-slate-300">„Region Hannover&quot;</span>.
        </p>
      )}
    </form>
  );
}
