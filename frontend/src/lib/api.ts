import type {
  BriefingResponse,
  CompanyDetail,
  EventOut,
  MacroRow,
  UniverseRow,
  UpcomingEarnings,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string, revalidate = 60): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    next: { revalidate },
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`${path} → ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export const api = {
  briefing: () => get<BriefingResponse>("/api/briefing", 60),
  universe: () => get<UniverseRow[]>("/api/universe", 60),
  events: (limit = 20) => get<EventOut[]>(`/api/events?limit=${limit}`, 30),
  upcomingEarnings: () => get<UpcomingEarnings[]>("/api/earnings/upcoming", 300),
  macro: () => get<MacroRow[]>("/api/macro", 300),
  company: (ticker: string) =>
    get<CompanyDetail>(`/api/companies/${ticker.toUpperCase()}`, 300),
};
