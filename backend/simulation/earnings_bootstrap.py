"""Conditional bootstrap of post-earnings reactions.

For a target event (ticker + hypothesis_score), find historical earnings
events with similar scores across the entire universe — not just the
target ticker, so we have enough sample size — and bootstrap the
empirical distribution of post_earnings_1d_return over those peers.

The *method* used for picking peers is surfaced in the response:

  score_window   found ≥ `min_peers` events within ±`tolerance` of target
  same_sign      fell back to events with the same-sign hypothesis_score
  all_events     no hypothesis_score on target, or universe has none —
                 resample over every past event with a recorded reaction

Resampling is simple Efron-style bootstrap — sample with replacement,
n_bootstrap times. No smoothing, no kernel weighting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from analysis.outcomes import compute as compute_outcome
from app.models import Company, Earnings


DEFAULT_N_BOOTSTRAP = 5_000
DEFAULT_SCORE_TOLERANCE = 0.15
MIN_PEERS = 6
HISTOGRAM_BINS = 40


@dataclass
class PeerEvent:
    earnings_id: int
    ticker: str
    report_date: date
    fiscal_period: str | None
    hypothesis_score: float | None
    actual_1d_return: float | None
    eps_surprise_pct: float | None


@dataclass
class HistogramBin:
    low: float
    high: float
    count: int


@dataclass
class BootstrapQuantiles:
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean: float
    stdev: float


@dataclass
class BootstrapResult:
    target_ticker: str
    target_hypothesis_score: float | None
    target_fiscal_period: str | None
    method: str
    score_tolerance: float | None
    n_peers: int
    n_bootstrap: int
    peers: list[PeerEvent]
    histogram: list[HistogramBin]
    quantiles: BootstrapQuantiles
    prob_positive_return: float
    prob_up_2pct: float
    prob_down_2pct: float
    notes: list[str] = field(default_factory=list)


def _gather_historical(s: Session) -> list[PeerEvent]:
    rows = (
        s.query(Earnings, Company)
        .join(Company, Company.company_id == Earnings.company_id)
        .filter(Earnings.eps_actual.isnot(None))
        .order_by(Earnings.report_date.desc())
        .all()
    )
    peers: list[PeerEvent] = []
    for e, c in rows:
        oc = compute_outcome(s, e)
        if oc.post_earnings_1d_return is None:
            continue
        peers.append(
            PeerEvent(
                earnings_id=e.earnings_id,
                ticker=c.ticker,
                report_date=e.report_date,
                fiscal_period=e.fiscal_period,
                hypothesis_score=e.hypothesis_score,
                actual_1d_return=oc.post_earnings_1d_return,
                eps_surprise_pct=oc.eps_surprise_pct,
            )
        )
    return peers


def _pick_peers(
    peers: list[PeerEvent], target_score: float | None, tolerance: float
) -> tuple[list[PeerEvent], str, float | None]:
    if target_score is None:
        return peers, "all_events", None
    near = [
        p for p in peers
        if p.hypothesis_score is not None
        and abs(p.hypothesis_score - target_score) <= tolerance
    ]
    if len(near) >= MIN_PEERS:
        return near, "score_window", tolerance
    sign = 1 if target_score > 0 else -1 if target_score < 0 else 0
    same_sign = [
        p for p in peers
        if p.hypothesis_score is not None
        and (p.hypothesis_score > 0 if sign > 0 else p.hypothesis_score < 0 if sign < 0
             else abs(p.hypothesis_score) < 0.1)
    ]
    if len(same_sign) >= MIN_PEERS:
        return same_sign, "same_sign", None
    return peers, "all_events", None


def _find_target(
    s: Session, ticker: str, fiscal_period: str | None
) -> tuple[Company, Earnings | None, float | None]:
    company = s.query(Company).filter(Company.ticker == ticker.upper()).one_or_none()
    if company is None:
        raise ValueError(f"Unknown ticker {ticker}")

    q = s.query(Earnings).filter(Earnings.company_id == company.company_id)
    if fiscal_period:
        q = q.filter(Earnings.fiscal_period == fiscal_period)
        earn = q.first()
    else:
        # Prefer the next upcoming event; else the most recent past.
        today = date.today()
        earn = (
            q.filter(Earnings.report_date >= today)
            .order_by(Earnings.report_date)
            .first()
        )
        if earn is None:
            earn = q.order_by(Earnings.report_date.desc()).first()

    score = earn.hypothesis_score if earn else None
    # If no score on the earnings row, use the company's latest CompanySignal
    if earn is not None and score is None:
        from app.models import CompanySignal

        sig = s.get(CompanySignal, company.company_id)
        if sig:
            score = sig.hypothesis_score
    return company, earn, score


def bootstrap(
    s: Session,
    ticker: str,
    fiscal_period: str | None = None,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    tolerance: float = DEFAULT_SCORE_TOLERANCE,
    seed: int | None = None,
) -> BootstrapResult:
    import numpy as np

    company, target, score = _find_target(s, ticker, fiscal_period)
    peers_all = _gather_historical(s)

    # Exclude the target itself if it already has a reaction (i.e. it's past).
    if target is not None:
        peers_all = [p for p in peers_all if p.earnings_id != target.earnings_id]

    chosen, method, window = _pick_peers(peers_all, score, tolerance)
    notes: list[str] = []
    if len(chosen) < 3:
        notes.append(
            f"only {len(chosen)} peer events available — bootstrap distribution "
            "will be very narrow / unreliable"
        )

    rng = np.random.default_rng(seed)
    returns = np.asarray([p.actual_1d_return for p in chosen], dtype=float)
    if returns.size == 0:
        samples = np.zeros(1)
    else:
        idx = rng.integers(0, returns.size, n_bootstrap)
        samples = returns[idx]

    counts, edges = np.histogram(samples, bins=HISTOGRAM_BINS)
    histogram = [
        HistogramBin(low=float(edges[i]), high=float(edges[i + 1]), count=int(counts[i]))
        for i in range(HISTOGRAM_BINS)
    ]

    q = BootstrapQuantiles(
        p05=float(np.quantile(samples, 0.05)),
        p25=float(np.quantile(samples, 0.25)),
        p50=float(np.quantile(samples, 0.5)),
        p75=float(np.quantile(samples, 0.75)),
        p95=float(np.quantile(samples, 0.95)),
        mean=float(np.mean(samples)),
        stdev=float(np.std(samples, ddof=1)) if samples.size > 1 else 0.0,
    )

    return BootstrapResult(
        target_ticker=company.ticker,
        target_hypothesis_score=score,
        target_fiscal_period=target.fiscal_period if target else None,
        method=method,
        score_tolerance=window,
        n_peers=len(chosen),
        n_bootstrap=n_bootstrap,
        peers=chosen[:40],
        histogram=histogram,
        quantiles=q,
        prob_positive_return=float(np.mean(samples > 0)) if samples.size else 0.0,
        prob_up_2pct=float(np.mean(samples > 2.0)) if samples.size else 0.0,
        prob_down_2pct=float(np.mean(samples < -2.0)) if samples.size else 0.0,
        notes=notes,
    )
