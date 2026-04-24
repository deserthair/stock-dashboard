import { notFound } from "next/navigation";

import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import { Panel } from "@/components/ui/Panel";
import { Pill, hypothesisTone } from "@/components/ui/Pill";
import { EarningsHistory } from "@/components/company/EarningsHistory";
import { Financials } from "@/components/company/Financials";
import { FilingsList } from "@/components/company/FilingsList";
import { HolderNewsList } from "@/components/company/HolderNewsList";
import { HoldingsPanel } from "@/components/company/HoldingsPanel";
import { JobsList } from "@/components/company/JobsList";
import { NewsList } from "@/components/company/NewsList";
import { OptionsActivity } from "@/components/company/OptionsActivity";
import { PostmortemCard } from "@/components/company/PostmortemCard";
import { PriceChart } from "@/components/company/PriceChart";
import { SocialList } from "@/components/company/SocialList";
import { Tabs } from "@/components/company/Tabs";
import { TrendsCard } from "@/components/trends/TrendsSparkline";
import {
  directionClass,
  fmtErLabel,
  fmtNum,
  fmtPct,
  fmtSigma,
  fmtSigned,
} from "@/lib/format";
import { labelFor, rangeFromSearch } from "@/lib/dateRange";

export default async function CompanyPage({
  params,
  searchParams,
}: {
  params: { ticker: string };
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const range = rangeFromSearch(searchParams);
  let company;
  let universe;
  let news;
  let filings;
  let social;
  let jobs;
  let prices;
  let earnings;
  let fundamentals;
  let optionsSummary;
  let holdings;
  let holderNews;
  try {
    [company, universe, news, filings, social, jobs, prices, earnings, fundamentals, optionsSummary, holdings, holderNews] = await Promise.all([
      api.company(params.ticker),
      api.universe(),
      api.news(params.ticker, 30, range).catch(() => []),
      api.filings(params.ticker, 30, range).catch(() => []),
      api.social(params.ticker, 30, range).catch(() => []),
      api.jobs(params.ticker, 12, range).catch(() => []),
      api.companyPrices(params.ticker, 90).catch(() => ({ ticker: params.ticker.toUpperCase(), bars: [], markers: [] })),
      api.earningsAll({ ticker: params.ticker, past_only: true }, range).catch(() => []),
      api.companyFundamentals(params.ticker).catch(() => null),
      api.optionsSummary(params.ticker).catch(() => null),
      api.companyHoldings(params.ticker).catch(() => null),
      api.holderNewsFor(params.ticker, 40, range).catch(() => []),
    ]);
  } catch {
    notFound();
  }

  // Fetch postmortems for every past event (many will 404 — that's fine).
  const postmortems = (
    await Promise.all(
      earnings.map((e) =>
        api.postmortem(e.earnings_id).catch(() => null),
      ),
    )
  ).filter((x): x is NonNullable<typeof x> => x !== null);

  // Fetch Google Trends series for this ticker (brand + menu queries).
  const trendsQueries = await api
    .trendsQueries({ ticker: params.ticker })
    .catch(() => []);
  const trendsSeries = (
    await Promise.all(
      trendsQueries.map((q) =>
        api.trendsSeries(q.query_id, range).catch(() => null),
      ),
    )
  ).filter((x): x is NonNullable<typeof x> => x !== null);

  const s = company.signals;
  const up = (s.change_1d_pct ?? 0) >= 0;

  const overviewTab = (
    <div>
      <div className="mb-3 border border-border-hot border-l-[3px] border-l-accent bg-gradient-to-br from-[rgba(212,255,63,0.04)] via-transparent to-transparent px-4 py-3.5">
        <div className="mb-2 text-[10px] uppercase tracking-[0.15em] text-accent">
          ◆ Pre-Earnings Hypothesis
        </div>
        <div className="font-serif text-[14px] leading-[1.6] text-fg">
          Composite signal{" "}
          <strong className="text-accent">
            {fmtSigned(s.hypothesis_score, 2)}
          </strong>{" "}
          labels as{" "}
          <strong className="text-accent">
            {s.hypothesis_label ?? "—"}
          </strong>{" "}
          into the next print on{" "}
          {fmtErLabel(s.next_er_date, s.next_er_time)}. 30-day relative strength
          vs XLY: {fmtSigned(s.rs_vs_xly, 1)}; 7-day sentiment{" "}
          {fmtSigned(s.sentiment_7d, 2)}; news volume{" "}
          {s.news_volume_pct_baseline && s.news_volume_pct_baseline > 0
            ? `+${s.news_volume_pct_baseline.toFixed(0)}% above baseline`
            : "at baseline"}
          ; social vol z {fmtSigma(s.social_vol_z)}; jobs Δ 30D{" "}
          {fmtPct(s.jobs_change_30d_pct, { digits: 1 })}.
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <Pill tone={hypothesisTone(s.hypothesis_label)}>
            hypothesis {fmtSigned(s.hypothesis_score, 2)}
          </Pill>
          <Pill tone={(s.rs_vs_xly ?? 0) >= 0 ? "green" : "red"}>
            rs_30d {fmtSigned(s.rs_vs_xly, 1)}
          </Pill>
          <Pill tone={(s.sentiment_7d ?? 0) >= 0 ? "green" : "red"}>
            sent_7d {fmtSigned(s.sentiment_7d, 2)}
          </Pill>
          <Pill tone={(s.social_vol_z ?? 0) >= 1 ? "amber" : "default"}>
            social_z {fmtSigma(s.social_vol_z)}
          </Pill>
          <Pill tone={(s.jobs_change_30d_pct ?? 0) >= 0 ? "green" : "red"}>
            jobs {fmtPct(s.jobs_change_30d_pct, { digits: 1 })}
          </Pill>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[2fr_1fr]">
        <Panel title="Price · Events · 90D" meta={`${prices.bars.length} BARS · ${prices.markers.length} EVENTS`}>
          {prices.bars.length > 0 ? (
            <PriceChart bars={prices.bars} markers={prices.markers} />
          ) : (
            <div className="flex h-60 items-center justify-center border border-border bg-panel-2 text-fg-faint">
              <span className="text-[11px] uppercase tracking-[0.15em]">
                Waiting for yfinance · no prices yet
              </span>
            </div>
          )}
        </Panel>

        <Panel title="Feature Vector" meta="FEATURE_VERSION v0">
          <ul className="divide-y divide-border text-[11px]">
            <FeatureRow label="Δ 30D price" value={fmtPct(s.change_30d_pct)} pct={s.change_30d_pct} />
            <FeatureRow label="RS vs XLY" value={fmtSigned(s.rs_vs_xly, 1)} pct={s.rs_vs_xly} />
            <FeatureRow label="News 7D" value={`${s.news_7d_count ?? 0}`} pct={s.news_7d_count ?? 0} />
            <FeatureRow label="Sentiment 7D" value={fmtSigned(s.sentiment_7d, 2)} pct={s.sentiment_7d} />
            <FeatureRow label="Social vol Z" value={fmtSigma(s.social_vol_z)} pct={s.social_vol_z} />
            <FeatureRow label="Jobs Δ 30D" value={fmtPct(s.jobs_change_30d_pct, { digits: 1 })} pct={s.jobs_change_30d_pct} />
          </ul>
        </Panel>
      </div>

      {trendsSeries.length > 0 && (
        <div className="mt-3">
          <div className="mb-2 text-[10px] uppercase tracking-[0.15em] text-fg-faint">
            Google Trends · {company.ticker}
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {trendsSeries.map((t) => (
              <TrendsCard key={t.query.query_id} series={t} />
            ))}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <Shell universe={universe} activeTicker={company.ticker}>
      <div className="mb-3 flex items-center justify-between border-b border-border pb-2 text-[11px] text-fg-faint">
        <span className="uppercase tracking-[0.1em]">Tabs filter: {labelFor(range)}</span>
        <DateRangePicker />
      </div>

      <div className="mb-3 grid grid-cols-[auto_1fr_auto] items-center gap-6 border border-border bg-panel p-5">
        <div className="font-serif text-[48px] font-bold leading-none tracking-tight text-accent">
          {company.ticker}
        </div>
        <div>
          <div className="text-sm font-medium text-fg">{company.name}</div>
          <div className="mt-1 text-[11px] tracking-[0.05em] text-fg-faint">
            {[
              company.segment?.toUpperCase(),
              company.market_cap_tier && `${company.market_cap_tier.toUpperCase()} CAP`,
              `NEXT ER ${fmtErLabel(s.next_er_date, s.next_er_time)}`,
              company.ceo_name && `CEO ${company.ceo_name}`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </div>
        </div>
        <div className="text-right">
          <div
            className={`font-serif text-[32px] font-medium leading-none tracking-tight ${
              up ? "text-up" : "text-down"
            }`}
          >
            {fmtNum(s.last_price, 2)}
          </div>
          <div
            className={`font-mono text-[12px] ${up ? "text-up" : "text-down"}`}
          >
            {fmtPct(s.change_1d_pct)}
          </div>
        </div>
      </div>

      <Tabs
        tabs={[
          { id: "overview", label: "Overview", content: overviewTab },
          {
            id: "earnings",
            label: `Earnings History (${earnings.length})`,
            content: (
              <div className="space-y-3">
                {postmortems.length > 0 && (
                  <div className="space-y-3">
                    {postmortems.map((pm) => (
                      <PostmortemCard key={pm.earnings_id} pm={pm} />
                    ))}
                  </div>
                )}
                <EarningsHistory rows={earnings} />
              </div>
            ),
          },
          {
            id: "financials",
            label: `Financials${fundamentals ? ` (${fundamentals.metrics.quarters_available}q)` : ""}`,
            content: fundamentals ? (
              <Financials data={fundamentals} />
            ) : (
              <Panel title="Financials">
                <p className="text-[11px] text-fg-dim">
                  No fundamentals ingested yet. Run{" "}
                  <code>python -m ingest.sources.fundamentals</code>.
                </p>
              </Panel>
            ),
          },
          {
            id: "options",
            label: optionsSummary?.latest
              ? `Options (IV ${((optionsSummary.latest.atm_iv ?? 0) * 100).toFixed(0)}%)`
              : "Options",
            content: optionsSummary ? (
              <OptionsActivity data={optionsSummary} />
            ) : (
              <Panel title="Options Activity">
                <p className="text-[11px] text-fg-dim">
                  No snapshots yet. Run{" "}
                  <code>python -m ingest.sources.options</code>.
                </p>
              </Panel>
            ),
          },
          {
            id: "holdings",
            label: holdings
              ? `Holdings (${holdings.total_institutional_pct ?? "?"}% inst)`
              : "Holdings",
            content: holdings ? (
              <div className="space-y-3">
                <HoldingsPanel data={holdings} />
                <HolderNewsList items={holderNews} ticker={company.ticker} />
              </div>
            ) : (
              <Panel title="Holdings">
                <p className="text-[11px] text-fg-dim">
                  No institutional or insider data yet. Run{" "}
                  <code>python -m ingest.sources.holdings</code>.
                </p>
              </Panel>
            ),
          },
          { id: "news",     label: `News (${news.length})`,     content: <NewsList items={news} /> },
          { id: "social",   label: `Social (${social.length})`, content: <SocialList items={social} /> },
          { id: "filings",  label: `Filings (${filings.length})`, content: <FilingsList items={filings} /> },
          { id: "jobs",     label: `Jobs (${jobs.length})`,     content: <JobsList items={jobs} /> },
        ]}
      />
    </Shell>
  );
}

function FeatureRow({
  label,
  value,
  pct,
}: {
  label: string;
  value: string;
  pct: number | null | undefined;
}) {
  return (
    <li className="grid grid-cols-[1fr_auto] items-center gap-2 py-2">
      <span className="text-fg-dim">{label}</span>
      <span className={`tabular-nums ${directionClass(pct)}`}>{value}</span>
    </li>
  );
}
