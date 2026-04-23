from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SourceRun
from ..schemas import SourceRunOut

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/source-runs", response_model=list[SourceRunOut])
def list_runs(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[SourceRunOut]:
    rows = db.query(SourceRun).order_by(SourceRun.started_at.desc()).limit(limit).all()
    return [
        SourceRunOut(
            source_name=r.source_name,
            started_at=r.started_at,
            ended_at=r.ended_at,
            status=r.status,
            rows_fetched=r.rows_fetched,
            error_msg=r.error_msg,
        )
        for r in rows
    ]
