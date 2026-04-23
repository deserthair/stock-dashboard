from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company, RedditPost, SocialPost
from ..schemas import RedditPostOut, SocialPostOut

router = APIRouter(prefix="/api/social", tags=["social"])


@router.get("", response_model=list[SocialPostOut])
def list_social(
    db: Session = Depends(get_db),
    ticker: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[SocialPostOut]:
    q = (
        db.query(SocialPost, Company.ticker)
        .join(Company, SocialPost.company_id == Company.company_id, isouter=True)
    )
    if ticker:
        q = q.filter(Company.ticker == ticker.upper())
    rows = q.order_by(SocialPost.fetched_at.desc()).limit(limit).all()
    return [
        SocialPostOut(
            post_id=p.post_id,
            ticker=t,
            platform=p.platform,
            account=p.account,
            posted_at=p.posted_at,
            content=p.content,
            engagement=dict(p.engagement or {}),
            sentiment_score=p.sentiment_score,
        )
        for p, t in rows
    ]


@router.get("/reddit", response_model=list[RedditPostOut])
def list_reddit(
    db: Session = Depends(get_db),
    ticker: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[RedditPostOut]:
    q = (
        db.query(RedditPost, Company.ticker)
        .join(Company, RedditPost.company_id == Company.company_id, isouter=True)
    )
    if ticker:
        q = q.filter(Company.ticker == ticker.upper())
    rows = q.order_by(RedditPost.created_at.desc()).limit(limit).all()
    return [
        RedditPostOut(
            post_id=p.post_id,
            ticker=t,
            subreddit=p.subreddit,
            created_at=p.created_at,
            title=p.title,
            score=p.score,
            num_comments=p.num_comments,
            url=p.url,
            sentiment_score=p.sentiment_score,
        )
        for p, t in rows
    ]
