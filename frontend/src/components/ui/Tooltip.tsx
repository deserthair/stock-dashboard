import type { ReactNode } from "react";

/**
 * Pure-CSS hover tooltip. Wraps any inline element; the `tip` text appears
 * in a small popover above the wrapped element on hover/focus.
 *
 * Uses Tailwind `group` so the trigger child stays inert — the tooltip is a
 * sibling positioned absolutely. No JS, no dependencies.
 */
export function Tooltip({
  tip,
  children,
  className,
}: {
  tip: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={`group relative inline-flex ${className ?? ""}`}>
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-40 mb-1.5 -translate-x-1/2 whitespace-normal rounded-sm border border-border bg-panel-2 px-2 py-1 text-[10px] normal-case tracking-normal text-fg opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
        style={{ minWidth: "180px", maxWidth: "260px" }}
      >
        {tip}
      </span>
    </span>
  );
}
