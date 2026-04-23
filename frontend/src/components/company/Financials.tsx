import type { CompanyFundamentals } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { directionClass, fmtNum, fmtPct, fmtRevenue, fmtSigned } from "@/lib/format";

function fmtBillions(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toFixed(0)}`;
}

function toneFor(v: number | null | undefined): "green" | "red" | "amber" | "default" {
  if (v === null || v === undefined || Number.isNaN(v)) return "default";
  if (v > 15) return "green";
  if (v > 0) return "amber";
  return "red";
}

export function Financials({ data }: { data: CompanyFundamentals }) {
  const m = data.metrics;
  if (m.quarters_available === 0) {
    return (
      <Panel title="Financials" meta="YFINANCE" tight>
        <div className="px-3 py-8 text-center text-[11px] text-fg-faint">
          No fundamentals ingested yet for {data.ticker}. Run{" "}
          <code>python -m ingest.sources.fundamentals</code>.
        </div>
      </Panel>
    );
  }

  return (
    <div className="space-y-3">
      {/* Top-level quality snapshot */}
      <Panel
        title={`Quality · ${data.ticker}`}
        meta={`${m.quarters_available} quarters · ${m.years_of_history} yrs of history`}
      >
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Tile label="ROIC (TTM)"     value={fmtPct(m.roic_ttm_pct)}                  tone={toneFor(m.roic_ttm_pct)} />
          <Tile label="Revenue (TTM)"  value={fmtBillions(m.revenue_ttm)}              tone="default" />
          <Tile label="EPS (TTM)"      value={m.eps_ttm !== null ? `$${fmtNum(m.eps_ttm, 2)}` : "—"} tone="default" />
          <Tile label="FCF (TTM)"      value={fmtBillions(m.fcf_ttm)}                  tone="default" />
          <Tile label="Book Value"     value={fmtBillions(m.book_value)}               tone="default" />
          <Tile label="Dividend/Sh (TTM)" value={m.dividends_per_share_ttm ? `$${fmtNum(m.dividends_per_share_ttm, 2)}` : "—"} tone="default" />
          <Tile
            label="Dividend Yield"
            value={m.dividend_yield_pct !== null ? `${m.dividend_yield_pct.toFixed(2)}%` : "—"}
            tone={m.dividend_yield_pct && m.dividend_yield_pct > 0 ? "green" : "default"}
          />
          <Tile label="Invested Cap"   value={fmtBillions(data.quarterly.at(-1)?.invested_capital ?? null)} tone="default" />
        </div>
      </Panel>

      {/* Growth panel */}
      <Panel title="Growth Rates" meta="TTM vs prior TTM · 3-year CAGR" tight>
        <table className="w-full text-[11px] tabular-nums">
          <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
            <tr>
              <th className="border-b border-border px-3 py-1.5 text-left font-medium">Metric</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">YoY</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">3-yr CAGR</th>
            </tr>
          </thead>
          <tbody>
            <GrowthRow label="Sales (revenue)"     yoy={m.revenue_yoy_pct} cagr={m.revenue_cagr_3y_pct} />
            <GrowthRow label="EPS"                 yoy={m.eps_yoy_pct}     cagr={m.eps_cagr_3y_pct} />
            <GrowthRow label="Book value (equity)" yoy={m.equity_yoy_pct}  cagr={m.equity_cagr_3y_pct} />
            <GrowthRow label="Free cash flow"      yoy={m.fcf_yoy_pct}     cagr={m.fcf_cagr_3y_pct} />
            <GrowthRow label="Dividend per share"  yoy={m.dividend_yoy_pct} cagr={null} />
          </tbody>
        </table>
      </Panel>

      {/* Quarterly table */}
      <Panel title="Quarterly Fundamentals" meta="YFINANCE · NEWEST FIRST" tight>
        <div className="max-h-[360px] overflow-auto">
          <table className="w-full text-[11px] tabular-nums">
            <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
              <tr>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-left font-medium">Period</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Revenue</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Op Inc</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Net Inc</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">EPS</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">FCF</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Equity</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Debt</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">DPS</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">ROIC</th>
              </tr>
            </thead>
            <tbody>
              {[...data.quarterly].reverse().map((q) => (
                <tr key={q.period_end} className="hover:bg-panel-2">
                  <td className="border-b border-border px-3 py-1.5">
                    {q.fiscal_period ?? q.period_end}
                  </td>
                  <td className="border-b border-border px-3 py-1.5 text-right">{fmtBillions(q.revenue)}</td>
                  <td className="border-b border-border px-3 py-1.5 text-right">{fmtBillions(q.operating_income)}</td>
                  <td className="border-b border-border px-3 py-1.5 text-right">{fmtBillions(q.net_income)}</td>
                  <td className="border-b border-border px-3 py-1.5 text-right">
                    {q.eps_diluted !== null ? `$${fmtNum(q.eps_diluted, 2)}` : "—"}
                  </td>
                  <td className="border-b border-border px-3 py-1.5 text-right">{fmtBillions(q.free_cash_flow)}</td>
                  <td className="border-b border-border px-3 py-1.5 text-right">{fmtBillions(q.total_equity)}</td>
                  <td className="border-b border-border px-3 py-1.5 text-right">{fmtBillions(q.total_debt)}</td>
                  <td className="border-b border-border px-3 py-1.5 text-right">
                    {q.dividends_per_share !== null && q.dividends_per_share !== undefined
                      ? `$${q.dividends_per_share.toFixed(2)}`
                      : "—"}
                  </td>
                  <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(q.roic !== null && q.roic !== undefined ? q.roic * 100 : null)}`}>
                    {q.roic !== null && q.roic !== undefined ? `${(q.roic * 100).toFixed(1)}%` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function Tile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "green" | "red" | "amber" | "default";
}) {
  const color =
    tone === "green"
      ? "text-up"
      : tone === "red"
      ? "text-down"
      : tone === "amber"
      ? "text-amber"
      : "text-fg";
  return (
    <div className="border border-border bg-panel-2 p-3">
      <div className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">{label}</div>
      <div className={`mt-1 font-serif text-[20px] tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

function GrowthRow({
  label,
  yoy,
  cagr,
}: {
  label: string;
  yoy: number | null | undefined;
  cagr: number | null | undefined;
}) {
  return (
    <tr className="hover:bg-panel-2">
      <td className="border-b border-border px-3 py-1.5">{label}</td>
      <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(yoy)}`}>
        {yoy !== null && yoy !== undefined ? fmtPct(yoy, { digits: 2 }) : "—"}
      </td>
      <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(cagr)}`}>
        {cagr !== null && cagr !== undefined ? fmtPct(cagr, { digits: 2 }) : "—"}
      </td>
    </tr>
  );
}
