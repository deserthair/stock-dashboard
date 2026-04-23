"""Shared helpers for the exploratory analysis endpoints.

Pulls engineered feature vectors joined to their companies / target labels,
and exposes a `FrameRow` shape the scatter / heatmap / regression routes
all consume uniformly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import Company, Earnings, EarningsFeature

# Numeric feature columns from features_earnings that are defensible to
# correlate / regress against. Keep stable between endpoints so the UI
# picker and the ranked correlations agree.
FEATURE_COLS: tuple[str, ...] = (
    "return_30d",
    "volatility_30d",
    "volume_trend_30d",
    "rs_30d",
    "news_sentiment_mean_30d",
    "news_sentiment_trend_30d",
    "news_volume_30d",
    "news_volume_z",
    "social_sentiment_mean_30d",
    "social_volume_30d",
    "jobs_count_change_90d",
    "jobs_corporate_change_90d",
    "filings_8k_count_30d",
    "beef_change_90d",
    "chicken_change_90d",
    "wheat_change_90d",
    "gas_change_90d",
    "cons_sentiment_level",
    "cons_sentiment_change_90d",
    "unemployment_change_90d",
)


TARGET_COLS: tuple[str, ...] = (
    "eps_surprise_pct",
    "eps_beat",
    "post_earnings_1d_return",
    "post_earnings_5d_return",
)


@dataclass
class FrameRow:
    ticker: str
    earnings_id: int
    report_date: str          # ISO string
    features: dict[str, float | None]
    targets: dict[str, float | None]


def _eps_beat(e: Earnings) -> float | None:
    if e.eps_actual is None or e.eps_estimate is None:
        return None
    return 1.0 if e.eps_actual > e.eps_estimate else 0.0


def load_frame(
    s: Session,
    feature_version: str = "v0",
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[FrameRow]:
    from analysis.outcomes import compute as compute_outcome

    q = (
        s.query(EarningsFeature, Earnings, Company)
        .join(Earnings, Earnings.earnings_id == EarningsFeature.earnings_id)
        .join(Company, Company.company_id == Earnings.company_id)
        .filter(EarningsFeature.feature_version == feature_version)
    )
    if start_date is not None:
        q = q.filter(Earnings.report_date >= start_date)
    if end_date is not None:
        q = q.filter(Earnings.report_date <= end_date)
    rows = q.all()
    out: list[FrameRow] = []
    for feat, earn, company in rows:
        oc = compute_outcome(s, earn)
        targets = {
            "eps_surprise_pct": earn.eps_surprise_pct,
            "eps_beat": _eps_beat(earn),
            "post_earnings_1d_return": oc.post_earnings_1d_return,
            "post_earnings_5d_return": oc.post_earnings_5d_return,
        }
        features = {col: getattr(feat, col) for col in FEATURE_COLS}
        out.append(
            FrameRow(
                ticker=company.ticker,
                earnings_id=earn.earnings_id,
                report_date=earn.report_date.isoformat(),
                features=features,
                targets=targets,
            )
        )
    return out


def paired(
    frame: Iterable[FrameRow], feature: str, target: str
) -> tuple[list[float], list[float], list[FrameRow]]:
    xs: list[float] = []
    ys: list[float] = []
    rows: list[FrameRow] = []
    for row in frame:
        fv = row.features.get(feature)
        tv = row.targets.get(target)
        if fv is None or tv is None:
            continue
        try:
            xs.append(float(fv))
            ys.append(float(tv))
            rows.append(row)
        except (TypeError, ValueError):
            continue
    return xs, ys, rows
