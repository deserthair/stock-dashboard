"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

import { PRESETS, presetRange } from "@/lib/dateRange";

/**
 * Client picker that syncs the selected range into `?from=&to=` URL params.
 * Server pages re-render (via the Next.js router) whenever the params change.
 */
export function DateRangePicker({
  className,
}: {
  className?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, start] = useTransition();

  const from = params.get("from") ?? "";
  const to = params.get("to") ?? "";

  const push = (next: { from?: string; to?: string }) => {
    const sp = new URLSearchParams(params.toString());
    if (next.from) sp.set("from", next.from);
    else sp.delete("from");
    if (next.to) sp.set("to", next.to);
    else sp.delete("to");
    const qs = sp.toString();
    start(() => {
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    });
  };

  return (
    <div
      className={[
        "flex flex-wrap items-center gap-2 text-[11px]",
        className ?? "",
      ].join(" ")}
    >
      <span className="uppercase tracking-[0.15em] text-fg-faint">Range</span>
      <label className="flex items-center gap-1">
        <span className="sr-only">From</span>
        <input
          type="date"
          value={from}
          onChange={(e) => push({ from: e.target.value || undefined, to })}
          className="rounded-sm border border-border bg-panel-2 px-1.5 py-1 font-mono text-[11px] text-fg focus:border-accent focus:outline-none"
        />
      </label>
      <span className="text-fg-faint">→</span>
      <label className="flex items-center gap-1">
        <span className="sr-only">To</span>
        <input
          type="date"
          value={to}
          onChange={(e) => push({ from, to: e.target.value || undefined })}
          className="rounded-sm border border-border bg-panel-2 px-1.5 py-1 font-mono text-[11px] text-fg focus:border-accent focus:outline-none"
        />
      </label>

      <div className="ml-1 flex gap-[2px]">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => push(presetRange(p.days))}
            className="rounded-sm border border-border-hot bg-panel-2 px-1.5 py-1 uppercase tracking-[0.1em] text-fg-dim transition-colors hover:text-accent"
          >
            {p.label}
          </button>
        ))}
      </div>

      {(from || to) && (
        <button
          onClick={() => push({})}
          className="rounded-sm border border-border-hot bg-panel-2 px-1.5 py-1 uppercase tracking-[0.1em] text-fg-dim transition-colors hover:text-down"
        >
          Clear
        </button>
      )}

      {pending && (
        <span className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">
          updating…
        </span>
      )}
    </div>
  );
}
