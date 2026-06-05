"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import SearchForm from "@/components/SearchForm";
import ProgressBar from "@/components/ProgressBar";
import StatCard from "@/components/StatCard";
import ResultsTable from "@/components/ResultsTable";
import SavedSearches from "@/components/SavedSearches";
import AuthModal from "@/components/AuthModal";
import { Lead, SearchChip, SearchParams } from "@/lib/types";
import { exportUrl, getJob, startSearch, startVerify, streamUrl } from "@/lib/api";
import { clearToken, me } from "@/lib/auth";
import { createSearch, deleteSearch, listSearches } from "@/lib/searches";
import { loadSearches, removeSearch, saveSearch } from "@/lib/storage";

const Globe = dynamic(() => import("@/components/Globe"), {
  ssr: false,
  loading: () => <div className="mx-auto aspect-square w-full max-w-[440px] animate-pulse rounded-full bg-indigo-500/10" />,
});
const LeadMap = dynamic(() => import("@/components/LeadMap"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-slate-500">Karte lädt …</div>,
});

type Status = "idle" | "running" | "done" | "error";

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [phase, setPhase] = useState("");
  const [prog, setProg] = useState({ current: 0, total: 0 });
  const [stats, setStats] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [onlyNoWeb, setOnlyNoWeb] = useState(false);
  const [saved, setSaved] = useState<SearchChip[]>([]);
  const [user, setUser] = useState<string | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auth + gespeicherte Suchen laden
  useEffect(() => {
    (async () => {
      const u = await me();
      if (u) {
        setUser(u.email);
        setSaved(await listSearches());
      } else {
        setSaved(loadSearches());
      }
    })();
  }, []);

  const stopPoll = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const listen = useCallback((id: string, onDone: () => void) => {
    esRef.current?.close();
    const es = new EventSource(streamUrl(id));
    esRef.current = es;
    es.onmessage = (ev) => {
      const d = JSON.parse(ev.data);
      setPhase(d.phase);
      setProg({ current: d.current, total: d.total });
      setStats(d.stats || {});
      if (d.status === "done" || d.status === "error") {
        es.close();
        esRef.current = null;
        if (d.status === "error") {
          setStatus("error");
          setError(d.phase || "Unbekannter Fehler");
        } else {
          onDone();
        }
      }
    };
    es.onerror = () => {
      es.close();
      esRef.current = null;
    };
  }, []);

  async function persistSearch(chip: SearchChip) {
    if (user) {
      await createSearch(chip);
      setSaved(await listSearches());
    } else {
      setSaved(saveSearch({ ...chip, ts: Date.now() }));
    }
  }

  async function handleSearch(p: SearchParams, label: string) {
    setError(null);
    setLeads([]);
    setStats({});
    setVerifying(false);
    setStatus("running");
    setPhase("Starte …");
    setProg({ current: 0, total: 0 });
    document.getElementById("ergebnisse")?.scrollIntoView({ behavior: "smooth" });
    try {
      const id = await startSearch(p);
      setJobId(id);
      listen(id, async () => {
        const job = await getJob(id);
        setLeads(job.leads);
        setStats(job.stats);
        setPhase(job.phase);
        setStatus("done");
        persistSearch({ ...p, label, count: job.leads.length });
      });
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : "Fehler beim Start");
    }
  }

  async function handleVerify() {
    if (!jobId) return;
    setError(null);
    setVerifying(true);
    setStatus("running");
    setStats({});
    try {
      await startVerify(jobId);
      stopPoll();
      pollRef.current = setInterval(async () => {
        try {
          const job = await getJob(jobId);
          setLeads([...job.leads]);
        } catch {
          /* ignore */
        }
      }, 2500);
      listen(jobId, async () => {
        stopPoll();
        const job = await getJob(jobId);
        setLeads([...job.leads]);
        setStats(job.stats);
        setPhase(job.phase);
        setStatus("done");
        setVerifying(false);
      });
    } catch (e) {
      stopPoll();
      setVerifying(false);
      setStatus("error");
      setError(e instanceof Error ? e.message : "Fehler bei der Verifizierung");
    }
  }

  async function handleRemoveSaved(s: SearchChip) {
    if (user && s.id) {
      await deleteSearch(s.id);
      setSaved(await listSearches());
    } else {
      setSaved(removeSearch(s.label));
    }
  }

  async function handleAuth(email: string) {
    setUser(email);
    setSaved(await listSearches());
  }

  function handleLogout() {
    clearToken();
    setUser(null);
    setSaved(loadSearches());
  }

  useEffect(() => () => {
    esRef.current?.close();
    stopPoll();
  }, []);

  const running = status === "running";
  const hasLeads = leads.length > 0;

  return (
    <div className="min-h-screen">
      {/* Navbar */}
      <nav className="sticky top-0 z-20 border-b border-white/5 bg-slate-950/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="text-lg font-bold tracking-tight">
            Lead<span className="text-gradient">Finder</span>
          </div>
          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="hidden text-sm text-slate-300 sm:block">👤 {user}</span>
                <button onClick={handleLogout} className="glass rounded-lg px-3 py-1.5 text-sm text-slate-200 transition hover:border-red-400/40">
                  Logout
                </button>
              </>
            ) : (
              <button onClick={() => setAuthOpen(true)} className="btn-primary px-4 py-1.5">
                Login / Registrieren
              </button>
            )}
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-4">
        {/* Hero */}
        <section className="grid items-center gap-10 py-10 lg:grid-cols-2 lg:py-14">
          <div className="animate-fadeUp">
            <span className="inline-flex items-center gap-2 rounded-full glass px-3 py-1 text-xs text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Lead-Generierung für Web-Entwickler
            </span>
            <h1 className="mt-4 text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl">
              Finde Betriebe <span className="text-gradient">ohne Website</span>
            </h1>
            <p className="mt-4 max-w-md text-slate-400">
              KMUs in deiner Stadt oder Region – inklusive Telefonnummer, Karte,
              Fehltreffer-Verifizierung und CSV-Export. Komplett kostenlos.
            </p>

            <div className="mt-6">
              <SearchForm onSearch={handleSearch} disabled={running} />
            </div>
            <SavedSearches
              items={saved}
              cloud={!!user}
              onRun={(s) => handleSearch(s, s.label)}
              onRemove={handleRemoveSaved}
            />
          </div>

          <div className="animate-float">
            <Globe />
          </div>
        </section>

        {/* Ergebnisse */}
        <section id="ergebnisse" className="scroll-mt-20 pb-20">
          {running && (
            <div className="mb-4">
              <ProgressBar current={prog.current} total={prog.total} phase={phase} />
            </div>
          )}

          {error && (
            <div className="glass mb-4 rounded-2xl border-red-900/50 bg-red-950/30 p-4 text-sm text-red-300">⚠️ {error}</div>
          )}

          {hasLeads && (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard label="KMUs gefunden" value={leads.length} accent="text-indigo-300" icon="🏢" />
                <StatCard label="mit E-Mail" value={stats.mit_email ?? leads.filter((l) => l.email).length} icon="✉️" />
                <StatCard label="ohne Website (geprüft)" value={stats.ohne_website ?? "–"} accent="text-emerald-400" icon="✅" />
                <StatCard label="hat Website (geprüft)" value={stats.mit_website ?? "–"} accent="text-red-400" icon="🌐" />
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button onClick={handleVerify} disabled={running} className="glass rounded-xl px-4 py-2 text-sm font-medium text-slate-100 transition hover:border-indigo-400/50 disabled:opacity-50">
                  {verifying ? "🔍 Prüfe …" : "🔍 Fehltreffer prüfen"}
                </button>
                <a href={jobId ? exportUrl(jobId, onlyNoWeb) : "#"} className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition hover:brightness-110">
                  ⬇️ CSV exportieren
                </a>
                <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-400">
                  <input type="checkbox" checked={onlyNoWeb} onChange={(e) => setOnlyNoWeb(e.target.checked)} className="h-4 w-4 accent-indigo-500" />
                  nur „ohne Website“
                </label>
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <ResultsTable leads={leads} />
                <div className="h-[420px] overflow-hidden rounded-2xl border border-white/10 lg:h-[68vh]">
                  <LeadMap leads={leads} />
                </div>
              </div>
            </>
          )}

          {!hasLeads && !running && !error && (
            <p className="py-10 text-center text-slate-500">
              Stadt &amp; Branche wählen und „Leads finden“ klicken – die Ergebnisse erscheinen hier.
            </p>
          )}
        </section>
      </main>

      <footer className="border-t border-white/5 py-8 text-center text-xs text-slate-500">
        <p>Nur für legale Zwecke. Beim Kontaktieren UWG §7 &amp; DSGVO beachten (Telefon-Akquise B2B meist ok, Kalt-E-Mails heikel).</p>
        <p className="mt-1">Datenquelle: © OpenStreetMap-Mitwirkende · Verifizierung via DuckDuckGo</p>
      </footer>

      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} onAuth={handleAuth} />}
    </div>
  );
}
