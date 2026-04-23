"use client";

import { useState } from "react";
import type { ReactNode } from "react";

export interface TabDef {
  id: string;
  label: string;
  content: ReactNode;
}

export function Tabs({ tabs, initial }: { tabs: TabDef[]; initial?: string }) {
  const [active, setActive] = useState(initial ?? tabs[0]?.id);
  const current = tabs.find((t) => t.id === active) ?? tabs[0];
  return (
    <div>
      <div className="mb-3 flex border-b border-border">
        {tabs.map((t) => {
          const isActive = t.id === current?.id;
          return (
            <button
              key={t.id}
              onClick={() => setActive(t.id)}
              className={[
                "-mb-px border-b-2 px-3.5 py-2 font-mono text-[11px] uppercase tracking-[0.1em] transition-colors",
                isActive
                  ? "border-accent text-accent"
                  : "border-transparent text-fg-dim hover:text-fg",
              ].join(" ")}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      <div>{current?.content}</div>
    </div>
  );
}
