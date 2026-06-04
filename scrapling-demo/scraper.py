#!/usr/bin/env python3
"""
scraper.py — Haupt-Demo: Scrapling + Claude AI

Führt nacheinander alle drei Beispiele aus dem Ordner examples/ aus:

    [1/3] Basic Fetch    → books.toscrape.com
    [2/3] Stealth Fetch  → CSS-Selektor-Test
    [3/3] Claude-Analyse → Hacker-News-Trends

Aufruf (im Projektordner, mit aktivierter venv):

    python scraper.py

Hinweis: Schritt [3/3] benötigt einen gültigen ANTHROPIC_API_KEY in der
.env-Datei. Fehlt er, bricht nur dieser Schritt sauber ab – die anderen
beiden laufen trotzdem durch.
"""

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# examples/-Ordner zum Suchpfad hinzufügen, damit wir die Module importieren können
EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"
sys.path.insert(0, str(EXAMPLES_DIR))

BREITE = 40


def linie(zeichen="="):
    print(zeichen * BREITE)


def kopf():
    linie()
    print("  SCRAPLING + CLAUDE AI — DEMO")
    linie()
    print()
    print("[1/3] Basic Fetch    → books.toscrape.com")
    print("[2/3] Stealth Fetch  → CSS-Selektor-Test")
    print("[3/3] Claude-Analyse → Hacker-News-Trends")
    print()


def abschnitt(nummer, titel):
    print()
    linie("-")
    print(f"[{nummer}/3] {titel}")
    linie("-")
    print()


def schritt(nummer, titel, modulname):
    """Importiert ein Beispiel-Modul und ruft dessen main() auf – robust gekapselt."""
    abschnitt(nummer, titel)
    try:
        modul = __import__(modulname)
        modul.main()
    except Exception as e:
        print(f"❌ Schritt [{nummer}/3] ist fehlgeschlagen: {e}")


def main():
    kopf()

    schritt(1, "Basic Fetch → books.toscrape.com", "basic_fetch")
    schritt(2, "Stealth Fetch → CSS-Selektor-Test", "stealth_fetch")
    schritt(3, "Claude-Analyse → Hacker-News-Trends", "claude_analyze")

    print()
    linie()
    print("  DEMO ABGESCHLOSSEN ✅")
    linie()


if __name__ == "__main__":
    main()
