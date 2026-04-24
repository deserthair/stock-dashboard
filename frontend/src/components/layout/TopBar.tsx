"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const NAV = [
  { href: "/", label: "Briefing" },
  { href: "/company/CMG", label: "Company" },
  { href: "/earnings", label: "Earnings" },
  { href: "/correlations", label: "Correlations" },
  { href: "/simulate", label: "Simulate" },
  { href: "/macro", label: "Macro" },
  { href: "/commodities", label: "Commodities" },
  { href: "/trends", label: "Trends" },
  { href: "/hypotheses", label: "Hypotheses" },
  { href: "/ops", label: "Ops" },
];

function useNyClock() {
  const [label, setLabel] = useState("--:--:--");
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setLabel(
        new Intl.DateTimeFormat("en-US", {
          timeZone: "America/New_York",
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }).format(now),
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return label;
}

export function TopBar() {
  const pathname = usePathname();
  const clock = useNyClock();
  return (
    <div className="sticky top-0 z-50 flex h-10 items-center gap-6 border-b border-border bg-panel px-4">
      <div>
        <span className="font-serif text-[16px] font-black tracking-tight text-accent">
          RESTIN
        </span>
        <span className="ml-1 text-[10px] tracking-[0.15em] text-fg-faint">
          // RESTAURANT INTEL TERMINAL
        </span>
      </div>

      <nav className="flex gap-[2px] text-[11px] uppercase tracking-[0.1em]">
        {NAV.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname?.startsWith(item.href.split("/").slice(0, 2).join("/"));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "rounded-sm px-3 py-1.5 transition-colors",
                active
                  ? "border border-border-hot bg-panel-2 text-accent"
                  : "border border-transparent text-fg-dim hover:text-fg",
              ].join(" ")}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="ml-auto flex gap-4 text-[11px] text-fg-dim">
        <div>
          <span className="pulse-dot mr-1.5 align-middle" />
          MKT <strong className="font-medium text-fg">OPEN</strong>
        </div>
        <div>
          NY <strong className="font-medium text-fg">{clock}</strong>
        </div>
        <div>
          INGEST <strong className="font-medium text-accent">OK</strong>
        </div>
      </div>
    </div>
  );
}
