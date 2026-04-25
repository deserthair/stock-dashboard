import type { UniverseRow } from "@/lib/types";
import { AnnotationBadge } from "@/components/ui/AnnotationBadge";
import { Panel } from "@/components/ui/Panel";
import { Pill, hypothesisTone } from "@/components/ui/Pill";
import { Tooltip } from "@/components/ui/Tooltip";
import {
  directionClass,
  fmtErLabel,
  fmtPct,
  fmtSigma,
  fmtSigned,
  fmtNum,
} from "@/lib/format";
import { annotate } from "@/lib/interpret";

export function UniverseMatrix({ rows }: { rows: UniverseRow[] }) {
  const snapshot = rows.map((r) => ({
    ticker: r.ticker,
    last: r.last_price,
    d1: r.change_1d_pct,
    d30: r.change_30d_pct,
    rs: r.rs_vs_xly,
    news7d: r.news_7d_count,
    sent7d: r.sentiment_7d,
    socialZ: r.social_vol_z,
    jobs30d: r.jobs_change_30d_pct,
    hypothesis: r.hypothesis_label,
    score: r.hypothesis_score,
  }));
  return (
    <Panel
      title="Universe Matrix"
      meta="LIVE · PRE-MKT"
      tight
      info={{
        title: "Universe Matrix",
        explanation:
          "The main scoreboard. One row per company we track, one column per signal we watch.\n\nColumn glossary:\n• Last — most recent share price.\n• Δ 1D / 5D / 30D — percent change over 1, 5, 30 days. Green = up, red = down.\n• RS vs XLY — 'relative strength' versus the consumer-discretionary ETF (XLY). Positive means the stock is beating that benchmark.\n• Next ER — the next earnings-report date.\n• News 7D — how many news articles in the last 7 days. An amber chip means well above normal volume.\n• Sent 7D — average sentiment of those articles (-1 negative, +1 positive).\n• Social Z — how unusual today's social-media chatter is, in standard deviations from normal.\n• Jobs Δ 30D — change in the company's open job postings over 30 days (a leading indicator of expansion or contraction).\n• Hypothesis — our model's overall lean (Bullish / Neutral / Bearish) plus a confidence score.",
        dataSnapshot: `Universe rows currently on screen (${rows.length}):\n${JSON.stringify(snapshot, null, 2)}`,
      }}
    >
      <table className="w-full text-[11px] tabular-nums">
        <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
          <tr>
            <Th>Ticker</Th>
            <Th tip="Most recent share price.">Last</Th>
            <Th align="right" tip="Percent change over 1 day. Green = up, red = down.">Δ 1D</Th>
            <Th align="right" tip="Percent change over 5 trading days.">Δ 5D</Th>
            <Th align="right" tip="Percent change over 30 trading days.">Δ 30D</Th>
            <Th
              align="right"
              tip="Relative strength vs XLY (the consumer-discretionary ETF). Positive = beating the sector benchmark."
            >
              RS vs XLY
            </Th>
            <Th tip="Date of the next earnings report.">Next ER</Th>
            <Th align="right" tip="Number of news articles in the last 7 days. Amber chip = unusually high volume.">News 7D</Th>
            <Th
              align="right"
              tip="Average tone of news articles in the last 7 days. Range -1 (negative) to +1 (positive)."
            >
              Sent 7D
            </Th>
            <Th
              align="right"
              tip="How unusual today's social-media chatter is, measured in standard deviations from baseline. Above ~2 = notable."
            >
              Social Z
            </Th>
            <Th
              align="right"
              tip="Change in the company's open job postings over the last 30 days. A leading indicator of expansion or contraction."
            >
              Jobs Δ 30D
            </Th>
            <Th
              align="right"
              tip="Our model's lean: Bullish / Neutral / Bearish, plus a confidence score between -1 and +1."
            >
              Hypothesis
            </Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.ticker} className="hover:bg-panel-2">
              <td className="border-b border-border px-3 py-1.5 text-accent">
                <strong className="font-semibold">{r.ticker}</strong>
              </td>
              <td className="border-b border-border px-3 py-1.5 text-fg">
                {fmtNum(r.last_price, 2)}
              </td>
              <Td align="right" className={directionClass(r.change_1d_pct)}>
                {fmtPct(r.change_1d_pct)}
              </Td>
              <Td align="right" className={directionClass(r.change_5d_pct)}>
                {fmtPct(r.change_5d_pct)}
              </Td>
              <Td align="right" className={directionClass(r.change_30d_pct)}>
                {fmtPct(r.change_30d_pct)}
                <AnnotationBadge ann={annotate("change_30d_pct", r.change_30d_pct)} />
              </Td>
              <Td align="right" className={directionClass(r.rs_vs_xly)}>
                {fmtSigned(r.rs_vs_xly, 1)}
                <AnnotationBadge ann={annotate("rs_vs_xly", r.rs_vs_xly)} />
              </Td>
              <Td>{fmtErLabel(r.next_er_date, r.next_er_time)}</Td>
              <Td align="right">
                <span className="mr-1.5">{r.news_7d_count ?? "—"}</span>
                {r.news_volume_pct_baseline && r.news_volume_pct_baseline > 50 && (
                  <Pill tone="amber">+{r.news_volume_pct_baseline.toFixed(0)}%</Pill>
                )}
              </Td>
              <Td align="right" className={directionClass(r.sentiment_7d)}>
                {fmtSigned(r.sentiment_7d, 2)}
                <AnnotationBadge ann={annotate("sentiment_7d", r.sentiment_7d)} />
              </Td>
              <Td align="right">
                {fmtSigma(r.social_vol_z)}
                <AnnotationBadge ann={annotate("social_z", r.social_vol_z)} />
              </Td>
              <Td align="right" className={directionClass(r.jobs_change_30d_pct)}>
                {fmtPct(r.jobs_change_30d_pct, { digits: 1 })}
                <AnnotationBadge ann={annotate("jobs_30d_pct", r.jobs_change_30d_pct)} />
              </Td>
              <Td align="right">
                {r.hypothesis_label ? (
                  <span className="inline-flex items-center">
                    <Pill tone={hypothesisTone(r.hypothesis_label)}>
                      {r.hypothesis_label}
                      {r.hypothesis_score !== null &&
                        ` ${fmtSigned(r.hypothesis_score, 2)}`}
                    </Pill>
                    <AnnotationBadge ann={annotate("hypothesis_score", r.hypothesis_score)} />
                  </span>
                ) : (
                  <Pill>—</Pill>
                )}
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

function Th({
  children,
  align,
  tip,
}: {
  children: React.ReactNode;
  align?: "right";
  tip?: string;
}) {
  return (
    <th
      className={`border-b border-border px-3 py-1.5 font-medium ${
        align === "right" ? "text-right" : "text-left"
      }`}
    >
      {tip ? (
        <Tooltip tip={tip}>
          <span className="cursor-help underline decoration-dotted decoration-fg-faint underline-offset-2">
            {children}
          </span>
        </Tooltip>
      ) : (
        children
      )}
    </th>
  );
}

function Td({
  children,
  align,
  className,
}: {
  children: React.ReactNode;
  align?: "right";
  className?: string;
}) {
  return (
    <td
      className={[
        "border-b border-border px-3 py-1.5",
        align === "right" ? "text-right" : "",
        className ?? "",
      ].join(" ")}
    >
      {children}
    </td>
  );
}
