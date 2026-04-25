import type { ReactNode } from "react";
import { InfoIcon, type InfoContent } from "./InfoIcon";

export function StatTile({
  label,
  value,
  valueClass,
  delta,
  info,
}: {
  label: string;
  value: ReactNode;
  valueClass?: string;
  delta?: ReactNode;
  info?: InfoContent;
}) {
  return (
    <div className="relative rounded-sm border border-border bg-panel p-3">
      <div className="mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-[0.15em] text-fg-faint">
        <span>{label}</span>
        {info && <InfoIcon info={info} />}
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
