"""Probabilistic Discounted Cash Flow simulator.

For each Monte Carlo draw we sample:

  revenue_growth     ~ Normal(μ=historical_yoy_mean,  σ=historical_yoy_std)
  fcf_margin         ~ Normal(μ=historical_fcf_margin, σ)
  wacc               ~ Normal(μ=wacc_mean, σ=wacc_std)      (discount rate)
  terminal_growth    ~ Normal(μ=terminal_g_mean, σ=0.005)    (long-run GDP-ish)

Project `years_explicit` years of FCF forward:
  FCF_t = Revenue_{t-1} × (1 + growth) × fcf_margin

Terminal value via Gordon growth:
  TV = FCF_{n+1} / (wacc − g_terminal)           (if wacc > g_terminal, else drop sample)

Intrinsic value:
  IV = Σ  FCF_t / (1 + wacc)^t   +   TV / (1 + wacc)^n
  IV_per_share = IV / shares_diluted

Inputs fall back to sensible defaults when historical data is noisy /
missing. All math is vectorised in numpy — 10k draws in milliseconds.

This is NOT a valuation model. It's a *distribution* of valuations under
plausible parameter uncertainty. The P(undervalued) reading tells you
what fraction of the Monte Carlo draws say the current price is below
intrinsic. A thick distribution with huge std → low confidence; a narrow
one → high confidence (in the parameter distributions, not in reality)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from analysis.fundamentals import compute as compute_quality
from app.models import CompanySignal, Company, Fundamental


@dataclass
class HistogramBin:
    low: float
    high: float
    count: int


@dataclass
class DCFStats:
    mean: float
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    stdev: float


@dataclass
class DCFResult:
    ticker: str
    current_price: float | None
    n_simulations: int
    n_valid: int                       # after dropping wacc ≤ g_terminal draws
    years_explicit: int
    shares_diluted: float | None

    # Parameter-distribution inputs actually used
    revenue_growth_mean_pct: float
    revenue_growth_std_pct: float
    fcf_margin_mean_pct: float
    fcf_margin_std_pct: float
    wacc_mean_pct: float
    wacc_std_pct: float
    terminal_growth_pct: float

    # Outputs
    intrinsic_value_stats: DCFStats
    intrinsic_value_histogram: list[HistogramBin]
    prob_undervalued: float | None     # P(intrinsic > current_price)
    margin_of_safety_at_p50_pct: float | None

    # Context
    fit_quarters: int
    notes: list[str] = field(default_factory=list)


# ---- parameter estimation helpers ------------------------------------


def _yoy_growth_series(rows: list[Fundamental]) -> list[float]:
    """Compute TTM-vs-TTM revenue YoY growth from rows (oldest first)."""
    if len(rows) < 8:
        return []
    ttms = []
    for i in range(4, len(rows) + 1):
        window = rows[i - 4 : i]
        vals = [r.revenue for r in window if r.revenue is not None]
        if len(vals) == 4:
            ttms.append(sum(vals))
    growths: list[float] = []
    for i in range(4, len(ttms)):
        if ttms[i - 4] and ttms[i - 4] != 0:
            growths.append(ttms[i] / ttms[i - 4] - 1.0)
    return growths


def _fit_parameters(rows: list[Fundamental]) -> tuple[dict, list[str]]:
    """Returns (param_distribution_dict, notes[])."""
    import numpy as np

    notes: list[str] = []
    growths = _yoy_growth_series(rows)
    if growths:
        g_mean = float(np.mean(growths))
        g_std = float(np.std(growths, ddof=1)) if len(growths) > 1 else 0.03
    else:
        g_mean = 0.06
        g_std = 0.03
        notes.append("insufficient history for revenue YoY — default μ=6% σ=3%")

    # FCF margin: mean of FCF/revenue over recent quarters
    margins = [
        float(r.free_cash_flow) / float(r.revenue)
        for r in rows[-8:]
        if r.free_cash_flow is not None and r.revenue and r.revenue != 0
    ]
    if margins:
        m_mean = float(np.mean(margins))
        m_std = float(np.std(margins, ddof=1)) if len(margins) > 1 else 0.02
    else:
        m_mean = 0.10
        m_std = 0.03
        notes.append("insufficient history for FCF margin — default μ=10% σ=3%")

    return (
        {
            "g_mean": g_mean,
            "g_std": max(g_std, 0.005),
            "m_mean": m_mean,
            "m_std": max(m_std, 0.005),
        },
        notes,
    )


def _latest_shares(rows: list[Fundamental]) -> float | None:
    for r in reversed(rows):
        if r.shares_diluted:
            return float(r.shares_diluted)
    return None


def _starting_revenue_ttm(rows: list[Fundamental]) -> float | None:
    """Sum last 4 quarters of revenue."""
    vals = [r.revenue for r in rows[-4:] if r.revenue is not None]
    if len(vals) == 4:
        return float(sum(vals))
    return None


# ---- main simulation --------------------------------------------------


def simulate(
    s: Session,
    ticker: str,
    n_simulations: int = 10_000,
    years_explicit: int = 10,
    wacc_mean: float = 0.09,
    wacc_std: float = 0.01,
    terminal_growth: float = 0.025,
    seed: int | None = None,
    growth_override: float | None = None,        # override fitted revenue_growth μ
    growth_std_override: float | None = None,
    margin_override: float | None = None,
) -> DCFResult:
    import numpy as np

    company = s.query(Company).filter(Company.ticker == ticker.upper()).one_or_none()
    if company is None:
        raise ValueError(f"Unknown ticker {ticker}")

    rows = (
        s.query(Fundamental)
        .filter(Fundamental.company_id == company.company_id)
        .order_by(Fundamental.period_end)
        .all()
    )
    if len(rows) < 4:
        raise ValueError(
            f"Not enough quarterly fundamentals for {ticker} ({len(rows)} rows, "
            "need ≥ 4). Run `python -m ingest.sources.fundamentals` first."
        )

    sig = s.get(CompanySignal, company.company_id)
    current_price = float(sig.last_price) if sig and sig.last_price else None

    params, notes = _fit_parameters(rows)
    g_mean = growth_override if growth_override is not None else params["g_mean"]
    g_std = growth_std_override if growth_std_override is not None else params["g_std"]
    m_mean = margin_override if margin_override is not None else params["m_mean"]
    m_std = params["m_std"]

    starting_revenue = _starting_revenue_ttm(rows)
    if starting_revenue is None:
        raise ValueError(f"No complete TTM revenue available for {ticker}")

    shares = _latest_shares(rows)
    if shares is None or shares <= 0:
        raise ValueError(f"No shares-outstanding figure available for {ticker}")

    rng = np.random.default_rng(seed)

    # Draw parameter samples (n_simulations of each)
    growths = rng.normal(g_mean, g_std, n_simulations)
    margins = rng.normal(m_mean, m_std, n_simulations)
    waccs = rng.normal(wacc_mean, wacc_std, n_simulations)

    # Clip to sane ranges to avoid pathological draws
    growths = np.clip(growths, -0.3, 0.6)
    margins = np.clip(margins, -0.2, 0.5)
    waccs = np.clip(waccs, 0.02, 0.30)

    # Drop samples where wacc ≤ terminal_growth (Gordon growth blows up)
    valid = waccs > terminal_growth + 0.005
    if valid.sum() < n_simulations * 0.5:
        notes.append(
            f"dropped {n_simulations - int(valid.sum())} draws where WACC ≤ terminal_g"
        )
    growths = growths[valid]
    margins = margins[valid]
    waccs = waccs[valid]
    n_valid = int(valid.sum())
    if n_valid == 0:
        raise ValueError(
            "All draws had WACC ≤ terminal_growth — pick a lower terminal_growth "
            "or a higher wacc_mean."
        )

    # Project FCF over `years_explicit` years (vectorised across samples)
    # Revenue_t = starting_revenue × (1 + g)^t,   t in 1..n
    # FCF_t     = Revenue_t × margin
    t = np.arange(1, years_explicit + 1)
    rev_paths = starting_revenue * (1 + growths[:, None]) ** t[None, :]  # [n_valid, years]
    fcf_paths = rev_paths * margins[:, None]
    discount = (1 + waccs[:, None]) ** t[None, :]
    pv_fcfs = (fcf_paths / discount).sum(axis=1)

    # Terminal value (in year n+1 terms), discounted back
    fcf_terminal_year = fcf_paths[:, -1] * (1 + terminal_growth)
    terminal_values = fcf_terminal_year / (waccs - terminal_growth)
    pv_terminal = terminal_values / (1 + waccs) ** years_explicit

    enterprise_value = pv_fcfs + pv_terminal
    # Simplifying assumption: equity value ≈ enterprise value (ignore net cash/debt).
    # For a demo this is acceptable; real analysis would subtract net debt.
    equity_value = enterprise_value
    intrinsic_per_share = equity_value / shares

    q = np.quantile(intrinsic_per_share, [0.05, 0.25, 0.5, 0.75, 0.95])
    stats = DCFStats(
        mean=float(np.mean(intrinsic_per_share)),
        p05=float(q[0]),
        p25=float(q[1]),
        p50=float(q[2]),
        p75=float(q[3]),
        p95=float(q[4]),
        stdev=float(np.std(intrinsic_per_share, ddof=1)),
    )

    # Histogram — 50 bins within a 1-99 percentile window so outliers don't squash it
    lo = float(np.quantile(intrinsic_per_share, 0.01))
    hi = float(np.quantile(intrinsic_per_share, 0.99))
    counts, edges = np.histogram(intrinsic_per_share, bins=50, range=(lo, hi))
    histogram = [
        HistogramBin(low=float(edges[i]), high=float(edges[i + 1]), count=int(counts[i]))
        for i in range(50)
    ]

    prob_undervalued: float | None = None
    margin_of_safety: float | None = None
    if current_price is not None and current_price > 0:
        prob_undervalued = float(np.mean(intrinsic_per_share > current_price))
        margin_of_safety = (stats.p50 / current_price - 1.0) * 100

    return DCFResult(
        ticker=company.ticker,
        current_price=current_price,
        n_simulations=n_simulations,
        n_valid=n_valid,
        years_explicit=years_explicit,
        shares_diluted=shares,
        revenue_growth_mean_pct=round(g_mean * 100, 2),
        revenue_growth_std_pct=round(g_std * 100, 2),
        fcf_margin_mean_pct=round(m_mean * 100, 2),
        fcf_margin_std_pct=round(m_std * 100, 2),
        wacc_mean_pct=round(wacc_mean * 100, 2),
        wacc_std_pct=round(wacc_std * 100, 2),
        terminal_growth_pct=round(terminal_growth * 100, 2),
        intrinsic_value_stats=stats,
        intrinsic_value_histogram=histogram,
        prob_undervalued=prob_undervalued,
        margin_of_safety_at_p50_pct=round(margin_of_safety, 2) if margin_of_safety is not None else None,
        fit_quarters=len(rows),
        notes=notes,
    )
