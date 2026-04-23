import type { ReactNode } from "react";

export function Panel({
  title,
  meta,
  tight,
  className,
  children,
}: {
  title?: ReactNode;
  meta?: ReactNode;
  tight?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={[
        "mb-3 rounded-sm border border-border bg-panel",
        className ?? "",
      ].join(" ")}
    >
      {(title || meta) && (
        <header className="flex items-center border-b border-border bg-panel-2 px-3 py-2 text-[10px] uppercase tracking-[0.15em] text-fg-dim">
          <span className="font-semibold text-fg">{title}</span>
          {meta && <span className="ml-auto text-fg-faint">{meta}</span>}
        </header>
      )}
      <div className={tight ? "" : "p-3"}>{children}</div>
    </section>
  );
}
