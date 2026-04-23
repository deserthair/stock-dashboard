"""Feature × feature correlation heatmap.

Returns a square matrix of Pearson coefficients over the engineered
feature set, using only rows where both columns are observed."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from .frame import FEATURE_COLS, load_frame


def build(
    s: Session,
    method: str = "pearson",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    import numpy as np
    from scipy import stats

    frame = load_frame(s, start_date=start_date, end_date=end_date)
    if len(frame) < 3:
        return {"method": method, "features": list(FEATURE_COLS), "matrix": []}

    cols = list(FEATURE_COLS)
    n = len(cols)
    matrix: list[list[float | None]] = [[None] * n for _ in range(n)]
    sample_sizes: list[list[int]] = [[0] * n for _ in range(n)]

    for i, a in enumerate(cols):
        for j, b in enumerate(cols):
            if j < i:
                matrix[i][j] = matrix[j][i]
                sample_sizes[i][j] = sample_sizes[j][i]
                continue
            pairs = [
                (float(r.features[a]), float(r.features[b]))
                for r in frame
                if r.features[a] is not None and r.features[b] is not None
            ]
            if len(pairs) < 3:
                matrix[i][j] = None
                sample_sizes[i][j] = len(pairs)
                continue
            xs = np.asarray([p[0] for p in pairs], dtype=float)
            ys = np.asarray([p[1] for p in pairs], dtype=float)
            if np.std(xs) == 0 or np.std(ys) == 0:
                matrix[i][j] = None
                sample_sizes[i][j] = len(pairs)
                continue
            try:
                if method == "spearman":
                    r = stats.spearmanr(xs, ys).statistic
                else:
                    r = stats.pearsonr(xs, ys).statistic
                matrix[i][j] = float(r)
            except Exception:
                matrix[i][j] = None
            sample_sizes[i][j] = len(pairs)

    return {
        "method": method,
        "features": cols,
        "matrix": matrix,
        "sample_sizes": sample_sizes,
    }
