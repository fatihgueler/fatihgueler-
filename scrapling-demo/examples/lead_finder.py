#!/usr/bin/env python3
"""
lead_finder.py — Lead-Finder: Betriebe OHNE Website finden (kostenlos)

Findet z. B. alle Gastronomen / KMUs in einer Stadt, die KEINE eigene
Website haben – inkl. Telefon und (falls vorhanden) E-Mail. Ideal, um als
Webentwickler genau die Betriebe zu finden, die eine Website gebrauchen
könnten.

So funktioniert's:
  1. Abfrage bei OpenStreetMap über die kostenlose Overpass-API
     → offene Daten (ODbL), KEIN API-Key nötig, KEINE Kosten
  2. Filter: nur Betriebe ohne `website`-Tag, die telefonisch erreichbar sind
  3. Ergebnis als CSV speichern (öffnet sich direkt in Excel)
  4. OPTIONAL: Wenn ein ANTHROPIC_API_KEY in der .env liegt, lässt sich die
     Liste von Claude priorisieren. Ohne Key wird dieser Schritt einfach
     übersprungen – das Tool funktioniert vollständig kostenlos.

⚖️  Bitte vor dem Kontaktieren die rechtlichen Hinweise in der README lesen
    (DSGVO + UWG §7: Telefon-Kaltakquise im B2B nur bei mutmaßlichem
    Interesse, Kalt-E-Mails grundsätzlich nur mit Einwilligung).
"""

import csv
import sys
import time
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
#  EINSTELLUNGEN  – hier anpassen
# ─────────────────────────────────────────────────────────────────────────

STADT = "Hannover"          # Name der Stadt/Gemeinde laut OpenStreetMap
ADMIN_LEVEL = "8"           # 8 = Stadt/Gemeinde, 6 = Landkreis/Region (größer)

# Welche Betriebsarten suchen? (OSM-"amenity"/"shop"-Werte → Anzeigename)
# Weitere Ideen: friseur, baeckerei, kfz → siehe KATEGORIEN_IDEEN unten.
KATEGORIEN = {
    "amenity=restaurant": "Restaurant",
    "amenity=cafe": "Café",
    "amenity=bar": "Bar",
    "amenity=pub": "Kneipe/Pub",
    "amenity=fast_food": "Imbiss/Fast Food",
}

# Nur Leads behalten, die wenigstens eine Telefonnummer haben?
# (Betriebe ohne Website UND ohne Telefon kann man ohnehin nicht erreichen.)
NUR_MIT_TELEFON = True

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Beispiele für weitere Kategorien (zum Reinkopieren in KATEGORIEN):
KATEGORIEN_IDEEN = {
    "shop=hairdresser": "Friseur",
    "shop=bakery": "Bäckerei",
    "shop=butcher": "Metzgerei",
    "shop=florist": "Blumenladen",
    "craft=carpenter": "Tischlerei",
    "amenity=pharmacy": "Apotheke",
}


# ─────────────────────────────────────────────────────────────────────────
#  Overpass-Abfrage (kostenlos, ohne Key)
# ─────────────────────────────────────────────────────────────────────────

def baue_query():
    """Baut EINE Overpass-Abfrage für alle Kategorien ohne website-Tag."""
    zeilen = []
    for schluessel in KATEGORIEN:
        key, _, value = schluessel.partition("=")
        # Nur Einträge OHNE website und OHNE contact:website
        # (Overpass-Negation: [!"key"] bedeutet "Tag fehlt")
        zeilen.append(
            f'  nwr["{key}"="{value}"][!"website"][!"contact:website"](area.a);'
        )
    union = "\n".join(zeilen)
    return (
        "[out:json][timeout:90];\n"
        f'area["name"="{STADT}"]["admin_level"="{ADMIN_LEVEL}"]'
        '["boundary"="administrative"]->.a;\n'
        f"(\n{union}\n);\n"
        "out center tags;"
    )


def hole_daten(query, versuche=4):
    """Ruft die Overpass-API auf – mit höflichem Backoff bei Rate-Limit (429)."""
    url = OVERPASS_URL + "?data=" + quote(query)
    wartezeit = 3
    for versuch in range(1, versuche + 1):
        try:
            antwort = Fetcher.get(url, stealthy_headers=True)
        except Exception as e:
            print(f"   ⚠️  Netzwerkfehler (Versuch {versuch}/{versuche}): {e}")
            antwort = None

        if antwort is not None and antwort.status == 200:
            try:
                return antwort.json().get("elements", [])
            except Exception:
                print("   ⚠️  Antwort war kein gültiges JSON – wahrscheinlich Auslastung.")
        elif antwort is not None and antwort.status == 429:
            print(f"   ⏳ Overpass ist überlastet (429). Warte {wartezeit}s …")

        if versuch < versuche:
            time.sleep(wartezeit)
            wartezeit *= 2  # 3 → 6 → 12 …

    raise RuntimeError("Overpass-API war nach mehreren Versuchen nicht erreichbar.")


# ─────────────────────────────────────────────────────────────────────────
#  Datensätze aufbereiten
# ─────────────────────────────────────────────────────────────────────────

def baue_adresse(t):
    """Setzt die Adresse aus den einzelnen OSM-Tags zusammen."""
    strasse = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    ort = " ".join(x for x in (t.get("addr:postcode"), t.get("addr:city")) if x)
    return ", ".join(x for x in (strasse, ort) if x)


def kategorie_name(t):
    """Ermittelt den Anzeigenamen der Kategorie aus den Tags."""
    for schluessel, anzeige in KATEGORIEN.items():
        key, _, value = schluessel.partition("=")
        if t.get(key) == value:
            return anzeige
    return "Sonstiges"


def verarbeite(elemente):
    """Wandelt die rohen OSM-Elemente in saubere Lead-Datensätze um."""
    leads = []
    gesehen = set()

    for e in elemente:
        t = e.get("tags", {})
        name = t.get("name")
        if not name:
            continue  # ohne Namen ist der Lead wertlos

        telefon = t.get("phone") or t.get("contact:phone") or t.get("contact:mobile") or ""
        email = t.get("email") or t.get("contact:email") or ""

        if NUR_MIT_TELEFON and not telefon:
            continue

        # Doppelte vermeiden (gleicher Name + gleiche Nummer)
        kennung = (name.lower(), telefon)
        if kennung in gesehen:
            continue
        gesehen.add(kennung)

        social = t.get("contact:facebook") or t.get("contact:instagram") or ""

        leads.append({
            "Name": name,
            "Kategorie": kategorie_name(t),
            "Adresse": baue_adresse(t),
            "Telefon": telefon,
            "E-Mail": email,
            "Social": social,
            "OSM-Link": f"https://www.openstreetmap.org/{e.get('type')}/{e.get('id')}",
        })

    # Alphabetisch nach Name sortieren
    leads.sort(key=lambda d: d["Name"].lower())
    return leads


def speichere_csv(leads, pfad):
    """Schreibt die Leads in eine CSV (utf-8-sig → Umlaute korrekt in Excel)."""
    spalten = ["Name", "Kategorie", "Adresse", "Telefon", "E-Mail", "Social", "OSM-Link"]
    with open(pfad, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=spalten)
        writer.writeheader()
        writer.writerows(leads)


# ─────────────────────────────────────────────────────────────────────────
#  OPTIONAL: Claude-Priorisierung (nur wenn ein API-Key vorhanden ist)
# ─────────────────────────────────────────────────────────────────────────

# Modell für den optionalen Schritt. Günstig & aktuell: claude-sonnet-4-6.
# Für höhere Qualität ginge auch "claude-opus-4-8".
CLAUDE_MODEL = "claude-sonnet-4-6"


def claude_api_key():
    """Liest den API-Key aus der .env – gibt None zurück, wenn keiner gesetzt ist."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return None  # ohne python-dotenv einfach den Claude-Schritt überspringen

    import os
    env_pfad = Path(__file__).resolve().parent.parent / ".env"
    if not env_pfad.exists():
        return None
    load_dotenv(env_pfad)
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key or key.strip() in ("", "dein_api_key_hier_eintragen"):
        return None
    return key


def priorisiere_mit_claude(api_key, leads, anzahl=25):
    """Lässt Claude die Top-Leads priorisieren (ein einziger API-Aufruf)."""
    import anthropic

    auszug = leads[:anzahl]
    liste = "\n".join(
        f"- {d['Name']} ({d['Kategorie']}, {d['Adresse'] or 'keine Adresse'}), Tel: {d['Telefon']}"
        for d in auszug
    )
    prompt = (
        "Du hilfst einem Freelance-Webentwickler bei der Lead-Auswahl. "
        "Hier sind Betriebe OHNE eigene Website. Wähle die 5 aussichtsreichsten "
        "Leads aus und begründe jeweils in einem Satz, warum sich eine Website "
        "besonders lohnen würde. Schlage außerdem einen kurzen, höflichen, "
        "DSGVO/UWG-konformen Gesprächseinstieg fürs Telefon vor. "
        "Antworte auf Deutsch.\n\n"
        f"{liste}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    antwort = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return next((b.text for b in antwort.content if b.type == "text"), "")


# ─────────────────────────────────────────────────────────────────────────
#  Hauptablauf
# ─────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 56)
    print(f"  LEAD-FINDER — Betriebe ohne Website in {STADT}")
    print("=" * 56)
    print(f"\nKategorien: {', '.join(KATEGORIEN.values())}")
    print("Quelle: OpenStreetMap / Overpass-API (kostenlos, ohne Key)\n")

    # 1. Daten holen ------------------------------------------------------
    print("🔎 Frage OpenStreetMap ab … (eine Abfrage, bitte kurz Geduld)")
    try:
        elemente = hole_daten(baue_query())
    except Exception as e:
        print(f"❌ {e}")
        return

    # 2. Aufbereiten ------------------------------------------------------
    leads = verarbeite(elemente)

    if not leads:
        print("\n⚠️  Keine passenden Leads gefunden.")
        print("    Tipp: STADT/ADMIN_LEVEL prüfen oder andere KATEGORIEN wählen.")
        return

    mit_mail = sum(1 for d in leads if d["E-Mail"])
    print(f"\n✅ {len(leads)} Betriebe OHNE Website gefunden "
          f"(alle mit Telefon, {mit_mail} davon mit E-Mail).\n")

    # Vorschau
    print("   Vorschau (erste 10):")
    for d in leads[:10]:
        print(f"   • {d['Name']:32.32} | {d['Telefon']:18.18} | {d['Kategorie']}")

    # 3. CSV speichern ----------------------------------------------------
    dateiname = f"leads_{STADT.lower().replace(' ', '_')}.csv"
    pfad = Path(__file__).resolve().parent.parent / dateiname
    speichere_csv(leads, pfad)
    print(f"\n💾 Gespeichert als: {pfad}")

    # 4. OPTIONAL: Claude-Priorisierung ----------------------------------
    api_key = claude_api_key()
    if not api_key:
        print("\nℹ️  Optionaler Claude-Schritt übersprungen (kein API-Key gesetzt).")
        print("    Das Tool ist damit fertig – komplett kostenlos. 🎉")
        print("    Für eine KI-Priorisierung: API-Key in .env eintragen.")
        return

    print("\n🤖 Claude priorisiert die Top-Leads … (ein API-Aufruf)\n")
    try:
        analyse = priorisiere_mit_claude(api_key, leads)
    except ImportError:
        print("❌ Paket 'anthropic' nicht installiert (pip install anthropic).")
        return
    except Exception as e:
        print(f"❌ Fehler bei der Claude-Anfrage: {e}")
        return

    print("-" * 56)
    print("  CLAUDES TOP-LEAD-EMPFEHLUNGEN")
    print("-" * 56 + "\n")
    print(analyse.strip() if analyse else "(Keine Textantwort erhalten.)")


if __name__ == "__main__":
    main()
