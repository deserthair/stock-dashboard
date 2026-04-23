"""Careers-page ingest (framework).

Writes a `jobs_snapshots` row per (company, day) with the total job count
and, where the page exposes them, counts by department and location.

Built-in configs cover the common ATS vendors the universe uses:
  - Workday  — JSON endpoint `/wday/cxs/<tenant>/<site>/jobs`
  - Greenhouse — JSON endpoint `https://boards-api.greenhouse.io/v1/boards/<board>/jobs`
  - Lever     — JSON endpoint `https://api.lever.co/v0/postings/<company>?mode=json`

Companies whose careers ATS is unknown (or use a custom CMS) are skipped
until a config is filled in. Writes snapshots idempotently per day."""

from __future__ import annotations

from datetime import date

import httpx

from app.db import SessionLocal
from app.models import Company, JobsSnapshot

from ..rate_limiter import for_source
from ..source_run import source_run

# ATS-aware configs.  CONFIG[ticker] = (kind, identifier, optional key fields)
CONFIG: dict[str, dict] = {
    # Best-effort starter configs — adjust slugs when each company's live.
    "CMG":  {"kind": "greenhouse", "board": "chipotle"},
    "CAVA": {"kind": "greenhouse", "board": "cava"},
    "WING": {"kind": "lever",      "company": "wingstop"},
    "DPZ":  {"kind": "lever",      "company": "dominos"},
    "SBUX": {"kind": "workday",    "tenant": "starbucks",    "site": "starbucksjobs"},
    "MCD":  {"kind": "workday",    "tenant": "mcdonalds",    "site": "External"},
    "TXRH": {"kind": "lever",      "company": "texasroadhouse"},
    "QSR":  {"kind": "workday",    "tenant": "rbi",          "site": "rbi_careers"},
}

UA = {"User-Agent": "restin/0.1 (jobs scraper)"}


def _from_greenhouse(client: httpx.Client, board: str) -> dict:
    r = client.get(
        f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
        timeout=20.0,
        headers=UA,
    )
    r.raise_for_status()
    jobs = r.json().get("jobs", [])
    by_dept: dict[str, int] = {}
    by_loc: dict[str, int] = {}
    for j in jobs:
        for d in j.get("departments") or []:
            name = d.get("name") or "Other"
            by_dept[name] = by_dept.get(name, 0) + 1
        loc = (j.get("location") or {}).get("name", "Other")
        by_loc[loc] = by_loc.get(loc, 0) + 1
    return {"total": len(jobs), "by_dept": by_dept, "by_loc": by_loc}


def _from_lever(client: httpx.Client, company: str) -> dict:
    r = client.get(
        f"https://api.lever.co/v0/postings/{company}?mode=json",
        timeout=20.0,
        headers=UA,
    )
    r.raise_for_status()
    jobs = r.json()
    by_dept: dict[str, int] = {}
    by_loc: dict[str, int] = {}
    for j in jobs:
        cat = j.get("categories") or {}
        d = cat.get("department") or cat.get("team") or "Other"
        loc = cat.get("location") or "Other"
        by_dept[d] = by_dept.get(d, 0) + 1
        by_loc[loc] = by_loc.get(loc, 0) + 1
    return {"total": len(jobs), "by_dept": by_dept, "by_loc": by_loc}


def _from_workday(client: httpx.Client, tenant: str, site: str) -> dict:
    url = f"https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    r = client.post(
        url,
        json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
        timeout=20.0,
        headers=UA,
    )
    r.raise_for_status()
    body = r.json()
    return {"total": int(body.get("total") or 0), "by_dept": {}, "by_loc": {}}


def _snapshot_for(cfg: dict, client: httpx.Client) -> dict | None:
    try:
        if cfg["kind"] == "greenhouse":
            return _from_greenhouse(client, cfg["board"])
        if cfg["kind"] == "lever":
            return _from_lever(client, cfg["company"])
        if cfg["kind"] == "workday":
            return _from_workday(client, cfg["tenant"], cfg["site"])
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        print(f"[jobs] {cfg}: {exc}")
        return None
    return None


def _corporate_count(by_dept: dict[str, int]) -> int:
    corp_kw = ("corporate", "engineering", "technology", "data", "finance", "support center")
    return sum(v for k, v in by_dept.items() if any(kw in k.lower() for kw in corp_kw))


def run_once() -> int:
    with source_run("jobs") as run:
        limiter = for_source("google_rss")
        rows = 0
        today = date.today()
        with httpx.Client() as client, SessionLocal() as s:
            for c in s.query(Company).all():
                cfg = CONFIG.get(c.ticker)
                if cfg is None:
                    continue
                limiter.acquire()
                snap = _snapshot_for(cfg, client)
                if snap is None:
                    continue
                existing = (
                    s.query(JobsSnapshot)
                    .filter_by(company_id=c.company_id, snapshot_date=today)
                    .one_or_none()
                )
                rec = existing or JobsSnapshot(
                    company_id=c.company_id, snapshot_date=today
                )
                rec.total_count = snap["total"]
                rec.by_department = snap["by_dept"]
                rec.by_location = snap["by_loc"]
                rec.corporate_count = _corporate_count(snap["by_dept"])
                if existing is None:
                    s.add(rec)
                rows += 1
            s.commit()
        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
