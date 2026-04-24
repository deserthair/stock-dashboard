from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from simulation import earnings_bootstrap, price_paths

from ..db import get_db
from ..schemas import (
    BootstrapQuantilesOut,
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
