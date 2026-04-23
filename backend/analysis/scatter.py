"""Scatter-point materialization for the correlation lab.

Returns every (feature_value, target_value) pair for a chosen feature/target,
plus a fitted least-squares regression line with bootstrapped 95% CI band
and Pearson/Spearman coefficients.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from .frame import load_frame, paired


@dataclass
class ScatterPoint:
    ticker: str
    earnings_id: int
    report_date: str
    x: float
    y: float


@dataclass
class RegressionLine:
    slope: float
    intercept: float
    r_squared: float
    n: int
    x_min: float
    x_max: float
    pearson_r: float | None
    pearson_p: float | None
    spearman_r: float | None
    spearman_p: float | None
    ci_low_at_min: float | None
    ci_high_at_min: float | None
    ci_low_at_max: float | None
    ci_high_at_max: float | None


def build(
    s: Session, feature: str, target: str, n_boot: int = 500
) -> tuple[list[ScatterPoint], RegressionLine | None]:
    import numpy as np
    from scipy import stats

    frame = load_frame(s)
    xs, ys, rows = paired(frame, feature, target)
    points = [
        ScatterPoint(
            ticker=r.ticker,
            earnings_id=r.earnings_id,
            report_date=r.report_date,
            x=x,
            y=y,
        )
        for r, x, y in zip(rows, xs, ys)
    ]
    if len(xs) < 3 or np.std(xs) == 0:
        return points, None

    x_arr = np.asarray(xs, dtype=float)
    y_arr = np.asarray(ys, dtype=float)
    slope, intercept = np.polyfit(x_arr, y_arr, 1)
    y_pred = slope * x_arr + intercept
    ss_res = float(np.sum((y_arr - y_pred) ** 2))
    ss_tot = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    try:
        pr = stats.pearsonr(x_arr, y_arr)
        pearson_r, pearson_p = float(pr.statistic), float(pr.pvalue)
    except Exception:
        pearson_r = pearson_p = None
    try:
        sr = stats.spearmanr(x_arr, y_arr)
        spearman_r, spearman_p = float(sr.statistic), float(sr.pvalue)
    except Exception:
        spearman_r = spearman_p = None

    # Bootstrap CI band for the slope line at the chart extremes.
    rng = np.random.default_rng(42)
    x_min, x_max = float(x_arr.min()), float(x_arr.max())
    preds_min: list[float] = []
    preds_max: list[float] = []
    n = len(xs)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        xb, yb = x_arr[idx], y_arr[idx]
        if np.std(xb) == 0:
            continue
        sb, ib = np.polyfit(xb, yb, 1)
        preds_min.append(sb * x_min + ib)
        preds_max.append(sb * x_max + ib)
    ci_low_min = ci_high_min = ci_low_max = ci_high_max = None
    if preds_min:
        ci_low_min = float(np.quantile(preds_min, 0.025))
        ci_high_min = float(np.quantile(preds_min, 0.975))
        ci_low_max = float(np.quantile(preds_max, 0.025))
        ci_high_max = float(np.quantile(preds_max, 0.975))

    line = RegressionLine(
        slope=float(slope),
        intercept=float(intercept),
        r_squared=float(r2),
        n=n,
        x_min=x_min,
        x_max=x_max,
        pearson_r=pearson_r,
        pearson_p=pearson_p,
        spearman_r=spearman_r,
        spearman_p=spearman_p,
        ci_low_at_min=ci_low_min,
        ci_high_at_min=ci_high_min,
        ci_low_at_max=ci_low_max,
        ci_high_at_max=ci_high_max,
    )
    return points, line
