"""APScheduler entrypoint — Phase 1 sources only.

Run with: python -m ingest.scheduler
"""

from __future__ import annotations

import logging
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from app.db import Base, engine
from app.seed import run as seed_run

from . import prices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
log = logging.getLogger("scheduler")


def main() -> None:
    Base.metadata.create_all(engine)
    # Ensure the universe row exists before any ingest runs.
    seed_run()

    sched = BlockingScheduler(timezone="UTC")

    sched.add_job(
        prices.run_once,
        trigger="interval",
        minutes=15,
        next_run_time=datetime.utcnow(),
        id="prices",
        replace_existing=True,
    )

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
