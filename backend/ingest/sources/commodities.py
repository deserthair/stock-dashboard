"""Commodity futures + PPI ingest.

Pulls daily closes for:

  **CME / ICE front-month futures (via yfinance):**
  - LE=F   Live Cattle         (beef)
  - GF=F   Feeder Cattle       (beef / ranch margin)
  - HE=F   Lean Hogs           (pork)
  - ZC=F   Corn                (poultry / beef feed)
  - ZS=F   Soybeans            (poultry / pork feed)
  - ZW=F   Wheat               (pizza / buns)
  - KC=F   Coffee              (SBUX)
  - SB=F   Sugar               (soft drinks / sweeteners)
  - OJ=F   Orange Juice        (SBUX refreshers)
  - DC=F   Class III Milk      (dairy / cheese)
  - CL=F   Crude Oil           (fuel / logistics)

  **BLS PPI via FRED (for commodities without tradable futures):**
  - WPU01830302   Lettuce
  - WPU01830306   Tomatoes
  - WPU0211       Poultry (chicken)

Writes daily rows to `commodity_prices`. Ensures metadata rows in
`commodity_meta`. yfinance failures are logged and skipped per-ticker."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import httpx

from app.config import get_settings
from app.db import SessionLocal
from app.models import CommodityMeta, CommodityPrice

from ..rate_limiter import for_source
from ..source_run import source_run

log = logging.getLogger("commodities")


FUTURES_META = [
    # (symbol, label, category, unit, exposure)
    ("LE=F",  "Live Cattle",        "protein", "cents/lb", ["TXRH", "MCD", "CMG"]),
    ("GF=F",  "Feeder Cattle",      "protein", "cents/lb", ["TXRH", "MCD"]),
    ("HE=F",  "Lean Hogs",          "protein", "cents/lb", ["DPZ", "SBUX", "QSR"]),
    ("ZC=F",  "Corn",               "grain",   "cents/bu", ["WING", "CAVA", "QSR"]),
    ("ZS=F",  "Soybeans",           "grain",   "cents/bu", ["WING", "CAVA", "QSR"]),
    ("ZW=F",  "Wheat",              "grain",   "cents/bu", ["DPZ", "SBUX"]),
    ("KC=F",  "Coffee",             "soft",    "cents/lb", ["SBUX"]),
    ("SB=F",  "Sugar",              "soft",    "cents/lb", ["SBUX", "QSR"]),
    ("OJ=F",  "Orange Juice",       "soft",    "cents/lb", ["SBUX"]),
    ("DC=F",  "Class III Milk",     "dairy",   "$/cwt",    ["SBUX", "CMG"]),
    ("CL=F",  "WTI Crude Oil",      "energy",  "$/bbl",    ["ALL"]),
]

FRED_META = [
    # (symbol, label, category, unit, exposure, series_id)
    ("PPI_POULTRY",  "Poultry (PPI)",  "protein", "index", ["WING", "CAVA", "QSR"], "WPU0211"),
    ("PPI_LETTUCE",  "Lettuce (PPI)",  "produce", "index", ["CMG", "CAVA", "TXRH"], "WPU01830302"),
    ("PPI_TOMATOES", "Tomatoes (PPI)", "produce", "index", ["CMG", "DPZ"],          "WPU01830306"),
]


def _ensure_meta(s) -> None:
    for symbol, label, category, unit, exposure in FUTURES_META:
        rec = s.get(CommodityMeta, symbol) or CommodityMeta(symbol=symbol)
        rec.label = label
        rec.category = category
        rec.unit = unit
        rec.exposure = exposure
        rec.source = "yfinance"
        rec.series_id = None
        s.merge(rec)
    for symbol, label, category, unit, exposure, series_id in FRED_META:
        rec = s.get(CommodityMeta, symbol) or CommodityMeta(symbol=symbol)
        rec.label = label
        rec.category = category
        rec.unit = unit
        rec.exposure = exposure
        rec.source = "fred"
        rec.series_id = series_id
        s.merge(rec)
    s.commit()


def _run_futures(s) -> int:
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return 0
    limiter = for_source("yfinance")
    rows = 0
    for symbol, _, _, _, _ in FUTURES_META:
        limiter.acquire()
        try:
            hist = yf.Ticker(symbol).history(period="5y", interval="1d")
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: %s", symbol, exc)
            continue
        if hist is None or hist.empty:
            continue
        for idx, row in hist.iterrows():
            d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
            rec = s.get(CommodityPrice, (symbol, d)) or CommodityPrice(
                symbol=symbol, trade_date=d
            )
            rec.close = float(row["Close"]) if row["Close"] == row["Close"] else None
            rec.volume = int(row["Volume"]) if row["Volume"] == row["Volume"] else None
            s.merge(rec)
            rows += 1
    return rows


def _run_fred(s) -> int:
    settings = get_settings()
    if not settings.fred_api_key:
        log.info("FRED_API_KEY not set; skipping PPI commodities")
        return 0
    limiter = for_source("fred")
    rows = 0
    start = (datetime.utcnow() - timedelta(days=5 * 365)).date().isoformat()
    with httpx.Client() as client:
        for symbol, _, _, _, _, series_id in FRED_META:
            limiter.acquire()
            try:
                r = client.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": settings.fred_api_key,
                        "file_type": "json",
                        "observation_start": start,
                    },
                    timeout=20.0,
                )
                r.raise_for_status()
            except httpx.HTTPError as exc:
                log.warning("%s: %s", series_id, exc)
                continue
            for row in r.json().get("observations", []):
                v = row.get("value")
                if v in (".", "", None):
                    continue
                try:
                    d = date.fromisoformat(row["date"])
                    val = float(v)
                except (KeyError, ValueError):
                    continue
                rec = s.get(CommodityPrice, (symbol, d)) or CommodityPrice(
                    symbol=symbol, trade_date=d
                )
                rec.close = val
                s.merge(rec)
                rows += 1
    return rows


def run_once() -> int:
    with source_run("commodities") as run:
        with SessionLocal() as s:
            _ensure_meta(s)
            n1 = _run_futures(s)
            n2 = _run_fred(s)
            s.commit()
        run.rows_fetched = n1 + n2
        return n1 + n2


if __name__ == "__main__":
    run_once()
