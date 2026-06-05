"use client";

import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Lead } from "@/lib/types";

type Pt = Lead & { lat: number; lon: number };

export default function LeadMap({ leads }: { leads: Lead[] }) {
  const pts = leads.filter((l) => l.lat != null && l.lon != null) as Pt[];

  const center: [number, number] = pts.length
    ? [
        pts.reduce((s, l) => s + l.lat, 0) / pts.length,
        pts.reduce((s, l) => s + l.lon, 0) / pts.length,
      ]
    : [52.3759, 9.732];

  return (
    <MapContainer center={center} zoom={11} scrollWheelZoom className="h-full w-full">
      <TileLayer
        attribution='&copy; OpenStreetMap-Mitwirkende'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {pts.map((l, i) => (
        <CircleMarker
          key={i}
          center={[l.lat, l.lon]}
          radius={6}
          pathOptions={{
            color: l.pruefung === "hat Website" ? "#ef4444" : "#10b981",
            fillColor: l.pruefung === "hat Website" ? "#ef4444" : "#10b981",
            fillOpacity: 0.7,
            weight: 1,
          }}
        >
          <Popup>
            <div className="text-slate-900">
              <strong>{l.name}</strong>
              <br />
              {l.kategorie}
              <br />
              {l.telefon}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
