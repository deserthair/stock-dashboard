"""Per-event feature attribution.

For a given target (default eps_surprise_pct) we refit the Lasso once over
all available earnings, then for each event decompose the prediction into
per-feature contributions: contribution_i = value_i * coef_i.

Returned contributions are sorted by |contribution| descending so callers
can take the top N drivers per event."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from .frame import FEATURE_COLS, load_frame
from .regression import _fit, _prep_matrix


@dataclass
class Contribution:
    feature: str
    value: float
    coefficient: float
    contribution: float


@dataclass
class EventAttribution:
    earnings_id: int
    ticker: str
    report_date: str
    prediction: float
    intercept: float
    r_squared: float
    contributions: list[Contribution]


def build_attributions(
    s: Session,
    target: str = "eps_surprise_pct",
    start_date: date | None = None,
    end_date: date | None = None,
    method: str = "lasso",
) -> dict[int, EventAttribution]:
    """Return {earnings_id: EventAttribution} covering every event in the
    window that has values for all features the Lasso retained."""
    frame = load_frame(s, start_date=start_date, end_date=end_date)
    kept, X, y = _prep_matrix(frame, target)
    if not kept:
        return {}

    fit = _fit(method, X, y, kept, target)
    if fit is None:
        return {}

    coef_by_feature = {c.feature: c.value for c in fit.coefficients}
    intercept = fit.intercept

    out: dict[int, EventAttribution] = {}
    for row in frame:
        # Require all kept features present so the decomposition is honest.
        missing = [f for f in kept if row.features.get(f) is None]
        if missing:
            continue
        contribs: list[Contribution] = []
        pred = intercept
        for f in kept:
            v = float(row.features[f])
            c = coef_by_feature.get(f, 0.0)
            con = v * c
            pred += con
            contribs.append(
                Contribution(feature=f, value=v, coefficient=c, contribution=con)
            )
        contribs.sort(key=lambda c: abs(c.contribution), reverse=True)
        out[row.earnings_id] = EventAttribution(
            earnings_id=row.earnings_id,
            ticker=row.ticker,
            report_date=row.report_date,
            prediction=round(pred, 4),
            intercept=round(intercept, 4),
            r_squared=round(fit.r_squared, 3),
            contributions=contribs,
        )
    return out
