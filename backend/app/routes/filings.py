from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company, Filing
from ..schemas import FilingOut
from ._filters import apply_date_range

router = APIRouter(prefix="/api/filings", tags=["filings"])


@router.get("", response_model=list[FilingOut])
def list_filings(
    db: Session = Depends(get_db),
    ticker: str | None = None,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[FilingOut]:
    q = (
        db.query(Filing, Company.ticker)
        .join(Company, Filing.company_id == Company.company_id)
    )
    if ticker:
        q = q.filter(Company.ticker == ticker.upper())
    q = apply_date_range(q, Filing.filed_at, start_date, end_date, is_datetime=True)
    rows = q.order_by(Filing.filed_at.desc()).limit(limit).all()
    return [
        FilingOut(
            filing_id=f.filing_id,
            ticker=t,
            filing_type=f.filing_type,
            filed_at=f.filed_at,
            primary_doc_url=f.primary_doc_url,
            item_numbers=list(f.item_numbers or []),
            title=f.title,
        )
        for f, t in rows
    ]
