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
    Company,
    CompanySignal,
    Earnings,
    EarningsFeature,
    EarningsPostmortem,
    Event,
    MacroSeries,
    PriceDaily,
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


if __name__ == "__main__":
    run()
