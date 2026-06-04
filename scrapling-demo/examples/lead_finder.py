#!/usr/bin/env python3
"""
lead_finder.py — Lead-Finder: KMUs OHNE Website finden (kostenlos)

Findet alle kleinen/mittleren Betriebe (KMUs) in einer Stadt ODER Region,
die KEINE eigene Website haben – inkl. Telefon und (falls vorhanden) E-Mail.
Ideal, um als Webentwickler genau die Betriebe zu finden, die einen neuen
Webauftritt gebrauchen könnten.

So funktioniert's:
  1. Abfrage bei OpenStreetMap über die kostenlose Overpass-API
     → offene Daten (ODbL), KEIN API-Key nötig, KEINE Kosten
  2. Filter: nur Betriebe ohne `website`-Tag, die telefonisch erreichbar sind
  3. Ergebnis als CSV speichern (öffnet sich direkt in Excel)
  4. OPTIONAL: Wenn ein ANTHROPIC_API_KEY in der .env liegt, lässt sich die
     Liste von Claude priorisieren. Ohne Key wird dieser Schritt einfach
     übersprungen – das Tool funktioniert vollständig kostenlos.

Aufruf:
  python lead_finder.py                       # Standard: Stadt Hannover
  python lead_finder.py "Region Hannover" 6   # Hannover und Umgebung
  python lead_finder.py "Braunschweig" 8      # andere Stadt

Tipp: Danach examples/lead_verify.py laufen lassen, um Betriebe auszusortieren,
die in Wahrheit doch eine Website haben.

⚖️  Bitte vor dem Kontaktieren die rechtlichen Hinweise in der README lesen
    (DSGVO + UWG §7: Telefon-Kaltakquise im B2B nur bei mutmaßlichem
    Interesse, Kalt-E-Mails grundsätzlich nur mit Einwilligung).
"""

import csv
import sys
import time
from pathlib import Path

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
#  EINSTELLUNGEN  – hier anpassen (oder per Kommandozeile übergeben)
# ─────────────────────────────────────────────────────────────────────────

# Standard: nur die Stadt Hannover (Level 8).
# "Hannover und Umgebung"?  ->  python lead_finder.py "Region Hannover" 6
STADT = "Hannover"
ADMIN_LEVEL = "8"           # 8 = einzelne Stadt/Gemeinde, 6 = Region/Landkreis

# Welche Betriebe suchen?  (OSM-Filter)
#   - Eintrag OHNE "="  → BELIEBIGER Wert dieses Keys
#       "shop"  = ALLE Läden,  "craft" = ALLE Handwerksbetriebe
#   - Eintrag MIT "="   → genau dieser Typ
OSM_FILTER = [
    "shop",                  # alle Einzelhändler: Bäcker, Friseur, Metzger, Blumen, Optiker …
    "craft",                 # alle Handwerksbetriebe: Tischler, Elektriker, Maler, Dachdecker …
    "amenity=restaurant",
    "amenity=cafe",
    "amenity=bar",
    "amenity=pub",
    "amenity=fast_food",
    "amenity=biergarten",
    "amenity=ice_cream",
    "amenity=pharmacy",
    "amenity=fuel",          # Tankstellen
    "amenity=driving_school",
    "office=lawyer",         # Anwaltskanzlei
    "office=tax_advisor",    # Steuerberater
    "office=insurance",      # Versicherungsbüro
    "office=estate_agent",   # Immobilienmakler
    "tourism=hotel",
    "tourism=guest_house",   # Pension
]

# Lesbare deutsche Bezeichnungen (Fallback: der rohe OSM-Wert)
KAT_LABELS = {
    "restaurant": "Restaurant", "cafe": "Café", "bar": "Bar", "pub": "Kneipe/Pub",
    "fast_food": "Imbiss", "biergarten": "Biergarten", "ice_cream": "Eisdiele",
    "pharmacy": "Apotheke", "fuel": "Tankstelle", "driving_school": "Fahrschule",
    "hairdresser": "Friseur", "bakery": "Bäckerei", "butcher": "Metzgerei",
    "florist": "Blumenladen", "optician": "Optiker", "kiosk": "Kiosk",
    "supermarket": "Supermarkt", "clothes": "Bekleidung", "shoes": "Schuhe",
    "beauty": "Kosmetik", "car_repair": "KFZ-Werkstatt", "hardware": "Eisenwaren",
    "jewelry": "Juwelier", "confectionery": "Konditorei", "greengrocer": "Obst/Gemüse",
    "carpenter": "Tischlerei", "electrician": "Elektriker", "painter": "Maler",
    "plumber": "Klempner/Sanitär", "roofer": "Dachdecker", "gardener": "Gärtner",
    "metal_construction": "Metallbau", "tiler": "Fliesenleger", "shoemaker": "Schuster",
    "lawyer": "Anwalt", "tax_advisor": "Steuerberater", "insurance": "Versicherung",
    "estate_agent": "Immobilienmakler", "hotel": "Hotel", "guest_house": "Pension",
    # weitere häufige Typen
    "tailor": "Schneiderei", "laundry": "Wäscherei", "dry_cleaning": "Reinigung",
    "mobile_phone": "Handy-Shop", "travel_agency": "Reisebüro", "bicycle": "Fahrradladen",
    "books": "Buchhandlung", "furniture": "Möbelgeschäft", "electronics": "Elektronik",
    "beverages": "Getränkemarkt", "deli": "Feinkost", "doityourself": "Baumarkt",
    "variety_store": "Kaufhaus", "second_hand": "Second-Hand", "pet": "Tierbedarf",
    "toys": "Spielwaren", "stationery": "Schreibwaren", "sports": "Sportgeschäft",
    "chemist": "Drogerie", "tobacco": "Tabakladen", "massage": "Massage",
    "tattoo": "Tattoo-Studio", "photographer": "Fotograf", "locksmith": "Schlüsseldienst",
    "shoemaker": "Schuster", "glaziery": "Glaserei", "hearing_aids": "Hörgeräte",
    "car": "Autohaus", "car_parts": "Autoteile", "motorcycle": "Motorradhändler",
    "hardware_store": "Eisenwaren", "gift": "Geschenkartikel", "newsagent": "Zeitschriften",
}

# Nur Leads behalten, die wenigstens eine Telefonnummer haben?
NUR_MIT_TELEFON = True

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


# ─────────────────────────────────────────────────────────────────────────
#  Overpass-Abfrage (kostenlos, ohne Key) – in leichte Teilabfragen gesplittet
# ─────────────────────────────────────────────────────────────────────────

def gruppiere_filter(filters):
    """Teilt die Filter in mehrere kleine Abfragen auf (schont den Server).

    Jeder Platzhalter-Filter (z. B. 'shop' = alle Läden) ist schwer und bekommt
    eine eigene Abfrage; alle exakten 'key=value'-Filter werden zusammengefasst.
    """
    platzhalter = [f for f in filters if "=" not in f]
    exakt = [f for f in filters if "=" in f]
    buckets = [[p] for p in platzhalter]
    if exakt:
        buckets.append(exakt)
    return buckets


def filter_label(filters):
    """Kurzbeschreibung einer Teilabfrage für die Konsolenausgabe."""
    if len(filters) == 1 and "=" not in filters[0]:
        return {"shop": "alle Läden", "craft": "alle Handwerksbetriebe"}.get(
            filters[0], f"alle {filters[0]}")
    return "Gastronomie & Dienstleister"


def baue_query(filters, stadt, level):
    """Baut EINE Overpass-Abfrage für die gegebenen Filter ohne website-Tag."""
    zeilen = []
    for f in filters:
        if "=" in f:
            key, _, value = f.partition("=")
            bedingung = f'["{key}"="{value}"]'
        else:
            bedingung = f'["{f}"]'
        # [!"website"] = "Tag fehlt" (Overpass-Negation)
        zeilen.append(f'  nwr{bedingung}[!"website"][!"contact:website"](area.a);')
    union = "\n".join(zeilen)
    return (
        "[out:json][timeout:180];\n"
        f'area["name"="{stadt}"]["admin_level"="{level}"]'
        '["boundary"="administrative"]->.a;\n'
        f"(\n{union}\n);\n"
        "out center tags;"
    )


def hole_daten(query, versuche=4):
    """Ruft die Overpass-API auf – mit höflichem Backoff bei Rate-Limit (429)."""
    wartezeit = 3
    for versuch in range(1, versuche + 1):
        try:
            # timeout=180: große Abfragen dauern länger als die 30s-Standardvorgabe
            antwort = Fetcher.get(
                OVERPASS_URL,
                params={"data": query},
                timeout=180,
                retries=1,
                stealthy_headers=True,
            )
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


def hole_alle(stadt, level):
    """Führt alle Teilabfragen aus und führt die Elemente zusammen (dedupliziert)."""
    buckets = gruppiere_filter(OSM_FILTER)
    elemente = []
    gesehen = set()
    for i, bucket in enumerate(buckets, start=1):
        print(f"   • Teil {i}/{len(buckets)}: {filter_label(bucket)} …")
        for e in hole_daten(baue_query(bucket, stadt, level)):
            schluessel = (e.get("type"), e.get("id"))
            if schluessel not in gesehen:
                gesehen.add(schluessel)
                elemente.append(e)
        if i < len(buckets):
            time.sleep(2)  # höfliche Pause zwischen den Teilabfragen
    return elemente


# ─────────────────────────────────────────────────────────────────────────
#  Datensätze aufbereiten
# ─────────────────────────────────────────────────────────────────────────

def baue_adresse(t):
    """Setzt die Adresse aus den einzelnen OSM-Tags zusammen."""
    strasse = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    ort = " ".join(x for x in (t.get("addr:postcode"), t.get("addr:city")) if x)
    return ", ".join(x for x in (strasse, ort) if x)


def kategorie_name(t):
    """Ermittelt einen lesbaren Kategorie-Namen aus den Tags."""
    for key in ("shop", "craft", "amenity", "office", "tourism"):
        wert = t.get(key)
        if wert:
            return KAT_LABELS.get(wert, wert)  # Fallback: roher OSM-Wert
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

    leads.sort(key=lambda d: (d["Kategorie"].lower(), d["Name"].lower()))
    return leads


def speichere_csv(leads, pfad):
    """Schreibt die Leads in eine CSV (utf-8-sig → Umlaute korrekt in Excel)."""
    spalten = ["Name", "Kategorie", "Adresse", "Telefon", "E-Mail", "Social", "OSM-Link"]
    with open(pfad, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=spalten)
        writer.writeheader()
        writer.writerows(leads)


def zaehle_kategorien(leads):
    """Zählt die Leads je Kategorie (für eine kurze Übersicht)."""
    zaehler = {}
    for d in leads:
        zaehler[d["Kategorie"]] = zaehler.get(d["Kategorie"], 0) + 1
    return sorted(zaehler.items(), key=lambda x: x[1], reverse=True)


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
        return None

    import os
    env_pfad = Path(__file__).resolve().parent.parent / ".env"
    if not env_pfad.exists():
        return None
    load_dotenv(env_pfad)
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key or key.strip() in ("", "dein_api_key_hier_eintragen"):
        return None
    return key


def priorisiere_mit_claude(api_key, leads, anzahl=30):
    """Lässt Claude die Top-Leads priorisieren (ein einziger API-Aufruf)."""
    import anthropic

    auszug = leads[:anzahl]
    liste = "\n".join(
        f"- {d['Name']} ({d['Kategorie']}, {d['Adresse'] or 'keine Adresse'}), Tel: {d['Telefon']}"
        for d in auszug
    )
    prompt = (
        "Du hilfst einem Freelance-Webentwickler bei der Lead-Auswahl. "
        "Hier sind KMUs OHNE eigene Website. Wähle die 5 aussichtsreichsten "
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
    # Stadt/Level optional per Kommandozeile übergeben
    stadt = sys.argv[1] if len(sys.argv) > 1 else STADT
    level = sys.argv[2] if len(sys.argv) > 2 else ADMIN_LEVEL

    print("=" * 58)
    print(f"  LEAD-FINDER — KMUs ohne Website in {stadt}")
    print("=" * 58)
    print("\nGesucht: alle Läden, Handwerk, Gastronomie, Apotheken,")
    print("         Hotels & lokale Dienstleister (KMUs)")
    print("Quelle:  OpenStreetMap / Overpass-API (kostenlos, ohne Key)\n")

    # 1. Daten holen (mehrere Teilabfragen) -------------------------------
    print("🔎 Frage OpenStreetMap ab (in mehreren Teilen, bitte Geduld) …")
    try:
        elemente = hole_alle(stadt, level)
    except Exception as e:
        print(f"❌ {e}")
        return

    # 2. Aufbereiten ------------------------------------------------------
    leads = verarbeite(elemente)

    if not leads:
        print("\n⚠️  Keine passenden Leads gefunden.")
        print('    Tipp: Stadt/Level prüfen, z. B.  python lead_finder.py "Region Hannover" 6')
        return

    mit_mail = sum(1 for d in leads if d["E-Mail"])
    print(f"\n✅ {len(leads)} KMUs OHNE Website gefunden "
          f"(alle mit Telefon, {mit_mail} davon mit E-Mail).\n")

    print("   Verteilung nach Kategorie (Top 12):")
    for kat, n in zaehle_kategorien(leads)[:12]:
        print(f"     {n:4}×  {kat}")

    # 3. CSV speichern ----------------------------------------------------
    dateiname = f"leads_{stadt.lower().replace(' ', '_')}.csv"
    pfad = Path(__file__).resolve().parent.parent / dateiname
    speichere_csv(leads, pfad)
    print(f"\n💾 Gespeichert als: {pfad}")
    print("   Tipp: Fehltreffer aussortieren mit  python examples/lead_verify.py "
          f"{dateiname}")

    # 4. OPTIONAL: Claude-Priorisierung ----------------------------------
    api_key = claude_api_key()
    if not api_key:
        print("\nℹ️  Optionaler Claude-Schritt übersprungen (kein API-Key gesetzt).")
        print("    Das Tool ist damit fertig – komplett kostenlos. 🎉")
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

    print("-" * 58)
    print("  CLAUDES TOP-LEAD-EMPFEHLUNGEN")
    print("-" * 58 + "\n")
    print(analyse.strip() if analyse else "(Keine Textantwort erhalten.)")


if __name__ == "__main__":
    main()
