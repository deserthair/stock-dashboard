import type { ReactNode } from "react";
import { InfoIcon, type InfoContent } from "./InfoIcon";

export function Panel({
  title,
  meta,
  tight,
  className,
  info,
  children,
}: {
  title?: ReactNode;
  meta?: ReactNode;
  tight?: boolean;
  className?: string;
  info?: InfoContent;
  children: ReactNode;
}) {
  return (
    <section
      className={[
        "mb-3 rounded-sm border border-border bg-panel",
        className ?? "",
      ].join(" ")}
    >
      {(title || meta || info) && (
        <header className="flex items-center border-b border-border bg-panel-2 px-3 py-2 text-[10px] uppercase tracking-[0.15em] text-fg-dim">
          <span className="flex items-center gap-1.5 font-semibold text-fg">
            {title}
            {info && <InfoIcon info={info} />}
          </span>
          {meta && <span className="ml-auto text-fg-faint">{meta}</span>}
        </header>
      )}
      <div className={tight ? "" : "p-3"}>{children}</div>
    </section>
  );
}
