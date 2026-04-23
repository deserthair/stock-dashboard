"""FRED macro ingest.

Pulls time series from the St. Louis Fed FRED API and writes to
`macro_observations` + refreshes aggregate metadata in `macro_series`.

Requires FRED_API_KEY. Skipped if missing."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx

from app.config import get_settings
from app.db import SessionLocal
from app.models import MacroObservation, MacroSeries

from ..rate_limiter import for_source
from ..source_run import source_run

SERIES = [
    ("PBEEFUSDM",      "Live Cattle (PBEEF)"),
    ("WPU0211",        "Chicken (WPU0211)"),
    ("PWHEAMTUSDM",    "Wheat (PWHEAMT)"),
    ("GASREGW",        "Retail Gas (GASREGW)"),
    ("UMCSENT",        "Cons Sent (UMCSENT)"),
    ("CES7072200003",  "Food Wages (CES707)"),
    ("UNRATE",         "Unemployment"),
    ("DGS10",          "10Y Treasury"),
    ("DEXUSEU",        "USD/EUR"),
]

BASE = "https://api.stlouisfed.org/fred/series/observations"


def _fetch_series(client: httpx.Client, series_id: str, api_key: str) -> list[tuple[date, float]]:
    start = (datetime.utcnow() - timedelta(days=365)).date().isoformat()
    r = client.get(
        BASE,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start,
        },
        timeout=20.0,
    )
    r.raise_for_status()
    obs = r.json().get("observations", [])
    out: list[tuple[date, float]] = []
    for row in obs:
        v = row.get("value")
        if v in (".", "", None):
            continue
        try:
            out.append((date.fromisoformat(row["date"]), float(v)))
        except (ValueError, KeyError):
            continue
    return out


def _summarize(points: list[tuple[date, float]]) -> tuple[float | None, float | None, str, float]:
    if not points:
        return None, None, "flat", 0.0
    points = sorted(points, key=lambda p: p[0])
    latest_date, latest_value = points[-1]
    cutoff = latest_date - timedelta(days=90)
    earlier = [v for d, v in points if d <= cutoff]
    if not earlier:
        return latest_value, None, "flat", 0.0
    ref = earlier[-1]
    if ref == 0:
        return latest_value, None, "flat", 0.0
    change_pct = (latest_value / ref - 1) * 100
    direction = "up" if change_pct > 0.1 else "down" if change_pct < -0.1 else "flat"
    bar = min(25.0, abs(change_pct) * 2.5)  # visual scale (cap at ~25% of half-width)
    return latest_value, round(change_pct, 2), direction, round(bar, 1)


def run_once() -> int:
    with source_run("macro") as run:
        settings = get_settings()
        if not settings.fred_api_key:
            print("[macro] FRED_API_KEY not set; skipping")
            run.skip = True
            return 0

        limiter = for_source("fred")
        rows = 0
        with httpx.Client() as client, SessionLocal() as s:
            for series_id, label in SERIES:
                limiter.acquire()
                try:
                    points = _fetch_series(client, series_id, settings.fred_api_key)
                except httpx.HTTPError as exc:
                    print(f"[macro] {series_id}: {exc}")
                    continue

                for d, v in points:
                    row = s.get(MacroObservation, (series_id, d))
                    if row is None:
                        s.add(MacroObservation(series_id=series_id, obs_date=d, value=v))
                        rows += 1
                    else:
                        row.value = v

                latest_val, change_pct, direction, bar = _summarize(points)
                meta = s.get(MacroSeries, series_id) or MacroSeries(series_id=series_id)
                meta.label = label
                meta.latest_value = latest_val
                meta.latest_date = points[-1][0] if points else None
                meta.change_90d_pct = change_pct
                meta.change_label = (
                    f"{'+' if (change_pct or 0) > 0 else ''}{change_pct:.1f}%"
                    if change_pct is not None else None
                )
                meta.direction = direction
                meta.bar_width_pct = bar
                s.merge(meta)

            s.commit()

        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
