"""SEC EDGAR filings ingest.

Pulls the submissions feed for each company's CIK and upserts 10-K / 10-Q /
8-K / DEF 14A rows into `filings`. No API key required — EDGAR requires a
descriptive User-Agent header with contact info (set via env).

For 8-Ks, parses the item numbers (e.g. 2.02, 5.02) from the filing title."""

from __future__ import annotations

import os
import re
from datetime import datetime

import httpx

from app.db import SessionLocal
from app.models import Company, Filing

from ..rate_limiter import for_source
from ..source_run import source_run

INTERESTING_FORMS = {"10-K", "10-Q", "8-K", "DEF 14A"}
USER_AGENT = os.environ.get(
    "EDGAR_USER_AGENT", "restin/0.1 (set EDGAR_USER_AGENT=name email)"
)
ITEM_RE = re.compile(r"\bItem\s+(\d+\.\d+)\b", re.IGNORECASE)


def _submissions_url(cik: str) -> str:
    return f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"


def _archive_url(cik: str, accession: str, primary_doc: str) -> str:
    acc = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{primary_doc}"


def run_once() -> int:
    with source_run("filings") as run:
        limiter = for_source("edgar")
        rows = 0
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        with httpx.Client(headers=headers) as client, SessionLocal() as s:
            for c in s.query(Company).all():
                if not c.cik:
                    continue
                limiter.acquire()
                try:
                    r = client.get(_submissions_url(c.cik), timeout=20.0)
                    r.raise_for_status()
                except httpx.HTTPError as exc:
                    print(f"[filings] {c.ticker}: {exc}")
                    continue

                recent = r.json().get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                accessions = recent.get("accessionNumber", [])
                dates = recent.get("filingDate", [])
                primary_docs = recent.get("primaryDocument", [])
                titles = recent.get("primaryDocDescription", [])

                for i, form in enumerate(forms):
                    if form not in INTERESTING_FORMS:
                        continue
                    accession = accessions[i]
                    existing = (
                        s.query(Filing)
                        .filter_by(accession_number=accession)
                        .one_or_none()
                    )
                    if existing is not None:
                        continue
                    try:
                        filed_at = datetime.fromisoformat(dates[i])
                    except ValueError:
                        continue
                    title = titles[i] if i < len(titles) else None
                    item_numbers = ITEM_RE.findall(title or "") if form == "8-K" else []
                    s.add(
                        Filing(
                            company_id=c.company_id,
                            filing_type=form,
                            accession_number=accession,
                            filed_at=filed_at,
                            primary_doc_url=_archive_url(
                                c.cik, accession, primary_docs[i]
                            )
                            if i < len(primary_docs)
                            else None,
                            item_numbers=item_numbers,
                            title=title,
                        )
                    )
                    rows += 1
            s.commit()

        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
