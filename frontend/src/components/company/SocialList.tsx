import type { SocialPostOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { fmtSigned } from "@/lib/format";

function sentimentTone(score: number | null) {
  if (score === null || Number.isNaN(score)) return "default";
  if (score > 0.2) return "green";
  if (score < -0.2) return "red";
  return "amber";
}

export function SocialList({ items }: { items: SocialPostOut[] }) {
  if (!items.length) {
    return (
      <Panel title="Social" meta="REDDIT · EMAIL DIGESTS" tight>
        <div className="px-3 py-8 text-center text-[11px] text-fg-faint">
          No social posts ingested yet. Reddit + IMAP email workers populate this.
        </div>
      </Panel>
    );
  }
  return (
    <Panel title="Social" meta={`${items.length} POSTS`} tight>
      {items.map((p) => (
        <div
          key={p.post_id}
          className="border-b border-border px-3 py-2.5 text-[11px]"
        >
          <div className="mb-1 flex gap-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
            <span className="text-accent">{p.platform}</span>
            {p.account && <span>· {p.account}</span>}
            {p.posted_at && (
              <span>
                · {new Date(p.posted_at).toLocaleString("en-US", { timeZone: "America/New_York" })}
              </span>
            )}
            {p.sentiment_score !== null && (
              <span className="ml-auto">
                <Pill tone={sentimentTone(p.sentiment_score)}>
                  sent {fmtSigned(p.sentiment_score, 2)}
                </Pill>
              </span>
            )}
          </div>
          <div className="font-serif text-[13px]">{p.content}</div>
          {p.engagement && Object.keys(p.engagement).length > 0 && (
            <div className="mt-1 text-[10px] text-fg-faint">
              {Object.entries(p.engagement).map(([k, v]) => (
                <span key={k} className="mr-3">
                  {k}: <span className="text-fg">{String(v)}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </Panel>
  );
}
