import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lead-Finder — KMUs ohne Website",
  description: "Finde Betriebe ohne eigene Website – inkl. Telefon, Karte und Export.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
