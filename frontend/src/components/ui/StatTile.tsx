import type { ReactNode } from "react";

export function StatTile({
  label,
  value,
  valueClass,
  delta,
}: {
  label: string;
  value: ReactNode;
  valueClass?: string;
  delta?: ReactNode;
}) {
  return (
    <div className="relative rounded-sm border border-border bg-panel p-3">
      <div className="mb-2 text-[10px] uppercase tracking-[0.15em] text-fg-faint">
        {label}
      </div>
      <div
        className={[
          "font-serif text-[28px] font-medium leading-none tracking-tight",
          valueClass ?? "text-fg",
        ].join(" ")}
      >
        {value}
      </div>
      {delta !== undefined && (
        <div className="mt-1.5 text-[11px] tabular-nums text-fg-dim">{delta}</div>
      )}
    </div>
  );
}
