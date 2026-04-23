export function fmtPct(
  value: number | null | undefined,
  opts: { digits?: number; explicit?: boolean; unit?: string } = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const { digits = 2, explicit = true, unit = "%" } = opts;
  const sign = explicit && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}${unit}`;
}

export function fmtNum(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function fmtSigned(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}

export function fmtRevenue(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return value.toLocaleString();
}

export function fmtSigma(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}σ`;
}

export function directionClass(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "text-fg-dim";
  if (Math.abs(value) < 0.1) return "text-fg-dim";
  return value > 0 ? "text-up" : "text-down";
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  // yyyy-mm-dd → mm/dd
  const [, m, d] = iso.split("-");
  return `${m}/${d}`;
}

export function fmtErLabel(
  iso: string | null | undefined,
  time: string | null | undefined,
): string {
  if (!iso) return "—";
  return `${fmtDate(iso)} ${time ?? ""}`.trim();
}
