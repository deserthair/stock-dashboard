"""Google News RSS ingest — for both tracked companies and institutional holders.

Writes unique items to `news`, de-duped by SHA-256 of the final URL. No key
required. Runs one query per subject (company brand + institution name),
since Google News's URL rewriter changes the final link based on query
context — so an article "Vanguard raises stake in CMG" legitimately gets
two rows, one tagged `company_id=CMG` and one tagged
`institution_id=Vanguard`."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import quote_plus

import feedparser

from app.db import SessionLocal
from app.models import Company, Institution, NewsItem

from ..rate_limiter import for_source
from ..source_run import source_run

RSS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
STOP_PUBLISHERS = {"reddit.com"}


def _company_query(ticker: str, name: str) -> str:
    short = re.sub(r",? Inc\.?| Corporation| Corp\.?| Group| Mexican Grill.*|, Inc\.? *$", "", name)
    return quote_plus(f"{ticker} OR \"{short.strip()}\"")


def _institution_query(inst: Institution) -> str:
    """Use an explicit news_query override if set, else just the name."""
    q = inst.news_query or inst.name
    return quote_plus(q)


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


def _ingest_one(s, query: str, *, company_id: int | None = None, institution_id: int | None = None) -> int:
    """Fetch one Google News RSS query and write unique items. Returns row count."""
    feed = feedparser.parse(RSS.format(q=query))
    rows = 0
    for entry in feed.entries[:50]:
        link = entry.get("link")
        if not link:
            continue
        publisher = _publisher_of(entry)
        if publisher and any(sp in publisher.lower() for sp in STOP_PUBLISHERS):
            continue
        url_hash = hashlib.sha256(link.encode()).hexdigest()
        if s.query(NewsItem).filter_by(url_hash=url_hash).one_or_none() is not None:
            continue
        headline = entry.get("title", "")[:512]
        published = _parse_dt(entry.get("published_parsed"))
        s.add(
            NewsItem(
                company_id=company_id,
                institution_id=institution_id,
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
    return rows


def run_once() -> int:
    with source_run("news_rss") as run:
        limiter = for_source("google_rss")
        rows = 0
        with SessionLocal() as s:
            for c in s.query(Company).filter(Company.is_benchmark.is_(False)).all():
                limiter.acquire()
                rows += _ingest_one(
                    s, _company_query(c.ticker, c.name), company_id=c.company_id
                )

            for inst in s.query(Institution).all():
                limiter.acquire()
                rows += _ingest_one(
                    s, _institution_query(inst), institution_id=inst.institution_id
                )

            s.commit()
        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
