import Link from "next/link";

import type { UniverseRow } from "@/lib/types";
import { fmtPct } from "@/lib/format";

interface TickerBlock {
  label: string;
  rows: Array<{ ticker: string; name: string; pct: number | null; pctLabel?: string }>;
}

function directionClass(pct: number | null): string {
  if (pct === null || pct === undefined) return "text-fg-dim";
  if (Math.abs(pct) < 0.1) return "text-fg-dim";
  return pct > 0 ? "text-up" : "text-down";
}

const WATCHLIST = [
  { ticker: "XLY", name: "Cons Disc", pct: 0.52 },
  { ticker: "SPY", name: "S&P 500", pct: 0.21 },
];

const MACRO_TAGS = [
  { ticker: "BEEF", name: "Live Cattle", pct: 0.84 },
  { ticker: "GAS", name: "Retail Gas", pct: -0.33 },
  { ticker: "10Y", name: "Treasury", pct: 0.03, pctLabel: "+3bp" },
];

function SidebarLabel({ children, first }: { children: React.ReactNode; first?: boolean }) {
  return (
    <div
      className={[
        "px-4 text-[10px] uppercase tracking-[0.15em] text-fg-faint",
        first ? "mb-2" : "mb-2 mt-5",
      ].join(" ")}
    >
      {children}
    </div>
  );
}

function TickerRow({
  ticker,
  name,
  pct,
  pctLabel,
  href,
  active,
}: {
  ticker: string;
  name: string;
  pct: number | null;
  pctLabel?: string;
  href?: string;
  active?: boolean;
}) {
  const content = (
    <div
      className={[
        "flex cursor-pointer items-center border-l-2 px-4 py-1.5 text-[11px] transition-colors",
        active
          ? "border-accent bg-panel-2"
          : "border-transparent hover:bg-panel-2",
      ].join(" ")}
    >
      <span className={`w-[46px] font-semibold ${active ? "text-accent" : "text-fg"}`}>
        {ticker}
      </span>
      <span className="text-fg-dim">{name}</span>
      <span
        className={`ml-auto font-mono tabular-nums ${directionClass(pct)}`}
      >
        {pctLabel ?? fmtPct(pct, { digits: 2 })}
      </span>
    </div>
  );
  if (href) return <Link href={href}>{content}</Link>;
  return content;
}

export function Sidebar({
  universe,
  activeTicker,
}: {
  universe: UniverseRow[];
  activeTicker?: string;
}) {
  return (
    <aside className="min-h-[calc(100vh-40px)] w-[220px] border-r border-border bg-panel py-4">
      <SidebarLabel first>Universe</SidebarLabel>
      {universe.map((row) => (
        <TickerRow
          key={row.ticker}
          ticker={row.ticker}
          name={row.name.replace(/,?\s+(Inc\.|Corporation|Corp\.?|Group|Mexican Grill,?|International).*$/, "")
            .replace("Texas Roadhouse", "Tx Roadhouse")
            .replace("Restaurant Brands", "Rest. Brands")
            .replace("McDonald's", "McDonald's")
            .slice(0, 16)}
          pct={row.change_1d_pct}
          href={`/company/${row.ticker}`}
          active={activeTicker === row.ticker}
        />
      ))}

      <SidebarLabel>Watch</SidebarLabel>
      {WATCHLIST.map((r) => (
        <TickerRow key={r.ticker} {...r} />
      ))}

      <SidebarLabel>Macro</SidebarLabel>
      {MACRO_TAGS.map((r) => (
        <TickerRow key={r.ticker} {...r} />
      ))}
    </aside>
  );
}
