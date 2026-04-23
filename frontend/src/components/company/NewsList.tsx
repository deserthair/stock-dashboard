import type { NewsItemOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { fmtSigned } from "@/lib/format";

function sentimentTone(score: number | null) {
  if (score === null || Number.isNaN(score)) return "default";
  if (score > 0.2) return "green";
  if (score < -0.2) return "red";
  return "amber";
}

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso);
  const delta = Math.max(0, (Date.now() - then.getTime()) / 1000);
  if (delta < 3600) return `${Math.round(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.round(delta / 3600)}h ago`;
  return `${Math.round(delta / 86400)}d ago`;
}

export function NewsList({ items }: { items: NewsItemOut[] }) {
  if (!items.length) {
    return (
      <Panel title="News" meta="GOOGLE RSS · PR PAGES" tight>
        <div className="px-3 py-8 text-center text-[11px] text-fg-faint">
          No news ingested yet. The `news_rss` and `pr_pages` workers populate this as they run.
        </div>
      </Panel>
    );
  }
  return (
    <Panel title="News" meta={`${items.length} ITEMS`} tight>
      {items.map((n) => (
        <a
          key={n.news_id}
          href={n.url}
          target="_blank"
          rel="noreferrer"
          className="block cursor-pointer border-b border-border px-3 py-2.5 transition-colors hover:bg-panel-2"
        >
          <div className="mb-1 flex gap-2 text-[10px] text-fg-faint">
            <span className="uppercase tracking-[0.1em]">{n.source}</span>
            {n.publisher && <span>· {n.publisher}</span>}
            <span>· {relativeTime(n.published_at ?? n.fetched_at)}</span>
            {n.sentiment_score !== null && (
              <span className="ml-auto">
                <Pill tone={sentimentTone(n.sentiment_score)}>
                  sent {fmtSigned(n.sentiment_score, 2)}
                </Pill>
              </span>
            )}
          </div>
          <div className="font-serif text-[13px] leading-snug">{n.headline}</div>
          {n.topics && n.topics.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {n.topics.slice(0, 4).map((t) => (
                <span
                  key={t}
                  className="rounded-sm border border-border-hot bg-panel-2 px-1.5 py-0 text-[10px] text-fg-dim"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </a>
      ))}
    </Panel>
  );
}
