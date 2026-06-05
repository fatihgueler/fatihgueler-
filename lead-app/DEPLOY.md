# 🚀 Deployment

Ziel: Die App von überall (auch Handy) nutzbar machen.

Du hast zwei Möglichkeiten fürs Frontend:
- **Variante A (empfohlen, alles bei Railway):** Backend **und** Frontend laufen
  als zwei Services in einem Railway-Projekt.
- **Variante B:** Frontend bei **Vercel**, Backend bei Railway.

> Alle Configs liegen schon im Repo: `backend/Dockerfile`, `frontend/Dockerfile`,
> Postgres- & CORS-Env. Du musst nur die Accounts verbinden und Werte setzen.

---

## Schritt 1 — Backend (Railway)

1. Auf **railway.app** mit GitHub einloggen.
2. **New Project → Deploy from GitHub repo** → dieses Repo wählen.
3. **Settings → Root Directory** = `lead-app/backend` (Railway baut das `Dockerfile`).
4. **New → Database → PostgreSQL** hinzufügen → `DATABASE_URL` wird automatisch gesetzt.
   *(Ohne Postgres: SQLite, wird bei jedem Redeploy zurückgesetzt → für echte Konten Postgres nehmen.)*
5. **Variables:** `JWT_SECRET` = langer Zufallswert (z. B. `openssl rand -hex 32`).
6. **Settings → Networking → Generate Domain** → URL merken, z. B.
   `https://leadfinder-backend.up.railway.app`. Test: `…/api/health` → `{"status":"ok"}`.

---

## Schritt 2 — Frontend (Variante A: auch auf Railway)

1. Im **gleichen Railway-Projekt**: **New → GitHub Repo** (dasselbe Repo) →
   ein zweiter Service entsteht.
2. **Settings → Root Directory** = `lead-app/frontend` (Railway baut das `frontend/Dockerfile`).
3. **Variables:** `NEXT_PUBLIC_API_URL` = die **Backend-URL aus Schritt 1**
   (ohne `/` am Ende).
   ⚠️ Wird beim Build eingebacken — also **vor** dem ersten Deploy setzen
   (oder danach einmal „Redeploy" klicken).
4. **Settings → Networking → Generate Domain** → das ist deine App-URL,
   z. B. `https://leadfinder.up.railway.app`.

---

## Schritt 3 — Verbinden & absichern

1. Zurück zum **Backend-Service → Variables**: `CORS_ORIGINS` = deine Frontend-URL
   (z. B. `https://leadfinder.up.railway.app`) → Backend deployt automatisch neu.
2. Fertig! 🎉 App unter der Frontend-URL — Login, Suche, Karte, Export, von überall.

---

## Variante B — Frontend stattdessen auf Vercel

1. **vercel.com** → GitHub → **Import** dieses Repo.
2. **Root Directory** = `lead-app/frontend` (Next.js wird erkannt).
3. **Environment Variable:** `NEXT_PUBLIC_API_URL` = Backend-URL (aus Schritt 1).
4. **Deploy** → URL z. B. `https://lead-finder.vercel.app`.
5. Im Backend (Railway) `CORS_ORIGINS` = die Vercel-URL setzen.

---

## Updates ausrollen

Beide Dienste sind mit GitHub verbunden: Ein `git push` auf den Branch löst
automatisch neue Deployments aus.

> Wichtig: Ändert sich die Backend-URL, muss das **Frontend neu gebaut** werden
> (`NEXT_PUBLIC_API_URL` wird beim Build eingebacken) → in Railway/Vercel
> einmal „Redeploy".

## Hinweise & Kosten

- **Railway Free Tier:** begrenzte Stunden/Monat; Services können bei Inaktivität pausieren.
- **Postgres ist Pflicht für dauerhafte Konten** (SQLite im Container ist flüchtig).
- **`JWT_SECRET` geheim halten**; lokales `.env.local` & `*.db` sind via `.gitignore` ausgeschlossen.

## Alles selbst hosten (Docker)

Beide Teile haben ein `Dockerfile`:

```bash
# Backend
cd lead-app/backend
docker build -t leadfinder-backend .
docker run -p 8000:8000 -e JWT_SECRET=$(openssl rand -hex 32) leadfinder-backend

# Frontend (API-URL beim Build mitgeben)
cd ../frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 -t leadfinder-frontend .
docker run -p 3000:3000 leadfinder-frontend
```
