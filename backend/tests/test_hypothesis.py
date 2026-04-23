"""Unit tests for the hypothesis-scoring logic.

The composite score aggregates over available signals. Missing signals
drop out gracefully; the label rule is fixed at ±0.20 thresholds.
"""

from normalize.hypothesis import _normalize, _score_for


class _FakeSig:
    def __init__(self, **kwargs):
        for k in (
            "rs_vs_xly",
            "sentiment_7d",
            "news_volume_pct_baseline",
            "social_vol_z",
            "jobs_change_30d_pct",
            "change_30d_pct",
        ):
            setattr(self, k, kwargs.get(k))


def test_clip_range():
    assert _normalize(100, "divide_by", 10.0) == 1.0
    assert _normalize(-100, "divide_by", 10.0) == -1.0
    assert _normalize(1.0, "multiply", 2.0) == 1.0


def test_label_thresholds():
    # Very bullish setup — should clearly BEAT
    sig = _FakeSig(
        rs_vs_xly=8, sentiment_7d=0.5, news_volume_pct_baseline=200,
        social_vol_z=2, jobs_change_30d_pct=10, change_30d_pct=12,
    )
    score, label = _score_for(sig)
    assert label == "BEAT"
    assert score is not None and score > 0.5

    # Very bearish
    sig = _FakeSig(
        rs_vs_xly=-8, sentiment_7d=-0.4, news_volume_pct_baseline=-50,
        social_vol_z=-2, jobs_change_30d_pct=-8, change_30d_pct=-10,
    )
    score, label = _score_for(sig)
    assert label == "MISS"
    assert score is not None and score < -0.3


def test_no_signal_when_mostly_null():
    sig = _FakeSig(rs_vs_xly=5)  # only one signal
    score, label = _score_for(sig)
    assert label == "NO SIGNAL"
    assert score is None


def test_mixed_when_small():
    sig = _FakeSig(
        rs_vs_xly=0.5, sentiment_7d=0.02, news_volume_pct_baseline=10,
        social_vol_z=0.2, jobs_change_30d_pct=1, change_30d_pct=0.5,
    )
    _, label = _score_for(sig)
    assert label == "MIXED"
