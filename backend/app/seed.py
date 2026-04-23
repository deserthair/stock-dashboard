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

        # --- upcoming earnings
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

        s.commit()
    print("Seed complete.")


if __name__ == "__main__":
    run()
