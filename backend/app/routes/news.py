from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company, NewsItem
from ..schemas import NewsItemOut
from ._filters import apply_date_range

router = APIRouter(prefix="/api/news", tags=["news"])


def _serialize(n: NewsItem) -> NewsItemOut:
    return NewsItemOut(
        news_id=n.news_id,
        ticker=n.company.ticker if n.company else None,
        source=n.source,
        url=n.url,
        published_at=n.published_at,
        fetched_at=n.fetched_at,
        headline=n.headline,
        publisher=n.publisher,
        sentiment_score=n.sentiment_score,
        relevance_score=n.relevance_score,
        topics=list(n.topics or []),
    )


@router.get("", response_model=list[NewsItemOut])
def list_news(
    db: Session = Depends(get_db),
    ticker: str | None = None,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[NewsItemOut]:
    q = db.query(NewsItem).join(Company, NewsItem.company_id == Company.company_id, isouter=True)
    if ticker:
        q = q.filter(Company.ticker == ticker.upper())
    # Range applied against fetched_at (published_at is frequently null).
    q = apply_date_range(q, NewsItem.fetched_at, start_date, end_date, is_datetime=True)
    rows = q.order_by(NewsItem.fetched_at.desc()).limit(limit).all()
    return [_serialize(n) for n in rows]
