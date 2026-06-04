#!/usr/bin/env python3
"""
claude_analyze.py — Scrapling + Claude AI kombiniert

Ablauf:
  1. Startseite von Hacker News mit dem Standard-`Fetcher` scrapen
  2. Alle Artikel-Titel per CSS-Selektor extrahieren  (.titleline > a)
  3. Die Titel in EINEM Aufruf an Claude senden und eine kurze
     Themen-Analyse auf Deutsch anfordern
  4. Claudes Antwort formatiert in der Konsole ausgeben

⚠️  Benötigt einen gültigen ANTHROPIC_API_KEY in der .env-Datei!
    (Siehe README.md – ohne echten Key bricht das Skript sauber ab.)
"""

import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from dotenv import load_dotenv
    from scrapling.fetchers import Fetcher
except ImportError as e:
    print(f"❌ Fehlende Abhängigkeit: {e}")
    print('   Installiere alles mit:  pip install -r requirements.txt')
    sys.exit(1)


# Claude-Modell (laut Aufgabenstellung). Bei Bedarf austauschbar,
# z. B. gegen ein neueres Modell wie "claude-sonnet-4-6".
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Öffentliche Seite – Hacker News erlaubt einfaches Lesen der Startseite
HN_URL = "https://news.ycombinator.com"
TITEL_SELEKTOR = ".titleline > a"

PROMPT_VORLAGE = (
    "Hier sind die aktuellen Top-Artikel von Hacker News. "
    "Analysiere kurz: Welche 3 Themen dominieren gerade? "
    "Antworte auf Deutsch in 5-7 Sätzen.\n\n"
    "{titel}"
)


def lade_api_key():
    """Lädt den API-Key aus der .env-Datei (im Projektordner) und prüft ihn."""
    # .env liegt eine Ebene über examples/  ->  scrapling-demo/.env
    env_pfad = Path(__file__).resolve().parent.parent / ".env"

    if not env_pfad.exists():
        print(f"❌ Keine .env-Datei gefunden unter: {env_pfad}")
        print("   Lege eine .env an mit der Zeile:")
        print("   ANTHROPIC_API_KEY=dein_api_key_hier_eintragen")
        return None

    load_dotenv(env_pfad)
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key or api_key.strip() in ("", "dein_api_key_hier_eintragen"):
        print("❌ Kein gültiger ANTHROPIC_API_KEY in der .env-Datei.")
        print(f"   Trage deinen echten Schlüssel hier ein: {env_pfad}")
        print("   Einen Key bekommst du unter: https://console.anthropic.com/settings/keys")
        return None

    return api_key


def scrape_hackernews():
    """Scraped die HN-Startseite und gibt eine Liste der Artikel-Titel zurück."""
    print(f"📰 Lade Hacker News: {HN_URL}")
    page = Fetcher.get(HN_URL, stealthy_headers=True)

    if page.status != 200:
        raise RuntimeError(f"Server antwortete mit Status {page.status}")

    # Die Artikel-Titel stecken in:  <span class="titleline"><a>…</a></span>
    links = page.css(TITEL_SELEKTOR)
    titel = [link.text.strip() for link in links if link.text and link.text.strip()]
    return titel


def frage_claude(api_key, titel):
    """Schickt die Titel in einem einzigen Aufruf an Claude und gibt den Text zurück."""
    # Import bewusst hier drin: so bleibt das Modul auch importierbar,
    # falls 'anthropic' (noch) nicht installiert ist.
    import anthropic

    titel_liste = "\n".join(f"- {t}" for t in titel)
    prompt = PROMPT_VORLAGE.format(titel=titel_liste)

    client = anthropic.Anthropic(api_key=api_key)
    antwort = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    # Die Antwort ist eine Liste von Blöcken – wir nehmen den ersten Text-Block.
    return next((block.text for block in antwort.content if block.type == "text"), "")


def main():
    print("=" * 50)
    print("  HACKER NEWS — ANALYSE MIT CLAUDE")
    print("=" * 50 + "\n")

    # 1. API-Key laden und prüfen
    api_key = lade_api_key()
    if not api_key:
        return

    # 2. Scraping
    try:
        titel = scrape_hackernews()
    except Exception as e:
        print(f"❌ Fehler beim Scrapen von Hacker News: {e}")
        return

    if not titel:
        print(f"⚠️  Keine Titel gefunden – Selektor '{TITEL_SELEKTOR}' lieferte nichts.")
        return

    print(f"✅ {len(titel)} Artikel-Titel gefunden.\n")
    for i, t in enumerate(titel, start=1):
        print(f"  {i:2}. {t}")
    print()

    # 3. An Claude senden
    print("🤖 Sende die Titel an Claude … bitte einen Moment Geduld …\n")
    try:
        analyse = frage_claude(api_key, titel)
    except ImportError:
        print("❌ Das Paket 'anthropic' ist nicht installiert.")
        print("   Installiere es mit:  pip install anthropic")
        return
    except Exception as e:
        # Fängt u. a. AuthenticationError, RateLimitError, APIConnectionError ab
        print(f"❌ Fehler bei der Anfrage an Claude: {e}")
        print("   Prüfe deinen API-Key und dein Anthropic-Guthaben.")
        return

    # 4. Antwort ausgeben
    print("-" * 50)
    print("  CLAUDES ANALYSE")
    print("-" * 50 + "\n")
    print(analyse.strip() if analyse else "(Keine Textantwort erhalten.)")
    print()


if __name__ == "__main__":
    main()
