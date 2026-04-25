import type { EventOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";

const SEV: Record<string, string> = {
  hi: "sev-hi",
  md: "sev-md",
  lo: "sev-lo",
};

export function EventFeed({ events }: { events: EventOut[] }) {
  const snapshot = events.map((e) => ({
    time: e.time_label,
    ticker: e.ticker,
    severity: e.severity,
    source: e.source,
    description: e.description,
  }));
  return (
    <Panel
      title="Live Event Feed"
      meta="AUTO · 5min"
      tight
      info={{
        title: "Live Event Feed",
        explanation:
          "A real-time list of notable things happening to the companies we track. Each row is one event: a news article, a filing with the SEC, a social-media spike, an analyst rating change, etc.\n\nThe colored bar on the left shows severity:\n• Red = high — likely to move the stock.\n• Amber = medium — worth a look.\n• Gray = low — background.\n\nThe time shows when it hit; the ticker (e.g. MCD) is the company; the rest is a one-line description and source. Updates roughly every 5 minutes.",
        dataSnapshot: `Events currently on screen (${events.length}):\n${JSON.stringify(snapshot, null, 2)}`,
      }}
    >
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
