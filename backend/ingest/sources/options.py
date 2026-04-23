"""Options-activity ingest.

For each tracked ticker, pulls the front-expiry option chain via yfinance
and computes a single daily snapshot:

  - ATM implied volatility — interpolated from the two strikes bracketing
    the current price (annualized decimal, e.g. 0.32 for 32%)
  - Total call + put volume and open interest across all strikes
  - Put/call ratios on both volume and open interest

Writes one row per (company, obs_date) to `options_snapshots`. The UI
charts the IV trend and P/C ratio over time; a spike in either suggests
elevated expectations going into an earnings print."""

from __future__ import annotations

import logging
from datetime import date, datetime

from app.db import SessionLocal
from app.models import Company, CompanySignal, OptionsSnapshot

from ..rate_limiter import for_source
from ..source_run import source_run

log = logging.getLogger("options")


def _atm_iv(calls_df, puts_df, underlying: float) -> float | None:
    """Linear-interpolate IV at the two strikes bracketing `underlying`.
    Averages the call and put IV for a smoother estimate."""
    if calls_df is None or puts_df is None:
        return None
    import numpy as np

    def _iv_for(df) -> float | None:
        if df.empty or "strike" not in df.columns or "impliedVolatility" not in df.columns:
            return None
        strikes = df["strike"].astype(float).to_numpy()
        ivs = df["impliedVolatility"].astype(float).to_numpy()
        idx = np.argsort(strikes)
        strikes, ivs = strikes[idx], ivs[idx]
        # Interpolate at `underlying`
        return float(np.interp(underlying, strikes, ivs))

    iv_c = _iv_for(calls_df)
    iv_p = _iv_for(puts_df)
    if iv_c is None and iv_p is None:
        return None
    if iv_c is None:
        return iv_p
    if iv_p is None:
        return iv_c
    return (iv_c + iv_p) / 2


def run_once() -> int:
    with source_run("options") as run:
        try:
            import yfinance as yf  # type: ignore
        except ImportError:
            run.skip = True
            return 0

        limiter = for_source("yfinance")
        rows = 0
        today = date.today()
        with SessionLocal() as s:
            companies = s.query(Company).filter(Company.is_benchmark.is_(False)).all()
            for c in companies:
                limiter.acquire()
                try:
                    tkr = yf.Ticker(c.ticker)
                    expiries = tkr.options or ()
                    if not expiries:
                        continue
                    expiry = expiries[0]
                    chain = tkr.option_chain(expiry)
                except Exception as exc:  # noqa: BLE001
                    log.warning("%s: %s", c.ticker, exc)
                    continue

                sig = s.get(CompanySignal, c.company_id)
                underlying = float(sig.last_price) if sig and sig.last_price else None
                if underlying is None:
                    continue

                calls, puts = chain.calls, chain.puts
                atm_iv = _atm_iv(calls, puts, underlying)
                call_vol = int(calls["volume"].fillna(0).sum()) if "volume" in calls else 0
                put_vol = int(puts["volume"].fillna(0).sum()) if "volume" in puts else 0
                call_oi = int(calls["openInterest"].fillna(0).sum()) if "openInterest" in calls else 0
                put_oi = int(puts["openInterest"].fillna(0).sum()) if "openInterest" in puts else 0

                rec = s.get(OptionsSnapshot, (c.company_id, today)) or OptionsSnapshot(
                    company_id=c.company_id, obs_date=today
                )
                try:
                    rec.expiry = date.fromisoformat(expiry)
                except ValueError:
                    rec.expiry = None
                rec.underlying_price = underlying
                rec.atm_iv = atm_iv
                rec.total_call_volume = call_vol
                rec.total_put_volume = put_vol
                rec.total_call_oi = call_oi
                rec.total_put_oi = put_oi
                rec.put_call_volume_ratio = (put_vol / call_vol) if call_vol else None
                rec.put_call_oi_ratio = (put_oi / call_oi) if call_oi else None
                s.merge(rec)
                rows += 1
            s.commit()

        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
