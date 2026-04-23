"""yfinance fundamentals ingest.

Pulls ~4 years of quarterly income statement / balance sheet / cash flow
line items per company and upserts into `fundamentals`, computing derived
quality metrics (invested_capital, NOPAT, ROIC) at write time so API
handlers don't retry the math.

Graceful fallback: if yfinance isn't installed or a company has no
quarterly_financials frame, the row is skipped and logged."""

from __future__ import annotations

import logging
from datetime import date, datetime

from app.db import SessionLocal
from app.models import Company, Fundamental

from ..rate_limiter import for_source
from ..source_run import source_run

log = logging.getLogger("fundamentals")

# US corporate tax rate assumed for NOPAT. Real analysis would derive this
# from the effective rate on the income statement, but 21% is the long-run
# anchor post-TCJA and good enough to compare across peers.
DEFAULT_TAX_RATE = 0.21


def _get(df, *candidates: str) -> dict:
    """Given a yfinance quarterly dataframe (columns = period_end dates),
    return {period_end: value} for the first matching row label."""
    if df is None or df.empty:
        return {}
    try:
        index = {str(i).strip() for i in df.index}
    except Exception:
        return {}
    for name in candidates:
        if name in df.index:
            s = df.loc[name]
            return {k.date() if hasattr(k, "date") else k: (float(v) if v is not None else None)
                    for k, v in s.items() if v == v}  # filter NaN
    # case-insensitive fallback
    lowered = {str(i).strip().lower(): i for i in df.index}
    for name in candidates:
        k = name.lower()
        if k in lowered:
            s = df.loc[lowered[k]]
            return {k.date() if hasattr(k, "date") else k: (float(v) if v is not None else None)
                    for k, v in s.items() if v == v}
    return {}


def _fiscal_period(d: date) -> str:
    # Calendar-quarter approximation; real FQs may shift. Good enough for UI labels.
    q = (d.month - 1) // 3 + 1
    return f"Q{q} {d.year}"


def _compute_derived(
    op_income: float | None,
    total_debt: float | None,
    total_equity: float | None,
    ocf: float | None,
    capex: float | None,
) -> tuple[float | None, float | None, float | None, float | None]:
    """Returns (free_cash_flow, invested_capital, nopat, roic)."""
    fcf = None
    if ocf is not None and capex is not None:
        # yfinance capex is typically stored as a negative number.
        fcf = ocf + capex
    invested_capital = None
    if total_debt is not None and total_equity is not None:
        invested_capital = total_debt + total_equity
    nopat = None
    if op_income is not None:
        nopat = op_income * (1 - DEFAULT_TAX_RATE)
    roic = None
    if nopat is not None and invested_capital and invested_capital > 0:
        roic = nopat / invested_capital
    return fcf, invested_capital, nopat, roic


def _collect_quarterly(tkr) -> dict[date, dict]:
    """Merge the 3 yfinance quarterly frames into {period_end: {attrs…}}."""
    income = getattr(tkr, "quarterly_financials", None)
    balance = getattr(tkr, "quarterly_balance_sheet", None)
    cashflow = getattr(tkr, "quarterly_cashflow", None)

    rev = _get(income, "Total Revenue", "TotalRevenue")
    gp = _get(income, "Gross Profit", "GrossProfit")
    oi = _get(income, "Operating Income", "OperatingIncome", "EBIT")
    ni = _get(income, "Net Income", "NetIncome", "Net Income Common Stockholders")
    eps = _get(income, "Diluted EPS", "DilutedEPS")
    sh = _get(income, "Diluted Average Shares", "DilutedAverageShares")

    assets = _get(balance, "Total Assets", "TotalAssets")
    equity = _get(balance, "Stockholders Equity", "Total Equity Gross Minority Interest", "StockholdersEquity")
    debt = _get(balance, "Total Debt", "TotalDebt", "Long Term Debt", "LongTermDebt")

    ocf = _get(cashflow, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities", "CashFlowFromContinuingOperatingActivities")
    capex = _get(cashflow, "Capital Expenditure", "CapitalExpenditure")
    divs = _get(cashflow, "Cash Dividends Paid", "CommonStockDividendPaid", "Cash Dividends Paid Common Stock")

    all_periods: set[date] = set()
    for m in (rev, gp, oi, ni, eps, sh, assets, equity, debt, ocf, capex, divs):
        all_periods.update(k for k in m.keys() if isinstance(k, date))

    out: dict[date, dict] = {}
    for p in all_periods:
        out[p] = {
            "revenue": rev.get(p),
            "gross_profit": gp.get(p),
            "operating_income": oi.get(p),
            "net_income": ni.get(p),
            "eps_diluted": eps.get(p),
            "shares_diluted": sh.get(p),
            "total_assets": assets.get(p),
            "total_equity": equity.get(p),
            "total_debt": debt.get(p),
            "operating_cash_flow": ocf.get(p),
            "capex": capex.get(p),
            "dividends_paid": divs.get(p),
        }
    return out


def run_once() -> int:
    with source_run("fundamentals") as run:
        try:
            import yfinance as yf  # type: ignore
        except ImportError:
            run.skip = True
            return 0

        limiter = for_source("yfinance")
        rows_written = 0

        with SessionLocal() as s:
            companies = (
                s.query(Company).filter(Company.is_benchmark.is_(False)).all()
            )
            for c in companies:
                limiter.acquire()
                try:
                    tkr = yf.Ticker(c.ticker)
                    quarterly = _collect_quarterly(tkr)
                    divs_series = tkr.dividends  # per-share dividend events
                except Exception as exc:  # noqa: BLE001
                    log.warning("%s: %s", c.ticker, exc)
                    continue

                for period_end, attrs in quarterly.items():
                    fcf, inv_cap, nopat, roic = _compute_derived(
                        attrs["operating_income"],
                        attrs["total_debt"],
                        attrs["total_equity"],
                        attrs["operating_cash_flow"],
                        attrs["capex"],
                    )
                    # Dividends per share for the quarter from the dividends series
                    dps = None
                    if divs_series is not None and not divs_series.empty:
                        # Sum all dividend payouts in the 3 months ending period_end
                        qstart = date(period_end.year, ((period_end.month - 1) // 3) * 3 + 1, 1)
                        try:
                            window = divs_series[
                                (divs_series.index.date >= qstart)
                                & (divs_series.index.date <= period_end)
                            ]
                            if len(window) > 0:
                                dps = float(window.sum())
                        except Exception:
                            pass

                    rec = s.get(Fundamental, (c.company_id, period_end)) or Fundamental(
                        company_id=c.company_id, period_end=period_end
                    )
                    rec.fiscal_period = _fiscal_period(period_end)
                    rec.revenue = attrs["revenue"]
                    rec.gross_profit = attrs["gross_profit"]
                    rec.operating_income = attrs["operating_income"]
                    rec.net_income = attrs["net_income"]
                    rec.eps_diluted = attrs["eps_diluted"]
                    rec.shares_diluted = attrs["shares_diluted"]
                    rec.total_assets = attrs["total_assets"]
                    rec.total_equity = attrs["total_equity"]
                    rec.total_debt = attrs["total_debt"]
                    rec.operating_cash_flow = attrs["operating_cash_flow"]
                    rec.capex = attrs["capex"]
                    rec.dividends_paid = attrs["dividends_paid"]
                    rec.dividends_per_share = dps
                    rec.free_cash_flow = fcf
                    rec.invested_capital = inv_cap
                    rec.nopat = nopat
                    rec.roic = roic
                    rec.fetched_at = datetime.utcnow()
                    s.merge(rec)
                    rows_written += 1
            s.commit()

        run.rows_fetched = rows_written
        return rows_written


if __name__ == "__main__":
    run_once()
