"""Google Trends ingest via pytrends (unofficial).

Tracks three query cohorts:

  - **company**  per-ticker brand query ("Chipotle", "Starbucks", ...)
  - **menu**     per-ticker menu-item query ("chipotle protein bowl", etc.)
  - **segment**  food-industry segment queries ("fast casual", "QSR earnings", …)
  - **macro**    consumer-behavior queries ("restaurant inflation", "fast food prices", …)

pytrends scrapes Google Trends — no official API, rate-limited, flaky.
The worker is graceful on 429s and empty responses; if pytrends isn't
installed the run logs `skipped` without crashing.

Writes weekly observations to `trends_observations`, keyed by query_id.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime

from app.db import SessionLocal
from app.models import Company, TrendsObservation, TrendsQuery

from ..source_run import source_run

log = logging.getLogger("trends")


# Per-ticker queries — populated dynamically from the universe on first run.
MENU_QUERIES = {
    "CMG":  "chipotle bowl",
    "SBUX": "starbucks drink",
    "MCD":  "mcdonalds menu",
    "CAVA": "cava bowl",
    "TXRH": "texas roadhouse",
    "WING": "wingstop flavors",
    "DPZ":  "dominos pizza",
    "QSR":  "tim hortons",
}

SEGMENT_QUERIES = [
    ("fast casual restaurants", "segment"),
    ("QSR earnings", "segment"),
    ("casual dining", "segment"),
    ("fast food delivery", "segment"),
]

MACRO_QUERIES = [
    ("restaurant inflation", "macro"),
    ("fast food prices", "macro"),
    ("dining out", "macro"),
    ("grocery vs restaurant", "macro"),
]


def _ensure_query_rows(s) -> None:
    """Make sure every query we care about has a TrendsQuery row."""
    companies = s.query(Company).filter(Company.is_benchmark.is_(False)).all()
    for c in companies:
        # Company brand query (e.g., "Chipotle")
        brand = c.name.split(",")[0].split(" Corporation")[0].split(" Inc")[0].strip()
        for q, label, category, ticker in (
            (brand, f"{c.ticker} brand", "company", c.ticker),
            (MENU_QUERIES.get(c.ticker, ""), f"{c.ticker} menu", "menu", c.ticker),
        ):
            if not q:
                continue
            existing = s.query(TrendsQuery).filter_by(query=q).one_or_none()
            if existing is None:
                s.add(
                    TrendsQuery(query=q, label=label, category=category, ticker=ticker)
                )
    for q, cat in SEGMENT_QUERIES + MACRO_QUERIES:
        if s.query(TrendsQuery).filter_by(query=q).one_or_none() is None:
            s.add(TrendsQuery(query=q, label=q, category=cat))
    s.commit()


def _write_series(s, tq: TrendsQuery, series) -> int:
    """Write a pandas Series (index=datetime, values=interest) to the DB."""
    rows = 0
    if series is None or len(series) == 0:
        return 0
    mean = float(series.mean()) if series.mean() else 1.0
    for ts, v in series.items():
        d = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])
        rec = s.get(TrendsObservation, (tq.query_id, d))
        if rec is None:
            rec = TrendsObservation(query_id=tq.query_id, obs_date=d)
            s.add(rec)
        val = float(v) if v is not None else None
        rec.value = val
        rec.ratio_to_mean = (val / mean) if val is not None and mean else None
        rows += 1
    tq.last_fetched_at = datetime.utcnow()
    return rows


def run_once(timeframe: str = "today 5-y") -> int:
    """Pull weekly interest over the last 5 years for every tracked query."""
    with source_run("trends") as run:
        try:
            from pytrends.request import TrendReq  # type: ignore
        except ImportError:
            log.info("pytrends not installed; skipping")
            run.skip = True
            return 0

        rows = 0
        pt = TrendReq(hl="en-US", tz=300, timeout=(10, 25), retries=2, backoff_factor=0.5)
        with SessionLocal() as s:
            _ensure_query_rows(s)
            queries = s.query(TrendsQuery).all()

            for tq in queries:
                try:
                    pt.build_payload([tq.query], timeframe=timeframe, geo="US")
                    df = pt.interest_over_time()
                except Exception as exc:  # noqa: BLE001 — pytrends raises opaque errors
                    log.warning("%s: %s", tq.query, exc)
                    time.sleep(1)
                    continue
                if df is None or df.empty or tq.query not in df.columns:
                    continue
                rows += _write_series(s, tq, df[tq.query])
                # Be polite; Google 429s aggressively.
                time.sleep(1.5)

            s.commit()

        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
