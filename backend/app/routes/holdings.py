from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Company,
    InsiderTransaction,
    Institution,
    InstitutionalHolding,
)
from ..schemas import (
    CompanyHoldingsOut,
    InsiderNetFlow,
    InsiderTransactionRow,
    InstitutionOut,
    InstitutionalHoldingRow,
    UniverseHoldingsOut,
    UniverseHoldingsRow,
)

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


def _to_inst(i: Institution) -> InstitutionOut:
    return InstitutionOut(
        institution_id=i.institution_id,
        name=i.name,
        kind=i.kind,
        website=i.website,
        x_handle=i.x_handle,
        cik=i.cik,
        aum_usd=i.aum_usd,
    )


def _holdings_for_company(
    db: Session, company_id: int, ticker: str
) -> tuple[list[InstitutionalHoldingRow], date | None]:
    """Returns holdings rows at the most recent as_of_date we have for this
    company, one per institution. Older snapshots inform the delta fields on
    each row."""
    latest_date = (
        db.query(func.max(InstitutionalHolding.as_of_date))
        .filter(InstitutionalHolding.company_id == company_id)
        .scalar()
    )
    if latest_date is None:
        return [], None
    rows = (
        db.query(InstitutionalHolding, Institution)
        .join(Institution, Institution.institution_id == InstitutionalHolding.institution_id)
        .filter(
            InstitutionalHolding.company_id == company_id,
            InstitutionalHolding.as_of_date == latest_date,
        )
        .order_by(InstitutionalHolding.value_usd.desc().nullslast())
        .all()
    )
    out: list[InstitutionalHoldingRow] = []
    for h, inst in rows:
        out.append(
            InstitutionalHoldingRow(
                as_of_date=h.as_of_date,
                institution=_to_inst(inst),
                ticker=ticker,
                shares=h.shares,
                value_usd=h.value_usd,
                pct_of_outstanding=h.pct_of_outstanding,
                shares_change=h.shares_change,
                pct_change=h.pct_change,
                source=h.source,
            )
        )
    return out, latest_date


def _insider_window(
    db: Session, company_id: int, ticker: str, window_days: int = 90
) -> tuple[list[InsiderTransactionRow], InsiderNetFlow]:
    cutoff = date.today() - timedelta(days=window_days)
    rows = (
        db.query(InsiderTransaction)
        .filter(
            InsiderTransaction.company_id == company_id,
            InsiderTransaction.transaction_date >= cutoff,
        )
        .order_by(InsiderTransaction.transaction_date.desc())
        .all()
    )
    buy_shares = sell_shares = 0
    buy_value = sell_value = 0.0
    serialized: list[InsiderTransactionRow] = []
    for r in rows:
        sh = r.shares or 0
        val = r.value_usd or 0.0
        # Count option_exercise + rsu_vest as neutral (no real market signal);
        # only buy and sell contribute to net flow.
        if r.transaction_type == "buy":
            buy_shares += sh
            buy_value += val
        elif r.transaction_type == "sell":
            sell_shares += sh
            sell_value += val
        serialized.append(
            InsiderTransactionRow(
                txn_id=r.txn_id,
                ticker=ticker,
                insider_name=r.insider_name,
                insider_title=r.insider_title,
                insider_is_officer=r.insider_is_officer,
                insider_is_director=r.insider_is_director,
                transaction_date=r.transaction_date,
                filed_at=r.filed_at,
                transaction_type=r.transaction_type,
                shares=r.shares,
                price=r.price,
                value_usd=r.value_usd,
                shares_owned_after=r.shares_owned_after,
                is_10b5_1=r.is_10b5_1,
            )
        )
    flow = InsiderNetFlow(
        ticker=ticker,
        window_days=window_days,
        net_shares=buy_shares - sell_shares,
        net_value_usd=round(buy_value - sell_value, 2),
        buy_shares=buy_shares,
        buy_value_usd=round(buy_value, 2),
        sell_shares=sell_shares,
        sell_value_usd=round(sell_value, 2),
        transaction_count=len(rows),
    )
    return serialized, flow


@router.get("/{ticker}", response_model=CompanyHoldingsOut)
def get_company_holdings(
    ticker: str,
    db: Session = Depends(get_db),
    insider_window_days: int = Query(default=90, ge=7, le=730),
) -> CompanyHoldingsOut:
    c = db.query(Company).filter(Company.ticker == ticker.upper()).one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker {ticker}")
    holdings, as_of = _holdings_for_company(db, c.company_id, c.ticker)
    insiders, flow = _insider_window(db, c.company_id, c.ticker, insider_window_days)

    total_pct = sum(
        (h.pct_of_outstanding or 0) for h in holdings if h.pct_of_outstanding is not None
    )
    return CompanyHoldingsOut(
        ticker=c.ticker,
        as_of_date=as_of,
        total_institutional_pct=round(total_pct, 2) if total_pct > 0 else None,
        total_institutions=len(holdings),
        holdings=holdings,
        insider_transactions_90d=insiders,
        insider_net_flow_90d=flow,
    )


@router.get("", response_model=UniverseHoldingsOut)
def list_universe_holdings(db: Session = Depends(get_db)) -> UniverseHoldingsOut:
    companies = (
        db.query(Company).filter(Company.is_benchmark.is_(False)).order_by(Company.ticker).all()
    )
    rows: list[UniverseHoldingsRow] = []
    latest_any: date | None = None

    for c in companies:
        holdings, as_of = _holdings_for_company(db, c.company_id, c.ticker)
        if as_of is not None and (latest_any is None or as_of > latest_any):
            latest_any = as_of

        total_pct = sum((h.pct_of_outstanding or 0) for h in holdings) or None
        top_holder = holdings[0] if holdings else None
        with_deltas = [h for h in holdings if h.shares_change is not None]
        biggest_buyer = max(with_deltas, key=lambda h: h.shares_change or 0, default=None)
        biggest_seller = min(with_deltas, key=lambda h: h.shares_change or 0, default=None)

        _, flow = _insider_window(db, c.company_id, c.ticker, 90)
        rows.append(
            UniverseHoldingsRow(
                ticker=c.ticker,
                name=c.name,
                total_institutional_pct=round(total_pct, 2) if total_pct else None,
                top_holder_name=top_holder.institution.name if top_holder else None,
                top_holder_pct=top_holder.pct_of_outstanding if top_holder else None,
                biggest_buyer_name=(
                    biggest_buyer.institution.name
                    if biggest_buyer and (biggest_buyer.shares_change or 0) > 0
                    else None
                ),
                biggest_buyer_delta_shares=(
                    biggest_buyer.shares_change if biggest_buyer and (biggest_buyer.shares_change or 0) > 0 else None
                ),
                biggest_seller_name=(
                    biggest_seller.institution.name
                    if biggest_seller and (biggest_seller.shares_change or 0) < 0
                    else None
                ),
                biggest_seller_delta_shares=(
                    biggest_seller.shares_change if biggest_seller and (biggest_seller.shares_change or 0) < 0 else None
                ),
                insider_net_shares_90d=flow.net_shares,
                insider_net_value_90d=flow.net_value_usd,
            )
        )

    # Top institutions by number of distinct companies held across universe
    top_inst_rows = (
        db.query(Institution, func.count(func.distinct(InstitutionalHolding.company_id)).label("cnt"))
        .join(
            InstitutionalHolding,
            Institution.institution_id == InstitutionalHolding.institution_id,
        )
        .group_by(Institution.institution_id)
        .order_by(func.count(func.distinct(InstitutionalHolding.company_id)).desc())
        .limit(15)
        .all()
    )
    top_institutions = [_to_inst(i) for i, _ in top_inst_rows]

    return UniverseHoldingsOut(
        as_of_date=latest_any,
        rows=rows,
        top_institutions=top_institutions,
    )
