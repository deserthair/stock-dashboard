import type { NewsItemOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { fmtSigned } from "@/lib/format";

function sentimentTone(score: number | null | undefined) {
  if (score === null || score === undefined) return "default" as const;
  if (score > 0.2) return "green" as const;
  if (score < -0.2) return "red" as const;
  return "amber" as const;
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso);
  const delta = Math.max(0, (Date.now() - then.getTime()) / 1000);
  if (delta < 3600) return `${Math.round(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.round(delta / 3600)}h ago`;
  return `${Math.round(delta / 86400)}d ago`;
}

export function HolderNewsList({
  items,
  ticker,
}: {
  items: NewsItemOut[];
  ticker: string;
}) {
  if (items.length === 0) {
    return (
      <Panel
        title={`Holder News · ${ticker}`}
        meta="GOOGLE NEWS RSS · INSTITUTIONAL COVERAGE"
        tight
      >
        <div className="px-3 py-6 text-center text-[11px] text-fg-faint">
          No news ingested for {ticker}&apos;s institutional holders yet. Run{" "}
          <code>python -m ingest.sources.news_rss</code>.
        </div>
      </Panel>
    );
  }

  // Group by institution so the UI can show who's being covered
  const byInst = new Map<string, NewsItemOut[]>();
  for (const n of items) {
    const key = n.institution_name ?? "Unknown";
    if (!byInst.has(key)) byInst.set(key, []);
    byInst.get(key)!.push(n);
  }

  return (
    <Panel
      title={`Holder News · ${ticker}`}
      meta={`${items.length} ITEMS · ${byInst.size} INSTITUTIONS COVERED`}
      tight
    >
      {items.map((n) => (
        <a
          key={n.news_id}
          href={n.url}
          target="_blank"
          rel="noreferrer"
          className="block cursor-pointer border-b border-border px-3 py-2.5 transition-colors hover:bg-panel-2"
        >
          <div className="mb-1 flex flex-wrap items-center gap-2 text-[10px] text-fg-faint">
            {n.institution_name && (
              <Pill tone="cyan">{n.institution_name}</Pill>
            )}
            {n.publisher && <span>· {n.publisher}</span>}
            <span>· {relativeTime(n.published_at ?? n.fetched_at)}</span>
            {n.sentiment_score !== null && n.sentiment_score !== undefined && (
              <span className="ml-auto">
                <Pill tone={sentimentTone(n.sentiment_score)}>
                  sent {fmtSigned(n.sentiment_score, 2)}
                </Pill>
              </span>
            )}
          </div>
          <div className="font-serif text-[13px] leading-snug">{n.headline}</div>
        </a>
      ))}
      <div className="px-3 py-2 text-[10px] text-fg-faint">
        News is fetched per-institution via Google News RSS (e.g.{" "}
        <code>&quot;Pershing Square OR Bill Ackman&quot;</code>). The same Holdings
        tab shows the positions; this panel surfaces what those holders are
        saying in public.
      </div>
    </Panel>
  );
}
