"""Backtest the simulation models against the historical record.

For every past earnings event with a confirmed post-earnings 1D return,
we train each candidate model using *only* data observable before the
event date (as-of cutoff) and collect (predicted, actual) pairs.

Models evaluated:

  gbm_1d              — GBM median 1-day return (no earnings jump)
  gbm_5d              — GBM median 5-day return
  merton_1d_earnings  — Merton 1-day with implied-move jump at T+1
  bootstrap           — median of the score-conditional bootstrap peer
                        reactions (peer pool is strictly events *before*
                        the target, so no leakage)
  hypothesis_linear   — a dumb baseline: 3.0 × hypothesis_score. If the
                        hypothesis actually predicts direction, this
                        model should have non-trivial correlation.

Aggregated metrics per model:

  n                      events evaluated
  correlation_r          Pearson r(predicted, actual)
  direction_accuracy     fraction where sign(predicted) == sign(actual)
  median_abs_error       median(|predicted - actual|) in % pts
  bias                   mean(predicted - actual)
  coverage_50            fraction where actual falls within predicted
                         25-75 band (for band-producing models)
  coverage_90            same for the 5-95 band

Models are ranked by correlation_r desc. Individual-event predictions
are returned too so the UI can plot a scatter (predicted vs actual) per
model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from analysis.outcomes import compute as compute_outcome
from app.models import (
    Company,
    CompanySignal,
    Earnings,
    OptionsSnapshot,
    PriceDaily,
)

from . import price_paths


MODELS = ("gbm_1d", "gbm_5d", "merton_1d_earnings", "bootstrap", "hypothesis_linear")


@dataclass
class BacktestPrediction:
    model: str
    earnings_id: int
    ticker: str
    report_date: date
    hypothesis_score: float | None
    predicted: float                   # predicted return in % points
    predicted_p25: float | None = None
    predicted_p75: float | None = None
    predicted_p05: float | None = None
    predicted_p95: float | None = None
    actual: float = 0.0                # actual 1D or 5D return in %
    inside_50: bool | None = None
    inside_90: bool | None = None


@dataclass
class BacktestModelSummary:
    model: str
    n: int
    correlation_r: float | None
    direction_accuracy: float | None
    median_abs_error: float | None
    bias: float | None
    coverage_50: float | None
    coverage_90: float | None


@dataclass
class BacktestReport:
    models: list[BacktestModelSummary]
    predictions: list[BacktestPrediction]
    n_events_evaluated: int
    n_events_candidates: int           # all past earnings with actual returns
    notes: list[str] = field(default_factory=list)


# --- helpers -----------------------------------------------------------


def _close_at(s: Session, company_id: int, target: date, direction: str = "ge") -> float | None:
    """`ge` = first close with trade_date ≥ target; `le` = last close ≤ target."""
    q = s.query(PriceDaily).filter(PriceDaily.company_id == company_id)
    if direction == "ge":
        row = q.filter(PriceDaily.trade_date >= target).order_by(PriceDaily.trade_date).first()
    else:
        row = q.filter(PriceDaily.trade_date <= target).order_by(PriceDaily.trade_date.desc()).first()
    return float(row.close) if row and row.close else None


def _actual_return(s: Session, company_id: int, event_date: date, horizon_days: int) -> float | None:
    pre = _close_at(s, company_id, event_date - timedelta(days=1), "le")
    post = _close_at(s, company_id, event_date + timedelta(days=horizon_days), "ge")
    if pre is None or post is None or pre == 0:
        return None
    return (post / pre - 1.0) * 100


def _as_of_for_event(event_date: date) -> date:
    """Cutoff = one trading day before the report — no lookahead."""
    return event_date - timedelta(days=1)


# --- per-model predictors ----------------------------------------------


def _predict_gbm(
    s: Session, ticker: str, company_id: int, event_date: date, horizon: int
) -> dict | None:
    as_of = _as_of_for_event(event_date)
    try:
        res = price_paths.simulate(
            s,
            ticker,
            horizon_days=horizon,
            n_paths=3000,
            model="gbm",
            fit_window_days=180,
            seed=42,
            as_of=as_of,
        )
    except ValueError:
        return None
    start = res.start_price
    last = res.bands[-1]
    p5 = (last.p05 / start - 1.0) * 100
    p25 = (last.p25 / start - 1.0) * 100
    p50 = (last.p50 / start - 1.0) * 100
    p75 = (last.p75 / start - 1.0) * 100
    p95 = (last.p95 / start - 1.0) * 100
    return {"p05": p5, "p25": p25, "p50": p50, "p75": p75, "p95": p95}


def _predict_merton(
    s: Session, ticker: str, company_id: int, event_date: date
) -> dict | None:
    """Merton model predicting 1-day return, where day 1 IS the earnings day.

    `horizon_days=2` so the earnings date (event_date, offset=1) falls
    inside the window and takes the jump."""
    as_of = _as_of_for_event(event_date)
    try:
        res = price_paths.simulate(
            s,
            ticker,
            horizon_days=2,
            n_paths=3000,
            model="merton",
            fit_window_days=180,
            seed=42,
            as_of=as_of,
        )
    except ValueError:
        return None
    start = res.start_price
    # Pick the quantiles at day 1 (the earnings day itself)
    b = res.bands[0]
    p5 = (b.p05 / start - 1.0) * 100
    p25 = (b.p25 / start - 1.0) * 100
    p50 = (b.p50 / start - 1.0) * 100
    p75 = (b.p75 / start - 1.0) * 100
    p95 = (b.p95 / start - 1.0) * 100
    return {"p05": p5, "p25": p25, "p50": p50, "p75": p75, "p95": p95}


def _predict_bootstrap(
    s: Session,
    score: float | None,
    peers: list[tuple[Earnings, float]],     # (earnings_row, actual_1d_return) already filtered
    tolerance: float = 0.15,
) -> dict | None:
    """Simple: median of same-sign peer 1D returns (or all peers if too few)."""
    if not peers:
        return None
    near = [
        r for e, r in peers
        if e.hypothesis_score is not None
        and score is not None
        and abs(e.hypothesis_score - score) <= tolerance
    ]
    chosen: list[float]
    if len(near) >= 6:
        chosen = near
    elif score is not None:
        sign = 1 if score > 0 else -1
        same = [
            r for e, r in peers
            if e.hypothesis_score is not None and (
                e.hypothesis_score > 0 if sign > 0 else e.hypothesis_score < 0
            )
        ]
        chosen = same if len(same) >= 6 else [r for _, r in peers]
    else:
        chosen = [r for _, r in peers]

    import numpy as np

    arr = np.asarray(chosen, dtype=float)
    return {
        "p05": float(np.quantile(arr, 0.05)),
        "p25": float(np.quantile(arr, 0.25)),
        "p50": float(np.median(arr)),
        "p75": float(np.quantile(arr, 0.75)),
        "p95": float(np.quantile(arr, 0.95)),
    }


# --- aggregate metrics -------------------------------------------------


def _summarize(model: str, preds: list[BacktestPrediction]) -> BacktestModelSummary:
    import numpy as np

    if not preds:
        return BacktestModelSummary(
            model=model, n=0,
            correlation_r=None, direction_accuracy=None,
            median_abs_error=None, bias=None,
            coverage_50=None, coverage_90=None,
        )
    predicted = np.asarray([p.predicted for p in preds], dtype=float)
    actual = np.asarray([p.actual for p in preds], dtype=float)

    corr: float | None = None
    if predicted.size >= 3 and predicted.std() > 0 and actual.std() > 0:
        corr = float(np.corrcoef(predicted, actual)[0, 1])

    dir_match = float(np.mean(np.sign(predicted) == np.sign(actual)))
    mae = float(np.median(np.abs(predicted - actual)))
    bias = float(np.mean(predicted - actual))

    cov_50 = cov_90 = None
    preds_with_bands = [p for p in preds if p.inside_50 is not None]
    if preds_with_bands:
        cov_50 = float(np.mean([p.inside_50 for p in preds_with_bands]))
    preds_with_90 = [p for p in preds if p.inside_90 is not None]
    if preds_with_90:
        cov_90 = float(np.mean([p.inside_90 for p in preds_with_90]))

    return BacktestModelSummary(
        model=model,
        n=len(preds),
        correlation_r=round(corr, 4) if corr is not None else None,
        direction_accuracy=round(dir_match, 4),
        median_abs_error=round(mae, 4),
        bias=round(bias, 4),
        coverage_50=round(cov_50, 4) if cov_50 is not None else None,
        coverage_90=round(cov_90, 4) if cov_90 is not None else None,
    )


# --- driver ------------------------------------------------------------


def run(s: Session) -> BacktestReport:
    candidate_events = (
        s.query(Earnings, Company)
        .join(Company, Company.company_id == Earnings.company_id)
        .filter(Earnings.eps_actual.isnot(None))
        .order_by(Earnings.report_date)
        .all()
    )

    # Precompute actual 1D + 5D returns per event
    events_with_returns: list[tuple[Earnings, Company, float, float | None]] = []
    for e, c in candidate_events:
        oc = compute_outcome(s, e)
        if oc.post_earnings_1d_return is None:
            continue
        events_with_returns.append((e, c, oc.post_earnings_1d_return, oc.post_earnings_5d_return))

    # For bootstrap: for each event, the peer pool is every *earlier* event
    # across the whole universe. Precompute a sorted list of (earnings, return).
    all_pairs = [
        (e, r1d) for e, _, r1d, _ in events_with_returns
    ]

    predictions_by_model: dict[str, list[BacktestPrediction]] = {m: [] for m in MODELS}

    for e, c, actual_1d, actual_5d in events_with_returns:
        # Peer pool for bootstrap: only events strictly before this event.
        peers_before: list[tuple[Earnings, float]] = [
            (ep, rp) for ep, rp in all_pairs
            if ep.report_date < e.report_date and ep.earnings_id != e.earnings_id
        ]

        # 1) gbm_1d
        gbm1 = _predict_gbm(s, c.ticker, c.company_id, e.report_date, horizon=1)
        if gbm1 is not None:
            pred = _make_pred("gbm_1d", e, c, gbm1, actual_1d)
            predictions_by_model["gbm_1d"].append(pred)

        # 2) gbm_5d (if 5d actual available)
        if actual_5d is not None:
            gbm5 = _predict_gbm(s, c.ticker, c.company_id, e.report_date, horizon=5)
            if gbm5 is not None:
                pred = _make_pred("gbm_5d", e, c, gbm5, actual_5d)
                predictions_by_model["gbm_5d"].append(pred)

        # 3) merton_1d_earnings
        mer = _predict_merton(s, c.ticker, c.company_id, e.report_date)
        if mer is not None:
            pred = _make_pred("merton_1d_earnings", e, c, mer, actual_1d)
            predictions_by_model["merton_1d_earnings"].append(pred)

        # 4) bootstrap
        bs = _predict_bootstrap(s, e.hypothesis_score, peers_before)
        if bs is not None:
            pred = _make_pred("bootstrap", e, c, bs, actual_1d)
            predictions_by_model["bootstrap"].append(pred)

        # 5) hypothesis_linear — 3.0 × score
        if e.hypothesis_score is not None:
            predicted = 3.0 * float(e.hypothesis_score)
            predictions_by_model["hypothesis_linear"].append(
                BacktestPrediction(
                    model="hypothesis_linear",
                    earnings_id=e.earnings_id,
                    ticker=c.ticker,
                    report_date=e.report_date,
                    hypothesis_score=e.hypothesis_score,
                    predicted=predicted,
                    actual=actual_1d,
                )
            )

    summaries = [_summarize(m, predictions_by_model[m]) for m in MODELS]
    summaries.sort(
        key=lambda x: (x.correlation_r if x.correlation_r is not None else -2),
        reverse=True,
    )

    flat_preds = [p for m in MODELS for p in predictions_by_model[m]]
    notes: list[str] = []
    if not events_with_returns:
        notes.append("No past earnings events with confirmed 1D returns — backtest empty.")

    return BacktestReport(
        models=summaries,
        predictions=flat_preds,
        n_events_evaluated=len(events_with_returns),
        n_events_candidates=len(candidate_events),
        notes=notes,
    )


def _make_pred(
    model: str,
    e: Earnings,
    c: Company,
    q: dict,
    actual: float,
) -> BacktestPrediction:
    inside50 = q["p25"] <= actual <= q["p75"]
    inside90 = q["p05"] <= actual <= q["p95"]
    return BacktestPrediction(
        model=model,
        earnings_id=e.earnings_id,
        ticker=c.ticker,
        report_date=e.report_date,
        hypothesis_score=e.hypothesis_score,
        predicted=q["p50"],
        predicted_p25=q["p25"],
        predicted_p75=q["p75"],
        predicted_p05=q["p05"],
        predicted_p95=q["p95"],
        actual=actual,
        inside_50=inside50,
        inside_90=inside90,
    )
