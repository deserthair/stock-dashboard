"""Unit tests for earnings outcome computation."""

from datetime import date

from app.models import Company, Earnings, PriceDaily
from app.db import SessionLocal
from analysis.outcomes import compute


def _mint_company(s, ticker="TST") -> int:
    existing = s.query(Company).filter_by(ticker=ticker).one_or_none()
    if existing is not None:
        return existing.company_id
    c = Company(ticker=ticker, name=f"Test {ticker}", is_benchmark=False)
    s.add(c)
    s.flush()
    return c.company_id


def test_beat_rally(seeded_db):
    with SessionLocal() as s:
        cid = _mint_company(s)
        s.query(Earnings).filter_by(company_id=cid).delete()
        s.query(PriceDaily).filter_by(company_id=cid).delete()

        # Stock at 100 before earnings, 105 after → +5% 1D rally
        for d, v in [
            (date(2026, 3, 10), 100.0),  # T-1
            (date(2026, 3, 11), 100.5),  # report day
            (date(2026, 3, 12), 105.0),  # T+1
            (date(2026, 3, 16), 108.0),  # T+5
        ]:
            s.add(PriceDaily(company_id=cid, trade_date=d, close=v))
        earn = Earnings(
            company_id=cid,
            report_date=date(2026, 3, 11),
            eps_estimate=1.00,
            eps_actual=1.20,  # BEAT
        )
        s.add(earn)
        s.flush()

        oc = compute(s, earn)
        assert oc.eps_beat is True
        assert oc.post_earnings_1d_return == 5.0
        assert oc.post_earnings_5d_return == 8.0
        assert oc.reaction == "beat_rally"


def test_miss_sell(seeded_db):
    with SessionLocal() as s:
        cid = _mint_company(s, "TST2")
        s.query(Earnings).filter_by(company_id=cid).delete()
        s.query(PriceDaily).filter_by(company_id=cid).delete()

        for d, v in [
            (date(2026, 3, 10), 100.0),
            (date(2026, 3, 12), 90.0),
        ]:
            s.add(PriceDaily(company_id=cid, trade_date=d, close=v))
        earn = Earnings(
            company_id=cid,
            report_date=date(2026, 3, 11),
            eps_estimate=1.50,
            eps_actual=1.20,
        )
        s.add(earn)
        s.flush()

        oc = compute(s, earn)
        assert oc.eps_beat is False
        assert oc.post_earnings_1d_return == -10.0
        assert oc.reaction == "miss_sell"


def test_no_reaction_without_prices(seeded_db):
    with SessionLocal() as s:
        cid = _mint_company(s, "TST3")
        s.query(Earnings).filter_by(company_id=cid).delete()
        s.query(PriceDaily).filter_by(company_id=cid).delete()
        earn = Earnings(
            company_id=cid,
            report_date=date(2026, 3, 11),
            eps_estimate=1.00,
            eps_actual=0.99,
        )
        s.add(earn)
        s.flush()

        oc = compute(s, earn)
        assert oc.eps_beat is False
        assert oc.post_earnings_1d_return is None
        assert oc.reaction is None
