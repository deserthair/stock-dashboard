from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company, JobsSnapshot
from ..schemas import JobsSnapshotOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobsSnapshotOut])
def list_jobs(
    db: Session = Depends(get_db),
    ticker: str | None = None,
    limit: int = Query(default=30, ge=1, le=365),
) -> list[JobsSnapshotOut]:
    q = (
        db.query(JobsSnapshot, Company.ticker)
        .join(Company, JobsSnapshot.company_id == Company.company_id)
    )
    if ticker:
        q = q.filter(Company.ticker == ticker.upper())
    rows = q.order_by(JobsSnapshot.snapshot_date.desc()).limit(limit).all()
    return [
        JobsSnapshotOut(
            snapshot_date=js.snapshot_date,
            ticker=t,
            total_count=js.total_count,
            corporate_count=js.corporate_count,
            by_department=dict(js.by_department or {}),
            by_location=dict(js.by_location or {}),
        )
        for js, t in rows
    ]
