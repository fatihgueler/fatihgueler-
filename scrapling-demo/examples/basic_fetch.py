#!/usr/bin/env python3
"""
basic_fetch.py — Einfaches Web-Scraping mit Scrapling

Lädt die öffentliche Demo-Seite books.toscrape.com (ausdrücklich zum Üben
freigegeben) und gibt Titel + Preis der ersten 5 Bücher aus.

Verwendet den Standard-`Fetcher`: ein schneller HTTP-Request, ganz ohne
Browser. Ideal für Seiten, die kein JavaScript zum Rendern brauchen.
"""

import sys

# Sorgt dafür, dass Umlaute/Emojis auch auf Windows-Konsolen korrekt erscheinen
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


# Öffentliche Übungs-Seite – ausdrücklich zum Scrapen gedacht
URL = "https://books.toscrape.com"


def main():
    print(f"📚 Lade Bücher von: {URL}\n")

    # 1. Seite abrufen ----------------------------------------------------
    try:
        # stealthy_headers=True sendet realistische Browser-Header mit
        page = Fetcher.get(URL, stealthy_headers=True)
    except Exception as e:
        print(f"❌ Fehler beim Abrufen der Seite: {e}")
        print("   Tipp: Internetverbindung prüfen und erneut versuchen.")
        return

    if page.status != 200:
        print(f"⚠️  Server antwortete mit Status {page.status} (erwartet: 200).")
        return

    # 2. Daten auslesen ---------------------------------------------------
    try:
        # Jedes Buch steckt in einem <article class="product_pod">
        books = page.css("article.product_pod")

        if not books:
            print("⚠️  Keine Bücher gefunden – hat sich die Seitenstruktur geändert?")
            return

        print(f"✅ {len(books)} Bücher auf der Seite gefunden. Die ersten 5:\n")

        for i, book in enumerate(books[:5], start=1):
            # Der volle Titel steht im 'title'-Attribut des <a>-Tags
            # (der sichtbare Text wird auf der Seite abgeschnitten).
            title_link = book.css("h3 a")
            titel = title_link[0].attrib.get("title", "Unbekannt") if title_link else "Unbekannt"

            # Der Preis steht im Element mit der Klasse .price_color
            price_el = book.css(".price_color")
            preis = price_el[0].text.strip() if price_el else "k. A."

            print(f"  {i}. {titel}")
            print(f"     Preis: {preis}\n")

    except Exception as e:
        print(f"❌ Fehler beim Auslesen der Buchdaten: {e}")


if __name__ == "__main__":
    main()
