# 🧭 LeadFinder — Web-App

Die **Web-App-Version** des Lead-Finders: KMUs **ohne eigene Website** finden –
mit moderner Oberfläche, **Live-Fortschritt**, **Karte**, Fehltreffer-Prüfung und
**CSV-Export**. Datenquelle: OpenStreetMap (kostenlos, kein API-Key).

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  Frontend (Next.js/React)   │  HTTP  │  Backend (FastAPI / Python)  │
│  Tailwind · Leaflet-Karte   │ ─────▶ │  Scrapling · OSM · DuckDuckGo │
│  Suchmaske · Tabelle · SSE  │ ◀───── │  Jobs · Live-Progress · CSV  │
└─────────────────────────────┘        └──────────────────────────────┘
        Port 3000                               Port 8000
```

---

## ✨ Features

- 🔎 **Suche** nach Stadt **oder** Region, mit Branchen-Presets (Alle KMUs,
  Gastronomie, Einzelhandel, Handwerk, Dienstleister)
- 📡 **Live-Fortschritt** während der Suche (Server-Sent Events)
- 🗺️ **Karte** (Leaflet/OpenStreetMap) mit Pin pro Betrieb
- 📋 **Ergebnis-Tabelle** mit Telefon-Links und Status-Badges
- 🔍 **Fehltreffer prüfen** — markiert Betriebe, die doch eine Website haben
  (grün = ohne Website, rot = hat Website)
- ⬇️ **CSV-Export** (Excel-tauglich), optional nur „ohne Website“

---

## 🚀 Schnellstart

Voraussetzungen: **Python 3.9+** und **Node.js 18+**.

### 1) Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r requirements.txt
scrapling install                  # einmalig: Browser-Dependencies
uvicorn main:app --reload --port 8000
```

→ Backend läuft auf <http://localhost:8000> (API-Doku: <http://localhost:8000/docs>)

### 2) Frontend (Next.js)

In einem zweiten Terminal:

```bash
cd frontend
cp .env.local.example .env.local   # zeigt aufs Backend (localhost:8000)
npm install
npm run dev
```

→ App öffnen: <http://localhost:3000>

---

## 🔌 API-Endpunkte (Backend)

| Methode | Pfad | Zweck |
|---|---|---|
| `POST` | `/api/search` | Lead-Suche starten → `{ job_id }` |
| `GET`  | `/api/jobs/{id}` | Status + Ergebnisse abrufen |
| `GET`  | `/api/jobs/{id}/stream` | Live-Fortschritt (SSE) |
| `POST` | `/api/jobs/{id}/verify` | Fehltreffer-Verifizierung starten |
| `GET`  | `/api/jobs/{id}/export.csv` | Ergebnisse als CSV |

Beispiel:

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"stadt":"Hannover","level":"8","kategorien":null,"nur_mit_telefon":true}'
```

`level`: `8` = einzelne Stadt, `6` = Region/Umland (z. B. Stadt `"Region Hannover"`).

---

## 🧱 Tech-Stack

- **Backend:** FastAPI · Uvicorn · Scrapling (Overpass + DuckDuckGo) · Python
- **Frontend:** Next.js 15 · React 19 · TypeScript · Tailwind CSS · React-Leaflet

Die Kernlogik liegt in `backend/core.py` (dieselbe, die auch die CLI-Skripte in
`../scrapling-demo` nutzen) — die Web-App ist nur eine komfortable Oberfläche darüber.

---

## 🚀 Deployment

Schritt-für-Schritt-Anleitung für **Railway (Backend) + Vercel (Frontend)**:
siehe **[DEPLOY.md](./DEPLOY.md)**. Configs (`backend/Dockerfile`, Postgres- &
CORS-Env) liegen bereits im Repo.

## 🔐 Benutzerkonten

Login/Registrierung (JWT) + gespeicherte Suchen pro Nutzer (SQLite lokal,
PostgreSQL in Produktion). Relevante Env-Variablen:

| Variable | Zweck | Default |
|---|---|---|
| `JWT_SECRET` | Signatur der Login-Tokens | Dev-Wert (in Prod setzen!) |
| `DATABASE_URL` | Datenbank | `sqlite:///./leadfinder.db` |
| `CORS_ORIGINS` | erlaubte Frontend-Domains (kommagetrennt) | `*` |

---

## ⚖️ Rechtlicher Hinweis

Lead-Daten nur für **legale, erlaubte Zwecke** nutzen. Beim Kontaktieren gilt in
Deutschland **UWG §7** (Telefon-Kaltakquise im B2B nur bei mutmaßlichem Interesse,
Kalt-E-Mails grundsätzlich nur mit Einwilligung) und die **DSGVO**. Details siehe
`../scrapling-demo/README.md`. Keine Rechtsberatung.
