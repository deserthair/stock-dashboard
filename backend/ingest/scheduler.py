"""APScheduler entrypoint — wires all ingest + analysis jobs.

Run with: python -m ingest.scheduler

Cadences follow the plan's guidance:
  - prices:       every 15 min during the trading day
  - news_rss:     every 2 hours
  - pr_pages:     every 6 hours (low-volume, high-signal)
  - reddit:       every 3 hours
  - email_imap:   every 10 min (most real-time)
  - filings:      every 2 hours
  - earnings:     daily (04:00 UTC)
  - macro:        daily (07:00 UTC)
  - weather:      daily (06:00 UTC)
  - jobs:         weekly (Monday 05:00 UTC)

Analysis layers chain after ingest to keep the denormalized signals and
event feed fresh:
  - sentiment:    every 30 min (works on unscored items)
  - signals:      every 30 min
  - event_detect: every 30 min
  - features:     daily (08:00 UTC)
  - correlations: daily (08:30 UTC, after features)
"""

from __future__ import annotations

import logging
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from analysis import correlation as analysis_corr
from app.db import Base, engine
from app.seed import run as seed_run
from features import engineer as features_engineer
from ingest.sources import (
    earnings as src_earnings,
    email_imap as src_email,
    filings as src_filings,
    jobs as src_jobs,
    macro as src_macro,
    news_rss as src_news,
    pr_pages as src_pr,
    prices as src_prices,
    reddit as src_reddit,
    weather as src_weather,
)
from normalize import events as norm_events
from normalize import sentiment as norm_sentiment
from normalize import signals as norm_signals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
log = logging.getLogger("scheduler")


JOBS = [
    (src_prices.run_once,      "prices",       {"trigger": "interval", "minutes": 15}),
    (src_news.run_once,        "news_rss",     {"trigger": "interval", "hours": 2}),
    (src_pr.run_once,          "pr_pages",     {"trigger": "interval", "hours": 6}),
    (src_reddit.run_once,      "reddit",       {"trigger": "interval", "hours": 3}),
    (src_email.run_once,       "email_imap",   {"trigger": "interval", "minutes": 10}),
    (src_filings.run_once,     "filings",      {"trigger": "interval", "hours": 2}),
    (src_earnings.run_once,    "earnings",     {"trigger": "cron", "hour": 4}),
    (src_macro.run_once,       "macro",        {"trigger": "cron", "hour": 7}),
    (src_weather.run_once,     "weather",      {"trigger": "cron", "hour": 6}),
    (src_jobs.run_once,        "jobs",         {"trigger": "cron", "day_of_week": "mon", "hour": 5}),

    (norm_sentiment.run_once,  "sentiment",    {"trigger": "interval", "minutes": 30}),
    (norm_signals.run_once,    "signals",      {"trigger": "interval", "minutes": 30}),
    (norm_events.run_once,     "events",       {"trigger": "interval", "minutes": 30}),

    (features_engineer.run_once, "features",   {"trigger": "cron", "hour": 8}),
    (analysis_corr.run_once,   "correlations", {"trigger": "cron", "hour": 8, "minute": 30}),
]


def main() -> None:
    Base.metadata.create_all(engine)
    seed_run()

    sched = BlockingScheduler(timezone="UTC")
    for fn, job_id, kwargs in JOBS:
        sched.add_job(
            fn,
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300,
            coalesce=True,
            max_instances=1,
            next_run_time=datetime.utcnow(),
            **kwargs,
        )
        log.info("registered job %s: %s", job_id, kwargs)

    def _shutdown(*_: object) -> None:
        log.info("shutting down scheduler")
        sched.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    log.info("scheduler started")
    sched.start()


if __name__ == "__main__":
    main()
