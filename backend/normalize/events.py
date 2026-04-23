"""Event detection.

Scans the normalized sources (news, filings, reddit, macro observations)
and writes unified rows to the `events` table with severity and description.
Runs after each ingest pass.

Rules:
  - 8-K filing                                       → severity hi, type=filing
  - news day-count > 2σ above 30d mean per company   → severity md, type=news_spike
  - reddit post (>250 score OR top-of-batch)         → severity lo, type=reddit
  - macro observation day-change > 2σ                → severity hi, type=macro_shock
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func

from app.db import SessionLocal
from app.models import Company, Event, Filing, MacroObservation, NewsItem, RedditPost

from ingest.source_run import source_run


def _upsert_event(s, *, company_id, ticker, event_type, event_at, severity, source, description, source_ref):
    existing = (
        s.query(Event)
        .filter_by(event_type=event_type, source_ref=source_ref)
        .one_or_none()
    )
    if existing is not None:
        return False
    s.add(
        Event(
            company_id=company_id,
            ticker_label=ticker,
            event_type=event_type,
            event_at=event_at,
            severity=severity,
            source=source,
            description=description[:512],
            source_ref=source_ref,
        )
    )
    return True


def run_once() -> int:
    with source_run("event_detect") as run:
        rows = 0
        now = datetime.utcnow()
        since_30d = now - timedelta(days=30)
        since_7d = now - timedelta(days=7)
        with SessionLocal() as s:
            companies = s.query(Company).all()

            # Filings → events (high severity on 8-K, med otherwise)
            for f in (
                s.query(Filing).filter(Filing.filed_at >= since_30d).all()
            ):
                ticker = next((c.ticker for c in companies if c.company_id == f.company_id), "?")
                items_suffix = f" · Item {', '.join(f.item_numbers)}" if f.item_numbers else ""
                if _upsert_event(
                    s,
                    company_id=f.company_id,
                    ticker=ticker,
                    event_type="filing",
                    event_at=f.filed_at,
                    severity="hi" if f.filing_type == "8-K" else "md",
                    source="EDGAR",
                    description=f"{f.filing_type} filed{items_suffix}" + (f" · {f.title}" if f.title else ""),
                    source_ref=f.accession_number,
                ):
                    rows += 1

            # News spikes per company: daily counts vs 30d baseline
            for c in companies:
                daily_counts: dict[datetime.date, int] = defaultdict(int)
                for n in (
                    s.query(NewsItem)
                    .filter(
                        NewsItem.company_id == c.company_id,
                        NewsItem.published_at.isnot(None),
                        NewsItem.published_at >= since_30d,
                    )
                    .all()
                ):
                    daily_counts[n.published_at.date()] += 1
                if len(daily_counts) < 5:
                    continue
                values = list(daily_counts.values())
                mean = statistics.fmean(values)
                stdev = statistics.pstdev(values) or 1.0
                for d, count in daily_counts.items():
                    if count < mean + 2 * stdev or count < 5:
                        continue
                    src_ref = f"news_spike:{c.ticker}:{d.isoformat()}"
                    event_at = datetime.combine(d, datetime.min.time())
                    if _upsert_event(
                        s,
                        company_id=c.company_id,
                        ticker=c.ticker,
                        event_type="news_spike",
                        event_at=event_at,
                        severity="md",
                        source="GOOGLE RSS",
                        description=(
                            f"News spike — {count} items "
                            f"({(count - mean) / stdev:+.1f}σ vs 30d)"
                        ),
                        source_ref=src_ref,
                    ):
                        rows += 1

            # Reddit "top post" → event (low severity)
            top_posts = (
                s.query(RedditPost)
                .filter(RedditPost.created_at >= since_7d, RedditPost.score >= 250)
                .order_by(RedditPost.score.desc())
                .limit(25)
                .all()
            )
            for p in top_posts:
                ticker = next(
                    (c.ticker for c in companies if c.company_id == p.company_id), "?"
                )
                if _upsert_event(
                    s,
                    company_id=p.company_id,
                    ticker=ticker,
                    event_type="reddit",
                    event_at=p.created_at,
                    severity="lo",
                    source="REDDIT",
                    description=f"r/{p.subreddit} — {p.title} ({p.score} upvotes)",
                    source_ref=f"reddit:{p.post_id}",
                ):
                    rows += 1

            # Macro shocks — per-series day-over-day changes > 2σ
            series_ids = [
                r[0]
                for r in s.query(MacroObservation.series_id).distinct().all()
            ]
            for series_id in series_ids:
                obs = (
                    s.query(MacroObservation)
                    .filter(MacroObservation.series_id == series_id)
                    .order_by(MacroObservation.obs_date)
                    .all()
                )
                if len(obs) < 20:
                    continue
                changes: list[float] = []
                for prev, curr in zip(obs, obs[1:]):
                    if prev.value and curr.value:
                        changes.append((curr.value / prev.value - 1.0) * 100)
                if len(changes) < 20:
                    continue
                mean = statistics.fmean(changes)
                stdev = statistics.pstdev(changes) or 1.0
                for prev, curr in zip(obs, obs[1:]):
                    if not (prev.value and curr.value):
                        continue
                    chg = (curr.value / prev.value - 1.0) * 100
                    if abs(chg - mean) < 2 * stdev:
                        continue
                    if curr.obs_date < since_30d.date():
                        continue
                    src_ref = f"macro_shock:{series_id}:{curr.obs_date.isoformat()}"
                    if _upsert_event(
                        s,
                        company_id=None,
                        ticker="FRED",
                        event_type="macro_shock",
                        event_at=datetime.combine(curr.obs_date, datetime.min.time()),
                        severity="hi",
                        source="FRED",
                        description=f"{series_id} moved {chg:+.2f}% day-over-day ({(chg - mean)/stdev:+.1f}σ)",
                        source_ref=src_ref,
                    ):
                        rows += 1

            s.commit()

        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
