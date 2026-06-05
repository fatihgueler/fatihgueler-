import { API } from "./api";
import { authHeaders } from "./auth";
import { SearchChip } from "./types";

/** Serverseitige gespeicherte Suchen (pro eingeloggtem Nutzer). */

export async function listSearches(): Promise<SearchChip[]> {
  const r = await fetch(`${API}/api/searches`, { headers: authHeaders() });
  if (!r.ok) return [];
  return r.json();
}

export async function createSearch(s: SearchChip): Promise<void> {
  await fetch(`${API}/api/searches`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      label: s.label,
      stadt: s.stadt,
      level: s.level,
      kategorien: s.kategorien,
      nur_mit_telefon: s.nur_mit_telefon,
      count: s.count,
    }),
  });
}

export async function deleteSearch(id: string): Promise<void> {
  await fetch(`${API}/api/searches/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}
