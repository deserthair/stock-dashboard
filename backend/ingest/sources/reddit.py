"""Reddit ingest via the public JSON endpoints.

Unauthenticated — rate-limited but works without PRAW credentials. If
REDDIT_CLIENT_ID + SECRET are set we can swap in PRAW later for higher
throughput. Writes to `reddit_posts` and mirrors a subset into
`social_posts` with platform='reddit'."""

from __future__ import annotations

from datetime import datetime
import re

import httpx

from app.db import SessionLocal
from app.models import Company, RedditPost, SocialPost

from ..rate_limiter import for_source
from ..source_run import source_run

SUBREDDITS = ["stocks", "investing", "SecurityAnalysis", "wallstreetbets"]
HEADERS = {"User-Agent": "restin/0.1 (subreddit search)"}


def _search_url(sub: str, query: str) -> str:
    return (
        f"https://www.reddit.com/r/{sub}/search.json"
        f"?q={query}&restrict_sr=1&sort=new&t=week&limit=25"
    )


def run_once() -> int:
    with source_run("reddit") as run:
        limiter = for_source("reddit")
        rows = 0
        with httpx.Client(headers=HEADERS) as client, SessionLocal() as s:
            companies = s.query(Company).all()
            tickers = {c.ticker: c.company_id for c in companies}
            for c in companies:
                name_bits = re.split(r",|\s+", c.name)
                query = f"{c.ticker} OR {name_bits[0]}"
                for sub in SUBREDDITS:
                    limiter.acquire()
                    try:
                        r = client.get(_search_url(sub, query), timeout=20.0)
                        if r.status_code == 429:
                            break  # backoff; next run will retry
                        r.raise_for_status()
                    except httpx.HTTPError as exc:
                        print(f"[reddit] {c.ticker}/{sub}: {exc}")
                        continue
                    for child in r.json().get("data", {}).get("children", []):
                        d = child.get("data", {})
                        post_id = d.get("id")
                        if not post_id:
                            continue
                        if s.get(RedditPost, post_id) is not None:
                            continue
                        created = datetime.utcfromtimestamp(
                            int(d.get("created_utc", 0))
                        )
                        title = (d.get("title") or "")[:512]
                        body = d.get("selftext")
                        blob = f"{title} {body or ''}".upper()
                        mentions = [t for t in tickers if t in blob]
                        post = RedditPost(
                            post_id=post_id,
                            subreddit=sub,
                            company_id=c.company_id,
                            created_at=created,
                            title=title,
                            body=body,
                            url=(d.get("url") or "")[:512] or None,
                            score=int(d.get("score") or 0),
                            num_comments=int(d.get("num_comments") or 0),
                            ticker_mentions=mentions,
                        )
                        s.add(post)
                        # mirror interesting posts into social_posts
                        if post.score >= 10:
                            s.add(
                                SocialPost(
                                    company_id=c.company_id,
                                    platform="reddit",
                                    account=f"r/{sub}",
                                    external_id=post_id,
                                    posted_at=created,
                                    content=title,
                                    engagement={
                                        "score": post.score,
                                        "comments": post.num_comments,
                                    },
                                )
                            )
                        rows += 1
            s.commit()

        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
