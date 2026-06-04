# 🕷️ Scrapling + Claude AI — Demo

Eine kleine, lauffähige Entwicklungsumgebung, die **Web-Scraping mit
[Scrapling](https://github.com/D4Vinci/Scrapling)** und die **Claude API von
Anthropic** kombiniert. Du scrapst echte Webseiten und lässt Claude die
Ergebnisse direkt analysieren.

---

## 📋 Voraussetzungen

- **Python 3.9 oder neuer** (`python --version` bzw. `python3 --version`)
- **pip** (`pip --version`)
- Einen **Anthropic API-Key** für den Claude-Teil
  → kostenlos erstellbar unter <https://console.anthropic.com/settings/keys>

> Schritt 1 und 2 der Demo laufen **ohne** API-Key. Nur die Claude-Analyse
> (Schritt 3) braucht einen gültigen Schlüssel.

---

## ⚙️ Installation in 3 Schritten

```bash
# 1) Virtuelle Umgebung erstellen und aktivieren
python -m venv venv
source venv/bin/activate        # Windows:  venv\Scripts\activate

# 2) Abhängigkeiten installieren
pip install -r requirements.txt

# 3) Browser-Dependencies für den StealthyFetcher installieren
scrapling install
```

> **Hinweis (Schritt 3):** `scrapling install` lädt einen Headless-Browser
> herunter und wird nur für `stealth_fetch.py` benötigt. `basic_fetch.py` und
> `claude_analyze.py` funktionieren auch ohne diesen Schritt.

Falls `pip` unter Linux meckert (`externally-managed-environment`), nutze die
aktivierte venv (siehe Schritt 1) oder notfalls:
`pip install -r requirements.txt --break-system-packages`.

---

## 🔑 API-Key eintragen

Der Schlüssel wird aus der Datei **`.env`** im Projektordner geladen.

1. Falls noch keine `.env` existiert, lege sie aus der Vorlage an:

   ```bash
   cp .env.example .env        # Windows:  copy .env.example .env
   ```

2. Öffne die Datei `.env` (sie liegt direkt neben dieser README).
3. Ersetze den Platzhalter durch deinen echten Key:

   ```env
   ANTHROPIC_API_KEY=sk-ant-dein-echter-key
   ```

4. Speichern – fertig. Der Key wird **nicht** ins Git eingecheckt
   (die `.env` ist in `.gitignore` ausgenommen).

> 🔒 Teile deinen API-Key mit niemandem und committe ihn nicht in ein
> öffentliches Repository.

---

## ▶️ Demo ausführen

```bash
python scraper.py
```

Das Hauptskript führt nacheinander alle drei Beispiele aus:

```
========================================
  SCRAPLING + CLAUDE AI — DEMO
========================================

[1/3] Basic Fetch    → books.toscrape.com
[2/3] Stealth Fetch  → CSS-Selektor-Test
[3/3] Claude-Analyse → Hacker-News-Trends
```

Die Beispiele lassen sich auch einzeln starten:

```bash
python examples/basic_fetch.py      # Standard-HTTP-Scraping
python examples/stealth_fetch.py    # Scraping über echten Browser
python examples/claude_analyze.py   # Scrapling + Claude (braucht API-Key)
```

---

## ⭐ Lead-Finder: Betriebe ohne Website finden (kostenlos)

`examples/lead_finder.py` ist das praxisnahe Highlight: Es findet z. B. alle
**Gastronomen oder KMUs in einer Stadt, die noch keine eigene Website haben** –
inklusive **Telefonnummer** und (falls vorhanden) **E-Mail**. Perfekt, um als
Webentwickler genau die Betriebe zu finden, die einen neuen Webauftritt
gebrauchen könnten.

```bash
python examples/lead_finder.py                      # nur Stadt Hannover
python examples/lead_finder.py "Region Hannover" 6  # Hannover und Umgebung
```

Beispiel-Ausgabe (Stadt Hannover, alle KMUs):

```
✅ 482 KMUs OHNE Website gefunden (alle mit Telefon, 43 davon mit E-Mail).
   Verteilung nach Kategorie (Top 12):
       56×  Friseur
       54×  Restaurant
       34×  Imbiss
       23×  Bäckerei
       ...
💾 Gespeichert als: leads_hannover.csv
```

Die Ergebnisse landen in einer **CSV-Datei** (öffnet sich direkt in Excel) mit
den Spalten: Name, Kategorie, Adresse, Telefon, E-Mail, Social, OSM-Link.

### Wie funktioniert das – und warum kostenlos?

- **Datenquelle: OpenStreetMap** über die **Overpass-API** – offene Daten
  (ODbL-Lizenz), **kein API-Key, keine Kosten**. Jeder Eintrag hat strukturierte
  Tags wie `phone`, `email`, `website`. So lässt sich direkt filtern:
  *„alle Restaurants ohne `website`-Tag"*.
- **Claude ist optional:** Ist ein `ANTHROPIC_API_KEY` gesetzt, priorisiert
  Claude die vielversprechendsten Leads und schlägt einen rechtssicheren
  Telefon-Einstieg vor. Ohne Key wird dieser Schritt einfach übersprungen –
  **der Lead-Finder läuft vollständig gratis.**

### Anpassen (oben in der Datei)

```python
STADT = "Hannover"     # Zielstadt; "Hannover und Umgebung" → "Region Hannover" + ADMIN_LEVEL="6"
ADMIN_LEVEL = "8"      # 8 = Stadt/Gemeinde, 6 = Region/Landkreis (größer)

OSM_FILTER = [         # was suchen? Eintrag OHNE "=" = ALLE Werte des Keys
    "shop",            # alle Läden (Bäcker, Friseur, Metzger, Optiker, …)
    "craft",           # alle Handwerksbetriebe (Tischler, Elektriker, Maler, …)
    "amenity=restaurant", "amenity=cafe", "amenity=bar",
    "office=lawyer", "office=tax_advisor", "tourism=hotel",
    # … volle Liste steht oben in der Datei, einfach kürzen/ergänzen
]
```

> 💡 **Realistische Erwartung:** OpenStreetMap hat **Telefonnummern gut** erfasst,
> **E-Mails nur selten** (gerade Betriebe ohne Website hinterlegen kaum eine
> Mail). Für genau diese Betriebe ist das **Telefon der realistische Kanal** –
> was rechtlich ohnehin günstiger ist (siehe unten).

### 🔍 Schritt 2 (optional): Fehltreffer rausfiltern

OSM ist manchmal unvollständig – manche „ohne Website"-Betriebe haben in
Wirklichkeit doch eine. `examples/lead_verify.py` prüft das per Websuche nach:

```bash
python examples/lead_verify.py            # prüft leads_hannover.csv
python examples/lead_verify.py meine.csv  # oder eine andere Liste
```

- Sucht pro Lead bei **DuckDuckGo (kostenlos, kein Key)** und erkennt an den
  Treffer-Domains, ob eine echte eigene Website existiert. Verzeichnisse/Portale
  (dasoertliche, lieferando, facebook …) werden ignoriert.
- Schreibt `leads_..._verifiziert.csv` (bereinigte Leads) und
  `leads_..._mit_website.csv` (aussortierte – zur Kontrolle).
- Menge per `LIMIT` einstellbar (Standard 25 zum Testen; `0` = alle).

> Heuristik, kein Orakel – im Zweifel **bleibt** ein Lead drin. Für große Mengen
> DuckDuckGo nicht überlasten: in Etappen laufen lassen (`LIMIT`) oder für hohe
> Volumina eine Such-API (z. B. Brave Search) nutzen.

### ⚖️ Rechtliches zur Lead-Nutzung (Deutschland)

Das Sammeln öffentlich verfügbarer **Geschäfts**daten zur B2B-Akquise ist
grundsätzlich zulässig (berechtigtes Interesse, Art. 6 Abs. 1 f DSGVO). Beim
**Kontaktieren** gilt aber **UWG § 7**:

- 📞 **Telefon (B2B):** nur bei *mutmaßlichem Interesse* erlaubt. Bei einem
  Webdesign-Angebot an einen Betrieb ohne Website oft vertretbar – aber kein
  Freifahrtschein.
- ✉️ **Kalt-E-Mail / Fax:** grundsätzlich **nur mit vorheriger Einwilligung** –
  Werbe-Mails an Betriebe ohne Einwilligung sind i. d. R. unzulässig (Abmahngefahr).
- 📬 **Brief/Post:** rechtlich am unkritischsten.
- Bei **Einzelunternehmern** sind Telefon/E-Mail personenbezogene Daten →
  sparsam speichern, Widersprüche respektieren.

Im Zweifel anwaltlich beraten lassen. Dieses Tool stellt **keine Rechtsberatung**
dar.

---

## 📂 Projektstruktur

```
scrapling-demo/
├── .env                  # Dein API-Key (Platzhalter, lokal befüllen)
├── .env.example          # Vorlage für die .env
├── requirements.txt      # Python-Abhängigkeiten
├── README.md             # Diese Anleitung
├── scraper.py            # Haupt-Demo (führt alle 3 Beispiele aus)
└── examples/
    ├── basic_fetch.py    # Titel + Preise von books.toscrape.com
    ├── stealth_fetch.py  # StealthyFetcher + einzelner CSS-Selektor
    ├── claude_analyze.py # HN-Titel scrapen → von Claude analysieren lassen
    ├── lead_finder.py    # ⭐ Betriebe OHNE Website finden (Leads, kostenlos)
    └── lead_verify.py    # 🔍 Fehltreffer rausfiltern (Websuche, kostenlos)
```

---

## 🤔 Was ist Scrapling?

**Scrapling** ist eine moderne Python-Bibliothek für Web-Scraping. Sie bündelt
mehrere „Fetcher" unter einer einheitlichen, einfachen API:

- **`Fetcher`** – schnelle HTTP-Requests mit realistischen Browser-Headern
  (kein Browser nötig). Perfekt für statische Seiten.
- **`StealthyFetcher`** – startet im Hintergrund einen echten, getarnten
  Browser, um auch besser geschützte Seiten zu laden.
- **`DynamicFetcher`** – für Seiten, die Inhalte erst per JavaScript nachladen.

Elemente werden bequem über **CSS-Selektoren** ausgelesen, z. B.:

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get("https://books.toscrape.com")
preise = page.css(".price_color")      # Liste passender Elemente
print(preise[0].text)                  # z. B. "£51.77"
```

In dieser Demo liefert Scrapling die Rohdaten (Buchpreise, Hacker-News-Titel),
und die **Claude API** übernimmt anschließend die inhaltliche Analyse.

---

## ⚖️ Disclaimer

Diese Demo dient ausschließlich **Lern- und Demonstrationszwecken**.

Web-Scraping ist nur für **legale und ausdrücklich erlaubte Zwecke** zulässig.
Bitte beachte stets:

- die **Nutzungsbedingungen** (Terms of Service) der jeweiligen Website,
- die Datei **`robots.txt`** der Seite,
- geltendes **Urheber- und Datenschutzrecht** (u. a. DSGVO),
- einen **rücksichtsvollen Umgang** mit fremden Servern (keine Überlastung).

Die hier verwendeten Seiten `books.toscrape.com` und `news.ycombinator.com`
eignen sich gut zum Üben. Verwende die Werkzeuge verantwortungsvoll. Die
Nutzung erfolgt auf eigene Verantwortung.
