from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from simulation import dcf as dcf_sim
from simulation import earnings_bootstrap, price_paths

from ..db import get_db
from ..schemas import (
    BootstrapQuantilesOut,
    DCFResultOut,
    DCFStatsOut,
    EarningsBootstrapOut,
    HistogramBinOut,
    PeerEventOut,
    PricePathSimulationOut,
    QuantileBandOut,
    TerminalStatsOut,
)

router = APIRouter(prefix="/api/simulate", tags=["simulate"])


@router.get("/price-paths/{ticker}", response_model=PricePathSimulationOut)
def price_path_simulation(
    ticker: str,
    db: Session = Depends(get_db),
    horizon_days: int = Query(default=30, ge=5, le=365),
    n_paths: int = Query(default=10_000, ge=500, le=50_000),
    model: str = Query(default="gbm", pattern="^(gbm|merton)$"),
    fit_window_days: int = Query(default=180, ge=30, le=3650),
    seed: int | None = Query(default=None),
) -> PricePathSimulationOut:
    try:
        result = price_paths.simulate(
            db,
            ticker,
            horizon_days=horizon_days,
            n_paths=n_paths,
            model=model,
            fit_window_days=fit_window_days,
            seed=seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return PricePathSimulationOut(
        ticker=result.ticker,
        model=result.model,
        start_price=result.start_price,
        start_date=result.start_date,
        horizon_days=result.horizon_days,
        n_paths=result.n_paths,
        annual_drift_pct=result.annual_drift_pct,
        annual_volatility_pct=result.annual_volatility_pct,
        fit_window_days=result.fit_window_days,
        fit_observations=result.fit_observations,
        bands=[QuantileBandOut(**b.__dict__) for b in result.bands],
        terminal_histogram=[
            HistogramBinOut(**h.__dict__) for h in result.terminal_histogram
        ],
        terminal_stats=TerminalStatsOut(**result.terminal_stats.__dict__),
        earnings_dates_in_window=result.earnings_dates_in_window,
        jump_sigma_at_earnings=result.jump_sigma_at_earnings,
        notes=result.notes,
    )


@router.get("/dcf/{ticker}", response_model=DCFResultOut)
def dcf_simulation(
    ticker: str,
    db: Session = Depends(get_db),
    n_simulations: int = Query(default=10_000, ge=500, le=50_000),
    years_explicit: int = Query(default=10, ge=3, le=20),
    wacc_mean: float = Query(default=0.09, ge=0.02, le=0.25),
    wacc_std: float = Query(default=0.01, ge=0.001, le=0.05),
    terminal_growth: float = Query(default=0.025, ge=0.0, le=0.06),
    growth_override: float | None = Query(default=None),
    margin_override: float | None = Query(default=None),
    seed: int | None = Query(default=None),
) -> DCFResultOut:
    try:
        result = dcf_sim.simulate(
            db,
            ticker,
            n_simulations=n_simulations,
            years_explicit=years_explicit,
            wacc_mean=wacc_mean,
            wacc_std=wacc_std,
            terminal_growth=terminal_growth,
            growth_override=growth_override,
            margin_override=margin_override,
            seed=seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return DCFResultOut(
        ticker=result.ticker,
        current_price=result.current_price,
        n_simulations=result.n_simulations,
        n_valid=result.n_valid,
        years_explicit=result.years_explicit,
        shares_diluted=result.shares_diluted,
        revenue_growth_mean_pct=result.revenue_growth_mean_pct,
        revenue_growth_std_pct=result.revenue_growth_std_pct,
        fcf_margin_mean_pct=result.fcf_margin_mean_pct,
        fcf_margin_std_pct=result.fcf_margin_std_pct,
        wacc_mean_pct=result.wacc_mean_pct,
        wacc_std_pct=result.wacc_std_pct,
        terminal_growth_pct=result.terminal_growth_pct,
        intrinsic_value_stats=DCFStatsOut(**result.intrinsic_value_stats.__dict__),
        intrinsic_value_histogram=[
            HistogramBinOut(**h.__dict__) for h in result.intrinsic_value_histogram
        ],
        prob_undervalued=result.prob_undervalued,
        margin_of_safety_at_p50_pct=result.margin_of_safety_at_p50_pct,
        fit_quarters=result.fit_quarters,
        notes=result.notes,
    )


@router.get("/earnings-bootstrap/{ticker}", response_model=EarningsBootstrapOut)
def earnings_reaction_bootstrap(
    ticker: str,
    db: Session = Depends(get_db),
    fiscal_period: str | None = Query(default=None),
    n_bootstrap: int = Query(default=5_000, ge=500, le=50_000),
    tolerance: float = Query(default=0.15, ge=0.01, le=1.0),
    seed: int | None = Query(default=None),
) -> EarningsBootstrapOut:
    try:
        result = earnings_bootstrap.bootstrap(
            db,
            ticker,
            fiscal_period=fiscal_period,
            n_bootstrap=n_bootstrap,
            tolerance=tolerance,
            seed=seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return EarningsBootstrapOut(
        target_ticker=result.target_ticker,
        target_hypothesis_score=result.target_hypothesis_score,
        target_fiscal_period=result.target_fiscal_period,
        method=result.method,
        score_tolerance=result.score_tolerance,
        n_peers=result.n_peers,
        n_bootstrap=result.n_bootstrap,
        peers=[PeerEventOut(**p.__dict__) for p in result.peers],
        histogram=[HistogramBinOut(**h.__dict__) for h in result.histogram],
        quantiles=BootstrapQuantilesOut(**result.quantiles.__dict__),
        prob_positive_return=result.prob_positive_return,
        prob_up_2pct=result.prob_up_2pct,
        prob_down_2pct=result.prob_down_2pct,
        notes=result.notes,
    )
