import type { UniverseRow } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { Pill, hypothesisTone } from "@/components/ui/Pill";
import {
  directionClass,
  fmtErLabel,
  fmtPct,
  fmtSigma,
  fmtSigned,
  fmtNum,
} from "@/lib/format";

export function UniverseMatrix({ rows }: { rows: UniverseRow[] }) {
  return (
    <Panel title="Universe Matrix" meta="LIVE · PRE-MKT" tight>
      <table className="w-full text-[11px] tabular-nums">
        <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
          <tr>
            <Th>Ticker</Th>
            <Th>Last</Th>
            <Th align="right">Δ 1D</Th>
            <Th align="right">Δ 5D</Th>
            <Th align="right">Δ 30D</Th>
            <Th align="right">RS vs XLY</Th>
            <Th>Next ER</Th>
            <Th align="right">News 7D</Th>
            <Th align="right">Sent 7D</Th>
            <Th align="right">Social Z</Th>
            <Th align="right">Jobs Δ 30D</Th>
            <Th align="right">Hypothesis</Th>
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
              </Td>
              <Td align="right" className={directionClass(r.rs_vs_xly)}>
                {fmtSigned(r.rs_vs_xly, 1)}
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
              </Td>
              <Td align="right">{fmtSigma(r.social_vol_z)}</Td>
              <Td align="right" className={directionClass(r.jobs_change_30d_pct)}>
                {fmtPct(r.jobs_change_30d_pct, { digits: 1 })}
              </Td>
              <Td align="right">
                {r.hypothesis_label ? (
                  <Pill tone={hypothesisTone(r.hypothesis_label)}>
                    {r.hypothesis_label}
                    {r.hypothesis_score !== null &&
                      ` ${fmtSigned(r.hypothesis_score, 2)}`}
                  </Pill>
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
}: {
  children: React.ReactNode;
  align?: "right";
}) {
  return (
    <th
      className={`border-b border-border px-3 py-1.5 font-medium ${
        align === "right" ? "text-right" : "text-left"
      }`}
    >
      {children}
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
