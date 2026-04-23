"""Refresh the denormalized `company_signals` row from normalized data."""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta

from app.db import SessionLocal
from app.models import (
    Company,
    CompanySignal,
    JobsSnapshot,
    NewsItem,
    SocialPost,
)

from ingest.source_run import source_run


def run_once() -> int:
    with source_run("signals") as run:
        now = datetime.utcnow()
        since_7d = now - timedelta(days=7)
        since_30d = now - timedelta(days=30)
        since_90d = now - timedelta(days=90)
        rows = 0

        with SessionLocal() as s:
            for c in s.query(Company).all():
                news_7d = (
                    s.query(NewsItem)
                    .filter(
                        NewsItem.company_id == c.company_id,
                        NewsItem.fetched_at >= since_7d,
                    )
                    .all()
                )
                news_30d = (
                    s.query(NewsItem)
                    .filter(
                        NewsItem.company_id == c.company_id,
                        NewsItem.fetched_at >= since_30d,
                    )
                    .all()
                )
                sig = s.get(CompanySignal, c.company_id) or CompanySignal(
                    company_id=c.company_id
                )

                if news_7d:
                    sig.news_7d_count = len(news_7d)
                    sentiments = [n.sentiment_score for n in news_7d if n.sentiment_score is not None]
                    if sentiments:
                        sig.sentiment_7d = round(statistics.fmean(sentiments), 2)

                if news_30d:
                    baseline_per_day = len(news_30d) / 30.0 * 7.0
                    if baseline_per_day > 0 and sig.news_7d_count:
                        pct = (sig.news_7d_count / baseline_per_day - 1.0) * 100
                        sig.news_volume_pct_baseline = round(pct, 1)

                # Social volume Z-score: 7d count vs 30d daily std
                social_30d = (
                    s.query(SocialPost)
                    .filter(
                        SocialPost.company_id == c.company_id,
                        SocialPost.fetched_at >= since_30d,
                    )
                    .all()
                )
                if social_30d:
                    by_day: dict = {}
                    for sp in social_30d:
                        day = (sp.fetched_at or now).date()
                        by_day[day] = by_day.get(day, 0) + 1
                    if len(by_day) >= 5:
                        values = list(by_day.values())
                        mean = statistics.fmean(values)
                        stdev = statistics.pstdev(values) or 1.0
                        today_count = sum(
                            1
                            for sp in social_30d
                            if (sp.fetched_at or now) >= since_7d
                        ) / 7.0
                        sig.social_vol_z = round((today_count - mean) / stdev, 1)

                # Jobs change: latest vs ~30d prior snapshot
                js_latest = (
                    s.query(JobsSnapshot)
                    .filter(JobsSnapshot.company_id == c.company_id)
                    .order_by(JobsSnapshot.snapshot_date.desc())
                    .first()
                )
                js_past = (
                    s.query(JobsSnapshot)
                    .filter(
                        JobsSnapshot.company_id == c.company_id,
                        JobsSnapshot.snapshot_date <= since_30d.date(),
                    )
                    .order_by(JobsSnapshot.snapshot_date.desc())
                    .first()
                )
                if js_latest and js_past and js_past.total_count:
                    sig.jobs_change_30d_pct = round(
                        (js_latest.total_count / js_past.total_count - 1) * 100, 1
                    )

                sig.updated_at = now
                s.merge(sig)
                rows += 1

            s.commit()

        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
