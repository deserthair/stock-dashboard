"""NOAA weather ingest.

Pulls daily observations from NOAA's free v1 API for a small set of
stations covering metros with high restaurant-industry concentration.
No key required for small volumes (rate-limited by IP)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx

from app.db import SessionLocal
from app.models import WeatherObservation

from ..rate_limiter import for_source
from ..source_run import source_run

BASE = "https://www.ncei.noaa.gov/access/services/data/v1"

# GHCND station ids — NYC Central Park, Chicago O'Hare, LA Downtown,
# Dallas Love, Atlanta Hartsfield, Denver Stapleton.
STATIONS = [
    "USW00094728",  # NYC
    "USW00094846",  # Chicago
    "USW00023174",  # LAX / LA
    "USW00013960",  # Dallas
    "USW00013874",  # Atlanta
    "USW00023062",  # Denver
]


def _fetch(client: httpx.Client, station: str, start: date, end: date) -> list[dict]:
    params = {
        "dataset": "daily-summaries",
        "dataTypes": "TAVG,TMAX,TMIN,PRCP",
        "stations": station,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "format": "json",
        "units": "standard",
    }
    r = client.get(BASE, params=params, timeout=30.0, headers={"User-Agent": "restin/0.1"})
    r.raise_for_status()
    try:
        return r.json() or []
    except ValueError:
        return []


def run_once() -> int:
    with source_run("weather") as run:
        limiter = for_source("noaa")
        rows = 0
        end = date.today()
        start = end - timedelta(days=30)
        with httpx.Client() as client, SessionLocal() as s:
            for station in STATIONS:
                limiter.acquire()
                try:
                    data = _fetch(client, station, start, end)
                except httpx.HTTPError as exc:
                    print(f"[weather] {station}: {exc}")
                    continue
                for row in data:
                    try:
                        d = datetime.strptime(row["DATE"], "%Y-%m-%d").date()
                    except (KeyError, ValueError):
                        continue
                    rec = s.get(WeatherObservation, (station, d))
                    if rec is None:
                        rec = WeatherObservation(station_id=station, obs_date=d)
                        s.add(rec)
                        rows += 1
                    for attr, key in (("tavg_f", "TAVG"), ("tmax_f", "TMAX"), ("tmin_f", "TMIN"), ("prcp_in", "PRCP")):
                        v = row.get(key)
                        if v not in (None, "", "M"):
                            try:
                                setattr(rec, attr, float(v))
                            except ValueError:
                                pass
            s.commit()
        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
