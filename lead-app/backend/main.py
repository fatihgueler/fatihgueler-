"""
main.py — FastAPI-Backend der Lead-App.

Stellt die Kernlogik (core.py) als JSON-API bereit und ergänzt
Benutzerkonten (JWT) + gespeicherte Suchen pro Nutzer (SQLite).

  POST /api/search               → Lead-Suche starten  → { job_id }
  GET  /api/jobs/{id}            → Status + Ergebnisse
  GET  /api/jobs/{id}/stream     → Live-Fortschritt (SSE)
  POST /api/jobs/{id}/verify     → Fehltreffer-Verifizierung starten
  GET  /api/jobs/{id}/export.csv → Ergebnisse als CSV

  POST /api/auth/register        → Konto anlegen → { token, email }
  POST /api/auth/login           → Einloggen     → { token, email }
  GET  /api/auth/me              → aktueller Nutzer

  GET    /api/searches           → gespeicherte Suchen des Nutzers
  POST   /api/searches           → Suche speichern
  DELETE /api/searches/{id}      → Suche löschen

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
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

import core
from auth import create_token, get_current_user, hash_password, verify_password
from database import get_session, init_db
from models import (
    AuthRequest, AuthResponse, SavedSearch, SavedSearchIn, SavedSearchOut, User,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Lead-Finder API", version="2.0", lifespan=lifespan)

# Erlaubte Frontend-Domains: in Produktion via CORS_ORIGINS setzen
# (z. B. "https://deine-app.vercel.app"), sonst alle erlaubt.
import os  # noqa: E402

_origins = os.getenv("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",")] if _origins != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-Memory-Job-Speicher (Suchläufe)
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()


class SearchRequest(BaseModel):
    stadt: str = "Hannover"
    level: str = "8"
    kategorien: list[str] | None = None
    nur_mit_telefon: bool = True


def _neuer_job(typ: str) -> dict:
    job = {
        "id": uuid.uuid4().hex[:12], "type": typ, "status": "running",
        "phase": "Starte …", "current": 0, "total": 0,
        "leads": [], "stats": {}, "error": None, "created": time.time(),
    }
    with LOCK:
        JOBS[job["id"]] = job
    return job


# ───────────────────────── Hintergrund-Worker ─────────────────────────

def _such_worker(job: dict, req: SearchRequest):
    try:
        def progress(stufe, gesamt, label):
            job["current"], job["total"] = stufe, gesamt
            job["phase"] = f"Suche: {label} ({stufe}/{gesamt})"

        leads = core.finde_leads(req.stadt, req.level, req.kategorien, req.nur_mit_telefon, progress)
        job["leads"] = leads
        job["stats"] = {"gesamt": len(leads), "mit_email": sum(1 for d in leads if d["email"])}
        job["phase"] = f"Fertig: {len(leads)} KMUs ohne Website"
        job["status"] = "done"
    except Exception as e:  # noqa: BLE001
        job["error"], job["phase"], job["status"] = str(e), "Fehler", "error"


def _verify_worker(job: dict):
    leads = job["leads"]
    job["total"] = len(leads)
    keine = hat = offen = 0
    for i, lead in enumerate(leads, start=1):
        status, domain = core.verifiziere_lead(lead)
        if status == "hat":
            lead["pruefung"], lead["website"] = "hat Website", domain
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
        time.sleep(1.8)
    job["phase"] = f"Verifizierung fertig: {keine} bestätigt ohne Website"
    job["status"] = "done"


# ───────────────────────── Such-Endpunkte ─────────────────────────

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
    job["status"], job["type"], job["current"] = "running", "verify", 0
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
                "current": job["current"], "total": job["total"], "stats": job["stats"],
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
    buf.write("﻿")
    w = csv.writer(buf)
    w.writerow(["Name", "Kategorie", "Adresse", "Telefon", "E-Mail", "Social", "OSM-Link", "Prüfung", "Website"])
    for d in leads:
        w.writerow([d["name"], d["kategorie"], d["adresse"], d["telefon"], d["email"],
                    d["social"], d["osm"], d.get("pruefung", ""), d.get("website", "")])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="leads_{job["id"]}.csv"'},
    )


# ───────────────────────── Auth-Endpunkte ─────────────────────────

@app.post("/api/auth/register", response_model=AuthResponse)
def register(body: AuthRequest, session: Session = Depends(get_session)):
    email = body.email.strip().lower()
    if "@" not in email or len(body.password) < 6:
        raise HTTPException(400, "Gültige E-Mail und Passwort (min. 6 Zeichen) nötig")
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(409, "E-Mail ist bereits registriert")
    user = User(email=email, hashed_password=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return AuthResponse(token=create_token(user.id), email=user.email)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: AuthRequest, session: Session = Depends(get_session)):
    email = body.email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "E-Mail oder Passwort falsch")
    return AuthResponse(token=create_token(user.id), email=user.email)


@app.get("/api/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"email": user.email, "id": user.id}


# ───────────────────────── Gespeicherte Suchen ─────────────────────────

def _to_out(s: SavedSearch) -> SavedSearchOut:
    return SavedSearchOut(
        id=s.id, label=s.label, stadt=s.stadt, level=s.level,
        kategorien=json.loads(s.kategorien) if s.kategorien else None,
        nur_mit_telefon=s.nur_mit_telefon, count=s.count,
    )


@app.get("/api/searches", response_model=list[SavedSearchOut])
def list_searches(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    rows = session.exec(
        select(SavedSearch).where(SavedSearch.user_id == user.id).order_by(SavedSearch.created_at.desc())
    ).all()
    return [_to_out(s) for s in rows]


@app.post("/api/searches", response_model=SavedSearchOut)
def create_search(body: SavedSearchIn, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # gleiches Label desselben Nutzers ersetzen (wie ein Verlauf)
    for old in session.exec(
        select(SavedSearch).where(SavedSearch.user_id == user.id, SavedSearch.label == body.label)
    ).all():
        session.delete(old)
    s = SavedSearch(
        user_id=user.id, label=body.label, stadt=body.stadt, level=body.level,
        kategorien=json.dumps(body.kategorien) if body.kategorien else None,
        nur_mit_telefon=body.nur_mit_telefon, count=body.count,
    )
    session.add(s)
    session.commit()
    session.refresh(s)
    return _to_out(s)


@app.delete("/api/searches/{search_id}")
def delete_search(search_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    s = session.get(SavedSearch, search_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Suche nicht gefunden")
    session.delete(s)
    session.commit()
    return {"ok": True}
