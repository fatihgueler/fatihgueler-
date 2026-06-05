"""
main.py — FastAPI-Backend der Lead-App.

Stellt die Kernlogik (core.py) als JSON-API bereit:

  POST /api/search              → Lead-Suche starten  → { job_id }
  GET  /api/jobs/{id}           → Status + Ergebnisse
  GET  /api/jobs/{id}/stream    → Live-Fortschritt (Server-Sent Events)
  POST /api/jobs/{id}/verify    → Fehltreffer-Verifizierung starten
  GET  /api/jobs/{id}/export.csv→ Ergebnisse als CSV (Excel)

Starten:
  uvicorn main:app --reload --port 8000
"""

import asyncio
import csv
import io
import json
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import core

app = FastAPI(title="Lead-Finder API", version="1.0")

# Frontend (Next.js, Port 3000) darf zugreifen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Einfacher In-Memory-Job-Speicher (für den MVP ausreichend)
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()


class SearchRequest(BaseModel):
    stadt: str = "Hannover"
    level: str = "8"                      # 8 = Stadt, 6 = Region
    kategorien: list[str] | None = None   # OSM-Filter; None = Standard (alle KMUs)
    nur_mit_telefon: bool = True


def _neuer_job(typ: str) -> dict:
    job = {
        "id": uuid.uuid4().hex[:12],
        "type": typ,
        "status": "running",
        "phase": "Starte …",
        "current": 0,
        "total": 0,
        "leads": [],
        "stats": {},
        "error": None,
        "created": time.time(),
    }
    with LOCK:
        JOBS[job["id"]] = job
    return job


# ───────────────────────── Hintergrund-Worker ─────────────────────────

def _such_worker(job: dict, req: SearchRequest):
    try:
        def progress(stufe, gesamt, label):
            job["current"] = stufe
            job["total"] = gesamt
            job["phase"] = f"Suche: {label} ({stufe}/{gesamt})"

        leads = core.finde_leads(
            req.stadt, req.level, req.kategorien, req.nur_mit_telefon, progress
        )
        job["leads"] = leads
        job["stats"] = {
            "gesamt": len(leads),
            "mit_email": sum(1 for d in leads if d["email"]),
        }
        job["phase"] = f"Fertig: {len(leads)} KMUs ohne Website"
        job["status"] = "done"
    except Exception as e:  # noqa: BLE001
        job["error"] = str(e)
        job["phase"] = "Fehler"
        job["status"] = "error"


def _verify_worker(job: dict):
    leads = job["leads"]
    job["total"] = len(leads)
    keine = hat = offen = 0
    for i, lead in enumerate(leads, start=1):
        status, domain = core.verifiziere_lead(lead)
        if status == "hat":
            lead["pruefung"] = "hat Website"
            lead["website"] = domain
            hat += 1
        elif status == "keine":
            lead["pruefung"] = "ohne Website (bestätigt)"
            keine += 1
        else:
            lead["pruefung"] = "ungeprüft"
            offen += 1
        job["current"] = i
        job["phase"] = f"Verifiziere … {i}/{len(leads)}"
        job["stats"] = {"ohne_website": keine, "mit_website": hat, "offen": offen}
        time.sleep(1.8)  # höflich gegenüber DuckDuckGo
    job["phase"] = f"Verifizierung fertig: {keine} bestätigt ohne Website"
    job["status"] = "done"


# ───────────────────────── Endpunkte ─────────────────────────

@app.get("/")
def root():
    return {"app": "Lead-Finder API", "status": "ok", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/search")
def search(req: SearchRequest):
    job = _neuer_job("search")
    threading.Thread(target=_such_worker, args=(job, req), daemon=True).start()
    return {"job_id": job["id"]}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job nicht gefunden")
    return job


@app.post("/api/jobs/{job_id}/verify")
def verify(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job nicht gefunden")
    if not job["leads"]:
        raise HTTPException(400, "Job hat noch keine Leads")
    # Verifizierung läuft auf demselben Job-Objekt (aktualisiert die Leads)
    job["status"] = "running"
    job["type"] = "verify"
    job["current"] = 0
    threading.Thread(target=_verify_worker, args=(job,), daemon=True).start()
    return {"job_id": job_id, "anzahl": len(job["leads"])}


@app.get("/api/jobs/{job_id}/stream")
async def stream(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job nicht gefunden")

    async def gen():
        last = None
        while True:
            job = JOBS.get(job_id)
            if not job:
                break
            snap = {
                "status": job["status"], "phase": job["phase"],
                "current": job["current"], "total": job["total"],
                "stats": job["stats"],
            }
            if snap != last:
                yield f"data: {json.dumps(snap, ensure_ascii=False)}\n\n"
                last = snap
            if job["status"] in ("done", "error"):
                break
            await asyncio.sleep(0.7)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/export.csv")
def export_csv(job_id: str, nur_ohne_website: bool = False):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job nicht gefunden")

    leads = job["leads"]
    if nur_ohne_website:
        leads = [d for d in leads if d.get("pruefung") != "hat Website"]

    buf = io.StringIO()
    buf.write("﻿")  # BOM → Umlaute korrekt in Excel
    writer = csv.writer(buf)
    writer.writerow(["Name", "Kategorie", "Adresse", "Telefon", "E-Mail", "Social", "OSM-Link", "Prüfung", "Website"])
    for d in leads:
        writer.writerow([
            d["name"], d["kategorie"], d["adresse"], d["telefon"],
            d["email"], d["social"], d["osm"], d.get("pruefung", ""), d.get("website", ""),
        ])
    buf.seek(0)

    name = f"leads_{job['id']}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
