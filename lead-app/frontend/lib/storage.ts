import { SearchParams } from "./types";

const KEY = "leadfinder_saved_searches";

export interface SavedSearch extends SearchParams {
  label: string;
  ts: number;
  count?: number;
}

export function loadSearches(): SavedSearch[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveSearch(s: SavedSearch): SavedSearch[] {
  const all = loadSearches().filter((x) => x.label !== s.label);
  all.unshift(s);
  const trimmed = all.slice(0, 8);
  try {
    localStorage.setItem(KEY, JSON.stringify(trimmed));
  } catch {
    /* localStorage evtl. nicht verfügbar */
  }
  return trimmed;
}

export function removeSearch(label: string): SavedSearch[] {
  const all = loadSearches().filter((x) => x.label !== label);
  try {
    localStorage.setItem(KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
  return all;
}
