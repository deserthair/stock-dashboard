"""Finnhub earnings-calendar ingest.

Pulls the earnings calendar for the tracked universe and upserts into
`earnings`. Requires FINNHUB_API_KEY. Skipped if missing."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx

from app.config import get_settings
from app.db import SessionLocal
from app.models import Company, Earnings

from ..rate_limiter import for_source
from ..source_run import source_run

BASE = "https://finnhub.io/api/v1/calendar/earnings"


def _fetch(client: httpx.Client, ticker: str, api_key: str) -> list[dict]:
    frm = datetime.utcnow().date()
    to = frm + timedelta(days=90)
    r = client.get(
        BASE,
        params={"from": frm.isoformat(), "to": to.isoformat(), "symbol": ticker, "token": api_key},
        timeout=20.0,
    )
    r.raise_for_status()
    return r.json().get("earningsCalendar", [])


def run_once() -> int:
    with source_run("earnings") as run:
        settings = get_settings()
        if not settings.finnhub_api_key:
            print("[earnings] FINNHUB_API_KEY not set; skipping")
            run.skip = True
            return 0

        limiter = for_source("finnhub")
        rows = 0
        with httpx.Client() as client, SessionLocal() as s:
            for c in s.query(Company).all():
                limiter.acquire()
                try:
                    data = _fetch(client, c.ticker, settings.finnhub_api_key)
                except httpx.HTTPError as exc:
                    print(f"[earnings] {c.ticker}: {exc}")
                    continue
                for entry in data:
                    try:
                        d = date.fromisoformat(entry["date"])
                    except (KeyError, ValueError):
                        continue
                    rec = (
                        s.query(Earnings)
                        .filter_by(company_id=c.company_id, report_date=d)
                        .one_or_none()
                    )
                    if rec is None:
                        rec = Earnings(company_id=c.company_id, report_date=d)
                        s.add(rec)
                        rows += 1
                    rec.fiscal_period = (
                        f"Q{entry['quarter']} {entry['year']}"
                        if entry.get("quarter") and entry.get("year")
                        else rec.fiscal_period
                    )
                    rec.time_of_day = {"bmo": "BMO", "amc": "AMC"}.get(
                        (entry.get("hour") or "").lower(), rec.time_of_day
                    )
                    rec.eps_estimate = entry.get("epsEstimate") or rec.eps_estimate
                    rec.eps_actual = entry.get("epsActual") or rec.eps_actual
                    rec.revenue_estimate = entry.get("revenueEstimate") or rec.revenue_estimate
                    rec.revenue_actual = entry.get("revenueActual") or rec.revenue_actual
                    if rec.eps_estimate and rec.eps_actual:
                        rec.eps_surprise_pct = round(
                            (rec.eps_actual - rec.eps_estimate)
                            / max(abs(rec.eps_estimate), 1e-9)
                            * 100,
                            2,
                        )
            s.commit()

        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
