from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company, Correlation, Earnings, EarningsFeature
from ..schemas import CorrelationOut, FeatureVectorOut

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/correlations", response_model=list[CorrelationOut])
def list_correlations(
    db: Session = Depends(get_db),
    target: str | None = None,
    method: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[CorrelationOut]:
    q = db.query(Correlation)
    if target:
        q = q.filter(Correlation.target_name == target)
    if method:
        q = q.filter(Correlation.method == method)
    rows = (
        q.order_by(Correlation.p_adjusted.asc().nullslast())
        .limit(limit)
        .all()
    )
    return [
        CorrelationOut(
            feature_name=r.feature_name,
            target_name=r.target_name,
            method=r.method,
            n=r.n,
            coefficient=r.coefficient,
            ci_low=r.ci_low,
            ci_high=r.ci_high,
            p_value=r.p_value,
            p_adjusted=r.p_adjusted,
        )
        for r in rows
    ]


@router.get("/features/{earnings_id}", response_model=FeatureVectorOut)
def get_feature_vector(earnings_id: int, db: Session = Depends(get_db)) -> FeatureVectorOut:
    row = (
        db.query(EarningsFeature, Earnings, Company)
        .join(Earnings, Earnings.earnings_id == EarningsFeature.earnings_id)
        .join(Company, Company.company_id == Earnings.company_id)
        .filter(EarningsFeature.earnings_id == earnings_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"No features for earnings_id {earnings_id}")
    feat, earn, company = row
    values = {
        k: getattr(feat, k)
        for k in feat.__table__.columns.keys()
        if k not in {"feature_id", "earnings_id", "feature_version", "computed_at"}
    }
    return FeatureVectorOut(
        earnings_id=earn.earnings_id,
        ticker=company.ticker,
        report_date=earn.report_date,
        feature_version=feat.feature_version,
        values=values,
    )
