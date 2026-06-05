export interface Lead {
  name: string;
  kategorie: string;
  adresse: string;
  telefon: string;
  email: string;
  social: string;
  lat: number | null;
  lon: number | null;
  osm: string;
  pruefung: string;
  website: string;
}

export interface Job {
  id: string;
  type: string;
  status: "running" | "done" | "error";
  phase: string;
  current: number;
  total: number;
  leads: Lead[];
  stats: Record<string, number>;
  error: string | null;
}

export interface SearchParams {
  stadt: string;
  level: string;
  kategorien: string[] | null;
  nur_mit_telefon: boolean;
}
