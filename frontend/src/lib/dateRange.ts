/**
 * Shared helpers for reading date-range filters from URL search params.
 *
 * Contract: the URL carries optional `from` and `to` strings in YYYY-MM-DD
 * format. Pages pass them straight through to the backend — validation lives
 * there. If only one bound is present we still send it.
 */

export type DateRange = {
  from?: string;
  to?: string;
};

export function rangeFromSearch(
  searchParams: Record<string, string | string[] | undefined> | undefined,
): DateRange {
  const one = (v: string | string[] | undefined): string | undefined => {
    if (Array.isArray(v)) return v[0] ?? undefined;
    return v ?? undefined;
  };
  const raw = { from: one(searchParams?.from), to: one(searchParams?.to) };
  // Accept only valid YYYY-MM-DD; otherwise drop silently. The picker can
  // never produce bad values but external links might.
  const ok = (v: string | undefined) =>
    v && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : undefined;
  return { from: ok(raw.from), to: ok(raw.to) };
}

export function toQueryString(range: DateRange): string {
  const parts: string[] = [];
  if (range.from) parts.push(`start_date=${range.from}`);
  if (range.to) parts.push(`end_date=${range.to}`);
  return parts.length ? `&${parts.join("&")}` : "";
}

/** Render a compact label summarising the active range. */
export function labelFor(range: DateRange): string {
  if (!range.from && !range.to) return "All time";
  if (range.from && range.to) return `${range.from} → ${range.to}`;
  if (range.from) return `Since ${range.from}`;
  return `Until ${range.to}`;
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

export const PRESETS: Array<{ label: string; days?: number }> = [
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
  { label: "6M", days: 180 },
  { label: "1Y", days: 365 },
  { label: "ALL" },
];

export function presetRange(days: number | undefined): DateRange {
  if (days === undefined) return {};
  return { from: isoDaysAgo(days), to: new Date().toISOString().slice(0, 10) };
}
