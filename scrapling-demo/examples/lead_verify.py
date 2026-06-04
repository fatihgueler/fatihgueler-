#!/usr/bin/env python3
"""
lead_verify.py — Fehltreffer aus einer Lead-Liste herausfiltern (wiederaufsetzbar)

Problem: „Kein website-Tag in OpenStreetMap" heißt nicht zu 100 %, dass der
Betrieb wirklich keine Website hat – OSM ist manchmal nur unvollständig.

Dieses Tool prüft jeden Lead per Websuche (DuckDuckGo, kostenlos) nach und
sortiert Betriebe aus, die in Wahrheit doch eine eigene Website haben.

WICHTIG: Es ist WIEDERAUFSETZBAR. Jeder geprüfte Lead wird in einer
Fortschritts-Datei (…_geprueft.csv) festgehalten. Startest du das Tool erneut,
macht es genau dort weiter, wo es aufgehört hat. So lässt sich auch eine große
Liste (z. B. 1000+ Leads) bequem in Etappen abarbeiten, ohne DuckDuckGo zu
überlasten.

Erzeugte Dateien (Basis = Name der Eingabe-CSV):
  …_geprueft.csv     → ALLE Leads inkl. Prüf-Status (= Fortschritt, dient dem Resume)
  …_verifiziert.csv  → bestätigt OHNE Website (deine bereinigten Leads)
  …_mit_website.csv  → aussortiert (hatten doch eine Website)

Aufruf:
  python lead_verify.py                              # prüft leads_hannover.csv (alle offenen)
  python lead_verify.py leads_region_hannover.csv    # andere Liste
  python lead_verify.py leads_region_hannover.csv 100  # nur die nächsten 100 prüfen

Läuft komplett KOSTENLOS (DuckDuckGo, kein Key).

⚠️  Heuristik, kein Orakel: gelegentliche Fehlentscheidungen sind möglich.
    Im Zweifel wird ein Lead BEHALTEN (lieber prüfen als verlieren).
"""

import csv
import re
import sys
import time
import random
import unicodedata
from pathlib import Path
from urllib.parse import quote

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from scrapling.fetchers import Fetcher
except ImportError:
    print("❌ Scrapling ist nicht installiert.")
    print('   Installiere es mit:  pip install "scrapling[fetchers]"')
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────
#  EINSTELLUNGEN
# ─────────────────────────────────────────────────────────────────────────

EINGABE_CSV = "leads_hannover.csv"   # oder als 1. Argument übergeben
# Wie viele OFFENE Leads pro Lauf prüfen?  0 = alle (mit automatischen Pausen)
LIMIT = 0
STADT_FALLBACK = "Hannover"

PAUSE_SEK = (2.0, 4.0)        # Zufallspause zwischen einzelnen Suchen
COOLDOWN_NACH = 40            # nach so vielen Suchen eine längere Pause einlegen
COOLDOWN_SEK = 45            # Dauer dieser regelmäßigen Pause
MAX_FEHLER_AM_STUECK = 5      # so viele Fehler in Folge → DuckDuckGo blockt evtl.
ZWANGSPAUSE_SEK = 120        # dann diese Zwangspause einlegen
SPEICHERN_ALLE = 15          # Fortschritt alle N Leads zwischenspeichern

# Domains, die KEINE eigene Firmenwebsite sind (Verzeichnisse, Portale, Social)
VERZEICHNIS_MARKER = [
    "facebook.", "instagram.", "twitter.", "x.com", "linkedin.", "xing.",
    "yelp.", "tripadvisor.", "lieferando.", "wolt.com", "ubereats", "quandoo.",
    "opentable.", "foursquare.", "pinterest.", "youtube.", "tiktok.", "wer-kennt-den",
    "gelbeseiten.", "dasoertliche.", "das-oertliche", "dastelefonbuch.", "das-telefonbuch",
    "11880", "meinestadt.", "golocal.", "wlw.", "cylex", "firmenwissen", "firmenkataloge",
    "deutschebiz", "auto-werkstatt.de", "oeffnungszeiten", "öffnungszeiten", "bazaaar",
    "kennstdueinen", "google.", "goyellow.", "branchenbuch", "stadtbranchenbuch",
    "werkenntdenbesten", "unternehmensauskunft", "northdata", "companyhouse",
    "yellowmap", "wogibtswas", "wikipedia.", "openstreetmap.", "infobel", "pages24",
    "tupalo", "yalwa", "nochoffen", "werliefertwas", "marktplatz-mittelstand",
    "hotfrog", "speisekarte.", "restaurant-kritik", "treatwell", "venuu",
    "telefonbuch", "kaufda", "firmeneintrag", "adressen.", "stadtportal",
]

# Prüf-Status → Text in der CSV
TEXT_KEINE = "keine eigene Website gefunden"
TEXT_OFFEN = "ungeprüft (Suche fehlgeschlagen)"


# ─────────────────────────────────────────────────────────────────────────
#  Text-Normalisierung & Namensabgleich
# ─────────────────────────────────────────────────────────────────────────

NAME_STOPWORDS = {
    "gmbh", "kg", "ohg", "co", "mbh", "inh", "und", "der", "die", "das",
    "restaurant", "cafe", "bar", "hotel", "pension", "imbiss", "friseur",
    "salon", "kosmetik", "hannover", "gbr", "haus", "stube", "berlin",
    "pizzeria", "trattoria", "bistro", "kiosk", "apotheke", "baeckerei",
}


def normalisieren(s):
    s = s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def name_tokens(name):
    toks = re.split(r"[^a-z0-9]+", normalisieren(name))
    return {t for t in toks if len(t) >= 4 and t not in NAME_STOPWORDS}


def domain_kern_tokens(host):
    teile = host.split(".")
    kern = teile[-2] if len(teile) >= 2 else teile[0]
    toks = re.split(r"[^a-z0-9]+", normalisieren(kern))
    return {t for t in toks if len(t) >= 4}


def ist_verzeichnis(host):
    return any(marker in host for marker in VERZEICHNIS_MARKER)


def ort_aus_adresse(adresse):
    if adresse and "," in adresse:
        tail = adresse.split(",")[-1].strip()
        ort = " ".join(t for t in tail.split() if not t.isdigit())
        if ort:
            return ort
    return STADT_FALLBACK


# ─────────────────────────────────────────────────────────────────────────
#  Websuche (DuckDuckGo HTML, kostenlos)
# ─────────────────────────────────────────────────────────────────────────

def suche_domains(query, max_treffer=8):
    """Sucht bei DuckDuckGo; gibt Treffer-Hostnamen zurück (oder None bei Fehler)."""
    url = "https://html.duckduckgo.com/html/?q=" + quote(query)
    try:
        r = Fetcher.get(url, timeout=25, retries=1, stealthy_headers=True)
    except Exception:
        return None
    if r.status != 200:
        return None

    hosts = []
    for u in r.css(".result__url")[:max_treffer]:
        txt = (u.text or "").strip()
        if not txt:
            continue
        host = txt.split("/")[0].strip().lower()
        if host.startswith("www."):
            host = host[4:]
        if host:
            hosts.append(host)
    return hosts


def pruefe_lead(lead):
    """Bewertet einen Lead → (status, domain). status: keine|hat|offen."""
    ort = ort_aus_adresse(lead.get("Adresse", ""))
    domains = suche_domains(f"{lead['Name']} {ort}")

    if domains is None:
        return ("offen", "")  # Suche fehlgeschlagen → später erneut versuchen

    nt = name_tokens(lead["Name"])
    for host in domains:
        if ist_verzeichnis(host):
            continue
        if nt & domain_kern_tokens(host):  # Name taucht in der Domain auf
            return ("hat", host)
    return ("keine", "")


# ─────────────────────────────────────────────────────────────────────────
#  Fortschritt laden / speichern (Resume)
# ─────────────────────────────────────────────────────────────────────────

SPALTEN = ["Name", "Kategorie", "Adresse", "Telefon", "E-Mail", "Social", "OSM-Link", "Prüfung"]


def lade_ledger(pfad):
    """Lädt bisherigen Fortschritt: OSM-Link → Prüf-Text."""
    if not pfad.exists():
        return {}
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        return {r["OSM-Link"]: r.get("Prüfung", "") for r in csv.DictReader(f)}


def ist_erledigt(pruef_text):
    """Erledigt = entschieden (keine Website / hat Website). 'ungeprüft' bleibt offen."""
    return bool(pruef_text) and not pruef_text.startswith("ungeprüft")


def schreibe(pfad, rows):
    with open(pfad, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def speichere_alle(basis_pfad, alle_leads, status):
    """Schreibt Ledger + verifizierte + aussortierte Liste."""
    for lead in alle_leads:
        lead["Prüfung"] = status.get(lead["OSM-Link"], "")

    schreibe(basis_pfad.with_name(basis_pfad.stem + "_geprueft.csv"), alle_leads)
    schreibe(basis_pfad.with_name(basis_pfad.stem + "_verifiziert.csv"),
             [l for l in alle_leads if status.get(l["OSM-Link"]) == TEXT_KEINE])
    aussortiert = [l for l in alle_leads if (status.get(l["OSM-Link"]) or "").startswith("hat Website")]
    if aussortiert:
        schreibe(basis_pfad.with_name(basis_pfad.stem + "_mit_website.csv"), aussortiert)


# ─────────────────────────────────────────────────────────────────────────
#  Hauptablauf
# ─────────────────────────────────────────────────────────────────────────

def main():
    eingabe = sys.argv[1] if len(sys.argv) > 1 else EINGABE_CSV
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else LIMIT

    basis_pfad = Path(__file__).resolve().parent.parent / eingabe
    if not basis_pfad.exists():
        print(f"❌ Eingabedatei nicht gefunden: {basis_pfad}")
        print("   Erst lead_finder.py laufen lassen oder CSV als Argument angeben.")
        return

    with open(basis_pfad, encoding="utf-8-sig", newline="") as f:
        alle_leads = list(csv.DictReader(f))
    if not alle_leads:
        print("⚠️  Die CSV enthält keine Leads.")
        return

    # Bisherigen Fortschritt laden (Resume)
    ledger_pfad = basis_pfad.with_name(basis_pfad.stem + "_geprueft.csv")
    status = lade_ledger(ledger_pfad)

    offen = [l for l in alle_leads if not ist_erledigt(status.get(l["OSM-Link"], ""))]
    erledigt_vorher = len(alle_leads) - len(offen)

    if limit and limit > 0:
        offen = offen[:limit]

    print("=" * 60)
    print("  LEAD-VERIFIZIERUNG — Fehltreffer aussortieren")
    print("=" * 60)
    print(f"\nDatei: {eingabe}  ({len(alle_leads)} Leads gesamt)")
    print(f"Bereits erledigt: {erledigt_vorher}  |  Jetzt zu prüfen: {len(offen)}")
    if not offen:
        print("\n✅ Nichts mehr offen – alle Leads sind bereits geprüft.")
        speichere_alle(basis_pfad, alle_leads, status)
        return
    print("Quelle: DuckDuckGo (kostenlos). Mit Cool-down-Pausen, bitte Geduld …\n")

    fehler_serie = 0
    seit_speichern = 0

    for i, lead in enumerate(offen, start=1):
        s, domain = pruefe_lead(lead)

        if s == "hat":
            status[lead["OSM-Link"]] = f"hat Website: {domain}"
            symbol = f"✗ hat Website ({domain})"
            fehler_serie = 0
        elif s == "keine":
            status[lead["OSM-Link"]] = TEXT_KEINE
            symbol = "✓ keine Website"
            fehler_serie = 0
        else:  # offen / Fehler
            status[lead["OSM-Link"]] = TEXT_OFFEN
            symbol = "? ungeprüft (Suche fehlgeschlagen)"
            fehler_serie += 1

        print(f"  [{i:4}/{len(offen)}] {lead['Name'][:32]:32} → {symbol}")

        # Fortschritt regelmäßig sichern (gegen Abbruch)
        seit_speichern += 1
        if seit_speichern >= SPEICHERN_ALLE:
            speichere_alle(basis_pfad, alle_leads, status)
            seit_speichern = 0

        # DuckDuckGo blockt? → längere Zwangspause
        if fehler_serie >= MAX_FEHLER_AM_STUECK:
            print(f"   ⏳ Mehrere Fehler in Folge – {ZWANGSPAUSE_SEK}s Zwangspause (DuckDuckGo schont sich) …")
            speichere_alle(basis_pfad, alle_leads, status)
            time.sleep(ZWANGSPAUSE_SEK)
            fehler_serie = 0

        if i < len(offen):
            # regelmäßiger Cool-down + normale Zufallspause
            if i % COOLDOWN_NACH == 0:
                print(f"   ⏳ Cool-down nach {COOLDOWN_NACH} Suchen ({COOLDOWN_SEK}s) …")
                time.sleep(COOLDOWN_SEK)
            else:
                time.sleep(random.uniform(*PAUSE_SEK))

    # Abschluss
    speichere_alle(basis_pfad, alle_leads, status)

    keine = sum(1 for l in alle_leads if status.get(l["OSM-Link"]) == TEXT_KEINE)
    hat = sum(1 for l in alle_leads if (status.get(l["OSM-Link"]) or "").startswith("hat Website"))
    rest_offen = sum(1 for l in alle_leads if not ist_erledigt(status.get(l["OSM-Link"], "")))

    print("\n" + "-" * 60)
    print(f"  ✓ Bestätigt OHNE Website: {keine}")
    print(f"  ✗ Aussortiert (hatten Website): {hat}")
    print(f"  ? Noch offen (erneut starten zum Fortsetzen): {rest_offen}")
    print("-" * 60)
    print(f"\n💾 Bereinigte Leads: {basis_pfad.stem}_verifiziert.csv")
    print(f"💾 Fortschritt:      {basis_pfad.stem}_geprueft.csv")
    if rest_offen:
        print(f"\nℹ️  Noch {rest_offen} offen. Einfach erneut starten – es macht dort weiter:")
        print(f"    python examples/lead_verify.py {eingabe}")


if __name__ == "__main__":
    main()
