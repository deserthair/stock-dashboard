"""Quality-metric derivations over quarterly fundamentals.

Exposes helpers that operate on a sorted list of `Fundamental` rows
(oldest first) and return:

  - TTM (trailing 4 quarters) aggregates for revenue / EPS / FCF / etc.
  - Year-over-year growth: TTM vs TTM_{−4 quarters}
  - 3-year CAGR where sufficient history exists
  - Current ROIC (TTM NOPAT / most-recent invested capital)
  - Total dividends per share over TTM, plus yield if last_price is known
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from app.models import Fundamental


@dataclass
class QualityMetrics:
    # Levels
    revenue_ttm: float | None
    net_income_ttm: float | None
    eps_ttm: float | None
    fcf_ttm: float | None
    book_value: float | None              # most recent total_equity
    dividends_per_share_ttm: float | None

    # Growth (YoY, TTM vs TTM_{t-4q})
    revenue_yoy_pct: float | None
    eps_yoy_pct: float | None
    equity_yoy_pct: float | None
    fcf_yoy_pct: float | None
    dividend_yoy_pct: float | None

    # 3-year CAGR (TTM vs 12q ago)
    revenue_cagr_3y_pct: float | None
    eps_cagr_3y_pct: float | None
    equity_cagr_3y_pct: float | None
    fcf_cagr_3y_pct: float | None

    # Returns on capital
    roic_latest_pct: float | None          # most recent row
    roic_ttm_pct: float | None             # TTM NOPAT / invested_capital

    # Yield
    dividend_yield_pct: float | None       # dps_ttm / last_price × 100

    # Coverage tags for the UI
    quarters_available: int
    years_of_history: float


def _ttm(rows: Sequence[Fundamental], attr: str, offset: int = 0) -> float | None:
    """Sum the last 4 quarters of `attr`, offset by `offset` quarters backward."""
    end = len(rows) - offset
    if end < 4:
        return None
    window = rows[end - 4 : end]
    vals = [getattr(r, attr, None) for r in window]
    if any(v is None for v in vals):
        return None
    return float(sum(vals))


def _pct_change(newer: float | None, older: float | None) -> float | None:
    if newer is None or older is None or older == 0:
        return None
    return round((newer / older - 1.0) * 100, 2)


def _cagr(newer: float | None, older: float | None, years: float) -> float | None:
    if newer is None or older is None or older <= 0 or newer <= 0 or years <= 0:
        return None
    return round(((newer / older) ** (1 / years) - 1) * 100, 2)


def compute(rows: Iterable[Fundamental], last_price: float | None = None) -> QualityMetrics:
    sorted_rows = sorted(rows, key=lambda r: r.period_end)
    n = len(sorted_rows)
    if n == 0:
        return QualityMetrics(
            revenue_ttm=None, net_income_ttm=None, eps_ttm=None, fcf_ttm=None,
            book_value=None, dividends_per_share_ttm=None,
            revenue_yoy_pct=None, eps_yoy_pct=None, equity_yoy_pct=None,
            fcf_yoy_pct=None, dividend_yoy_pct=None,
            revenue_cagr_3y_pct=None, eps_cagr_3y_pct=None,
            equity_cagr_3y_pct=None, fcf_cagr_3y_pct=None,
            roic_latest_pct=None, roic_ttm_pct=None,
            dividend_yield_pct=None,
            quarters_available=0, years_of_history=0.0,
        )

    latest = sorted_rows[-1]
    revenue_ttm = _ttm(sorted_rows, "revenue")
    ni_ttm = _ttm(sorted_rows, "net_income")
    eps_ttm = _ttm(sorted_rows, "eps_diluted")
    fcf_ttm = _ttm(sorted_rows, "free_cash_flow")
    dps_ttm = _ttm(sorted_rows, "dividends_per_share")

    # Year-ago TTM (window shifted 4 quarters backward)
    revenue_ttm_yoy = _ttm(sorted_rows, "revenue", offset=4)
    eps_ttm_yoy = _ttm(sorted_rows, "eps_diluted", offset=4)
    fcf_ttm_yoy = _ttm(sorted_rows, "free_cash_flow", offset=4)
    dps_ttm_yoy = _ttm(sorted_rows, "dividends_per_share", offset=4)

    equity_yoy = sorted_rows[-5].total_equity if n >= 5 else None

    # 3-year-ago TTM
    revenue_ttm_3y = _ttm(sorted_rows, "revenue", offset=12)
    eps_ttm_3y = _ttm(sorted_rows, "eps_diluted", offset=12)
    fcf_ttm_3y = _ttm(sorted_rows, "free_cash_flow", offset=12)
    equity_3y = sorted_rows[-13].total_equity if n >= 13 else None

    # TTM NOPAT / invested capital (most recent)
    nopat_ttm = _ttm(sorted_rows, "nopat")
    roic_ttm = (
        round(nopat_ttm / latest.invested_capital * 100, 2)
        if nopat_ttm is not None and latest.invested_capital
        else None
    )

    dividend_yield = None
    if last_price and dps_ttm and last_price > 0:
        dividend_yield = round(dps_ttm / last_price * 100, 2)

    return QualityMetrics(
        revenue_ttm=revenue_ttm,
        net_income_ttm=ni_ttm,
        eps_ttm=eps_ttm,
        fcf_ttm=fcf_ttm,
        book_value=latest.total_equity,
        dividends_per_share_ttm=dps_ttm,
        revenue_yoy_pct=_pct_change(revenue_ttm, revenue_ttm_yoy),
        eps_yoy_pct=_pct_change(eps_ttm, eps_ttm_yoy),
        equity_yoy_pct=_pct_change(latest.total_equity, equity_yoy),
        fcf_yoy_pct=_pct_change(fcf_ttm, fcf_ttm_yoy),
        dividend_yoy_pct=_pct_change(dps_ttm, dps_ttm_yoy),
        revenue_cagr_3y_pct=_cagr(revenue_ttm, revenue_ttm_3y, 3),
        eps_cagr_3y_pct=_cagr(eps_ttm, eps_ttm_3y, 3),
        equity_cagr_3y_pct=_cagr(latest.total_equity, equity_3y, 3),
        fcf_cagr_3y_pct=_cagr(fcf_ttm, fcf_ttm_3y, 3),
        roic_latest_pct=round(latest.roic * 100, 2) if latest.roic is not None else None,
        roic_ttm_pct=roic_ttm,
        dividend_yield_pct=dividend_yield,
        quarters_available=n,
        years_of_history=round((sorted_rows[-1].period_end - sorted_rows[0].period_end).days / 365.25, 1),
    )
