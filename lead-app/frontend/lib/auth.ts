import { API } from "./api";

const TOKEN_KEY = "leadfinder_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function post(path: string, body: unknown) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Es ist ein Fehler aufgetreten");
  return data as { token: string; email: string };
}

export async function register(email: string, password: string) {
  const d = await post("/api/auth/register", { email, password });
  setToken(d.token);
  return d;
}

export async function login(email: string, password: string) {
  const d = await post("/api/auth/login", { email, password });
  setToken(d.token);
  return d;
}

export async function me(): Promise<{ email: string } | null> {
  if (!getToken()) return null;
  try {
    const r = await fetch(`${API}/api/auth/me`, { headers: authHeaders() });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}
