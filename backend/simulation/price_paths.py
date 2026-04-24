"""Monte Carlo price-path simulator.

Two models are supported:

  **gbm** — vanilla Geometric Brownian Motion, μ and σ fit from the daily
  log-returns of the last `fit_window_days` of prices_daily.

  **merton** — GBM with scheduled jumps at each scheduled earnings date in
  the simulation horizon. Jump size ~ Normal(0, implied_move²), where the
  implied move is taken from the latest OptionsSnapshot's ATM IV
  (implied_move = S × IV × sqrt(days_to_earnings / 365)). Falls back to
  the historical average |eps_surprise_pct| × 2 if no options snapshot
  exists.

All math is vectorized through numpy. Response shape is narrow: per-day
quantile bands + a terminal-value histogram + a stats dict. Full paths
are NEVER shipped to the API — too much data, no useful downstream use."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Company, Earnings, OptionsSnapshot, PriceDaily


TRADING_DAYS_PER_YEAR = 252
MIN_FIT_OBSERVATIONS = 20
DEFAULT_FIT_WINDOW_DAYS = 180
HISTOGRAM_BINS = 50


@dataclass
class QuantileBand:
    day_offset: int
    obs_date: date
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float


@dataclass
class HistogramBin:
    low: float
    high: float
    count: int


@dataclass
class TerminalStats:
    expected_value: float
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    prob_positive_return: float      # P(S_T > S_0)
    prob_down_10pct: float            # P(S_T < S_0 × 0.9)
    prob_up_10pct: float              # P(S_T > S_0 × 1.1)


@dataclass
class SimulationResult:
    ticker: str
    model: str
    start_price: float
    start_date: date
    horizon_days: int
    n_paths: int
    annual_drift_pct: float
    annual_volatility_pct: float
    fit_window_days: int
    fit_observations: int
    bands: list[QuantileBand]
    terminal_histogram: list[HistogramBin]
    terminal_stats: TerminalStats
    earnings_dates_in_window: list[date] = field(default_factory=list)
    jump_sigma_at_earnings: float | None = None
    notes: list[str] = field(default_factory=list)


def _fit_log_returns(rows: list[PriceDaily]) -> tuple[float, float, int]:
    import numpy as np

    closes = [r.close for r in rows if r.close]
    if len(closes) < 2:
        return 0.0, 0.0, 0
    closes_arr = np.asarray(closes, dtype=float)
    log_r = np.diff(np.log(closes_arr))
    log_r = log_r[np.isfinite(log_r)]
    if log_r.size == 0:
        return 0.0, 0.0, 0
    mu_d = float(np.mean(log_r))
    sigma_d = float(np.std(log_r, ddof=1)) if log_r.size > 1 else 0.0
    return mu_d, sigma_d, int(log_r.size)


def _fetch_history(
    s: Session,
    company_id: int,
    window_days: int,
    as_of: date | None = None,
) -> list[PriceDaily]:
    """Returns rows ordered by trade_date asc. When `as_of` is set, only
    returns rows with trade_date ≤ as_of — required for backtesting so the
    simulator can't peek at future prices."""
    anchor = as_of or date.today()
    cutoff = anchor - timedelta(days=window_days * 2)
    q = s.query(PriceDaily).filter(
        PriceDaily.company_id == company_id,
        PriceDaily.trade_date >= cutoff,
    )
    if as_of is not None:
        q = q.filter(PriceDaily.trade_date <= as_of)
    return q.order_by(PriceDaily.trade_date).all()


def _scheduled_earnings(
    s: Session, company_id: int, start: date, end: date
) -> list[date]:
    rows = (
        s.query(Earnings)
        .filter(
            Earnings.company_id == company_id,
            Earnings.report_date >= start,
            Earnings.report_date <= end,
        )
        .all()
    )
    return sorted({r.report_date for r in rows})


def _implied_move_sigma(
    s: Session, company_id: int, current_price: float, next_earnings: date | None
) -> tuple[float | None, str | None]:
    """Per-event jump σ (as a fraction) from the latest options snapshot.

    Returns (sigma, note). If no snapshot exists, falls back to the
    historical average |eps_surprise_pct| across the ticker's past
    earnings, with a note explaining the fallback."""
    snap = (
        s.query(OptionsSnapshot)
        .filter(OptionsSnapshot.company_id == company_id)
        .order_by(OptionsSnapshot.obs_date.desc())
        .first()
    )
    if snap and snap.atm_iv and next_earnings:
        days_to = max(1, (next_earnings - date.today()).days)
        sigma = float(snap.atm_iv) * (days_to / 365) ** 0.5
        return sigma, f"jump σ from ATM IV ({snap.atm_iv:.3f}) × √({days_to}/365)"

    # Fallback: historical |eps_surprise_pct| mean / 100
    hist = (
        s.query(Earnings)
        .filter(
            Earnings.company_id == company_id,
            Earnings.eps_surprise_pct.isnot(None),
        )
        .all()
    )
    if hist:
        import numpy as np

        surprises = [abs(h.eps_surprise_pct) for h in hist if h.eps_surprise_pct is not None]
        if surprises:
            mean_surp = float(np.mean(surprises))
            # Rough rule: 1% EPS surprise ≈ 0.2% price move σ
            sigma = mean_surp / 100 * 0.2
            return sigma, f"jump σ from historical |EPS surprise| mean ({mean_surp:.1f}%)"
    return None, "no options snapshot or earnings history to estimate jump σ"


def _histogram(values, n_bins: int) -> list[HistogramBin]:
    import numpy as np

    arr = np.asarray(values, dtype=float)
    counts, edges = np.histogram(arr, bins=n_bins)
    return [
        HistogramBin(low=float(edges[i]), high=float(edges[i + 1]), count=int(counts[i]))
        for i in range(n_bins)
    ]


def simulate(
    s: Session,
    ticker: str,
    horizon_days: int = 30,
    n_paths: int = 10_000,
    model: str = "gbm",
    fit_window_days: int = DEFAULT_FIT_WINDOW_DAYS,
    seed: int | None = None,
    as_of: date | None = None,
) -> SimulationResult:
    import numpy as np

    company = s.query(Company).filter(Company.ticker == ticker.upper()).one_or_none()
    if company is None:
        raise ValueError(f"Unknown ticker {ticker}")

    history = _fetch_history(s, company.company_id, fit_window_days, as_of=as_of)
    mu_d, sigma_d, n_obs = _fit_log_returns(history)
    if n_obs < MIN_FIT_OBSERVATIONS:
        raise ValueError(
            f"Insufficient price history for {ticker}: {n_obs} daily returns "
            f"(need ≥ {MIN_FIT_OBSERVATIONS})"
        )

    last = history[-1]
    start_price = float(last.close)
    start_date_ = last.trade_date
    end_date_ = start_date_ + timedelta(days=horizon_days)

    earnings_in_window = _scheduled_earnings(
        s, company.company_id, start_date_ + timedelta(days=1), end_date_
    )
    jump_sigma = None
    notes: list[str] = []

    if model not in {"gbm", "merton"}:
        raise ValueError(f"Unknown model {model!r}")

    if model == "merton":
        if not earnings_in_window:
            notes.append("merton model requested but no earnings inside window — "
                         "reduces to GBM for this horizon")
        else:
            jump_sigma, note = _implied_move_sigma(
                s, company.company_id, start_price, earnings_in_window[0]
            )
            if note:
                notes.append(note)

    rng = np.random.default_rng(seed)

    # Daily step, n_paths columns.
    dt = 1 / TRADING_DAYS_PER_YEAR
    log_drift_step = (mu_d - 0.5 * sigma_d * sigma_d)
    daily_noise = rng.standard_normal((horizon_days, n_paths)) * sigma_d
    daily_log_returns = log_drift_step + daily_noise

    if model == "merton" and earnings_in_window and jump_sigma is not None:
        # Apply a log-return shock at the offset that falls on the earnings date
        for er in earnings_in_window:
            offset = (er - start_date_).days
            if 1 <= offset <= horizon_days:
                shocks = rng.standard_normal(n_paths) * jump_sigma
                daily_log_returns[offset - 1] += shocks

    cum_log_returns = np.cumsum(daily_log_returns, axis=0)
    path_prices = start_price * np.exp(cum_log_returns)

    # Per-day quantile bands
    quantiles = np.quantile(path_prices, [0.05, 0.25, 0.5, 0.75, 0.95], axis=1)
    bands: list[QuantileBand] = []
    for i in range(horizon_days):
        bands.append(
            QuantileBand(
                day_offset=i + 1,
                obs_date=start_date_ + timedelta(days=i + 1),
                p05=float(quantiles[0, i]),
                p25=float(quantiles[1, i]),
                p50=float(quantiles[2, i]),
                p75=float(quantiles[3, i]),
                p95=float(quantiles[4, i]),
            )
        )

    # Terminal distribution
    terminal = path_prices[-1]
    t_stats = TerminalStats(
        expected_value=float(np.mean(terminal)),
        p05=float(np.quantile(terminal, 0.05)),
        p25=float(np.quantile(terminal, 0.25)),
        p50=float(np.quantile(terminal, 0.5)),
        p75=float(np.quantile(terminal, 0.75)),
        p95=float(np.quantile(terminal, 0.95)),
        prob_positive_return=float(np.mean(terminal > start_price)),
        prob_down_10pct=float(np.mean(terminal < start_price * 0.9)),
        prob_up_10pct=float(np.mean(terminal > start_price * 1.1)),
    )

    return SimulationResult(
        ticker=company.ticker,
        model=model,
        start_price=start_price,
        start_date=start_date_,
        horizon_days=horizon_days,
        n_paths=n_paths,
        annual_drift_pct=round(mu_d * TRADING_DAYS_PER_YEAR * 100, 2),
        annual_volatility_pct=round(sigma_d * (TRADING_DAYS_PER_YEAR ** 0.5) * 100, 2),
        fit_window_days=fit_window_days,
        fit_observations=n_obs,
        bands=bands,
        terminal_histogram=_histogram(terminal, HISTOGRAM_BINS),
        terminal_stats=t_stats,
        earnings_dates_in_window=earnings_in_window,
        jump_sigma_at_earnings=jump_sigma,
        notes=notes,
    )
