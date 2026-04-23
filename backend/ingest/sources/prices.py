"""yfinance price ingest.

Writes to `prices_daily` and refreshes the denormalized `company_signals`
change_*_pct + last_price fields. Skipped silently if yfinance fails."""

from __future__ import annotations

from datetime import date

from app.db import SessionLocal
from app.models import Company, CompanySignal, PriceDaily

from ..rate_limiter import for_source
from ..source_run import source_run


def run_once() -> int:
    with source_run("prices") as run:
        try:
            import yfinance as yf  # type: ignore
        except ImportError:
            run.skip = True
            return 0

        limiter = for_source("yfinance")
        rows_written = 0
        with SessionLocal() as s:
            companies = s.query(Company).all()
            for c in companies:
                limiter.acquire()
                try:
                    hist = yf.Ticker(c.ticker).history(period="45d", interval="1d")
                except Exception as exc:
                    print(f"[prices] {c.ticker}: {exc}")
                    continue
                if hist is None or hist.empty:
                    continue

                for idx, row in hist.iterrows():
                    d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
                    pd = s.get(PriceDaily, (c.company_id, d))
                    if pd is None:
                        pd = PriceDaily(company_id=c.company_id, trade_date=d)
                        s.add(pd)
                    pd.open = float(row["Open"])
                    pd.high = float(row["High"])
                    pd.low = float(row["Low"])
                    pd.close = float(row["Close"])
                    pd.adj_close = float(row.get("Adj Close", row["Close"]))
                    pd.volume = int(row["Volume"])
                    rows_written += 1

                closes = hist["Close"].dropna().tolist()
                # Benchmarks get the minimal signal update (last_price + Δ); they are
                # hidden from /api/universe but feed rs_vs_xly for the tracked companies.
                if c.is_benchmark:
                    if len(closes) >= 2:
                        sig = s.get(CompanySignal, c.company_id) or CompanySignal(
                            company_id=c.company_id
                        )
                        sig.last_price = float(closes[-1])
                        sig.change_1d_pct = round((closes[-1] / closes[-2] - 1) * 100, 2)
                        if len(closes) >= 31:
                            sig.change_30d_pct = round((closes[-1] / closes[-31] - 1) * 100, 2)
                        s.merge(sig)
                    continue

                if len(closes) >= 2:
                    sig = s.get(CompanySignal, c.company_id) or CompanySignal(
                        company_id=c.company_id
                    )
                    sig.last_price = float(closes[-1])
                    sig.change_1d_pct = round((closes[-1] / closes[-2] - 1) * 100, 2)
                    if len(closes) >= 6:
                        sig.change_5d_pct = round((closes[-1] / closes[-6] - 1) * 100, 2)
                    if len(closes) >= 31:
                        sig.change_30d_pct = round((closes[-1] / closes[-31] - 1) * 100, 2)
                    s.merge(sig)

            # Pass 2: now that all close-changes are up to date, recompute rs_vs_xly
            xly = s.query(Company).filter(Company.ticker == "XLY").one_or_none()
            if xly:
                xly_sig = s.get(CompanySignal, xly.company_id)
                if xly_sig and xly_sig.change_30d_pct is not None:
                    for c in companies:
                        if c.is_benchmark:
                            continue
                        sig = s.get(CompanySignal, c.company_id)
                        if sig and sig.change_30d_pct is not None:
                            sig.rs_vs_xly = round(
                                sig.change_30d_pct - xly_sig.change_30d_pct, 1
                            )

            s.commit()

        run.rows_fetched = rows_written
        return rows_written


if __name__ == "__main__":
    run_once()
