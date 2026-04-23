"""Univariate correlation analysis over engineered features.

For every feature column, compute Pearson + Spearman vs the two targets:
  - eps_surprise_pct
  - eps_beat (binary 1/0; Pearson → point-biserial, Spearman → rank)

Report 95% bootstrap CI and Benjamini-Hochberg-adjusted p-values.
Writes results to `correlations` (one row per feature × target × method)."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from app.db import SessionLocal
from app.models import Correlation, Earnings, EarningsFeature

from ingest.source_run import source_run

FEATURE_COLS = [
    "return_30d",
    "volatility_30d",
    "volume_trend_30d",
    "news_sentiment_mean_30d",
    "news_volume_30d",
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
]

FEATURE_VERSION = "v0"


def _bh_adjust(p_values: list[float]) -> list[float]:
    n = len(p_values)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [0.0] * n
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        k = n - rank + 1  # original rank from smallest
        p = p_values[idx]
        adj = min(prev, p * n / k)
        adjusted[idx] = adj
        prev = adj
    return adjusted


def _bootstrap_ci(x, y, method: str, n_boot: int = 1000, rng=None) -> tuple[float, float]:
    import numpy as np
    from scipy import stats

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if rng is None:
        rng = np.random.default_rng(42)
    n = len(x)
    samples = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        xs, ys = x[idx], y[idx]
        if np.var(xs) == 0 or np.var(ys) == 0:
            continue
        if method == "pearson":
            samples.append(stats.pearsonr(xs, ys).statistic)
        else:
            samples.append(stats.spearmanr(xs, ys).statistic)
    if not samples:
        return (float("nan"), float("nan"))
    return (float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975)))


def _pairs(rows: list[tuple[float | None, float | None]]) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for x, y in rows:
        if x is None or y is None:
            continue
        xs.append(float(x))
        ys.append(float(y))
    return xs, ys


def run_once() -> int:
    with source_run("correlations") as run:
        try:
            from scipy import stats  # type: ignore
        except ImportError:
            run.skip = True
            return 0

        written = 0
        with SessionLocal() as s:
            rows = (
                s.query(EarningsFeature, Earnings)
                .join(Earnings, Earnings.earnings_id == EarningsFeature.earnings_id)
                .filter(EarningsFeature.feature_version == FEATURE_VERSION)
                .all()
            )
            if len(rows) < 6:
                run.skip = True
                return 0

            # Clear previous version before rewriting
            s.query(Correlation).filter_by(feature_version=FEATURE_VERSION).delete()

            results: list[tuple[str, str, str, int, float, float, float, float]] = []
            pvals: list[float] = []
            targets = {
                "eps_surprise_pct": lambda e: e.eps_surprise_pct,
                "eps_beat": lambda e: (
                    1.0 if e.eps_actual and e.eps_estimate and e.eps_actual > e.eps_estimate
                    else 0.0 if e.eps_actual and e.eps_estimate else None
                ),
            }

            for target_name, getter in targets.items():
                y_all = [getter(e) for _, e in rows]
                for col in FEATURE_COLS:
                    xs, ys = _pairs(
                        [(getattr(f, col), y) for (f, _), y in zip(rows, y_all)]
                    )
                    if len(xs) < 6 or not any(xs) or not any(ys):
                        continue
                    for method, fn in (
                        ("pearson", stats.pearsonr),
                        ("spearman", stats.spearmanr),
                    ):
                        try:
                            stat = fn(xs, ys)
                            coef = float(stat.statistic)
                            pval = float(stat.pvalue)
                        except (ValueError, ZeroDivisionError):
                            continue
                        lo, hi = _bootstrap_ci(xs, ys, method)
                        results.append(
                            (col, target_name, method, len(xs), coef, lo, hi, pval)
                        )
                        pvals.append(pval)

            adjusted = _bh_adjust(pvals)
            for (col, target, method, n, coef, lo, hi, pval), padj in zip(
                results, adjusted
            ):
                s.add(
                    Correlation(
                        feature_name=col,
                        target_name=target,
                        method=method,
                        n=n,
                        coefficient=coef,
                        ci_low=lo,
                        ci_high=hi,
                        p_value=pval,
                        p_adjusted=padj,
                        feature_version=FEATURE_VERSION,
                        computed_at=datetime.utcnow(),
                    )
                )
                written += 1
            s.commit()

        run.rows_fetched = written
        return written


if __name__ == "__main__":
    run_once()
