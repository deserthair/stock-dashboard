"""Multivariate regression for EPS surprise + post-earnings returns.

Fits two models per target:
  - OLS   — baseline with all features
  - Lasso — L1-regularized (alpha grid via 5-fold CV, or fallback alpha=0.1
    for sample sizes < 10 where CV is unreliable)

Returns coefficients, intercept, R² (in-sample), and — when n ≥ 10 —
leave-one-out R² as a fair out-of-sample estimate. Features with
> 30% missing values are dropped from the design matrix; remaining
missing values are imputed column-mean."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from .frame import FEATURE_COLS, TARGET_COLS, load_frame


@dataclass
class Coefficient:
    feature: str
    value: float
    abs_value: float


@dataclass
class RegressionFit:
    method: str
    target: str
    n: int
    features_used: list[str]
    intercept: float
    r_squared: float
    r_squared_loo: float | None
    rmse: float
    coefficients: list[Coefficient] = field(default_factory=list)
    note: str | None = None


def _prep_matrix(frame, target: str) -> tuple[list[str], list[list[float]], list[float]]:
    """Returns (feature_list, X (list of rows), y), dropping rows missing the target."""
    filtered = [r for r in frame if r.targets.get(target) is not None]
    if not filtered:
        return [], [], []

    # Drop features missing for > 30% of rows.
    keep: list[str] = []
    for col in FEATURE_COLS:
        missing = sum(1 for r in filtered if r.features.get(col) is None)
        if missing / len(filtered) <= 0.3:
            keep.append(col)

    # Column-mean impute remaining missing values.
    means: dict[str, float] = {}
    for col in keep:
        vals = [float(r.features[col]) for r in filtered if r.features.get(col) is not None]
        means[col] = sum(vals) / len(vals) if vals else 0.0

    X: list[list[float]] = []
    y: list[float] = []
    for r in filtered:
        row = []
        for col in keep:
            v = r.features.get(col)
            row.append(float(v) if v is not None else means[col])
        X.append(row)
        y.append(float(r.targets[target]))
    return keep, X, y


def _fit(method: str, X, y, kept: list[str], target: str) -> RegressionFit | None:
    import numpy as np
    from sklearn.linear_model import Lasso, LassoCV, LinearRegression
    from sklearn.metrics import mean_squared_error, r2_score

    X_np = np.asarray(X, dtype=float)
    y_np = np.asarray(y, dtype=float)
    n = X_np.shape[0]
    if n < 3 or X_np.shape[1] == 0:
        return None

    note: str | None = None
    if method == "lasso":
        if n >= 10:
            model = LassoCV(cv=min(5, n - 1), max_iter=5000)
        else:
            model = Lasso(alpha=0.1, max_iter=5000)
            note = f"n={n} too small for CV; used fixed alpha=0.1"
    else:
        model = LinearRegression()

    model.fit(X_np, y_np)
    y_pred = model.predict(X_np)
    r2 = float(r2_score(y_np, y_pred)) if np.var(y_np) > 0 else 0.0
    rmse = float(mean_squared_error(y_np, y_pred) ** 0.5)

    # Leave-one-out CV for an out-of-sample estimate when n is modest.
    r2_loo: float | None = None
    if n >= 10:
        preds_loo = []
        for i in range(n):
            mask = np.ones(n, dtype=bool)
            mask[i] = False
            m = type(model)(**model.get_params()) if method == "lasso" else LinearRegression()
            m.fit(X_np[mask], y_np[mask])
            preds_loo.append(float(m.predict(X_np[i : i + 1])[0]))
        preds_loo_np = np.asarray(preds_loo)
        if np.var(y_np) > 0:
            r2_loo = float(1.0 - np.sum((y_np - preds_loo_np) ** 2) / np.sum((y_np - np.mean(y_np)) ** 2))

    coefs = []
    coef_vals = getattr(model, "coef_", None)
    if coef_vals is not None:
        for name, val in zip(kept, coef_vals):
            coefs.append(Coefficient(feature=name, value=float(val), abs_value=abs(float(val))))
        coefs.sort(key=lambda c: c.abs_value, reverse=True)

    return RegressionFit(
        method=method,
        target=target,
        n=n,
        features_used=kept,
        intercept=float(getattr(model, "intercept_", 0.0)),
        r_squared=r2,
        r_squared_loo=r2_loo,
        rmse=rmse,
        coefficients=coefs,
        note=note,
    )


def fit_all(s: Session) -> list[RegressionFit]:
    frame = load_frame(s)
    out: list[RegressionFit] = []
    for target in TARGET_COLS:
        kept, X, y = _prep_matrix(frame, target)
        if not kept:
            continue
        for method in ("ols", "lasso"):
            fit = _fit(method, X, y, kept, target)
            if fit is not None:
                out.append(fit)
    return out
