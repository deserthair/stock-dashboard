import type { EventOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";

const SEV: Record<string, string> = {
  hi: "sev-hi",
  md: "sev-md",
  lo: "sev-lo",
};

export function EventFeed({ events }: { events: EventOut[] }) {
  return (
    <Panel title="Live Event Feed" meta="AUTO · 5min" tight>
      {events.map((e, idx) => (
        <div
          key={`${e.ticker}-${e.event_at}-${idx}`}
          className={`grid cursor-pointer grid-cols-[60px_70px_1fr] gap-3 border-b border-border px-3 py-2.5 text-[11px] transition-colors hover:bg-panel-2 ${
            SEV[e.severity] ?? ""
          }`}
        >
          <span className="tabular-nums text-fg-faint">{e.time_label}</span>
          <span
            className={`font-semibold tracking-wide ${
              e.severity === "hi" ? "text-accent" : "text-fg"
            }`}
          >
            {e.ticker}
          </span>
          <div className="text-fg">
            {e.description}
            {e.source && (
              <span className="ml-1.5 text-[10px] text-fg-faint">
                {e.source}
              </span>
            )}
          </div>
        </div>
      ))}
    </Panel>
  );
}
