"""Seed the database with the tracked universe and mockup-equivalent demo signals.

Idempotent: safe to run repeatedly. Real ingest workers in `ingest/` will
overwrite the price/earnings/event rows once they run against live sources.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta, timezone

from .db import Base, SessionLocal, engine
from .models import (
    Briefing,
    CommodityMeta,
    CommodityPrice,
    Company,
    CompanySignal,
    Earnings,
    EarningsFeature,
    EarningsPostmortem,
    Event,
    Fundamental,
    InsiderTransaction,
    Institution,
    InstitutionalHolding,
    MacroSeries,
    NewsItem,
    OptionsSnapshot,
    PriceDaily,
    TrendsObservation,
    TrendsQuery,
)

UNIVERSE = [
    {
        "ticker": "CMG",
        "name": "Chipotle Mexican Grill, Inc.",
        "segment": "Fast Casual",
        "market_cap_tier": "Large",
        "ir_url": "https://ir.chipotle.com",
        "careers_url": "https://jobs.chipotle.com",
        "x_handle": "ChipotleTweets",
        "ceo_name": "Scott Boatwright",
        "cik": "0001058090",
        "pr_page_url": "https://ir.chipotle.com/press-releases",
    },
    {
        "ticker": "SBUX",
        "name": "Starbucks Corporation",
        "segment": "Coffee",
        "market_cap_tier": "Mega",
        "ir_url": "https://investor.starbucks.com",
        "careers_url": "https://careers.starbucks.com",
        "x_handle": "Starbucks",
        "ceo_name": "Brian Niccol",
        "cik": "0000829224",
        "pr_page_url": "https://investor.starbucks.com/press-releases",
    },
    {
        "ticker": "MCD",
        "name": "McDonald's Corporation",
        "segment": "QSR",
        "market_cap_tier": "Mega",
        "ir_url": "https://corporate.mcdonalds.com/corpmcd/investors.html",
        "careers_url": "https://careers.mcdonalds.com",
        "x_handle": "McDonalds",
        "ceo_name": "Chris Kempczinski",
        "cik": "0000063908",
        "pr_page_url": "https://corporate.mcdonalds.com/corpmcd/our-stories/all-stories.html",
    },
    {
        "ticker": "CAVA",
        "name": "CAVA Group, Inc.",
        "segment": "Fast Casual",
        "market_cap_tier": "Mid",
        "ir_url": "https://investor.cava.com",
        "careers_url": "https://cava.com/careers",
        "x_handle": "cava",
        "ceo_name": "Brett Schulman",
        "cik": "0001639398",
        "pr_page_url": "https://investor.cava.com/news-releases",
    },
    {
        "ticker": "TXRH",
        "name": "Texas Roadhouse, Inc.",
        "segment": "Casual Dining",
        "market_cap_tier": "Large",
        "ir_url": "https://investor.texasroadhouse.com",
        "careers_url": "https://careers.texasroadhouse.com",
        "x_handle": "texasroadhouse",
        "ceo_name": "Jerry Morgan",
        "cik": "0001289460",
        "pr_page_url": "https://investor.texasroadhouse.com/press-releases",
    },
    {
        "ticker": "WING",
        "name": "Wingstop Inc.",
        "segment": "QSR",
        "market_cap_tier": "Mid",
        "ir_url": "https://ir.wingstop.com",
        "careers_url": "https://www.wingstop.com/careers",
        "x_handle": "wingstop",
        "ceo_name": "Michael Skipworth",
        "cik": "0001636222",
        "pr_page_url": "https://ir.wingstop.com/news-releases",
    },
    {
        "ticker": "DPZ",
        "name": "Domino's Pizza, Inc.",
        "segment": "Pizza / QSR",
        "market_cap_tier": "Large",
        "ir_url": "https://ir.dominos.com",
        "careers_url": "https://jobs.dominos.com",
        "x_handle": "dominos",
        "ceo_name": "Russell Weiner",
        "cik": "0001286681",
        "pr_page_url": "https://ir.dominos.com/news-releases",
    },
    {
        "ticker": "QSR",
        "name": "Restaurant Brands International Inc.",
        "segment": "QSR Conglomerate",
        "market_cap_tier": "Large",
        "ir_url": "https://www.rbi.com/investors",
        "careers_url": "https://careers.rbi.com",
        "x_handle": "RBItweets",
        "ceo_name": "Joshua Kobza",
        "cik": "0001618756",
        "pr_page_url": "https://www.rbi.com/English/news-and-events",
    },
]

BENCHMARKS = [
    {"ticker": "XLY", "name": "Consumer Discretionary Select Sector SPDR", "segment": "Sector ETF"},
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust",                   "segment": "Index ETF"},
]


SIGNALS = {
    "CMG":  dict(last_price=58.42,  change_1d_pct=1.84, change_5d_pct=3.12,  change_30d_pct=8.44,   rs_vs_xly=5.2,  next_er=("2026-04-23", "AMC"), news=47, news_pct=138, sent=0.22,  sv_z=2.1,  jobs=4.2,   hyp=("BEAT", 0.31)),
    "SBUX": dict(last_price=84.11,  change_1d_pct=-0.62,change_5d_pct=-1.80, change_30d_pct=-4.22,  rs_vs_xly=-3.1, next_er=("2026-04-29", "AMC"), news=22, news_pct=0,   sent=-0.08, sv_z=0.4,  jobs=8.1,   hyp=("MIXED", -0.05)),
    "MCD":  dict(last_price=291.58, change_1d_pct=0.34, change_5d_pct=1.22,  change_30d_pct=2.84,   rs_vs_xly=0.8,  next_er=("2026-05-01", "BMO"), news=31, news_pct=0,   sent=0.12,  sv_z=-0.2, jobs=0.4,   hyp=("MIXED", 0.08)),
    "CAVA": dict(last_price=112.80, change_1d_pct=3.12, change_5d_pct=7.41,  change_30d_pct=14.2,   rs_vs_xly=11.0, next_er=("2026-05-15", "AMC"), news=18, news_pct=0,   sent=0.41,  sv_z=1.8,  jobs=12.4,  hyp=("BEAT", 0.44)),
    "TXRH": dict(last_price=172.40, change_1d_pct=-1.08,change_5d_pct=-2.41, change_30d_pct=-6.11,  rs_vs_xly=-6.8, next_er=("2026-04-25", "AMC"), news=12, news_pct=0,   sent=-0.14, sv_z=-0.1, jobs=-1.2,  hyp=("MISS", -0.22)),
    "WING": dict(last_price=324.18, change_1d_pct=2.41, change_5d_pct=4.82,  change_30d_pct=6.31,   rs_vs_xly=3.2,  next_er=("2026-05-02", "BMO"), news=14, news_pct=0,   sent=0.18,  sv_z=0.7,  jobs=6.8,   hyp=("BEAT", 0.28)),
    "DPZ":  dict(last_price=452.60, change_1d_pct=0.08, change_5d_pct=0.22,  change_30d_pct=-1.42,  rs_vs_xly=-1.4, next_er=("2026-05-06", "BMO"), news=8,  news_pct=0,   sent=0.02,  sv_z=-0.3, jobs=1.1,   hyp=("NO SIGNAL", None)),
    "QSR":  dict(last_price=68.92,  change_1d_pct=-0.44,change_5d_pct=-0.91, change_30d_pct=-2.88,  rs_vs_xly=-2.2, next_er=("2026-05-08", "BMO"), news=11, news_pct=0,   sent=-0.04, sv_z=-0.4, jobs=3.2,   hyp=("MIXED", -0.11)),
}


EARNINGS_ESTIMATES = {
    "CMG":  dict(fiscal_period="Q1 2026", eps_estimate=0.52, revenue_estimate=2_910_000_000),
    "TXRH": dict(fiscal_period="Q1 2026", eps_estimate=1.84, revenue_estimate=1_420_000_000),
    "SBUX": dict(fiscal_period="Q2 2026", eps_estimate=0.81, revenue_estimate=9_120_000_000),
    "MCD":  dict(fiscal_period="Q1 2026", eps_estimate=2.72, revenue_estimate=6_180_000_000),
    "WING": dict(fiscal_period="Q1 2026", eps_estimate=0.94, revenue_estimate=162_000_000),
    "DPZ":  dict(fiscal_period="Q1 2026", eps_estimate=4.12, revenue_estimate=1_480_000_000),
    "QSR":  dict(fiscal_period="Q1 2026", eps_estimate=0.78, revenue_estimate=1_880_000_000),
    "CAVA": dict(fiscal_period="Q1 2026", eps_estimate=0.18, revenue_estimate=330_000_000),
}


# Historical earnings fixtures — one prior Q per ticker, enough to populate
# the hypothesis tracker and correlation scaffolding with something real to
# look at until backfill workers run against live data.
HISTORICAL_EARNINGS = [
    # (ticker, report_date, fiscal_period, tod, eps_est, eps_act, rev_est, rev_act, hyp_score)
    ("CMG",  "2026-01-29", "Q4 2025", "AMC", 0.45, 0.49, 2_780_000_000, 2_820_000_000,  0.28),
    ("CMG",  "2025-10-23", "Q3 2025", "AMC", 0.39, 0.41, 2_510_000_000, 2_550_000_000,  0.15),
    ("CMG",  "2025-07-24", "Q2 2025", "AMC", 0.42, 0.38, 2_650_000_000, 2_590_000_000, -0.10),
    ("SBUX", "2026-01-30", "Q1 2026", "AMC", 0.79, 0.71, 9_080_000_000, 8_860_000_000, -0.22),
    ("SBUX", "2025-10-29", "Q4 2025", "AMC", 0.83, 0.80, 9_240_000_000, 9_100_000_000, -0.08),
    ("MCD",  "2026-02-05", "Q4 2025", "BMO", 2.82, 2.80, 6_450_000_000, 6_430_000_000,  0.05),
    ("MCD",  "2025-10-28", "Q3 2025", "BMO", 3.18, 3.23, 6_820_000_000, 6_870_000_000,  0.18),
    ("CAVA", "2026-02-25", "Q4 2025", "AMC", 0.12, 0.15,   275_000_000,   286_000_000,  0.35),
    ("CAVA", "2025-11-07", "Q3 2025", "AMC", 0.14, 0.17,   261_000_000,   271_000_000,  0.40),
    ("TXRH", "2026-02-20", "Q4 2025", "AMC", 1.52, 1.48, 1_340_000_000, 1_322_000_000, -0.12),
    ("TXRH", "2025-10-30", "Q3 2025", "AMC", 1.45, 1.42, 1_280_000_000, 1_265_000_000, -0.18),
    ("WING", "2026-02-26", "Q4 2025", "BMO", 0.88, 0.96,   158_000_000,   164_500_000,  0.32),
    ("WING", "2025-11-06", "Q3 2025", "BMO", 0.91, 0.89,   152_000_000,   150_500_000,  0.22),
    ("DPZ",  "2026-02-27", "Q4 2025", "BMO", 4.35, 4.28, 1_520_000_000, 1_501_000_000,  0.02),
    ("DPZ",  "2025-10-09", "Q3 2025", "BMO", 4.10, 4.19, 1_470_000_000, 1_488_000_000,  0.11),
    ("QSR",  "2026-02-12", "Q4 2025", "BMO", 0.80, 0.76, 1_890_000_000, 1_860_000_000, -0.15),
    ("QSR",  "2025-11-05", "Q3 2025", "BMO", 0.85, 0.83, 1_950_000_000, 1_930_000_000, -0.05),
]


MACRO_ROWS = [
    ("PBEEFUSDM", "Live Cattle (PBEEF)",      8.4,  "+8.4%",  "up",   21),
    ("WPU0211",   "Chicken (WPU0211)",        -3.1, "-3.1%",  "down", 8),
    ("PWHEAMTUSDM","Wheat (PWHEAMT)",          2.1,  "+2.1%",  "up",   5),
    ("GASREGW",   "Retail Gas (GASREGW)",     -4.8, "-4.8%",  "down", 12),
    ("UMCSENT",   "Cons Sent (UMCSENT)",      1.6,  "+1.6",   "up",   4),
    ("CES7072200003","Food Wages (CES707)",    3.4,  "+3.4%",  "up",   9),
    ("UNRATE",    "Unemployment",             0.2,  "+0.2pt", "up",   3),
    ("DGS10",     "10Y Treasury",             0.24, "+24bp",  "up",   6),
]


def _seed_prices(s, by_ticker: dict[str, Company]) -> None:
    """Generate a deterministic 90-day walk per company aligned with the seeded
    change_30d_pct, so the chart terminates at ~last_price with a plausible path."""
    end = date(2026, 4, 22)
    for ticker, company in by_ticker.items():
        sig = SIGNALS.get(ticker)
        if sig is None:
            continue
        last = sig["last_price"]
        change_30d = sig["change_30d_pct"] / 100.0
        # start_price: solve so that last = start * (1 + change_30d) ~ 30d back,
        # but we plot 90d so synthesize a longer baseline
        change_90d = change_30d * 2.2  # slight amplification
        start = last / (1 + change_90d)
        rng = random.Random(hash(ticker) & 0xFFFFFFFF)

        price = start
        for i in range(91):
            d = end - timedelta(days=90 - i)
            # trend component + small daily noise
            trend = (last - start) / 90
            noise = rng.gauss(0, last * 0.008)
            price = max(1.0, price + trend + noise)
            # anchor the last observation to the seeded last_price
            if i == 90:
                price = last
            existing = s.get(PriceDaily, (company.company_id, d))
            if existing is None:
                existing = PriceDaily(company_id=company.company_id, trade_date=d)
                s.add(existing)
            existing.open = round(price * (1 + rng.gauss(0, 0.002)), 2)
            existing.high = round(price * (1 + abs(rng.gauss(0, 0.004))), 2)
            existing.low = round(price * (1 - abs(rng.gauss(0, 0.004))), 2)
            existing.close = round(price, 2)
            existing.adj_close = existing.close
            existing.volume = int(rng.uniform(500_000, 6_000_000))


def _seed_earnings_features(s, earnings_rows: list) -> None:
    """Synthesize plausible feature vectors per past earnings so the EDA
    endpoints (scatter / heatmap / regression) have something real to
    render in the sandbox. Overwritten the moment features.engineer.run_once
    is called against live data."""
    rng = random.Random(0xE4)
    for e in earnings_rows:
        # Skip upcoming (no outcome yet).
        if e.eps_actual is None or e.eps_estimate is None:
            continue
        surprise = (e.eps_actual - e.eps_estimate) / max(abs(e.eps_estimate), 1e-9)
        # Positively correlated features (news vol, sentiment, RS).
        news_vol = max(5, int(30 + surprise * 80 + rng.gauss(0, 8)))
        news_sent = max(-1, min(1, surprise * 1.4 + rng.gauss(0, 0.15)))
        social_sent = max(-1, min(1, surprise * 1.1 + rng.gauss(0, 0.2)))
        rs_30d = surprise * 18 + rng.gauss(0, 4)
        return_30d = surprise * 14 + rng.gauss(0, 3)
        # Weakly correlated or uncorrelated macro features.
        beef = rng.gauss(3, 4)
        chicken = rng.gauss(-1, 3)
        wheat = rng.gauss(0.5, 2)
        gas = rng.gauss(-1.5, 3)
        # Hiring: modest positive correlation with a beat
        jobs_total = surprise * 6 + rng.gauss(1.5, 3)
        jobs_corp = surprise * 10 + rng.gauss(0, 4)
        cons_sent = 74 + rng.gauss(0, 1.5)
        cons_sent_delta = rng.gauss(0.8, 0.8)
        unemp = rng.gauss(0.1, 0.2)

        existing = (
            s.query(EarningsFeature)
            .filter_by(earnings_id=e.earnings_id, feature_version="v0")
            .one_or_none()
        )
        feat = existing or EarningsFeature(
            earnings_id=e.earnings_id, feature_version="v0"
        )
        feat.return_30d = round(return_30d, 2)
        feat.volatility_30d = round(abs(rng.gauss(2.2, 0.6)), 3)
        feat.volume_trend_30d = round(rng.gauss(0, 15), 2)
        feat.rs_30d = round(rs_30d, 2)
        feat.news_sentiment_mean_30d = round(news_sent, 3)
        feat.news_sentiment_trend_30d = round(news_sent - rng.gauss(0, 0.1), 3)
        feat.news_volume_30d = news_vol
        feat.news_volume_z = round((news_vol - 30) / 10, 2)
        feat.social_sentiment_mean_30d = round(social_sent, 3)
        feat.social_volume_30d = max(0, int(rng.gauss(40, 12)))
        feat.jobs_count_change_90d = round(jobs_total, 2)
        feat.jobs_corporate_change_90d = round(jobs_corp, 2)
        feat.filings_8k_count_30d = rng.randint(0, 3)
        feat.filings_exec_change = False
        feat.beef_change_90d = round(beef, 2)
        feat.chicken_change_90d = round(chicken, 2)
        feat.wheat_change_90d = round(wheat, 2)
        feat.gas_change_90d = round(gas, 2)
        feat.cons_sentiment_level = round(cons_sent, 1)
        feat.cons_sentiment_change_90d = round(cons_sent_delta, 2)
        feat.unemployment_change_90d = round(unemp, 2)
        if existing is None:
            s.add(feat)


def _events_fixture(today: datetime, company_ids: dict[str, int]) -> list[Event]:
    rows = [
        ("CMG",  "filing",        0,  6, 14, "hi", "EDGAR",     "8-K filed · Item 7.01 Reg FD · investor day confirmed May 9"),
        ("SBUX", "news_spike",    0,  5, 52, "md", "GOOGLE RSS","News spike — Reuters on pricing strategy leak"),
        ("WING", "jobs_delta",    0,  3, 21, "md", "SCRAPE",    "Careers page +18 roles overnight (mostly Intl Dev)"),
        ("MCD",  "reddit",        0,  2,  8, "lo", "PRAW",      "Reddit thread r/stocks — value meal discussion (214 upvotes)"),
        ("TXRH", "social",        0,  1, 42, "lo", "EMAIL",     "IG post — new bourbon bar concept Austin"),
        ("CAVA", "social",        0,  0, 15, "md", "EMAIL",     "CEO X thread on unit economics (7 tweets)"),
        ("QSR",  "analyst",       1, 22, 40, "lo", "EMAIL",     "Seeking Alpha article — Popeyes intl rollout"),
        ("FRED", "macro_shock",   1, 21, 12, "hi", "FRED",      "Macro shock — cattle futures +2.1% daily move (>2σ)"),
        ("DPZ",  "analyst",       1, 19, 30, "lo", "EMAIL",     "Analyst note — BofA reiterates buy, PT raise"),
    ]
    out = []
    for ticker, etype, days_back, h, m, sev, source, desc in rows:
        ts = today.replace(hour=h, minute=m, second=0, microsecond=0) - timedelta(days=days_back)
        out.append(
            Event(
                company_id=company_ids.get(ticker),
                ticker_label=ticker,
                event_type=etype,
                event_at=ts,
                severity=sev,
                source=source,
                description=desc,
            )
        )
    return out


def _briefing_sections() -> list[dict]:
    return [
        {
            "heading": "Top Story",
            "body": (
                "<tag>CMG</tag> Chipotle reports after close tomorrow. News volume over the "
                "past 7 days runs <strong>+138% above 30-day baseline</strong>, driven largely "
                "by coverage of the new protein bowl menu tests in LA and Denver markets. "
                "Sentiment trend is <strong>mildly positive (+0.22)</strong> but analyst "
                "commentary on Reddit skews cautious, flagging traffic softness in earlier Q1 "
                "credit card data."
            ),
        },
        {
            "heading": "Macro Context",
            "body": (
                "Live cattle futures up <strong>+8.4% over 90 days</strong>, sustained pressure "
                "on beef-heavy concepts (<tag>TXRH</tag>, <tag>MCD</tag>, <tag>CMG</tag>). "
                "Chicken wholesale prices <strong>down 3.1%</strong> over same window — "
                "tailwind for <tag>WING</tag>, <tag>CAVA</tag>. Consumer sentiment ticked up "
                "1.2 pts to 74.8 in the latest UMich release but remains below 2024 avg."
            ),
        },
        {
            "heading": "Hypothesis Watch",
            "body": (
                "<tag>CMG</tag> Pre-earnings composite signal <strong>+0.31</strong> leaning "
                "bullish; 7 of 9 features align positive. Risk: news volume spike often "
                "precedes miss-and-sell when sentiment trend decelerates in final 5 days "
                "(current trajectory: flat-to-down). Track closely."
            ),
        },
        {
            "heading": "Flags",
            "body": (
                "<tag>SBUX</tag> Unusual job posting delta — <strong>corporate engineering "
                "roles +42% WoW</strong>, possible platform/ordering infra rebuild. Historical: "
                "+28% in 2023 preceded mobile order redesign. <tag>CAVA</tag> CEO posted first "
                "X thread in 3 weeks; themes around unit economics. Monitoring."
            ),
        },
    ]


def run() -> None:
    Base.metadata.create_all(engine)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = datetime(2026, 4, 22, 7, 0, 0)  # aligned with the mockup's "Apr 22, 2026 · Pre-Market"

    with SessionLocal() as s:
        # --- companies
        by_ticker: dict[str, Company] = {}
        for row in UNIVERSE:
            c = s.query(Company).filter_by(ticker=row["ticker"]).one_or_none()
            if c is None:
                c = Company(**row, is_benchmark=False)
                s.add(c)
            else:
                for k, v in row.items():
                    setattr(c, k, v)
                c.is_benchmark = False
            by_ticker[row["ticker"]] = c

        # --- benchmarks (XLY, SPY) — tracked via yfinance, hidden from the universe endpoint
        for row in BENCHMARKS:
            c = s.query(Company).filter_by(ticker=row["ticker"]).one_or_none()
            if c is None:
                c = Company(**row, is_benchmark=True)
                s.add(c)
            else:
                for k, v in row.items():
                    setattr(c, k, v)
                c.is_benchmark = True

        s.flush()

        # --- signals per company
        for ticker, sig in SIGNALS.items():
            company = by_ticker[ticker]
            er_date = date.fromisoformat(sig["next_er"][0])
            er_time = sig["next_er"][1]
            rec = s.get(CompanySignal, company.company_id) or CompanySignal(
                company_id=company.company_id
            )
            rec.last_price = sig["last_price"]
            rec.change_1d_pct = sig["change_1d_pct"]
            rec.change_5d_pct = sig["change_5d_pct"]
            rec.change_30d_pct = sig["change_30d_pct"]
            rec.rs_vs_xly = sig["rs_vs_xly"]
            rec.next_er_date = er_date
            rec.next_er_time = er_time
            rec.news_7d_count = sig["news"]
            rec.news_volume_pct_baseline = sig["news_pct"]
            rec.sentiment_7d = sig["sent"]
            rec.social_vol_z = sig["sv_z"]
            rec.jobs_change_30d_pct = sig["jobs"]
            rec.hypothesis_label = sig["hyp"][0]
            rec.hypothesis_score = sig["hyp"][1]
            s.merge(rec)

        # --- synthetic 90-day price history for each company
        # Gives the Company page chart something to render when yfinance can't reach
        # the internet. yfinance ingest overwrites these rows once it can fetch real data.
        _seed_prices(s, by_ticker)

        # --- upcoming + historical earnings (and their engineered feature vectors)
        s.query(EarningsFeature).delete()
        s.query(Earnings).delete()
        for ticker, sig in SIGNALS.items():
            if ticker not in EARNINGS_ESTIMATES:
                continue
            est = EARNINGS_ESTIMATES[ticker]
            s.add(
                Earnings(
                    company_id=by_ticker[ticker].company_id,
                    report_date=date.fromisoformat(sig["next_er"][0]),
                    fiscal_period=est["fiscal_period"],
                    time_of_day=sig["next_er"][1],
                    eps_estimate=est["eps_estimate"],
                    revenue_estimate=est["revenue_estimate"],
                    hypothesis_score=sig["hyp"][1],
                )
            )
        for (ticker, dt, period, tod, eps_est, eps_act, rev_est, rev_act, hyp) in HISTORICAL_EARNINGS:
            if ticker not in by_ticker:
                continue
            surprise = (
                round((eps_act - eps_est) / max(abs(eps_est), 1e-9) * 100, 2)
                if eps_est else None
            )
            s.add(
                Earnings(
                    company_id=by_ticker[ticker].company_id,
                    report_date=date.fromisoformat(dt),
                    fiscal_period=period,
                    time_of_day=tod,
                    eps_estimate=eps_est,
                    eps_actual=eps_act,
                    revenue_estimate=rev_est,
                    revenue_actual=rev_act,
                    eps_surprise_pct=surprise,
                    hypothesis_score=hyp,
                )
            )
        s.flush()
        _seed_earnings_features(s, s.query(Earnings).all())

        # --- events
        s.query(Event).delete()
        company_ids = {t: c.company_id for t, c in by_ticker.items()}
        for e in _events_fixture(today, company_ids):
            s.add(e)

        # --- macro
        s.query(MacroSeries).delete()
        for series_id, label, change_pct, change_label, direction, bar in MACRO_ROWS:
            s.add(
                MacroSeries(
                    series_id=series_id,
                    label=label,
                    latest_value=None,
                    change_90d_pct=change_pct,
                    change_label=change_label,
                    direction=direction,
                    bar_width_pct=bar,
                )
            )

        # --- briefing
        s.query(Briefing).delete()
        s.add(
            Briefing(
                generated_at=now,
                token_count=847,
                sections=_briefing_sections(),
            )
        )

        # --- demo postmortems (text seeded so UI has something without a Claude key)
        _seed_demo_postmortems(s, by_ticker)
        # --- demo Trends series so /api/trends renders without pytrends
        _seed_demo_trends(s, by_ticker)
        # --- demo quarterly fundamentals so /company/…/fundamentals renders without yfinance
        _seed_demo_fundamentals(s, by_ticker)
        # --- demo commodity futures + PPI series
        _seed_demo_commodities(s)
        # --- demo options snapshots per company
        _seed_demo_options(s, by_ticker)
        # --- demo institutional holdings + insider Form 4 transactions
        _seed_demo_holdings(s, by_ticker)
        s.commit()

    # Run a one-shot correlation pass now that features exist so the
    # ranked univariate table in /correlations has something out-of-the-box.
    try:
        from analysis.correlation import run_once as _corr

        _corr()
    except Exception as exc:  # noqa: BLE001 - seed is best-effort
        print(f"[seed] correlation pass failed: {exc}")
    print("Seed complete.")


DEMO_POSTMORTEMS = [
    # (ticker, fiscal_period, headline, narrative, tags)
    (
        "CMG",
        "Q4 2025",
        "CMG beat on elevated news volume but faced post-print profit-taking on beef costs",
        (
            "<p><tag>CMG</tag> delivered EPS of <strong>$0.49 vs $0.45 estimate</strong> "
            "(+8.9% surprise). News volume over the 30d prior ran <strong>46 items</strong>, "
            "well above the baseline, with sentiment holding <strong>+0.013</strong>. Lasso "
            "attribution pins almost the entire prediction to news_volume_30d (+18.5), "
            "consistent with protein-bowl menu coverage lifting the print.</p>"
            "<p>Market reaction was muted at <strong>+0.3% 1D</strong> despite the beat — "
            "beef cost pressure (live cattle +8.4% 90d) capped margin expectations heading "
            "into the next quarter, and options positioning suggested elevated expectations "
            "were already priced in.</p>"
        ),
        ["earnings_beat", "menu_innovation", "beef_costs", "priced_in"],
    ),
    (
        "SBUX",
        "Q1 2026",
        "SBUX missed on traffic softness; stock sold off on weak pricing commentary",
        (
            "<p><tag>SBUX</tag> reported EPS of <strong>$0.71 vs $0.79 estimate</strong> "
            "(−10.1% surprise). News sentiment in the prior 30 days ran decisively "
            "negative (<strong>−0.167</strong>) and a Reuters leak on pricing strategy "
            "five days before the print telegraphed the soft topline.</p>"
            "<p>Shares fell <strong>−10.1% 1D</strong>, the sharpest reaction in the "
            "universe, with the drawdown deepening through the week as analyst notes "
            "flagged declining transactions. Unusual corporate-engineering job posting "
            "spikes prior to the print now read as infra cost buildout timed against a "
            "weakening demand environment.</p>"
        ),
        ["earnings_miss", "traffic_soft", "pricing_leak", "guidance_cut"],
    ),
    (
        "CAVA",
        "Q4 2025",
        "CAVA beat decisively on new unit economics; stock rallied on guidance raise",
        (
            "<p><tag>CAVA</tag> posted EPS of <strong>$0.15 vs $0.12 estimate</strong> "
            "(+25% surprise) on revenue of $286M. The 30d news sentiment of "
            "<strong>+0.41</strong> and +1.8σ social volume reflected genuine menu and "
            "unit-economics traction, not just hype.</p>"
            "<p>The stock rallied <strong>+3.1% 1D</strong> with the move extending "
            "through the week. Chicken cost relief (−3.1% 90d) helped margins, and the "
            "CEO's first X thread in 3 weeks pre-print telegraphed confidence. "
            "Corporate-job postings up +12.4% also suggested management was leaning "
            "into growth investment rather than cost discipline.</p>"
        ),
        ["earnings_beat", "unit_economics", "menu_innovation", "chicken_tailwind"],
    ),
    (
        "TXRH",
        "Q4 2025",
        "TXRH missed narrowly; muted reaction as beef cost headwinds were well-telegraphed",
        (
            "<p><tag>TXRH</tag> came in at <strong>$1.48 vs $1.52 estimate</strong> "
            "(−2.6% surprise) — the weakest print in the beef-heavy casual-dining cohort. "
            "Negative news sentiment (−0.14) and relative weakness vs XLY (−6.8 over 30d) "
            "signaled the soft print in advance.</p>"
            "<p>Market reaction was a modest <strong>−1.1% 1D</strong>, well short of "
            "the SBUX-scale downside, because beef cost pressure (+8.4% 90d) was already "
            "in the cost structure everyone modeled. Jobs postings trended down, "
            "consistent with the chain tightening the belt rather than scaling.</p>"
        ),
        ["earnings_miss", "beef_costs", "casual_dining", "priced_in"],
    ),
]


def _seed_demo_postmortems(s, by_ticker: dict) -> None:
    s.query(EarningsPostmortem).delete()
    for ticker, period, headline, narrative, tags in DEMO_POSTMORTEMS:
        company = by_ticker.get(ticker)
        if company is None:
            continue
        earn = (
            s.query(Earnings)
            .filter_by(company_id=company.company_id, fiscal_period=period)
            .order_by(Earnings.report_date.desc())
            .first()
        )
        if earn is None:
            continue
        s.add(
            EarningsPostmortem(
                earnings_id=earn.earnings_id,
                generated_at=datetime.utcnow(),
                model="seed:demo",
                token_count=len(narrative) // 4,
                headline=headline,
                narrative=narrative,
                tags=tags,
            )
        )


DEMO_TRENDS_BASE = {
    # Per-ticker (query, label, category, ticker, trajectory) where trajectory
    # is a (slope, amplitude, phase_weeks) tuple for the 260-week synthetic walk.
    "CMG":  ("Chipotle",         "CMG brand",         "company", "CMG",  (0.15,  8, 0)),
    "SBUX": ("Starbucks",        "SBUX brand",        "company", "SBUX", (-0.03, 12, 4)),
    "MCD":  ("McDonalds",        "MCD brand",         "company", "MCD",  (0.05, 15, 2)),
    "CAVA": ("Cava Grill",       "CAVA brand",        "company", "CAVA", (0.30,  6, 0)),
    "TXRH": ("Texas Roadhouse",  "TXRH brand",        "company", "TXRH", (-0.02, 10, 3)),
    "WING": ("Wingstop",         "WING brand",        "company", "WING", (0.18,  9, 1)),
    "DPZ":  ("Dominos",          "DPZ brand",         "company", "DPZ",  (0.04,  7, 2)),
    "QSR":  ("Tim Hortons",      "QSR brand",         "company", "QSR",  (-0.01, 11, 5)),
}

DEMO_TRENDS_MENU = {
    "CMG":  ("chipotle protein bowl", "CMG menu", "menu", "CMG",  (0.42,  14, 0)),
    "SBUX": ("starbucks pumpkin spice","SBUX menu","menu","SBUX", (0.08,  35, 10)),  # strong seasonality
    "MCD":  ("big mac",               "MCD menu", "menu", "MCD",  (0.01,  5,  0)),
    "CAVA": ("cava bowl",             "CAVA menu","menu", "CAVA", (0.50,  10, 2)),
    "TXRH": ("texas roadhouse rolls", "TXRH menu","menu", "TXRH", (0.02,  6,  0)),
    "WING": ("wingstop flavors",      "WING menu","menu", "WING", (0.22,  8,  1)),
    "DPZ":  ("dominos delivery",      "DPZ menu", "menu", "DPZ",  (-0.05, 7,  0)),
    "QSR":  ("popeyes chicken sandwich","QSR menu","menu","QSR", (0.12,  20, 4)),
}

DEMO_TRENDS_SEGMENT = [
    ("fast casual restaurants", "Fast casual", "segment", None, (0.10, 4, 0)),
    ("QSR earnings",            "QSR earnings","segment", None, (0.04, 8, 2)),
    ("casual dining",           "Casual dining","segment",None, (-0.08, 5, 3)),
    ("fast food delivery",      "Fast food delivery","segment",None, (0.20, 6, 1)),
]

DEMO_TRENDS_MACRO = [
    ("restaurant inflation", "Restaurant inflation", "macro", None, (0.30,  7, 0)),
    ("fast food prices",     "Fast food prices",     "macro", None, (0.35, 10, 2)),
    ("dining out",           "Dining out",           "macro", None, (-0.04, 8, 5)),
    ("grocery vs restaurant","Grocery vs restaurant","macro", None, (0.18,  5, 3)),
]


def _seed_demo_trends(s, by_ticker: dict) -> None:
    """Synthesize 3 years of weekly Trends-style data per tracked query.

    Each query is a noisy linear trend plus a sinusoidal seasonality term,
    normalized to [0, 100]. Overwrites any prior demo data."""
    s.query(TrendsObservation).delete()
    s.query(TrendsQuery).delete()

    rng = random.Random(0xA1B)
    all_specs = (
        list(DEMO_TRENDS_BASE.values())
        + list(DEMO_TRENDS_MENU.values())
        + DEMO_TRENDS_SEGMENT
        + DEMO_TRENDS_MACRO
    )

    end = date(2026, 4, 20)  # most-recent Monday close to seed anchor
    n_weeks = 156  # 3 years
    for (query, label, category, ticker, traj) in all_specs:
        slope, amplitude, phase = traj
        q = TrendsQuery(
            query=query,
            label=label,
            category=category,
            ticker=ticker,
            last_fetched_at=datetime.utcnow(),
        )
        s.add(q)
        s.flush()

        base = 40.0
        raw = []
        for i in range(n_weeks):
            week_ts = end - timedelta(weeks=n_weeks - 1 - i)
            trend_component = slope * i
            seasonal = amplitude * math.sin((i + phase) / 8.0)
            noise = rng.gauss(0, 3)
            raw.append((week_ts, base + trend_component + seasonal + noise))

        # Scale to [0, 100] the way Trends does, using the window max.
        max_v = max(v for _, v in raw) or 1.0
        scaled = [(d, max(0.0, min(100.0, v / max_v * 100))) for d, v in raw]
        mean_v = sum(v for _, v in scaled) / len(scaled) if scaled else 1.0
        for d, v in scaled:
            s.add(
                TrendsObservation(
                    query_id=q.query_id,
                    obs_date=d,
                    value=round(v, 2),
                    ratio_to_mean=round(v / mean_v, 3) if mean_v else None,
                )
            )


# Per-ticker seed parameters for the synthetic quarterly fundamentals walk.
# (quarterly_revenue_latest, growth_rate_yoy, net_margin, fcf_margin,
#  debt_ratio, equity_base, div_per_share_quarterly).
FUNDAMENTALS_SEED = {
    # $-denominated, rough magnitudes loosely grounded in reality so the UI
    # numbers look sensible. Not a substitute for real yfinance data.
    "CMG":  dict(rev=2_800_000_000, grow=0.14, margin=0.13,  fcf_m=0.11, debt_r=0.20, eq=3_600_000_000, dps=0.00),
    "SBUX": dict(rev=9_100_000_000, grow=0.03, margin=0.10,  fcf_m=0.08, debt_r=1.50, eq=2_200_000_000, dps=0.57),
    "MCD":  dict(rev=6_400_000_000, grow=0.04, margin=0.33,  fcf_m=0.28, debt_r=2.20, eq=7_100_000_000, dps=1.67),
    "CAVA": dict(rev=275_000_000,   grow=0.31, margin=0.05,  fcf_m=0.04, debt_r=0.10, eq=760_000_000,   dps=0.00),
    "TXRH": dict(rev=1_330_000_000, grow=0.09, margin=0.09,  fcf_m=0.07, debt_r=0.02, eq=1_200_000_000, dps=0.61),
    "WING": dict(rev=155_000_000,   grow=0.26, margin=0.18,  fcf_m=0.22, debt_r=5.00, eq=150_000_000,   dps=0.23),
    "DPZ":  dict(rev=1_490_000_000, grow=0.05, margin=0.12,  fcf_m=0.14, debt_r=-2.50, eq=-200_000_000, dps=1.21),  # DPZ: negative equity from buybacks
    "QSR":  dict(rev=1_870_000_000, grow=0.06, margin=0.17,  fcf_m=0.20, debt_r=2.40, eq=3_100_000_000, dps=0.58),
}


def _seed_demo_fundamentals(s, by_ticker: dict) -> None:
    """Write ~16 quarters per ticker so the Financials tab has 3yr CAGR + TTM."""
    s.query(Fundamental).delete()
    tax_rate = 0.21
    rng = random.Random(0xF00D)

    # Use the most-recent CMG seeded earnings date as the anchor.
    latest_q = date(2026, 3, 31)  # Q1 2026 end

    for ticker, cfg in FUNDAMENTALS_SEED.items():
        company = by_ticker.get(ticker)
        if company is None:
            continue
        rev_base = cfg["rev"]
        growth = cfg["grow"]  # annual
        q_growth = (1 + growth) ** (1 / 4) - 1
        margin = cfg["margin"]
        fcf_margin = cfg["fcf_m"]
        debt_ratio = cfg["debt_r"]
        equity_base = cfg["eq"]
        dps = cfg["dps"]

        for q_back in range(16):
            # Walk backward in quarters from latest_q
            year = latest_q.year
            month = latest_q.month - 3 * q_back
            while month <= 0:
                month += 12
                year -= 1
            period_end = date(year, month, 28 if month == 2 else 30)
            qs_from_latest = q_back

            # Revenue scales down as we go back in time
            revenue = rev_base / ((1 + q_growth) ** qs_from_latest)
            revenue *= 1 + rng.gauss(0, 0.03)  # seasonality + noise
            net_income = revenue * (margin + rng.gauss(0, 0.01))
            shares = 140_000_000 if ticker == "MCD" else 28_000_000
            eps = net_income / shares
            fcf = revenue * (fcf_margin + rng.gauss(0, 0.01))
            ocf = fcf + revenue * 0.04  # impute capex ≈ 4% of rev
            capex = -revenue * 0.04
            equity = equity_base / ((1 + q_growth) ** qs_from_latest)
            total_debt = max(0, equity * abs(debt_ratio)) if debt_ratio != 0 else 0
            total_assets = max(equity + total_debt, revenue * 2.0)
            gross_profit = revenue * (margin + 0.15)
            op_income = revenue * (margin + 0.05)
            dividends_paid = -dps * shares
            dividends_per_share = dps

            invested_capital = total_debt + equity
            nopat = op_income * (1 - tax_rate)
            roic = nopat / invested_capital if invested_capital and invested_capital > 0 else None

            q = (period_end.month - 1) // 3 + 1
            s.add(
                Fundamental(
                    company_id=company.company_id,
                    period_end=period_end,
                    fiscal_period=f"Q{q} {period_end.year}",
                    revenue=round(revenue, 0),
                    gross_profit=round(gross_profit, 0),
                    operating_income=round(op_income, 0),
                    net_income=round(net_income, 0),
                    eps_diluted=round(eps, 2),
                    shares_diluted=shares,
                    total_assets=round(total_assets, 0),
                    total_debt=round(total_debt, 0),
                    total_equity=round(equity, 0),
                    operating_cash_flow=round(ocf, 0),
                    capex=round(capex, 0),
                    free_cash_flow=round(fcf, 0),
                    dividends_paid=round(dividends_paid, 0),
                    dividends_per_share=round(dividends_per_share, 4),
                    invested_capital=round(invested_capital, 0),
                    nopat=round(nopat, 0),
                    roic=round(roic, 4) if roic is not None else None,
                    source="seed:demo",
                )
            )


COMMODITY_DEMO = [
    # (symbol, label, category, unit, exposure, base_price, annual_drift_pct, amplitude, source, series_id)
    ("LE=F",  "Live Cattle",    "protein", "cents/lb", ["TXRH","MCD","CMG"],   185.0, 0.08, 6.0, "yfinance", None),
    ("GF=F",  "Feeder Cattle",  "protein", "cents/lb", ["TXRH","MCD"],         240.0, 0.10, 8.0, "yfinance", None),
    ("HE=F",  "Lean Hogs",      "protein", "cents/lb", ["DPZ","SBUX","QSR"],    85.0, -0.02, 10.0,"yfinance", None),
    ("ZC=F",  "Corn",           "grain",   "cents/bu", ["WING","CAVA","QSR"],  445.0, -0.01, 25.0,"yfinance", None),
    ("ZS=F",  "Soybeans",       "grain",   "cents/bu", ["WING","CAVA","QSR"], 1050.0, -0.03, 40.0,"yfinance", None),
    ("ZW=F",  "Wheat",          "grain",   "cents/bu", ["DPZ","SBUX"],         625.0,  0.02, 30.0,"yfinance", None),
    ("KC=F",  "Coffee",         "soft",    "cents/lb", ["SBUX"],               395.0,  0.22, 20.0,"yfinance", None),
    ("SB=F",  "Sugar",          "soft",    "cents/lb", ["SBUX","QSR"],          22.5, -0.05,  1.8,"yfinance", None),
    ("OJ=F",  "Orange Juice",   "soft",    "cents/lb", ["SBUX"],               365.0,  0.12, 30.0,"yfinance", None),
    ("DC=F",  "Class III Milk", "dairy",   "$/cwt",    ["SBUX","CMG"],          20.8,  0.03,  1.5,"yfinance", None),
    ("CL=F",  "WTI Crude Oil",  "energy",  "$/bbl",    ["ALL"],                 75.0, -0.08,  6.0,"yfinance", None),
    ("PPI_POULTRY",  "Poultry (PPI)",  "protein", "index", ["WING","CAVA","QSR"], 242.0, -0.04, 4.0, "fred", "WPU0211"),
    ("PPI_LETTUCE",  "Lettuce (PPI)",  "produce", "index", ["CMG","CAVA","TXRH"], 318.0,  0.15, 40.0,"fred", "WPU01830302"),
    ("PPI_TOMATOES", "Tomatoes (PPI)", "produce", "index", ["CMG","DPZ"],         285.0,  0.08, 22.0,"fred", "WPU01830306"),
]


def _seed_demo_commodities(s) -> None:
    s.query(CommodityPrice).delete()
    s.query(CommodityMeta).delete()
    rng = random.Random(0xC0)
    end = date(2026, 4, 20)
    n_days = 365 * 3  # ~3 years

    for (symbol, label, category, unit, exposure, base, drift, amp, source, series_id) in COMMODITY_DEMO:
        meta = CommodityMeta(
            symbol=symbol,
            label=label,
            category=category,
            unit=unit,
            exposure=exposure,
            source=source,
            series_id=series_id,
        )
        s.add(meta)
        daily_drift = (1 + drift) ** (1 / 365) - 1

        price = base / ((1 + drift) ** 3)  # 3y ago baseline
        for i in range(n_days):
            d = end - timedelta(days=n_days - 1 - i)
            # Skip weekends to mimic CME settlements (PPI still writes daily; fine)
            if source == "yfinance" and d.weekday() >= 5:
                continue
            seasonal = amp * math.sin((i / 60) + hash(symbol) % 7)
            noise = rng.gauss(0, base * 0.004)
            price = price * (1 + daily_drift) + (seasonal * 0.01 if symbol.endswith("=F") else 0) + noise
            price = max(price, base * 0.25)
            s.add(CommodityPrice(symbol=symbol, trade_date=d, close=round(price, 2), volume=None))


OPTIONS_DEMO = {
    # per-ticker (current IV, current P/C vol, trend_iv_pct_30d, trend_pc_pct_30d)
    "CMG":  (0.34, 0.82, 8.0, 12.0),     # elevated IV into earnings
    "SBUX": (0.31, 1.05, -3.0, 25.0),   # P/C ratio creeping up (bearish positioning)
    "MCD":  (0.21, 0.75, -1.0, -2.0),   # boring/stable
    "CAVA": (0.45, 0.62, 14.0, -5.0),   # very elevated IV
    "TXRH": (0.28, 0.95, 2.0, 18.0),
    "WING": (0.38, 0.68, 6.0, 4.0),
    "DPZ":  (0.23, 0.85, 0.0, 6.0),
    "QSR":  (0.19, 0.72, -2.0, 3.0),
}


def _seed_demo_options(s, by_ticker: dict) -> None:
    s.query(OptionsSnapshot).delete()
    rng = random.Random(0x0B7)
    end = date(2026, 4, 20)
    n_days = 90  # 3 months of daily snapshots
    # Approximate next monthly expiry ≈ 30d out
    expiry = end + timedelta(days=30)

    for ticker, (cur_iv, cur_pc, iv_trend, pc_trend) in OPTIONS_DEMO.items():
        company = by_ticker.get(ticker)
        if company is None:
            continue
        sig = s.get(CompanySignal, company.company_id)
        underlying = float(sig.last_price) if sig and sig.last_price else 100.0

        # Walk backward so latest day = target values, 30d-ago = target / (1+trend%)
        iv_30d_ago = cur_iv / (1 + iv_trend / 100)
        pc_30d_ago = cur_pc / (1 + pc_trend / 100)

        for i in range(n_days):
            d = end - timedelta(days=n_days - 1 - i)
            # Linear interpolate IV + PC with noise, anchored at day 60 (30d ago)
            if i >= n_days - 30:
                frac = (i - (n_days - 30)) / 30  # 0 → 1 over the last 30 days
                iv = iv_30d_ago + (cur_iv - iv_30d_ago) * frac
                pc = pc_30d_ago + (cur_pc - pc_30d_ago) * frac
            else:
                iv = iv_30d_ago * (1 + rng.gauss(0, 0.02))
                pc = pc_30d_ago * (1 + rng.gauss(0, 0.04))
            iv = max(0.05, iv + rng.gauss(0, 0.005))
            pc = max(0.2, pc + rng.gauss(0, 0.02))
            call_vol = int(rng.uniform(8000, 22000))
            put_vol = int(call_vol * pc)
            call_oi = int(rng.uniform(60000, 200000))
            put_oi = int(call_oi * pc * 0.9)
            s.add(
                OptionsSnapshot(
                    company_id=company.company_id,
                    obs_date=d,
                    expiry=expiry,
                    underlying_price=round(underlying, 2),
                    atm_iv=round(iv, 4),
                    total_call_volume=call_vol,
                    total_put_volume=put_vol,
                    total_call_oi=call_oi,
                    total_put_oi=put_oi,
                    put_call_volume_ratio=round(put_vol / call_vol, 3) if call_vol else None,
                    put_call_oi_ratio=round(put_oi / call_oi, 3) if call_oi else None,
                )
            )


INSTITUTIONS_SEED = [
    # (name, kind, website, x_handle, aum_usd, news_query)
    # news_query for activists/hedge funds includes the principal to boost
    # Google News relevance. None → worker falls back to `name`.
    ("Vanguard Group",              "index_fund",  "https://about.vanguard.com",       "vanguard_group",  8_600_000_000_000, "Vanguard Group"),
    ("BlackRock Inc.",              "index_fund",  "https://www.blackrock.com",        "BlackRock",      10_000_000_000_000, "BlackRock"),
    ("State Street Global Advisors","index_fund",  "https://www.ssga.com",             "StateStreet",     4_100_000_000_000, "State Street SSGA"),
    ("Fidelity Management & Research","institution","https://www.fidelity.com",        "Fidelity",        4_900_000_000_000, "Fidelity Management"),
    ("T. Rowe Price Associates",    "institution","https://www.troweprice.com",        "TRowePrice",      1_500_000_000_000, "T. Rowe Price"),
    ("Capital Research & Management","institution","https://www.capitalgroup.com",     "Capital_Group",   2_700_000_000_000, "Capital Group"),
    ("Geode Capital Management",    "index_fund",  "https://www.geodecapital.com",     None,              1_200_000_000_000, "Geode Capital"),
    ("Pershing Square Capital",     "activist",    "https://pershingsquareholdings.com","BillAckman",        18_000_000_000, "Pershing Square OR \"Bill Ackman\""),
    ("Berkshire Hathaway",          "hedge_fund",  "https://www.berkshirehathaway.com",None,                860_000_000_000, "Berkshire Hathaway OR \"Warren Buffett\""),
    ("Wellington Management",       "institution","https://www.wellington.com",        None,              1_400_000_000_000, "Wellington Management"),
    ("Norges Bank Investment Mgmt", "institution","https://www.nbim.no",               "NBIM",            1_700_000_000_000, "Norges Bank NBIM"),
    ("Morgan Stanley Investment Mgmt","institution","https://www.morganstanley.com",   None,                1_500_000_000_000, "Morgan Stanley Investment Management"),
]

# Per-ticker institutional holdings as of the seed anchor date.
# (institution_name, pct_of_outstanding, pct_change_QoQ)
# Approximates real ownership structures while staying internally consistent.
HOLDINGS_SEED = {
    "CMG":  [
        ("Vanguard Group",               8.9, 0.4),
        ("BlackRock Inc.",               6.5, -0.2),
        ("Pershing Square Capital",      4.8, 2.1),    # recent Ackman accumulation
        ("T. Rowe Price Associates",     4.1, 1.8),
        ("State Street Global Advisors", 3.7, 0.1),
        ("Fidelity Management & Research",3.4, -0.5),
        ("Geode Capital Management",     2.2, 0.3),
        ("Capital Research & Management",2.1, -1.2),
        ("Wellington Management",        1.8, 0.7),
    ],
    "SBUX": [
        ("Vanguard Group",               9.3, 0.2),
        ("BlackRock Inc.",               7.4, -0.4),
        ("State Street Global Advisors", 4.5, 0.1),
        ("Capital Research & Management",4.1, 0.8),
        ("Fidelity Management & Research",2.9, -0.7),
        ("Geode Capital Management",     2.3, 0.2),
        ("T. Rowe Price Associates",     2.0, -2.3),  # notable sell
        ("Morgan Stanley Investment Mgmt",1.7, -0.3),
    ],
    "MCD":  [
        ("Vanguard Group",               9.1, 0.3),
        ("BlackRock Inc.",               7.9, 0.1),
        ("State Street Global Advisors", 4.8, 0.0),
        ("Geode Capital Management",     2.4, 0.2),
        ("Capital Research & Management",2.0, -0.1),
        ("Fidelity Management & Research",1.9, 0.3),
        ("T. Rowe Price Associates",     1.5, 0.4),
        ("Norges Bank Investment Mgmt",  1.4, 0.2),
    ],
    "CAVA": [
        ("Vanguard Group",               6.2, 3.4),  # rapidly accumulating
        ("BlackRock Inc.",               5.1, 2.9),
        ("T. Rowe Price Associates",     4.0, 4.1),
        ("Capital Research & Management",3.4, 2.2),
        ("Fidelity Management & Research",2.8, 5.0),  # big buyer
        ("State Street Global Advisors", 2.1, 1.1),
        ("Geode Capital Management",     1.7, 1.5),
    ],
    "TXRH": [
        ("Vanguard Group",               10.1, 0.1),
        ("BlackRock Inc.",               8.2, -0.3),
        ("State Street Global Advisors", 4.3, 0.0),
        ("T. Rowe Price Associates",     3.7, -1.1),
        ("Fidelity Management & Research",2.8, -0.6),
        ("Geode Capital Management",     2.4, 0.2),
        ("Wellington Management",        1.9, 0.4),
    ],
    "WING": [
        ("Vanguard Group",               10.6, 0.5),
        ("BlackRock Inc.",                9.1, 0.2),
        ("T. Rowe Price Associates",      6.4, 1.3),
        ("State Street Global Advisors",  4.2, 0.0),
        ("Fidelity Management & Research",3.1, 0.8),
        ("Wellington Management",         2.3, 0.5),
        ("Geode Capital Management",      2.0, 0.3),
    ],
    "DPZ":  [
        ("Berkshire Hathaway",           8.8,  2.4),   # Buffett stake
        ("Vanguard Group",               8.4, -0.1),
        ("BlackRock Inc.",               6.8,  0.0),
        ("State Street Global Advisors", 4.1, -0.2),
        ("T. Rowe Price Associates",     3.2,  0.3),
        ("Fidelity Management & Research",2.6, -0.4),
        ("Capital Research & Management",2.0, -1.0),
    ],
    "QSR":  [
        ("Vanguard Group",               7.8,  0.2),
        ("BlackRock Inc.",               6.1, -0.1),
        ("Capital Research & Management",4.2,  0.9),
        ("State Street Global Advisors", 3.4,  0.0),
        ("T. Rowe Price Associates",     2.8, -0.4),
        ("Norges Bank Investment Mgmt",  2.0,  0.1),
        ("Geode Capital Management",     1.9,  0.2),
    ],
}

# Plausible Form 4 activity — mix of planned 10b5-1 sells, RSU vests, and the
# rarer open-market buys that actually signal. Over a 90-day window.
INSIDERS_SEED = {
    "CMG":  [
        ("Scott Boatwright",    "CEO",           "2026-04-01", "sell",   12_000,  58.00, True),
        ("Scott Boatwright",    "CEO",           "2026-02-10", "rsu_vest", 8_000, 62.00, False),
        ("Jack Hartung",        "CFO",           "2026-03-15", "sell",    5_500,  60.00, True),
        ("John Hartung",        "CFO",           "2026-01-28", "option_exercise", 4_000, 45.00, False),
        ("Laurie Schalow",      "Chief Corp Affairs","2026-02-05","sell",  1_800, 61.50, True),
    ],
    "SBUX": [
        ("Brian Niccol",        "CEO",           "2026-04-05", "sell",   40_000,  84.50, True),
        ("Rachel Ruggeri",      "CFO",           "2026-03-20", "sell",   14_000,  85.80, True),
        ("Rachel Ruggeri",      "CFO",           "2026-02-18", "rsu_vest",10_000,  85.00, False),
        ("Brady Brewer",        "CMO",           "2026-01-30", "sell",    6_500,  86.20, True),
        ("Sara Trilling",       "NA President",  "2026-02-25", "sell",    3_200,  85.60, True),
    ],
    "MCD":  [
        ("Chris Kempczinski",   "CEO",           "2026-03-25", "sell",    22_000, 290.00, True),
        ("Ian Borden",          "CFO",           "2026-02-12", "sell",     8_500, 288.40, True),
        ("Joe Erlinger",        "US President",  "2026-02-04", "sell",     4_200, 289.10, True),
        ("Ian Borden",          "CFO",           "2026-01-20", "rsu_vest", 15_000, 292.00, False),
    ],
    "CAVA": [
        ("Brett Schulman",      "CEO",           "2026-03-10", "sell",    18_000, 108.00, True),
        ("Ron Shaich",          "Director",      "2026-02-08", "buy",     50_000, 104.50, False),  # open market buy — signal
        ("Tricia Tolivar",      "CFO",           "2026-02-20", "sell",     6_000, 111.00, True),
        ("Brett Schulman",      "CEO",           "2026-01-15", "rsu_vest",20_000, 102.00, False),
    ],
    "TXRH": [
        ("Jerry Morgan",        "CEO",           "2026-03-18", "sell",    11_000, 175.00, True),
        ("Tonya Robinson",      "CFO",           "2026-02-14", "sell",     4_500, 174.00, True),
    ],
    "WING": [
        ("Michael Skipworth",   "CEO",           "2026-04-02", "sell",     6_500, 325.00, True),
        ("Alex Kaleida",        "CFO",           "2026-03-05", "sell",     2_800, 320.00, True),
        ("Michael Skipworth",   "CEO",           "2026-02-10", "rsu_vest", 4_000, 310.00, False),
    ],
    "DPZ":  [
        ("Russell Weiner",      "CEO",           "2026-03-12", "sell",     3_500, 455.00, True),
        ("Sandeep Reddy",       "CFO",           "2026-02-06", "rsu_vest", 2_500, 448.00, False),
    ],
    "QSR":  [
        ("Joshua Kobza",        "CEO",           "2026-03-08", "sell",    14_000,  69.00, True),
        ("Sami Siddiqui",       "CFO",           "2026-02-22", "sell",     5_500,  68.50, True),
    ],
}


def _seed_demo_holdings(s, by_ticker: dict) -> None:
    """Wipe + reseed institutions, institutional_holdings, insider_transactions.
    Produces two snapshot dates (current + prior quarter) so the QoQ delta
    fields have something to show on the Holdings tab."""
    s.query(InsiderTransaction).delete()
    s.query(InstitutionalHolding).delete()
    s.query(Institution).delete()
    s.flush()

    # Institutions
    inst_by_name: dict[str, Institution] = {}
    for (name, kind, website, x_handle, aum, news_query) in INSTITUTIONS_SEED:
        inst = Institution(
            name=name,
            kind=kind,
            website=website,
            x_handle=x_handle,
            aum_usd=float(aum),
            news_query=news_query,
        )
        s.add(inst)
        inst_by_name[name] = inst
    s.flush()

    # Two snapshot dates: current = 2026-04-20, prior = 2026-01-20
    current = date(2026, 4, 20)
    prior = date(2026, 1, 20)

    # Rough shares_outstanding estimates per ticker for magnitude scaling.
    shares_out = {
        "CMG":  27_000_000, "SBUX": 1_140_000_000, "MCD": 720_000_000,
        "CAVA": 117_000_000, "TXRH": 67_000_000, "WING": 29_000_000,
        "DPZ":  34_000_000, "QSR":  320_000_000,
    }

    for ticker, rows in HOLDINGS_SEED.items():
        company = by_ticker.get(ticker)
        if company is None:
            continue
        sh_out = shares_out.get(ticker, 100_000_000)
        sig = s.get(CompanySignal, company.company_id)
        price = float(sig.last_price) if sig and sig.last_price else 100.0

        for (inst_name, pct_now, pct_delta) in rows:
            inst = inst_by_name.get(inst_name)
            if inst is None:
                continue
            shares_now = int(sh_out * pct_now / 100)
            shares_prev = int(sh_out * (pct_now - pct_delta) / 100)
            shares_change = shares_now - shares_prev
            pct_change = (
                round((shares_now / shares_prev - 1) * 100, 2)
                if shares_prev > 0
                else None
            )

            s.add(
                InstitutionalHolding(
                    company_id=company.company_id,
                    institution_id=inst.institution_id,
                    as_of_date=prior,
                    shares=shares_prev,
                    value_usd=shares_prev * price * 0.92,  # prior price ≈ 92% of current
                    pct_of_outstanding=round(pct_now - pct_delta, 2),
                    source="seed:demo",
                )
            )
            s.add(
                InstitutionalHolding(
                    company_id=company.company_id,
                    institution_id=inst.institution_id,
                    as_of_date=current,
                    shares=shares_now,
                    value_usd=shares_now * price,
                    pct_of_outstanding=pct_now,
                    shares_change=shares_change,
                    pct_change=pct_change,
                    source="seed:demo",
                )
            )

    # Insider transactions
    import hashlib

    for ticker, txns in INSIDERS_SEED.items():
        company = by_ticker.get(ticker)
        if company is None:
            continue
        for (insider, title, dt, ttype, shares, price, is_planned) in txns:
            key = f"{ticker}|{insider}|{dt}|{shares}|{ttype}"
            acc = hashlib.sha256(key.encode()).hexdigest()[:32]
            is_officer = any(
                k in title.upper() for k in ("CEO", "CFO", "COO", "CMO", "PRESIDENT", "OFFICER")
            )
            is_director = "DIRECTOR" in title.upper()
            s.add(
                InsiderTransaction(
                    company_id=company.company_id,
                    accession_number=acc,
                    insider_name=insider,
                    insider_title=title,
                    insider_is_officer=is_officer,
                    insider_is_director=is_director,
                    transaction_date=date.fromisoformat(dt),
                    filed_at=datetime.utcnow(),
                    transaction_type=ttype,
                    shares=shares,
                    price=price,
                    value_usd=shares * price,
                    shares_owned_after=None,
                    is_10b5_1=is_planned and ttype == "sell",
                )
            )

    # Demo news items about each institution — survives yfinance outage
    _seed_demo_institution_news(s, inst_by_name)


INSTITUTION_NEWS_SEED = [
    # (institution_name, publisher, headline, days_ago, sentiment)
    ("Pershing Square Capital", "Reuters",
     "Bill Ackman raises Chipotle stake to 4.8%, highest in two years",
     2, 0.45),
    ("Pershing Square Capital", "Bloomberg",
     "Ackman says Chipotle's protein-bowl test validates menu-expansion thesis",
     5, 0.32),
    ("Pershing Square Capital", "CNBC",
     "Pershing Square files updated 13F showing CMG accumulation",
     8, 0.10),
    ("Berkshire Hathaway", "WSJ",
     "Berkshire adds to Domino's position; now 8.8% of shares outstanding",
     3, 0.28),
    ("Berkshire Hathaway", "Barron's",
     "Buffett's pizza bet: why Berkshire keeps buying DPZ",
     10, 0.22),
    ("BlackRock Inc.", "Reuters",
     "BlackRock Q1 flows: ETF inflows hit record $128B, passive share grows",
     4, 0.12),
    ("BlackRock Inc.", "Financial Times",
     "BlackRock trims discretionary-holdings on consumer-softness call",
     7, -0.15),
    ("Vanguard Group", "Bloomberg",
     "Vanguard's index funds drive ownership concentration in restaurant sector",
     6, 0.05),
    ("T. Rowe Price Associates", "Reuters",
     "T. Rowe Price slashes Starbucks position on traffic concerns",
     3, -0.38),
    ("T. Rowe Price Associates", "Barron's",
     "T. Rowe Price adds to Wingstop and Cava on unit-economics thesis",
     9, 0.25),
    ("Fidelity Management & Research", "CNBC",
     "Fidelity growth funds boost Cava Group stake by 42%",
     5, 0.41),
    ("State Street Global Advisors", "Reuters",
     "SSGA launches new consumer-discretionary ETF with restaurant tilt",
     11, 0.08),
    ("Capital Research & Management", "Bloomberg",
     "Capital Group's restaurant-sector analyst calls for beef-cost peak in Q3",
     6, 0.18),
    ("Norges Bank Investment Mgmt", "FT",
     "Norway's wealth fund disclosures show increased QSR exposure",
     14, 0.05),
    ("Wellington Management", "Reuters",
     "Wellington rotates into Texas Roadhouse on valuation compression",
     8, 0.16),
]


def _seed_demo_institution_news(s, inst_by_name: dict) -> None:
    """Write demo Google-News-style items tagged to institutions so the
    Holdings tab has something to render without live ingest."""
    import hashlib as _hashlib
    from datetime import timedelta as _td

    now = datetime.utcnow()
    for (inst_name, publisher, headline, days_ago, sentiment) in INSTITUTION_NEWS_SEED:
        inst = inst_by_name.get(inst_name)
        if inst is None:
            continue
        fetched = now - _td(days=days_ago)
        url = f"https://news.google.com/seed/{inst.institution_id}/{_hashlib.md5(headline.encode()).hexdigest()[:10]}"
        url_hash = _hashlib.sha256(url.encode()).hexdigest()
        existing = s.query(NewsItem).filter_by(url_hash=url_hash).one_or_none()
        if existing is not None:
            continue
        s.add(
            NewsItem(
                institution_id=inst.institution_id,
                company_id=None,
                source="google_rss",
                url=url,
                url_hash=url_hash,
                published_at=fetched,
                fetched_at=fetched,
                headline=headline,
                body=None,
                publisher=publisher,
                sentiment_score=sentiment,
                sentiment_confidence=0.7,
                relevance_score=0.8,
                topics=[],
            )
        )


if __name__ == "__main__":
    run()
