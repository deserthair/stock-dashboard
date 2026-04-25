"use client";

import { type ReactNode, useMemo, useState } from "react";

import type {
  EventOut,
  MacroRow,
  StatSummary,
  UniverseRow,
  UpcomingEarnings,
} from "@/lib/types";
import { EventFeed } from "./EventFeed";
import { MacroSignals } from "./MacroSignals";
import { StatRow } from "./StatRow";
import { UniverseMatrix } from "./UniverseMatrix";
import { UpcomingEarningsTable } from "./UpcomingEarningsTable";

const ALL = "__ALL__";

export function BriefingFilteredView({
  stats,
  events,
  universe,
  macro,
  upcomingEarnings,
  synthesis,
}: {
  stats: StatSummary;
  events: EventOut[];
  universe: UniverseRow[];
  macro: MacroRow[];
  upcomingEarnings: UpcomingEarnings[];
  synthesis: ReactNode;
}) {
  const [selected, setSelected] = useState<string>(ALL);

  const tickers = useMemo(
    () =>
      [...new Set(universe.map((u) => u.ticker))].sort((a, b) =>
        a.localeCompare(b),
      ),
    [universe],
  );

  const filteredUniverse = useMemo(
    () =>
      selected === ALL
        ? universe
        : universe.filter((u) => u.ticker === selected),
    [universe, selected],
  );

  const filteredEvents = useMemo(
    () =>
      selected === ALL
        ? events
        : events.filter((e) => e.ticker === selected),
    [events, selected],
  );

  const filteredEarnings = useMemo(
    () =>
      selected === ALL
        ? upcomingEarnings
        : upcomingEarnings.filter((e) => e.ticker === selected),
    [upcomingEarnings, selected],
  );

  // Recompute the stat row off the filtered universe so the top tiles
  // reflect what the user actually has on screen.
  const filteredStats: StatSummary = useMemo(() => {
    if (selected === ALL) return stats;
    const u = filteredUniverse;
    const upCount = u.filter((r) => (r.change_1d_pct ?? 0) > 0).length;
    const avgChange =
      u.length > 0
        ? u.reduce((sum, r) => sum + (r.change_1d_pct ?? 0), 0) / u.length
        : 0;
    const sevHi = filteredEvents.filter((e) => e.severity === "hi").length;
    const sevMd = filteredEvents.filter((e) => e.severity === "md").length;
    const sevLo = filteredEvents.filter((e) => e.severity === "lo").length;
    const nextLabel = filteredEarnings
      .slice(0, 3)
      .map(
        (e) =>
          `${e.ticker} ${new Date(e.report_date).toLocaleDateString("en-US", { month: "2-digit", day: "2-digit" })}`,
      )
      .join(" · ");
    return {
      ...stats,
      universe_change_1d_pct: Number(avgChange.toFixed(2)),
      up_count: upCount,
      total_count: u.length,
      events_24h_total: filteredEvents.length,
      events_24h_hi: sevHi,
      events_24h_md: sevMd,
      events_24h_lo: sevLo,
      earnings_next_14d: filteredEarnings.length,
      next_earnings_label: nextLabel,
    };
  }, [selected, stats, filteredUniverse, filteredEvents, filteredEarnings]);

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-3 rounded-sm border border-border bg-panel px-3 py-2">
        <label
          htmlFor="briefing-company-filter"
          className="text-[10px] uppercase tracking-[0.15em] text-fg-faint"
        >
          Filter
        </label>
        <select
          id="briefing-company-filter"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="rounded-sm border border-border bg-panel-2 px-2 py-1 text-[12px] text-fg outline-none focus:border-accent"
        >
          <option value={ALL}>All companies ({tickers.length})</option>
          {tickers.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        {selected !== ALL && (
          <button
            type="button"
            onClick={() => setSelected(ALL)}
            className="text-[11px] text-fg-dim transition-colors hover:text-accent"
          >
            Clear
          </button>
        )}
        <span className="ml-auto text-[10px] uppercase tracking-[0.15em] text-fg-faint">
          {selected === ALL
            ? `Showing all ${tickers.length} companies`
            : `Showing ${selected} only`}
        </span>
      </div>

      <StatRow stats={filteredStats} />

      <div className="mb-3 grid grid-cols-1 gap-3 xl:grid-cols-[2fr_1fr]">
        {synthesis}
        <EventFeed events={filteredEvents} />
      </div>

      <UniverseMatrix rows={filteredUniverse} />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <MacroSignals rows={macro} />
        <UpcomingEarningsTable rows={filteredEarnings} />
      </div>
    </>
  );
}
