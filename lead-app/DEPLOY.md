# 🚀 Deployment — Railway (Backend) + Vercel (Frontend)

Ziel: Die App von überall (auch Handy) nutzbar machen. Frontend → **Vercel**,
Backend (Python/Docker) → **Railway**.

> Alle Configs liegen schon im Repo (`backend/Dockerfile`, Env-Unterstützung).
> Du musst nur die Accounts verbinden und ein paar Werte setzen.

---

## Teil 1 — Backend auf Railway

1. Auf **railway.app** mit GitHub einloggen.
2. **New Project → Deploy from GitHub repo** → dieses Repo wählen.
3. **Settings → Root Directory** auf `lead-app/backend` setzen.
   Railway erkennt das `Dockerfile` und baut es automatisch.
4. **Datenbank (empfohlen):** im Projekt **New → Database → PostgreSQL**.
   Railway legt automatisch die Variable `DATABASE_URL` an und verbindet sie.
   *(Ohne Postgres läuft SQLite — wird aber bei jedem Redeploy zurückgesetzt.)*
5. **Variables** (Settings → Variables) setzen:
   | Variable | Wert |
   |---|---|
   | `JWT_SECRET` | langer Zufallswert, z. B. Ausgabe von `openssl rand -hex 32` |
   | `CORS_ORIGINS` | (erst in Teil 3 setzen — vorerst leer lassen) |
6. **Networking → Generate Domain** → du bekommst eine URL wie
   `https://leadfinder-backend-production.up.railway.app`. **Diese URL merken.**
7. Test im Browser: `https://…railway.app/api/health` → `{"status":"ok"}`.

---

## Teil 2 — Frontend auf Vercel

1. Auf **vercel.com** mit GitHub einloggen.
2. **Add New → Project → Import** dieses Repo.
3. **Root Directory** auf `lead-app/frontend` setzen.
   (Framework „Next.js" wird automatisch erkannt.)
4. **Environment Variables** → hinzufügen:
   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | die Railway-URL aus Teil 1 (**ohne** Slash am Ende) |
5. **Deploy**. Vercel gibt dir eine URL wie `https://lead-finder.vercel.app`.

---

## Teil 3 — Verbinden & absichern

1. Zurück zu **Railway → Variables**: `CORS_ORIGINS` = deine Vercel-URL,
   z. B. `https://lead-finder.vercel.app` → Backend macht automatisch ein Redeploy.
   *(Damit greift nur noch dein eigenes Frontend auf die API zu.)*
2. Fertig! 🎉 App unter deiner Vercel-URL — Login, Suchen, Karte, Export,
   alles von überall.

---

## Updates ausrollen

Beide Dienste sind mit GitHub verbunden: Ein `git push` auf den Branch löst
automatisch ein neues Deployment aus (Backend bei Railway, Frontend bei Vercel).

## Hinweise & Kosten

- **Railway Free Tier:** begrenzte Nutzungsstunden/Monat; das Backend kann bei
  Inaktivität pausieren (erster Request danach ist langsamer).
- **Postgres ist Pflicht für echte Konten** — sonst gehen Nutzer/Suchen bei
  jedem Redeploy verloren (SQLite im Container ist flüchtig).
- **`JWT_SECRET` geheim halten** und nicht ins Repo committen.
- Lokales `.env.local` (Frontend) und SQLite-`*.db` (Backend) sind via
  `.gitignore` ausgeschlossen.

## Alternative: alles selbst hosten (Docker)

Das Backend hat ein fertiges `Dockerfile`. Lokal/Server:

```bash
cd lead-app/backend
docker build -t leadfinder-backend .
docker run -p 8000:8000 -e JWT_SECRET=$(openssl rand -hex 32) leadfinder-backend
```

Das Frontend dann mit `NEXT_PUBLIC_API_URL=http://<server>:8000` bauen
(`npm run build && npm start`).
