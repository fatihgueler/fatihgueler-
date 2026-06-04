#!/usr/bin/env python3
"""
stealth_fetch.py — Tarnkappen-Scraping mit Scrapling

Nutzt den `StealthyFetcher`, der im Hintergrund einen echten (modifizierten)
Browser startet. So lassen sich auch Seiten abrufen, die einfache HTTP-Bots
erkennen und blockieren würden.

Zusätzlich zeigt das Beispiel die Arbeit mit einem einzelnen CSS-Selektor:
`.price_color` liefert alle Preisangaben.

ℹ️  Voraussetzung: einmalig die Browser-Dependencies installieren mit
       scrapling install
    (lädt einen Headless-Browser herunter).
"""

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from scrapling.fetchers import StealthyFetcher
except ImportError:
    print("❌ Scrapling ist nicht installiert.")
    print('   Installiere es mit:  pip install "scrapling[fetchers]"')
    sys.exit(1)


URL = "https://books.toscrape.com"
SELEKTOR = ".price_color"


def main():
    print(f"🕶️  StealthyFetcher startet einen echten Browser und lädt:\n   {URL}\n")

    # 1. Seite mit echtem Browser laden -----------------------------------
    try:
        # headless=True   -> Browser läuft unsichtbar im Hintergrund
        # network_idle=True -> warten, bis das Netzwerk zur Ruhe kommt
        page = StealthyFetcher.fetch(URL, headless=True, network_idle=True)
    except Exception as e:
        print(f"❌ Fehler beim Stealth-Abruf: {e}")
        print("   Tipp: Wurden die Browser-Dependencies installiert?")
        print("   Führe einmalig aus:  scrapling install")
        return

    # 2. Einen einzelnen CSS-Selektor anwenden ----------------------------
    try:
        # page.css(<selektor>) liefert eine Liste passender Elemente
        preise = page.css(SELEKTOR)

        if not preise:
            print(f"⚠️  Keine Treffer für den Selektor '{SELEKTOR}'.")
            return

        print(f"✅ Selektor '{SELEKTOR}' lieferte {len(preise)} Treffer.")
        print("   Die ersten 5 Preise:\n")

        for i, preis in enumerate(preise[:5], start=1):
            print(f"  {i}. {preis.text.strip()}")

    except Exception as e:
        print(f"❌ Fehler beim Auslesen der Preise: {e}")


if __name__ == "__main__":
    main()
