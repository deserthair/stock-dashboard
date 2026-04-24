"use client";

import { useState } from "react";

import { DCFPanel } from "@/components/simulate/DCFPanel";
import { Panel } from "@/components/ui/Panel";
import type {
  DCFResultOut,
  EarningsBootstrapOut,
  PricePathSimulationOut,
  UniverseRow,
} from "@/lib/types";
import { SimulatePanel } from "./SimulatePanel";

type TabId = "paths" | "dcf";

export function SimulateTabs({
  universe,
  initialTicker,
  initialPrice,
  initialBootstrap,
  initialDCF,
}: {
  universe: UniverseRow[];
  initialTicker: string;
  initialPrice: PricePathSimulationOut;
  initialBootstrap: EarningsBootstrapOut;
  initialDCF: DCFResultOut | null;
}) {
  const [active, setActive] = useState<TabId>("paths");

  const tabs: { id: TabId; label: string }[] = [
    { id: "paths", label: "Price paths + Earnings Bootstrap" },
    { id: "dcf", label: "Probabilistic DCF" },
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
    </div>
  );
}
