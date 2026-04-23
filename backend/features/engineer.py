"""Feature engineering: one row per earnings event in `features_earnings`.

Computes 30-day price/sentiment/news features and 90-day macro context,
strictly from data observable ≥24h before the earnings report (no leakage).
"""

from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta

from app.db import SessionLocal
from app.models import (
    Earnings,
    EarningsFeature,
    Filing,
    JobsSnapshot,
    MacroObservation,
    NewsItem,
    PriceDaily,
    SocialPost,
)

from ingest.source_run import source_run

FEATURE_VERSION = "v0"
CUTOFF_HOURS = 24  # features must be observable ≥ 24h before report


def _pct_change(points: list[tuple[date, float]], since: date) -> float | None:
    if len(points) < 2:
        return None
    points = sorted(points, key=lambda p: p[0])
    ref = next((v for d, v in points if d >= since), None) or points[0][1]
    if ref == 0:
        return None
    latest = points[-1][1]
    return (latest / ref - 1.0) * 100


def _compute_features(s, e: Earnings) -> EarningsFeature | None:
    cutoff = datetime.combine(e.report_date, datetime.min.time()) - timedelta(hours=CUTOFF_HOURS)

    prices = (
        s.query(PriceDaily)
        .filter(
            PriceDaily.company_id == e.company_id,
            PriceDaily.trade_date <= cutoff.date(),
            PriceDaily.trade_date >= (cutoff.date() - timedelta(days=60)),
        )
        .order_by(PriceDaily.trade_date)
        .all()
    )
    closes = [(p.trade_date, float(p.close)) for p in prices if p.close]
    volumes = [(p.trade_date, float(p.volume)) for p in prices if p.volume]

    return_30d = _pct_change(closes, cutoff.date() - timedelta(days=30))
    vol_z = None
    if len(closes) >= 30:
        recent = [v for _, v in closes[-30:]]
        daily_returns = [
            (recent[i] / recent[i - 1] - 1.0) for i in range(1, len(recent)) if recent[i - 1]
        ]
        if len(daily_returns) >= 5:
            vol_z = statistics.pstdev(daily_returns) * 100
    volume_trend_30d = None
    if len(volumes) >= 30:
        recent_v = [v for _, v in volumes[-30:]]
        early = statistics.fmean(recent_v[:10]) or 1.0
        late = statistics.fmean(recent_v[-10:])
        volume_trend_30d = (late / early - 1.0) * 100

    news = (
        s.query(NewsItem)
        .filter(
            NewsItem.company_id == e.company_id,
            NewsItem.fetched_at <= cutoff,
            NewsItem.fetched_at >= cutoff - timedelta(days=30),
        )
        .all()
    )
    sentiments = [n.sentiment_score for n in news if n.sentiment_score is not None]
    news_mean = round(statistics.fmean(sentiments), 3) if sentiments else None

    social = (
        s.query(SocialPost)
        .filter(
            SocialPost.company_id == e.company_id,
            SocialPost.fetched_at <= cutoff,
            SocialPost.fetched_at >= cutoff - timedelta(days=30),
        )
        .all()
    )
    social_sent = [p.sentiment_score for p in social if p.sentiment_score is not None]
    social_mean = round(statistics.fmean(social_sent), 3) if social_sent else None

    filings_8k = (
        s.query(Filing)
        .filter(
            Filing.company_id == e.company_id,
            Filing.filing_type == "8-K",
            Filing.filed_at <= cutoff,
            Filing.filed_at >= cutoff - timedelta(days=30),
        )
        .count()
    )
    filings_exec_change = bool(
        s.query(Filing)
        .filter(
            Filing.company_id == e.company_id,
            Filing.filing_type == "8-K",
            Filing.filed_at <= cutoff,
            Filing.filed_at >= cutoff - timedelta(days=60),
            Filing.item_numbers.is_not(None),
        )
        .all()
        and any(
            "5.02" in (f.item_numbers or [])
            for f in s.query(Filing)
            .filter(Filing.company_id == e.company_id, Filing.filed_at <= cutoff)
            .limit(40)
            .all()
        )
    )

    js_latest = (
        s.query(JobsSnapshot)
        .filter(
            JobsSnapshot.company_id == e.company_id,
            JobsSnapshot.snapshot_date <= cutoff.date(),
        )
        .order_by(JobsSnapshot.snapshot_date.desc())
        .first()
    )
    js_past = (
        s.query(JobsSnapshot)
        .filter(
            JobsSnapshot.company_id == e.company_id,
            JobsSnapshot.snapshot_date <= cutoff.date() - timedelta(days=90),
        )
        .order_by(JobsSnapshot.snapshot_date.desc())
        .first()
    )

    jobs_total = None
    jobs_corp = None
    if js_latest and js_past:
        if js_past.total_count:
            jobs_total = (js_latest.total_count / js_past.total_count - 1.0) * 100
        if js_past.corporate_count:
            jobs_corp = ((js_latest.corporate_count or 0) / js_past.corporate_count - 1.0) * 100

    def macro_change(series_id: str) -> float | None:
        obs = (
            s.query(MacroObservation)
            .filter(
                MacroObservation.series_id == series_id,
                MacroObservation.obs_date <= cutoff.date(),
            )
            .order_by(MacroObservation.obs_date)
            .all()
        )
        points = [(o.obs_date, float(o.value)) for o in obs if o.value is not None]
        return _pct_change(points, cutoff.date() - timedelta(days=90))

    def macro_latest(series_id: str) -> float | None:
        obs = (
            s.query(MacroObservation)
            .filter(
                MacroObservation.series_id == series_id,
                MacroObservation.obs_date <= cutoff.date(),
            )
            .order_by(MacroObservation.obs_date.desc())
            .first()
        )
        return float(obs.value) if obs and obs.value is not None else None

    feature = s.query(EarningsFeature).filter_by(
        earnings_id=e.earnings_id, feature_version=FEATURE_VERSION
    ).one_or_none() or EarningsFeature(
        earnings_id=e.earnings_id, feature_version=FEATURE_VERSION
    )
    feature.computed_at = datetime.utcnow()
    feature.return_30d = return_30d
    feature.volatility_30d = vol_z
    feature.volume_trend_30d = volume_trend_30d
    feature.news_sentiment_mean_30d = news_mean
    feature.news_volume_30d = len(news)
    feature.social_sentiment_mean_30d = social_mean
    feature.social_volume_30d = len(social)
    feature.filings_8k_count_30d = filings_8k
    feature.filings_exec_change = filings_exec_change
    feature.jobs_count_change_90d = jobs_total
    feature.jobs_corporate_change_90d = jobs_corp
    feature.beef_change_90d = macro_change("PBEEFUSDM")
    feature.chicken_change_90d = macro_change("WPU0211")
    feature.wheat_change_90d = macro_change("PWHEAMTUSDM")
    feature.gas_change_90d = macro_change("GASREGW")
    feature.cons_sentiment_level = macro_latest("UMCSENT")
    feature.cons_sentiment_change_90d = macro_change("UMCSENT")
    feature.unemployment_change_90d = macro_change("UNRATE")
    s.merge(feature)
    return feature


def run_once() -> int:
    with source_run("features") as run:
        rows = 0
        with SessionLocal() as s:
            earnings = (
                s.query(Earnings)
                .filter(Earnings.report_date <= date.today())
                .all()
            )
            for e in earnings:
                if _compute_features(s, e) is not None:
                    rows += 1
            s.commit()
        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
