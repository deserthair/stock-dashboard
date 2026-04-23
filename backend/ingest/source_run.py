"""Context manager that logs a source run to the `source_runs` table."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import logging
import traceback

from app.db import SessionLocal
from app.models import SourceRun

log = logging.getLogger("ingest")


@contextmanager
def source_run(name: str):
    """Usage:

        with source_run("prices") as run:
            ...work...
            run.rows_fetched = n
    """
    with SessionLocal() as s:
        run = SourceRun(source_name=name, started_at=datetime.utcnow(), status="running")
        s.add(run)
        s.commit()
        s.refresh(run)
        run_id = run.run_id

    try:
        class _Handle:
            rows_fetched = 0
            skip = False

        handle = _Handle()
        yield handle

        with SessionLocal() as s:
            rec = s.get(SourceRun, run_id)
            if rec is None:
                return
            rec.ended_at = datetime.utcnow()
            rec.status = "skipped" if handle.skip else "success"
            rec.rows_fetched = handle.rows_fetched
            s.commit()
        log.info("[%s] %s — %d rows", name, "skipped" if handle.skip else "ok", handle.rows_fetched)

    except Exception as exc:  # noqa: BLE001
        with SessionLocal() as s:
            rec = s.get(SourceRun, run_id)
            if rec is not None:
                rec.ended_at = datetime.utcnow()
                rec.status = "failed"
                rec.error_msg = f"{exc}\n{traceback.format_exc()}"
                s.commit()
        log.exception("[%s] failed: %s", name, exc)
