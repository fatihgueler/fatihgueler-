import { Job, SearchParams } from "./types";

// Slash(es) am Ende entfernen, damit `${API}/api/...` nie zu `//api/...` wird
// (doppelter Slash → 404). Robust auch bei NEXT_PUBLIC_API_URL mit „/" am Ende.
export const API = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export async function startSearch(params: SearchParams): Promise<string> {
  const res = await fetch(`${API}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error("Suche konnte nicht gestartet werden");
  const data = await res.json();
  return data.job_id as string;
}

export async function getJob(id: string): Promise<Job> {
  const res = await fetch(`${API}/api/jobs/${id}`);
  if (!res.ok) throw new Error("Job nicht gefunden");
  return res.json();
}

export async function startVerify(id: string): Promise<void> {
  const res = await fetch(`${API}/api/jobs/${id}/verify`, { method: "POST" });
  if (!res.ok) throw new Error("Verifizierung konnte nicht gestartet werden");
}

export function streamUrl(id: string): string {
  return `${API}/api/jobs/${id}/stream`;
}

export function exportUrl(id: string, nurOhneWebsite: boolean): string {
  return `${API}/api/jobs/${id}/export.csv?nur_ohne_website=${nurOhneWebsite}`;
}
