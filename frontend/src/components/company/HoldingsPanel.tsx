import type { CompanyHoldingsOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { StatTile } from "@/components/ui/StatTile";
import { directionClass, fmtPct } from "@/lib/format";

function fmtShares(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(0)}k`;
  return v.toLocaleString();
}

function fmtValue(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  return `$${v.toFixed(0)}`;
}

const KIND_TONE: Record<string, "green" | "red" | "amber" | "cyan" | "default"> = {
  activist: "amber",
  hedge_fund: "cyan",
  index_fund: "default",
  institution: "default",
  insider: "default",
};

const TXN_TONE: Record<string, "green" | "red" | "amber" | "default"> = {
  buy: "green",
  sell: "red",
  option_exercise: "amber",
  rsu_vest: "default",
  gift: "default",
};

export function HoldingsPanel({ data }: { data: CompanyHoldingsOut }) {
  const flow = data.insider_net_flow_90d;
  const hasHoldings = data.holdings.length > 0;

  return (
    <div className="space-y-3">
      <Panel
        title={`Institutional Holdings · ${data.ticker}`}
        meta={
          data.as_of_date
            ? `AS OF ${data.as_of_date} · TOP ${data.total_institutions}`
            : "NO DATA"
        }
      >
        {!hasHoldings ? (
          <p className="px-3 py-8 text-center text-[11px] text-fg-faint">
            No institutional-holder snapshots yet. Run{" "}
            <code>python -m ingest.sources.holdings</code> or re-seed.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <StatTile
                label="Total institutional %"
                value={
                  data.total_institutional_pct !== null && data.total_institutional_pct !== undefined
                    ? `${data.total_institutional_pct}%`
                    : "—"
                }
                delta={`Top ${data.total_institutions} holders`}
              />
              {(() => {
                const top = data.holdings[0];
                return (
                  <StatTile
                    label="Top holder"
                    value={top.institution.name.split(" ").slice(0, 2).join(" ")}
                    valueClass="text-accent"
                    delta={`${top.pct_of_outstanding ?? "—"}% of outstanding`}
                  />
                );
              })()}
              {(() => {
                const biggestBuyer = [...data.holdings]
                  .filter((h) => (h.shares_change ?? 0) > 0)
                  .sort((a, b) => (b.shares_change ?? 0) - (a.shares_change ?? 0))[0];
                if (!biggestBuyer)
                  return (
                    <StatTile
                      label="Biggest buyer QoQ"
                      value="—"
                      delta="no net adds in top holders"
                    />
                  );
                return (
                  <StatTile
                    label="Biggest buyer QoQ"
                    value={biggestBuyer.institution.name.split(" ").slice(0, 2).join(" ")}
                    valueClass="text-up"
                    delta={`+${fmtShares(biggestBuyer.shares_change)} (${biggestBuyer.pct_change}%)`}
                  />
                );
              })()}
              {(() => {
                const biggestSeller = [...data.holdings]
                  .filter((h) => (h.shares_change ?? 0) < 0)
                  .sort((a, b) => (a.shares_change ?? 0) - (b.shares_change ?? 0))[0];
                if (!biggestSeller)
                  return (
                    <StatTile
                      label="Biggest seller QoQ"
                      value="—"
                      delta="no net sells in top holders"
                    />
                  );
                return (
                  <StatTile
                    label="Biggest seller QoQ"
                    value={biggestSeller.institution.name.split(" ").slice(0, 2).join(" ")}
                    valueClass="text-down"
                    delta={`${fmtShares(biggestSeller.shares_change)} (${biggestSeller.pct_change}%)`}
                  />
                );
              })()}
            </div>

            <table className="mt-4 w-full text-[11px] tabular-nums">
              <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
                <tr>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Holder</th>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Kind</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">% Out</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">Shares</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">Value</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">Δ Shares QoQ</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">Δ %</th>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Links</th>
                </tr>
              </thead>
              <tbody>
                {data.holdings.map((h) => (
                  <tr key={h.institution.institution_id} className="hover:bg-panel-2">
                    <td className="border-b border-border px-3 py-1.5">{h.institution.name}</td>
                    <td className="border-b border-border px-3 py-1.5">
                      <Pill tone={KIND_TONE[h.institution.kind] ?? "default"}>
                        {h.institution.kind}
                      </Pill>
                    </td>
                    <td className="border-b border-border px-3 py-1.5 text-right">
                      {h.pct_of_outstanding !== null && h.pct_of_outstanding !== undefined
                        ? `${h.pct_of_outstanding}%`
                        : "—"}
                    </td>
                    <td className="border-b border-border px-3 py-1.5 text-right">
                      {fmtShares(h.shares)}
                    </td>
                    <td className="border-b border-border px-3 py-1.5 text-right">
                      {fmtValue(h.value_usd)}
                    </td>
                    <td
                      className={`border-b border-border px-3 py-1.5 text-right ${
                        (h.shares_change ?? 0) > 0
                          ? "text-up"
                          : (h.shares_change ?? 0) < 0
                          ? "text-down"
                          : "text-fg-dim"
                      }`}
                    >
                      {h.shares_change !== null && h.shares_change !== undefined
                        ? `${h.shares_change > 0 ? "+" : ""}${fmtShares(h.shares_change)}`
                        : "—"}
                    </td>
                    <td
                      className={`border-b border-border px-3 py-1.5 text-right ${directionClass(
                        h.pct_change,
                      )}`}
                    >
                      {h.pct_change !== null && h.pct_change !== undefined
                        ? fmtPct(h.pct_change, { digits: 1 })
                        : "—"}
                    </td>
                    <td className="border-b border-border px-3 py-1.5 text-[10px] text-fg-dim">
                      {h.institution.website && (
                        <a
                          href={h.institution.website}
                          target="_blank"
                          rel="noreferrer"
                          className="mr-2 hover:text-accent"
                        >
                          web
                        </a>
                      )}
                      {h.institution.x_handle && (
                        <a
                          href={`https://x.com/${h.institution.x_handle}`}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:text-accent"
                        >
                          @{h.institution.x_handle}
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Panel>

      <Panel
        title="Insider (Form 4) Activity · Last 90 days"
        meta={`${flow.transaction_count} TXNS`}
      >
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile
            label="Net shares"
            value={`${flow.net_shares >= 0 ? "+" : ""}${fmtShares(flow.net_shares)}`}
            valueClass={flow.net_shares > 0 ? "text-up" : flow.net_shares < 0 ? "text-down" : "text-fg-dim"}
          />
          <StatTile
            label="Net value"
            value={`${flow.net_value_usd >= 0 ? "+" : ""}${fmtValue(flow.net_value_usd)}`}
            valueClass={
              flow.net_value_usd > 0
                ? "text-up"
                : flow.net_value_usd < 0
                ? "text-down"
                : "text-fg-dim"
            }
          />
          <StatTile
            label="Buys"
            value={fmtShares(flow.buy_shares)}
            valueClass="text-up"
            delta={fmtValue(flow.buy_value_usd)}
          />
          <StatTile
            label="Sells"
            value={fmtShares(flow.sell_shares)}
            valueClass="text-down"
            delta={fmtValue(flow.sell_value_usd)}
          />
        </div>

        {data.insider_transactions_90d.length === 0 ? (
          <p className="mt-4 text-[11px] text-fg-faint">No Form 4 activity in the last 90 days.</p>
        ) : (
          <table className="mt-4 w-full text-[11px] tabular-nums">
            <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
              <tr>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Date</th>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Insider</th>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Type</th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">Shares</th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">Price</th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">Value</th>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Notes</th>
              </tr>
            </thead>
            <tbody>
              {data.insider_transactions_90d.map((t) => (
                <tr key={t.txn_id} className="hover:bg-panel-2">
                  <td className="border-b border-border px-3 py-1.5">{t.transaction_date}</td>
                  <td className="border-b border-border px-3 py-1.5">
                    <div className="text-fg">{t.insider_name}</div>
                    {t.insider_title && (
                      <div className="text-[10px] text-fg-faint">{t.insider_title}</div>
                    )}
                  </td>
                  <td className="border-b border-border px-3 py-1.5">
                    <Pill tone={TXN_TONE[t.transaction_type] ?? "default"}>
                      {t.transaction_type.replace("_", " ")}
                    </Pill>
                  </td>
                  <td className="border-b border-border px-3 py-1.5 text-right">
                    {fmtShares(t.shares)}
                  </td>
                  <td className="border-b border-border px-3 py-1.5 text-right">
                    {t.price !== null && t.price !== undefined ? `$${t.price.toFixed(2)}` : "—"}
                  </td>
                  <td className="border-b border-border px-3 py-1.5 text-right">
                    {fmtValue(t.value_usd)}
                  </td>
                  <td className="border-b border-border px-3 py-1.5 text-[10px] text-fg-dim">
                    {t.is_10b5_1 && (
                      <Pill tone="default">10b5-1 planned</Pill>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="mt-3 text-[10px] text-fg-faint">
          <strong>10b5-1</strong> sales are pre-scheduled via a trading plan
          filed months in advance — not a directional signal. An open-market{" "}
          <span className="text-up">buy</span> or a large unplanned{" "}
          <span className="text-down">sell</span> carries real information.
        </div>
      </Panel>
    </div>
  );
}
