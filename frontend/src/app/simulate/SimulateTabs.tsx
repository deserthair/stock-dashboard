"use client";

import { useState } from "react";

import { BacktestPanel } from "@/components/simulate/BacktestPanel";
import { DCFPanel } from "@/components/simulate/DCFPanel";
import { Panel } from "@/components/ui/Panel";
import type {
  BacktestReportOut,
  DCFResultOut,
  EarningsBootstrapOut,
  PricePathSimulationOut,
  UniverseRow,
} from "@/lib/types";
import { SimulatePanel } from "./SimulatePanel";

type TabId = "paths" | "dcf" | "backtest";

export function SimulateTabs({
  universe,
  initialTicker,
  initialPrice,
  initialBootstrap,
  initialDCF,
  initialBacktest,
}: {
  universe: UniverseRow[];
  initialTicker: string;
  initialPrice: PricePathSimulationOut;
  initialBootstrap: EarningsBootstrapOut;
  initialDCF: DCFResultOut | null;
  initialBacktest: BacktestReportOut | null;
}) {
  const [active, setActive] = useState<TabId>("paths");

  const bestR = initialBacktest?.models?.[0]?.correlation_r ?? null;
  const tabs: { id: TabId; label: string }[] = [
    { id: "paths", label: "Price paths + Earnings Bootstrap" },
    { id: "dcf", label: "Probabilistic DCF" },
    {
      id: "backtest",
      label:
        bestR !== null && bestR !== undefined
          ? `Backtest (best r = ${bestR >= 0 ? "+" : ""}${bestR.toFixed(2)})`
          : "Backtest",
    },
  ];

  return (
    <div>
      <div className="mb-3 flex border-b border-border">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActive(t.id)}
            className={[
              "-mb-px border-b-2 px-3.5 py-2 font-mono text-[11px] uppercase tracking-[0.1em] transition-colors",
              active === t.id
                ? "border-accent text-accent"
                : "border-transparent text-fg-dim hover:text-fg",
            ].join(" ")}
          >
            {t.label}
          </button>
        ))}
      </div>

      {active === "paths" && (
        <SimulatePanel
          universe={universe}
          initialTicker={initialTicker}
          initialPrice={initialPrice}
          initialBootstrap={initialBootstrap}
        />
      )}
      {active === "dcf" &&
        (initialDCF ? (
          <DCFPanel ticker={initialTicker} initial={initialDCF} />
        ) : (
          <Panel title="DCF unavailable">
            <p className="text-[11px] text-fg-dim">
              No fundamentals ingested for {initialTicker}. Run{" "}
              <code>python -m ingest.sources.fundamentals</code> first.
            </p>
          </Panel>
        ))}
      {active === "backtest" &&
        (initialBacktest ? (
          <BacktestPanel data={initialBacktest} />
        ) : (
          <Panel title="Backtest unavailable">
            <p className="text-[11px] text-fg-dim">
              Backtest failed to run. Check server logs.
            </p>
          </Panel>
        ))}
    </div>
  );
}
