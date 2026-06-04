#!/usr/bin/env python3
"""
lead_verify.py — Fehltreffer aus einer Lead-Liste herausfiltern

Problem: „Kein website-Tag in OpenStreetMap" heißt nicht zu 100 %, dass der
Betrieb wirklich keine Website hat – OSM ist manchmal nur unvollständig.

Dieses Tool prüft jeden Lead per Websuche (DuckDuckGo) nach und sortiert
Betriebe aus, die in Wahrheit doch eine eigene Website haben:

  1. Liest die von lead_finder.py erzeugte CSV ein
  2. Sucht pro Lead im Web nach "<Name> <Ort>"
  3. Klassifiziert die Treffer-Domains:
       - Verzeichnis/Portal/Social (dasoertliche, facebook, lieferando …) → ignorieren
       - echte eigene Domain (Name taucht in der Domain auf)             → Website!
  4. Schreibt zwei Dateien:
       - leads_..._verifiziert.csv   → bestätigt OHNE Website (deine Leads)
       - leads_..._mit_website.csv   → aussortiert (hatten doch eine Website)

Läuft komplett KOSTENLOS (DuckDuckGo, kein Key). Claude ist optional.

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

EINGABE_CSV = "leads_hannover.csv"   # oder als Argument:  python lead_verify.py meine.csv
LIMIT = 25                            # wie viele Leads prüfen? 0 = alle
PAUSE_SEK = (1.5, 3.0)                # höfliche Zufallspause zwischen Suchen
STADT_FALLBACK = "Hannover"           # falls in der Adresse kein Ort steht

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
    """Kleinbuchstaben, Umlaute ersetzen, Akzente entfernen."""
    s = s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def name_tokens(name):
    """Aussagekräftige Wörter aus dem Betriebsnamen (≥4 Zeichen, ohne Füllwörter)."""
    toks = re.split(r"[^a-z0-9]+", normalisieren(name))
    return {t for t in toks if len(t) >= 4 and t not in NAME_STOPWORDS}


def domain_kern_tokens(host):
    """Wörter aus dem Domain-Kern (z. B. 'friseur-mueller.de' → {friseur, mueller})."""
    teile = host.split(".")
    kern = teile[-2] if len(teile) >= 2 else teile[0]
    toks = re.split(r"[^a-z0-9]+", normalisieren(kern))
    return {t for t in toks if len(t) >= 4}


def ist_verzeichnis(host):
    return any(marker in host for marker in VERZEICHNIS_MARKER)


def ort_aus_adresse(adresse):
    """Holt den Ort aus 'Straße 1, 30419 Hannover' → 'Hannover'."""
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
    """Sucht bei DuckDuckGo und gibt die Treffer-Hostnamen zurück (oder None bei Fehler)."""
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
    """Bewertet einen Lead: ('keine_website'|'hat_website'|'ungeprueft', domain)."""
    ort = ort_aus_adresse(lead.get("Adresse", ""))
    domains = suche_domains(f"{lead['Name']} {ort}")

    if domains is None:
        return ("ungeprueft", "")  # Suche fehlgeschlagen → Lead behalten

    nt = name_tokens(lead["Name"])
    for host in domains:
        if ist_verzeichnis(host):
            continue
        # Echte eigene Website? → Name taucht im Domain-Kern auf
        if nt & domain_kern_tokens(host):
            return ("hat_website", host)

    return ("keine_website", "")


# ─────────────────────────────────────────────────────────────────────────
#  Hauptablauf
# ─────────────────────────────────────────────────────────────────────────

def main():
    eingabe = sys.argv[1] if len(sys.argv) > 1 else EINGABE_CSV
    pfad = Path(__file__).resolve().parent.parent / eingabe
    if not pfad.exists():
        print(f"❌ Eingabedatei nicht gefunden: {pfad}")
        print("   Erst lead_finder.py laufen lassen oder CSV als Argument angeben.")
        return

    with open(pfad, encoding="utf-8-sig", newline="") as f:
        leads = list(csv.DictReader(f))

    if not leads:
        print("⚠️  Die CSV enthält keine Leads.")
        return

    gesamt = len(leads)
    zu_pruefen = leads if LIMIT in (0, None) else leads[:LIMIT]

    print("=" * 60)
    print("  LEAD-VERIFIZIERUNG — Fehltreffer aussortieren")
    print("=" * 60)
    print(f"\nDatei: {eingabe}  ({gesamt} Leads, prüfe {len(zu_pruefen)})")
    print("Quelle: DuckDuckGo (kostenlos). Bitte etwas Geduld …\n")

    behalten, aussortiert, ungeprueft = [], [], 0

    for i, lead in enumerate(zu_pruefen, start=1):
        status, domain = pruefe_lead(lead)

        if status == "hat_website":
            lead["Prüfung"] = f"hat Website: {domain}"
            aussortiert.append(lead)
            symbol = f"✗ hat Website ({domain})"
        elif status == "ungeprueft":
            lead["Prüfung"] = "ungeprüft (Suche fehlgeschlagen)"
            behalten.append(lead)
            ungeprueft += 1
            symbol = "? ungeprüft"
        else:
            lead["Prüfung"] = "keine eigene Website gefunden"
            behalten.append(lead)
            symbol = "✓ keine Website"

        print(f"  [{i:3}/{len(zu_pruefen)}] {lead['Name'][:34]:34} → {symbol}")

        if i < len(zu_pruefen):
            time.sleep(random.uniform(*PAUSE_SEK))  # höflich bleiben

    # Ergebnisse speichern -----------------------------------------------
    basis = eingabe.rsplit(".", 1)[0]
    spalten = ["Name", "Kategorie", "Adresse", "Telefon", "E-Mail", "Social", "OSM-Link", "Prüfung"]

    def schreibe(name, rows):
        ziel = Path(__file__).resolve().parent.parent / name
        with open(ziel, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        return ziel

    ziel_ok = schreibe(f"{basis}_verifiziert.csv", behalten)
    if aussortiert:
        schreibe(f"{basis}_mit_website.csv", aussortiert)

    # Zusammenfassung -----------------------------------------------------
    print("\n" + "-" * 60)
    print(f"  Geprüft:     {len(zu_pruefen)}")
    print(f"  ✓ Behalten:  {len(behalten)}  (ohne Website – davon {ungeprueft} ungeprüft)")
    print(f"  ✗ Aussortiert: {len(aussortiert)}  (hatten doch eine Website)")
    print("-" * 60)
    print(f"\n💾 Bereinigte Lead-Liste: {ziel_ok}")
    if aussortiert:
        print(f"💾 Aussortierte (zur Kontrolle): {basis}_mit_website.csv")


if __name__ == "__main__":
    main()
