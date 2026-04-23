"""Company press release / IR page ingest (framework).

Each company's IR page has its own HTML structure, so this worker uses a
per-ticker config dict with a CSS selector for the link list. A few are
wired (Chipotle, Cava, Wingstop) with commonly-used Q4/EQS/S&P IR widget
patterns; the rest fall through and log a skip until a selector is added.

All hits are written to `news` with source='pr_page'. De-duped by URL hash."""

from __future__ import annotations

import hashlib
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.db import SessionLocal
from app.models import Company, NewsItem

from ..rate_limiter import for_source
from ..source_run import source_run


# Per-ticker scraper config. Selectors target the link text + href that
# represents individual press releases on each IR page. Many use the Q4
# widget (".wd_item", "a.wd_title") or EQS ("li.press-releases__item a").
CONFIG: dict[str, dict] = {
    "CMG":  {"url": "https://ir.chipotle.com/press-releases",            "link_sel": "a.press-release__link, a.news-release, a.wd_title"},
    "SBUX": {"url": "https://investor.starbucks.com/press-releases/default.aspx", "link_sel": "a.module_link, a.news-release, a.wd_title"},
    "CAVA": {"url": "https://investor.cava.com/news-releases",           "link_sel": "a.wd_title, a.news-release-title"},
    "TXRH": {"url": "https://investor.texasroadhouse.com/press-releases","link_sel": "a.wd_title, a.news-release"},
    "WING": {"url": "https://ir.wingstop.com/news-releases",             "link_sel": "a.wd_title, a.news-release"},
    "DPZ":  {"url": "https://ir.dominos.com/news-releases",              "link_sel": "a.wd_title, a.news-release"},
    "QSR":  {"url": "https://www.rbi.com/English/news-and-events/news-releases/default.aspx", "link_sel": "a.module_link, a.news-release"},
    # MCD's IR flow is JS-heavy; plug in a selector once determined.
}


def _scrape(client: httpx.Client, cfg: dict) -> list[dict]:
    r = client.get(cfg["url"], timeout=20.0, headers={"User-Agent": "restin/0.1"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    for a in soup.select(cfg["link_sel"]):
        href = a.get("href")
        title = (a.get_text() or "").strip()
        if not href or not title:
            continue
        out.append({"url": urljoin(cfg["url"], href), "title": title[:512]})
    return out


def run_once() -> int:
    with source_run("pr_pages") as run:
        limiter = for_source("google_rss")  # polite default
        rows = 0
        with httpx.Client() as client, SessionLocal() as s:
            for c in s.query(Company).all():
                cfg = CONFIG.get(c.ticker)
                if cfg is None:
                    continue
                limiter.acquire()
                try:
                    items = _scrape(client, cfg)
                except (httpx.HTTPError, Exception) as exc:
                    print(f"[pr_pages] {c.ticker}: {exc}")
                    continue
                for item in items[:40]:
                    url_hash = hashlib.sha256(item["url"].encode()).hexdigest()
                    existing = (
                        s.query(NewsItem).filter_by(url_hash=url_hash).one_or_none()
                    )
                    if existing is not None:
                        continue
                    s.add(
                        NewsItem(
                            company_id=c.company_id,
                            source="pr_page",
                            url=item["url"][:512],
                            url_hash=url_hash,
                            published_at=None,
                            headline=item["title"],
                            publisher=c.name,
                            fetched_at=datetime.utcnow(),
                        )
                    )
                    rows += 1
            s.commit()
        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
