"""Historical hypothesis tracker.

For every past earnings event with sufficient data to verify, compare the
hypothesis score that would have been assigned (based on the *current*
hypothesis_score stored on the earnings row, set by the seed or by a
backfill job) against the actual beat/miss outcome. Reports running
accuracy."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from analysis.attribution import build_attributions
from analysis.outcomes import compute as compute_outcome

from ..db import get_db
from ..models import Company, Earnings
from ..schemas import (
    FeatureContribution,
    HypothesisTrackerRow,
    HypothesisTrackerSummary,
)
from ._filters import apply_date_range, parse_range

router = APIRouter(prefix="/api/hypotheses", tags=["hypotheses"])


def _hyp_label(score: float | None) -> str | None:
    if score is None:
        return None
    if score > 0.20:
        return "BEAT"
    if score < -0.20:
        return "MISS"
    return "MIXED"


@router.get("", response_model=HypothesisTrackerSummary)
def list_hypotheses(
    db: Session = Depends(get_db),
    ticker: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> HypothesisTrackerSummary:
    q = (
        db.query(Earnings, Company)
        .join(Company, Company.company_id == Earnings.company_id)
    )
    if ticker:
        q = q.filter(Company.ticker == ticker.upper())
    q = apply_date_range(q, Earnings.report_date, start_date, end_date, is_datetime=False)
    rows = q.order_by(Earnings.report_date.desc()).all()

    # Fit Lasso once and decompose each event's prediction so the tracker
    # can surface the top 5 per-feature drivers per row.
    start, end = parse_range(start_date, end_date)
    attributions = build_attributions(db, start_date=start, end_date=end)

    tracker: list[HypothesisTrackerRow] = []
    scored = 0
    correct = 0
    for e, company in rows:
        oc = compute_outcome(db, e)
        score = e.hypothesis_score
        label = _hyp_label(score)
        actual = "BEAT" if oc.eps_beat else "MISS" if oc.eps_beat is False else None
        predict_correct = None
        if label in {"BEAT", "MISS"} and actual is not None:
            predict_correct = label == actual
            scored += 1
            if predict_correct:
                correct += 1

        drivers: list[FeatureContribution] = []
        attr = attributions.get(e.earnings_id)
        if attr is not None:
            for c in attr.contributions[:5]:
                drivers.append(
                    FeatureContribution(
                        feature=c.feature,
                        value=round(c.value, 4),
                        coefficient=round(c.coefficient, 4),
                        contribution=round(c.contribution, 4),
                    )
                )

        tracker.append(
            HypothesisTrackerRow(
                ticker=company.ticker,
                report_date=e.report_date,
                fiscal_period=e.fiscal_period,
                hypothesis_score=score,
                hypothesis_label=label,
                actual=actual,
                reaction=oc.reaction,
                eps_surprise_pct=oc.eps_surprise_pct,
                post_earnings_1d_return=oc.post_earnings_1d_return,
                prediction_correct=predict_correct,
                top_drivers=drivers,
            )
        )

    accuracy = round(correct / scored * 100, 1) if scored else None
    return HypothesisTrackerSummary(
        total=len(rows),
        scored=scored,
        correct=correct,
        accuracy_pct=accuracy,
        rows=tracker,
    )
