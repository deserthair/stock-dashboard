import Link from "next/link";

import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { INFO } from "@/lib/info";

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
};

export default async function HoldersPage() {
  const [universe, holdings] = await Promise.all([
    api.universe(),
    api.universeHoldings().catch(() => null),
  ]);

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex flex-wrap items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Holders</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          Institutional positions · insider Form 4 flow
          {holdings?.as_of_date ? ` · as of ${holdings.as_of_date}` : ""}
        </span>
      </header>

      {!holdings || holdings.rows.length === 0 ? (
        <Panel title="No holdings data yet">
          <p className="text-[11px] text-fg-dim">
            Run <code>python -m ingest.sources.holdings</code> (needs yfinance)
            or re-seed for demo data.
          </p>
        </Panel>
      ) : (
        <div className="space-y-3">
          <Panel
            title="Per-company ownership concentration"
            tight
            info={INFO.holders_concentration}
          >
            <table className="w-full text-[11px] tabular-nums">
              <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
                <tr>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Ticker</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">Inst %</th>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Top holder</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">Top %</th>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Biggest buyer QoQ</th>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Biggest seller QoQ</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">Insider net 90d</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">Insider $ 90d</th>
                </tr>
              </thead>
              <tbody>
                {holdings.rows.map((r) => (
                  <tr key={r.ticker} className="hover:bg-panel-2">
                    <td className="border-b border-border px-3 py-1.5">
                      <Link href={`/company/${r.ticker}`} className="font-semibold text-accent">
                        {r.ticker}
                      </Link>
                    </td>
                    <td className="border-b border-border px-3 py-1.5 text-right">
                      {r.total_institutional_pct !== null && r.total_institutional_pct !== undefined
                        ? `${r.total_institutional_pct}%`
                        : "—"}
                    </td>
                    <td className="border-b border-border px-3 py-1.5">
                      {r.top_holder_name ?? "—"}
                    </td>
                    <td className="border-b border-border px-3 py-1.5 text-right">
                      {r.top_holder_pct !== null && r.top_holder_pct !== undefined
                        ? `${r.top_holder_pct}%`
                        : "—"}
                    </td>
                    <td className="border-b border-border px-3 py-1.5">
                      {r.biggest_buyer_name ? (
                        <>
                          <span className="text-up">{r.biggest_buyer_name}</span>{" "}
                          <span className="text-[10px] text-fg-dim">
                            +{fmtShares(r.biggest_buyer_delta_shares)}
                          </span>
                        </>
                      ) : (
                        <span className="text-fg-faint">—</span>
                      )}
                    </td>
                    <td className="border-b border-border px-3 py-1.5">
                      {r.biggest_seller_name ? (
                        <>
                          <span className="text-down">{r.biggest_seller_name}</span>{" "}
                          <span className="text-[10px] text-fg-dim">
                            {fmtShares(r.biggest_seller_delta_shares)}
                          </span>
                        </>
                      ) : (
                        <span className="text-fg-faint">—</span>
                      )}
                    </td>
                    <td
                      className={`border-b border-border px-3 py-1.5 text-right ${
                        r.insider_net_shares_90d > 0
                          ? "text-up"
                          : r.insider_net_shares_90d < 0
                          ? "text-down"
                          : "text-fg-dim"
                      }`}
                    >
                      {r.insider_net_shares_90d > 0 ? "+" : ""}
                      {fmtShares(r.insider_net_shares_90d)}
                    </td>
                    <td
                      className={`border-b border-border px-3 py-1.5 text-right ${
                        r.insider_net_value_90d > 0
                          ? "text-up"
                          : r.insider_net_value_90d < 0
                          ? "text-down"
                          : "text-fg-dim"
                      }`}
                    >
                      {r.insider_net_value_90d > 0 ? "+" : ""}
                      {fmtValue(r.insider_net_value_90d)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>

          <Panel
            title="Top institutions across the universe"
            meta={`${holdings.top_institutions.length} HOLDERS`}
            tight
            info={INFO.holders_top_institutions}
          >
            <table className="w-full text-[11px] tabular-nums">
              <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
                <tr>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Institution</th>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Kind</th>
                  <th className="border-b border-border px-3 py-1.5 text-right font-medium">AUM</th>
                  <th className="border-b border-border px-3 py-1.5 text-left font-medium">Socials</th>
                </tr>
              </thead>
              <tbody>
                {holdings.top_institutions.map((i) => (
                  <tr key={i.institution_id} className="hover:bg-panel-2">
                    <td className="border-b border-border px-3 py-1.5">
                      {i.website ? (
                        <a
                          href={i.website}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:text-accent"
                        >
                          {i.name}
                        </a>
                      ) : (
                        i.name
                      )}
                    </td>
                    <td className="border-b border-border px-3 py-1.5">
                      <Pill tone={KIND_TONE[i.kind] ?? "default"}>{i.kind}</Pill>
                    </td>
                    <td className="border-b border-border px-3 py-1.5 text-right text-fg-dim">
                      {i.aum_usd ? `$${(i.aum_usd / 1e12).toFixed(1)}T` : "—"}
                    </td>
                    <td className="border-b border-border px-3 py-1.5 text-[10px] text-fg-dim">
                      {i.x_handle && (
                        <a
                          href={`https://x.com/${i.x_handle}`}
                          target="_blank"
                          rel="noreferrer"
                          className="mr-2 hover:text-accent"
                        >
                          @{i.x_handle}
                        </a>
                      )}
                      {i.cik && <span className="text-fg-faint">CIK {i.cik}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>

          <div className="mt-3 text-[10px] text-fg-faint">
            Sources: yfinance (<code>Ticker.institutional_holders</code> +{" "}
            <code>Ticker.insider_transactions</code>), SEC Form 13F / Form 4
            where available. Buying / selling deltas are computed as the most
            recent snapshot vs the prior quarter's. 10b5-1 sales are flagged
            on the Company page Holdings tab — those are pre-scheduled sells
            with no directional signal.
          </div>
        </div>
      )}
    </Shell>
  );
}
