"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import SearchForm from "@/components/SearchForm";
import ProgressBar from "@/components/ProgressBar";
import StatCard from "@/components/StatCard";
import ResultsTable from "@/components/ResultsTable";
import { Lead, SearchParams } from "@/lib/types";
import { exportUrl, getJob, startSearch, startVerify, streamUrl } from "@/lib/api";

const LeadMap = dynamic(() => import("@/components/LeadMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-slate-500">Karte lädt …</div>
  ),
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
  const esRef = useRef<EventSource | null>(null);

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

  const handleSearch = useCallback(
    async (p: SearchParams) => {
      setError(null);
      setLeads([]);
      setStats({});
      setStatus("running");
      setPhase("Starte …");
      setProg({ current: 0, total: 0 });
      try {
        const id = await startSearch(p);
        setJobId(id);
        listen(id, async () => {
          const job = await getJob(id);
          setLeads(job.leads);
          setStats(job.stats);
          setPhase(job.phase);
          setStatus("done");
        });
      } catch (e) {
        setStatus("error");
        setError(e instanceof Error ? e.message : "Fehler beim Start");
      }
    },
    [listen],
  );

  const handleVerify = useCallback(async () => {
    if (!jobId) return;
    setError(null);
    setVerifying(true);
    setStatus("running");
    setStats({});
    try {
      await startVerify(jobId);
      listen(jobId, async () => {
        const job = await getJob(jobId);
        setLeads([...job.leads]);
        setStats(job.stats);
        setPhase(job.phase);
        setStatus("done");
        setVerifying(false);
      });
    } catch (e) {
      setVerifying(false);
      setStatus("error");
      setError(e instanceof Error ? e.message : "Fehler bei der Verifizierung");
    }
  }, [jobId, listen]);

  useEffect(() => () => esRef.current?.close(), []);

  const running = status === "running";
  const hasLeads = leads.length > 0;
  const ohneWebsite = stats.ohne_website ?? null;

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">
          Lead<span className="text-brand">Finder</span>
        </h1>
        <p className="mt-1 text-slate-400">
          Finde KMUs <span className="text-slate-200">ohne eigene Website</span> – inkl. Telefon,
          Karte und CSV-Export. Datenquelle: OpenStreetMap (kostenlos).
        </p>
      </header>

      <SearchForm onSearch={handleSearch} disabled={running} />

      {running && (
        <div className="mt-6">
          <ProgressBar current={prog.current} total={prog.total} phase={phase} />
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-2xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          ⚠️ {error}
        </div>
      )}

      {hasLeads && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="KMUs gefunden" value={leads.length} accent="text-brand" />
            <StatCard label="mit E-Mail" value={stats.mit_email ?? leads.filter((l) => l.email).length} />
            <StatCard
              label="ohne Website (geprüft)"
              value={ohneWebsite ?? "–"}
              accent="text-emerald-400"
            />
            <StatCard label="hat Website (geprüft)" value={stats.mit_website ?? "–"} accent="text-red-400" />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={handleVerify}
              disabled={running || verifying}
              className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-100 transition hover:border-brand disabled:opacity-50"
            >
              🔍 Fehltreffer prüfen
            </button>

            <a
              href={jobId ? exportUrl(jobId, onlyNoWeb) : "#"}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500"
            >
              ⬇️ CSV exportieren
            </a>
            <label className="flex items-center gap-2 text-sm text-slate-400">
              <input
                type="checkbox"
                checked={onlyNoWeb}
                onChange={(e) => setOnlyNoWeb(e.target.checked)}
                className="accent-brand"
              />
              nur „ohne Website“ exportieren
            </label>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <ResultsTable leads={leads} />
            <div className="h-[70vh] overflow-hidden rounded-2xl border border-slate-800">
              <LeadMap leads={leads} />
            </div>
          </div>
        </>
      )}

      {!hasLeads && !running && !error && (
        <p className="mt-10 text-center text-slate-500">
          Stadt &amp; Branche wählen und „Leads finden“ klicken.
        </p>
      )}
    </main>
  );
}
