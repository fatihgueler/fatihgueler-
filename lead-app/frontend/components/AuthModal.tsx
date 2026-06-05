"use client";

import { useState } from "react";
import { login, register } from "@/lib/auth";

export default function AuthModal({
  onClose,
  onAuth,
}: {
  onClose: () => void;
  onAuth: (email: string) => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const fn = mode === "login" ? login : register;
      const res = await fn(email.trim(), pw);
      onAuth(res.email);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Fehler");
    } finally {
      setBusy(false);
    }
  }

  const tab = (active: boolean) =>
    `flex-1 rounded-lg py-2 text-sm font-medium transition ${
      active ? "bg-white/10 text-white" : "text-slate-400 hover:text-slate-200"
    }`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur"
      onClick={onClose}
    >
      <div
        className="glass-strong w-full max-w-sm rounded-2xl p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-center text-lg font-bold">
          Lead<span className="text-gradient">Finder</span>-Konto
        </h2>

        <div className="mb-4 flex gap-2 rounded-xl bg-slate-950/60 p-1">
          <button onClick={() => setMode("login")} className={tab(mode === "login")}>Login</button>
          <button onClick={() => setMode("register")} className={tab(mode === "register")}>Registrieren</button>
        </div>

        <form onSubmit={submit} className="space-y-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="E-Mail"
            className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
          />
          <input
            type="password"
            required
            minLength={6}
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            placeholder="Passwort (min. 6 Zeichen)"
            className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
          />
          {err && <p className="text-sm text-red-400">⚠️ {err}</p>}
          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? "…" : mode === "login" ? "Einloggen" : "Konto erstellen"}
          </button>
        </form>

        <button onClick={onClose} className="mt-3 w-full text-xs text-slate-500 transition hover:text-slate-300">
          Schließen
        </button>
      </div>
    </div>
  );
}
