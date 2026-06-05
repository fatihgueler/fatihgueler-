"""
core.py — Kernlogik der Lead-App.

Kapselt das, was vorher die CLI-Skripte gemacht haben, als importierbare
Funktionen für das FastAPI-Backend:

  • finde_leads(...)       → KMUs ohne Website aus OpenStreetMap (Overpass)
  • verifiziere_lead(...)  → per Websuche prüfen, ob doch eine Website existiert

Beides ist kostenlos und ohne API-Key nutzbar.
"""

import re
import time
import unicodedata
from urllib.parse import quote

from scrapling.fetchers import Fetcher

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Standard-Branchen (KMUs). Frontend kann eine eigene Auswahl schicken.
DEFAULT_FILTER = [
    "shop", "craft",
    "amenity=restaurant", "amenity=cafe", "amenity=bar", "amenity=pub",
    "amenity=fast_food", "amenity=biergarten", "amenity=ice_cream",
    "amenity=pharmacy", "amenity=fuel", "amenity=driving_school",
    "office=lawyer", "office=tax_advisor", "office=insurance", "office=estate_agent",
    "tourism=hotel", "tourism=guest_house",
]

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
    "tailor": "Schneiderei", "laundry": "Wäscherei", "dry_cleaning": "Reinigung",
    "mobile_phone": "Handy-Shop", "travel_agency": "Reisebüro", "bicycle": "Fahrradladen",
    "books": "Buchhandlung", "furniture": "Möbelgeschäft", "electronics": "Elektronik",
    "beverages": "Getränkemarkt", "deli": "Feinkost", "doityourself": "Baumarkt",
    "variety_store": "Kaufhaus", "second_hand": "Second-Hand", "pet": "Tierbedarf",
    "toys": "Spielwaren", "stationery": "Schreibwaren", "sports": "Sportgeschäft",
    "chemist": "Drogerie", "tobacco": "Tabakladen", "massage": "Massage",
    "tattoo": "Tattoo-Studio", "photographer": "Fotograf", "locksmith": "Schlüsseldienst",
    "glaziery": "Glaserei", "hearing_aids": "Hörgeräte", "car": "Autohaus",
    "car_parts": "Autoteile", "motorcycle": "Motorradhändler", "gift": "Geschenkartikel",
    "newsagent": "Zeitschriften",
}

# Domains, die KEINE eigene Firmenwebsite sind
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

NAME_STOPWORDS = {
    "gmbh", "kg", "ohg", "co", "mbh", "inh", "und", "der", "die", "das",
    "restaurant", "cafe", "bar", "hotel", "pension", "imbiss", "friseur",
    "salon", "kosmetik", "hannover", "gbr", "haus", "stube", "berlin",
    "pizzeria", "trattoria", "bistro", "kiosk", "apotheke", "baeckerei",
}


# ───────────────────────── OpenStreetMap / Overpass ─────────────────────────

def _klausel(f):
    if "=" in f:
        key, _, value = f.partition("=")
        bedingung = f'["{key}"="{value}"]'
    else:
        bedingung = f'["{f}"]'
    return f'  nwr{bedingung}[!"website"][!"contact:website"](area.a);'


def gruppiere_filter(filters):
    """Platzhalter (shop/craft) je eigene Abfrage, exakte Filter zusammen."""
    platzhalter = [f for f in filters if "=" not in f]
    exakt = [f for f in filters if "=" in f]
    buckets = [[p] for p in platzhalter]
    if exakt:
        buckets.append(exakt)
    return buckets


def filter_label(filters):
    if len(filters) == 1 and "=" not in filters[0]:
        return {"shop": "alle Läden", "craft": "Handwerksbetriebe"}.get(
            filters[0], f"alle {filters[0]}")
    return "Gastronomie & Dienstleister"


def baue_query(filters, stadt, level):
    union = "\n".join(_klausel(f) for f in filters)
    return (
        "[out:json][timeout:180];\n"
        f'area["name"="{stadt}"]["admin_level"="{level}"]'
        '["boundary"="administrative"]->.a;\n'
        f"(\n{union}\n);\n"
        "out center tags;"
    )


def hole_daten(query, versuche=4):
    wartezeit = 3
    for versuch in range(1, versuche + 1):
        try:
            antwort = Fetcher.get(
                OVERPASS_URL, params={"data": query},
                timeout=180, retries=1, stealthy_headers=True,
            )
        except Exception:
            antwort = None
        if antwort is not None and antwort.status == 200:
            try:
                return antwort.json().get("elements", [])
            except Exception:
                pass
        if versuch < versuche:
            time.sleep(wartezeit)
            wartezeit *= 2
    raise RuntimeError("Overpass-API war nicht erreichbar (evtl. überlastet, später erneut).")


def _adresse(t):
    strasse = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    ort = " ".join(x for x in (t.get("addr:postcode"), t.get("addr:city")) if x)
    return ", ".join(x for x in (strasse, ort) if x)


def _kategorie(t):
    for key in ("shop", "craft", "amenity", "office", "tourism"):
        wert = t.get(key)
        if wert:
            return KAT_LABELS.get(wert, wert)
    return "Sonstiges"


def _coords(e):
    if e.get("lat") is not None:
        return e.get("lat"), e.get("lon")
    c = e.get("center") or {}
    return c.get("lat"), c.get("lon")


def finde_leads(stadt, level="8", filters=None, nur_mit_telefon=True, progress=None):
    """Findet KMUs ohne Website. progress(stufe, gesamt, label) wird je Teil aufgerufen."""
    filters = filters or DEFAULT_FILTER
    buckets = gruppiere_filter(filters)

    elemente, gesehen = [], set()
    for i, bucket in enumerate(buckets, start=1):
        if progress:
            progress(i, len(buckets), filter_label(bucket))
        for e in hole_daten(baue_query(bucket, stadt, level)):
            schluessel = (e.get("type"), e.get("id"))
            if schluessel not in gesehen:
                gesehen.add(schluessel)
                elemente.append(e)
        if i < len(buckets):
            time.sleep(1.5)

    leads, doppelt = [], set()
    for e in elemente:
        t = e.get("tags", {})
        name = t.get("name")
        if not name:
            continue
        telefon = t.get("phone") or t.get("contact:phone") or t.get("contact:mobile") or ""
        if nur_mit_telefon and not telefon:
            continue
        kennung = (name.lower(), telefon)
        if kennung in doppelt:
            continue
        doppelt.add(kennung)

        lat, lon = _coords(e)
        leads.append({
            "name": name,
            "kategorie": _kategorie(t),
            "adresse": _adresse(t),
            "telefon": telefon,
            "email": t.get("email") or t.get("contact:email") or "",
            "social": t.get("contact:facebook") or t.get("contact:instagram") or "",
            "lat": lat, "lon": lon,
            "osm": f"https://www.openstreetmap.org/{e.get('type')}/{e.get('id')}",
            "pruefung": "",          # wird beim Verifizieren gesetzt
            "website": "",           # gefundene Domain (falls vorhanden)
        })

    leads.sort(key=lambda d: (d["kategorie"].lower(), d["name"].lower()))
    return leads


# ───────────────────────── Verifizierung (Websuche) ─────────────────────────

def _norm(s):
    s = s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def name_tokens(name):
    toks = re.split(r"[^a-z0-9]+", _norm(name))
    return {t for t in toks if len(t) >= 4 and t not in NAME_STOPWORDS}


def domain_tokens(host):
    teile = host.split(".")
    kern = teile[-2] if len(teile) >= 2 else teile[0]
    return {t for t in re.split(r"[^a-z0-9]+", _norm(kern)) if len(t) >= 4}


def ist_verzeichnis(host):
    return any(m in host for m in VERZEICHNIS_MARKER)


def _ort(adresse):
    if adresse and "," in adresse:
        tail = adresse.split(",")[-1].strip()
        ort = " ".join(t for t in tail.split() if not t.isdigit())
        if ort:
            return ort
    return ""


def suche_domains(query, max_treffer=8):
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


def verifiziere_lead(lead):
    """Gibt (status, domain) zurück. status: 'keine' | 'hat' | 'offen'."""
    domains = suche_domains(f"{lead['name']} {_ort(lead.get('adresse', ''))}".strip())
    if domains is None:
        return ("offen", "")
    nt = name_tokens(lead["name"])
    for host in domains:
        if ist_verzeichnis(host):
            continue
        if nt & domain_tokens(host):
            return ("hat", host)
    return ("keine", "")
