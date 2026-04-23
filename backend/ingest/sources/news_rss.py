"""Google News RSS ingest.

Polls Google News RSS per ticker and writes unique items to `news`.
De-dupes by SHA-256 of the final URL. No key required."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import quote_plus

import feedparser

from app.db import SessionLocal
from app.models import Company, NewsItem

from ..rate_limiter import for_source
from ..source_run import source_run

RSS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
STOP_PUBLISHERS = {"reddit.com"}  # duplicated by reddit ingest


def _query_for(ticker: str, name: str) -> str:
    short = re.sub(r",? Inc\.?| Corporation| Corp\.?| Group| Mexican Grill.*|, Inc\.? *$", "", name)
    return quote_plus(f"{ticker} OR \"{short.strip()}\"")


def _parse_dt(struct_time: object | None) -> datetime | None:
    if struct_time is None:
        return None
    try:
        return datetime(*struct_time[:6])  # type: ignore[misc,index]
    except (TypeError, ValueError):
        return None


def _publisher_of(entry) -> str | None:
    src = entry.get("source")
    if isinstance(src, dict):
        return src.get("title") or src.get("href")
    if isinstance(src, str):
        return src
    return None


def run_once() -> int:
    with source_run("news_rss") as run:
        limiter = for_source("google_rss")
        rows = 0
        with SessionLocal() as s:
            for c in s.query(Company).all():
                limiter.acquire()
                url = RSS.format(q=_query_for(c.ticker, c.name))
                feed = feedparser.parse(url)
                for entry in feed.entries[:50]:
                    link = entry.get("link")
                    if not link:
                        continue
                    publisher = _publisher_of(entry)
                    if publisher and any(sp in publisher.lower() for sp in STOP_PUBLISHERS):
                        continue
                    url_hash = hashlib.sha256(link.encode()).hexdigest()
                    existing = (
                        s.query(NewsItem).filter_by(url_hash=url_hash).one_or_none()
                    )
                    if existing is not None:
                        continue
                    headline = entry.get("title", "")[:512]
                    published = _parse_dt(entry.get("published_parsed"))
                    s.add(
                        NewsItem(
                            company_id=c.company_id,
                            source="google_rss",
                            url=link[:512],
                            url_hash=url_hash,
                            published_at=published,
                            headline=headline,
                            body=entry.get("summary"),
                            publisher=publisher,
                        )
                    )
                    rows += 1
            s.commit()
        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
