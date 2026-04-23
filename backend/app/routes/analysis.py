from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from analysis import heatmap as analysis_heatmap
from analysis import regression as analysis_regression
from analysis import scatter as analysis_scatter
from analysis.attribution import build_attributions
from analysis.frame import FEATURE_COLS, TARGET_COLS

from ..db import get_db
from ..models import Company, Correlation, Earnings, EarningsFeature
from ..schemas import (
    AnalysisAxesResponse,
    CoefficientOut,
    CorrelationOut,
    EventAttributionResponse,
    FeatureContribution,
    FeatureVectorOut,
    HeatmapResponse,
    RegressionFitOut,
    RegressionLineOut,
    ScatterPointOut,
    ScatterResponse,
)
from ._filters import parse_range

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


@router.get("/axes", response_model=AnalysisAxesResponse)
def get_axes() -> AnalysisAxesResponse:
    return AnalysisAxesResponse(features=list(FEATURE_COLS), targets=list(TARGET_COLS))


@router.get("/scatter", response_model=ScatterResponse)
def get_scatter(
    feature: str = Query(...),
    target: str = Query(...),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ScatterResponse:
    if feature not in FEATURE_COLS:
        raise HTTPException(status_code=400, detail=f"Unknown feature {feature}")
    if target not in TARGET_COLS:
        raise HTTPException(status_code=400, detail=f"Unknown target {target}")
    s, e = parse_range(start_date, end_date)
    points, line = analysis_scatter.build(db, feature, target, start_date=s, end_date=e)
    return ScatterResponse(
        feature=feature,
        target=target,
        points=[
            ScatterPointOut(
                ticker=p.ticker,
                earnings_id=p.earnings_id,
                report_date=p.report_date,
                x=p.x,
                y=p.y,
            )
            for p in points
        ],
        line=(
            RegressionLineOut(**line.__dict__) if line is not None else None
        ),
    )


@router.get("/heatmap", response_model=HeatmapResponse)
def get_heatmap(
    method: str = Query(default="pearson", pattern="^(pearson|spearman)$"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HeatmapResponse:
    s, e = parse_range(start_date, end_date)
    data = analysis_heatmap.build(db, method=method, start_date=s, end_date=e)
    return HeatmapResponse(**data)


@router.get("/attribution/{earnings_id}", response_model=EventAttributionResponse)
def get_attribution(
    earnings_id: int,
    target: str = Query(default="eps_surprise_pct"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> EventAttributionResponse:
    if target not in TARGET_COLS:
        raise HTTPException(status_code=400, detail=f"Unknown target {target}")
    s, e = parse_range(start_date, end_date)
    attrs = build_attributions(db, target=target, start_date=s, end_date=e)
    attr = attrs.get(earnings_id)
    if attr is None:
        raise HTTPException(
            status_code=404,
            detail=f"No attribution available for earnings_id {earnings_id}; "
                   "the Lasso fit dropped this event or it lacks all kept features.",
        )
    earn_row = db.query(Earnings).filter_by(earnings_id=earnings_id).one_or_none()
    if earn_row is None:
        raise HTTPException(status_code=404, detail=f"Unknown earnings_id {earnings_id}")
    return EventAttributionResponse(
        earnings_id=attr.earnings_id,
        ticker=attr.ticker,
        report_date=earn_row.report_date,
        target=target,
        prediction=attr.prediction,
        intercept=attr.intercept,
        r_squared=attr.r_squared,
        contributions=[
            FeatureContribution(
                feature=c.feature,
                value=round(c.value, 4),
                coefficient=round(c.coefficient, 4),
                contribution=round(c.contribution, 4),
            )
            for c in attr.contributions
        ],
    )


@router.get("/regression", response_model=list[RegressionFitOut])
def get_regressions(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RegressionFitOut]:
    s, e = parse_range(start_date, end_date)
    fits = analysis_regression.fit_all(db, start_date=s, end_date=e)
    return [
        RegressionFitOut(
            method=f.method,
            target=f.target,
            n=f.n,
            features_used=f.features_used,
            intercept=f.intercept,
            r_squared=f.r_squared,
            r_squared_loo=f.r_squared_loo,
            rmse=f.rmse,
            coefficients=[
                CoefficientOut(feature=c.feature, value=c.value, abs_value=c.abs_value)
                for c in f.coefficients
            ],
            note=f.note,
        )
        for f in fits
    ]
