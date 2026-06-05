"use client";

import { SavedSearch } from "@/lib/storage";

export default function SavedSearches({
  items,
  onRun,
  onRemove,
}: {
  items: SavedSearch[];
  onRun: (s: SavedSearch) => void;
  onRemove: (label: string) => void;
}) {
  if (!items.length) return null;
  return (
    <div className="mt-5">
      <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">Zuletzt gesucht</div>
      <div className="flex flex-wrap gap-2">
        {items.map((s) => (
          <span key={s.label} className="glass group flex items-center gap-2 rounded-full px-3 py-1.5 text-sm">
            <button onClick={() => onRun(s)} className="text-slate-200 transition hover:text-white">
              {s.label}
              {typeof s.count === "number" && <span className="ml-1 text-slate-500">({s.count})</span>}
            </button>
            <button
              onClick={() => onRemove(s.label)}
              className="text-slate-600 transition hover:text-red-400"
              aria-label="Suche entfernen"
            >
              ✕
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}
