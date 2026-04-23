"""IMAP email ingest for Google Alerts / Seeking Alpha / X / Reddit digests.

Connects via IMAP (Gmail by default), pulls unseen messages from INBOX,
classifies by sender domain, extracts ticker mentions, and writes to
`email_messages`. Notable posts are mirrored into `social_posts`.

Requires `GMAIL_USER` and `GMAIL_APP_PASSWORD`; skipped if either is missing."""

from __future__ import annotations

import os
import re
from datetime import datetime

from app.db import SessionLocal
from app.models import Company, EmailMessage, SocialPost

from ..source_run import source_run

SOURCE_TYPE_RULES = [
    ("googlealerts-noreply@google.com", "google_alert"),
    ("noreply@reddit.com",              "reddit_digest"),
    ("notify@twitter.com",              "x"),
    ("info@twitter.com",                "x"),
    ("news@seekingalpha.com",           "seekingalpha"),
    ("no-reply@linkedin.com",           "linkedin"),
    ("newsletters-noreply@linkedin.com","linkedin"),
]


def _source_type_for(from_addr: str | None) -> str | None:
    if not from_addr:
        return None
    low = from_addr.lower()
    for needle, label in SOURCE_TYPE_RULES:
        if needle in low:
            return label
    if "ir-" in low or "investors@" in low or "ir@" in low:
        return "ir"
    return None


def _mentions(text: str, tickers: set[str]) -> list[str]:
    found: set[str] = set()
    upper = text.upper()
    for t in tickers:
        if re.search(rf"\b{re.escape(t)}\b", upper):
            found.add(t)
    return sorted(found)


def run_once() -> int:
    with source_run("email_imap") as run:
        user = os.environ.get("GMAIL_USER")
        pwd = os.environ.get("GMAIL_APP_PASSWORD")
        if not user or not pwd:
            print("[email_imap] GMAIL_USER/GMAIL_APP_PASSWORD not set; skipping")
            run.skip = True
            return 0

        try:
            from imap_tools import AND, MailBox
        except ImportError:
            run.skip = True
            return 0

        rows = 0
        with SessionLocal() as s:
            tickers = {c.ticker for c in s.query(Company).all()}

            with MailBox("imap.gmail.com").login(user, pwd, initial_folder="INBOX") as mb:
                for msg in mb.fetch(AND(seen=False), mark_seen=True, limit=200):
                    mid = msg.uid or msg.headers.get("message-id", [""])[0]
                    if not mid:
                        continue
                    if s.get(EmailMessage, mid) is not None:
                        continue
                    from_addr = msg.from_ or None
                    subject = (msg.subject or "")[:512]
                    body = msg.text or msg.html or ""
                    source_type = _source_type_for(from_addr)
                    blob = f"{subject}\n{body[:5000]}"
                    found = _mentions(blob, tickers)

                    s.add(
                        EmailMessage(
                            message_id=mid,
                            from_addr=from_addr,
                            subject=subject,
                            received_at=msg.date or datetime.utcnow(),
                            body_text=body,
                            source_type=source_type,
                            ticker_mentions=found,
                            processed=False,
                        )
                    )
                    rows += 1

                    if source_type in {"x", "reddit_digest", "linkedin"} and found:
                        s.add(
                            SocialPost(
                                platform={"x": "x", "reddit_digest": "reddit", "linkedin": "linkedin"}[source_type],
                                account=from_addr,
                                external_id=mid,
                                posted_at=msg.date,
                                content=subject,
                                engagement={},
                            )
                        )
            s.commit()

        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
