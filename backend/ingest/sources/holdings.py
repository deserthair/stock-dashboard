"""Institutional holdings + insider transactions ingest.

Two cohorts in one worker (they share yfinance plumbing):

  **Institutional holdings** — top ~10 institutional holders per ticker
  via `Ticker.institutional_holders`. Written to institutions +
  institutional_holdings. Writes a new snapshot row per run tagged with
  today's date, so quarter-over-quarter deltas accumulate naturally.

  **Insider transactions** — Form 4 activity via `Ticker.insider_transactions`.
  Keyed by a stable hash of (ticker, insider_name, transaction_date,
  shares, transaction_type) since yfinance doesn't expose the Form 4
  accession_number. Idempotent — re-running adds nothing new.

All fetches graceful-skip on ImportError or empty yfinance frames. In
the sandbox this simply logs zero rows; seed provides demo data so the
UI renders."""

from __future__ import annotations

import hashlib
import logging
import math
from datetime import date, datetime

from app.db import SessionLocal
from app.models import (
    Company,
    InsiderTransaction,
    Institution,
    InstitutionalHolding,
)

from ..rate_limiter import for_source
from ..source_run import source_run

log = logging.getLogger("holdings")


def _clean(v):
    if v is None:
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
        return v
    except Exception:
        return None


def _get_or_make_institution(s, name: str, kind: str = "institution") -> Institution:
    existing = s.query(Institution).filter_by(name=name).one_or_none()
    if existing is not None:
        return existing
    inst = Institution(name=name[:256], kind=kind)
    s.add(inst)
    s.flush()
    return inst


def _classify_kind(name: str) -> str:
    low = name.lower()
    if any(k in low for k in ("vanguard", "blackrock", "state street", "ssga", "invesco", "ishares")):
        return "index_fund"
    if any(k in low for k in ("pershing", "elliott", "icahn", "trian", "third point", "starboard")):
        return "activist"
    if any(k in low for k in ("berkshire", "bridgewater", "citadel", "renaissance", "millennium",
                               "point72", "two sigma", "d.e. shaw", "aqr", "baupost")):
        return "hedge_fund"
    return "institution"


def _txn_hash(ticker: str, insider: str, dt: date, shares, ttype: str) -> str:
    raw = f"{ticker}|{insider}|{dt.isoformat()}|{shares}|{ttype}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _classify_txn_type(raw: str | None) -> str:
    """Coerce yfinance's various transaction-type strings to our 5 canonical
    buckets: buy / sell / option_exercise / gift / rsu_vest."""
    if not raw:
        return "sell"  # conservative — yfinance defaults are usually sells
    low = raw.lower()
    if "exercise" in low:
        return "option_exercise"
    if "gift" in low:
        return "gift"
    if "rsu" in low or "vest" in low or "award" in low:
        return "rsu_vest"
    if "purchase" in low or "buy" in low or "acquisition" in low or "acquired" in low:
        return "buy"
    return "sell"


def run_once() -> int:
    with source_run("holdings") as run:
        try:
            import yfinance as yf  # type: ignore
        except ImportError:
            run.skip = True
            return 0

        limiter = for_source("yfinance")
        rows_written = 0
        as_of = date.today()

        with SessionLocal() as s:
            companies = s.query(Company).filter(Company.is_benchmark.is_(False)).all()
            for c in companies:
                limiter.acquire()
                try:
                    tkr = yf.Ticker(c.ticker)
                    inst_df = getattr(tkr, "institutional_holders", None)
                    txn_df = getattr(tkr, "insider_transactions", None)
                except Exception as exc:  # noqa: BLE001
                    log.warning("%s: %s", c.ticker, exc)
                    continue

                # --- institutional holdings -----------------------------------
                if inst_df is not None and not inst_df.empty:
                    for _, row in inst_df.iterrows():
                        name = str(_clean(row.get("Holder")) or "").strip()
                        if not name:
                            continue
                        inst = _get_or_make_institution(s, name, _classify_kind(name))

                        shares = _clean(row.get("Shares"))
                        value = _clean(row.get("Value"))
                        pct = _clean(row.get("pctHeld"))
                        if pct is not None:
                            pct = float(pct) * 100  # yfinance returns 0-1

                        rec = s.get(
                            InstitutionalHolding,
                            (c.company_id, inst.institution_id, as_of),
                        )
                        if rec is None:
                            rec = InstitutionalHolding(
                                company_id=c.company_id,
                                institution_id=inst.institution_id,
                                as_of_date=as_of,
                            )
                            s.add(rec)
                        rec.shares = int(shares) if shares is not None else None
                        rec.value_usd = float(value) if value is not None else None
                        rec.pct_of_outstanding = float(pct) if pct is not None else None

                        # Compute delta vs most recent prior snapshot
                        prior = (
                            s.query(InstitutionalHolding)
                            .filter(
                                InstitutionalHolding.company_id == c.company_id,
                                InstitutionalHolding.institution_id == inst.institution_id,
                                InstitutionalHolding.as_of_date < as_of,
                            )
                            .order_by(InstitutionalHolding.as_of_date.desc())
                            .first()
                        )
                        if prior is not None and prior.shares and rec.shares is not None:
                            rec.shares_change = rec.shares - prior.shares
                            if prior.shares:
                                rec.pct_change = round(
                                    (rec.shares / prior.shares - 1) * 100, 2
                                )
                        rec.source = "yfinance"
                        rows_written += 1

                # --- insider transactions ------------------------------------
                if txn_df is not None and not txn_df.empty:
                    for _, row in txn_df.iterrows():
                        insider = str(_clean(row.get("Insider")) or "").strip()
                        if not insider:
                            continue
                        raw_date = _clean(row.get("Start Date"))
                        try:
                            txn_date = (
                                raw_date.date() if hasattr(raw_date, "date") else date.fromisoformat(str(raw_date)[:10])
                            )
                        except (TypeError, ValueError):
                            continue
                        shares = _clean(row.get("Shares"))
                        ttype = _classify_txn_type(_clean(row.get("Transaction")))
                        value = _clean(row.get("Value"))

                        acc = _txn_hash(c.ticker, insider, txn_date, shares, ttype)
                        existing = (
                            s.query(InsiderTransaction)
                            .filter_by(accession_number=acc)
                            .one_or_none()
                        )
                        if existing is not None:
                            continue

                        title = str(_clean(row.get("Position")) or "")
                        s.add(
                            InsiderTransaction(
                                company_id=c.company_id,
                                accession_number=acc,
                                insider_name=insider[:128],
                                insider_title=title[:128] or None,
                                insider_is_officer="officer" in title.lower() or "ceo" in title.lower() or "cfo" in title.lower(),
                                insider_is_director="director" in title.lower(),
                                transaction_date=txn_date,
                                filed_at=datetime.utcnow(),
                                transaction_type=ttype,
                                shares=int(shares) if shares is not None else None,
                                price=None,
                                value_usd=float(value) if value is not None else None,
                            )
                        )
                        rows_written += 1

            s.commit()

        run.rows_fetched = rows_written
        return rows_written


if __name__ == "__main__":
    run_once()
