"""Composite hypothesis score.

Scores each company's pre-earnings setup on a [-1, 1] scale by combining
the available signal columns with a fixed weighting. Updates
`company_signals.hypothesis_score` + `hypothesis_label`.

Labels:
  score > 0.20  → BEAT
  score < -0.20 → MISS
  else          → MIXED
If any required signals are missing, label = 'NO SIGNAL'.
"""

from __future__ import annotations

from app.db import SessionLocal
from app.models import Company, CompanySignal

from ingest.source_run import source_run


WEIGHTS = {
    "rs_vs_xly":                ("divide_by", 10.0, 0.25),
    "sentiment_7d":             ("multiply",   2.0, 0.25),
    "news_volume_pct_baseline": ("divide_by",100.0, 0.15),
    "social_vol_z":             ("divide_by",  3.0, 0.15),
    "jobs_change_30d_pct":      ("divide_by", 10.0, 0.10),
    "change_30d_pct":           ("divide_by", 10.0, 0.10),
}


def _normalize(value: float, mode: str, scale: float) -> float:
    if mode == "divide_by":
        x = value / scale
    elif mode == "multiply":
        x = value * scale
    else:
        x = value
    # clip to [-1, 1]
    if x > 1:
        return 1.0
    if x < -1:
        return -1.0
    return x


def _score_for(sig: CompanySignal) -> tuple[float | None, str]:
    present = 0
    total_weight = 0.0
    acc = 0.0
    for col, (mode, scale, weight) in WEIGHTS.items():
        raw = getattr(sig, col, None)
        if raw is None:
            continue
        acc += _normalize(float(raw), mode, scale) * weight
        total_weight += weight
        present += 1

    if present < 3 or total_weight == 0:
        return None, "NO SIGNAL"

    # Rescale so partial features don't depress the magnitude.
    score = round(acc / total_weight, 3)
    label = "BEAT" if score > 0.20 else "MISS" if score < -0.20 else "MIXED"
    return score, label


def run_once() -> int:
    with source_run("hypothesis") as run:
        rows = 0
        with SessionLocal() as s:
            for c in s.query(Company).filter(Company.is_benchmark.is_(False)).all() \
                    if hasattr(Company, "is_benchmark") else s.query(Company).all():
                sig = s.get(CompanySignal, c.company_id)
                if sig is None:
                    continue
                score, label = _score_for(sig)
                sig.hypothesis_score = score
                sig.hypothesis_label = label
                s.merge(sig)
                rows += 1
            s.commit()
        run.rows_fetched = rows
        return rows


if __name__ == "__main__":
    run_once()
