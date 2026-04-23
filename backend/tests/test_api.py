"""Smoke tests for every API route against the seeded DB."""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_universe_excludes_benchmarks(client):
    r = client.get("/api/universe")
    assert r.status_code == 200
    tickers = [row["ticker"] for row in r.json()]
    assert len(tickers) == 8
    assert "XLY" not in tickers
    assert "SPY" not in tickers
    assert "CMG" in tickers


def test_universe_row_shape(client):
    row = next(r for r in client.get("/api/universe").json() if r["ticker"] == "CMG")
    for key in (
        "ticker", "name", "last_price", "change_1d_pct", "hypothesis_label",
        "hypothesis_score", "next_er_date",
    ):
        assert key in row


def test_briefing_endpoint(client):
    r = client.get("/api/briefing")
    assert r.status_code == 200
    body = r.json()
    assert body["stats"]["total_count"] == 8
    assert len(body["briefing"]["sections"]) == 4
    headings = [s["heading"] for s in body["briefing"]["sections"]]
    assert headings == ["Top Story", "Macro Context", "Hypothesis Watch", "Flags"]


def test_events_feed(client):
    r = client.get("/api/events?limit=5")
    assert r.status_code == 200
    assert len(r.json()) <= 5


def test_earnings_calendar_upcoming(client):
    r = client.get("/api/earnings?upcoming_only=true")
    assert r.status_code == 200
    rows = r.json()
    assert all(row["report_date"] >= "2026-04-22" for row in rows)


def test_earnings_calendar_past_has_outcomes(client):
    r = client.get("/api/earnings?ticker=CMG&past_only=true")
    rows = r.json()
    # seeded historical Q4 2025 for CMG has a computed reaction
    q4 = [r for r in rows if r["fiscal_period"] == "Q4 2025"]
    assert q4, "expected a CMG Q4 2025 historical row"
    assert q4[0]["eps_beat"] is True


def test_hypotheses_tracker(client):
    r = client.get("/api/hypotheses")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 17  # 8 upcoming + 17 historical - seeds overlap
    # At least one scored row must exist
    assert body["scored"] >= 1
    assert body["accuracy_pct"] is not None


def test_company_detail(client):
    r = client.get("/api/companies/CMG")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "CMG"
    assert body["cik"] is None or len(body["cik"]) >= 6 or body["cik"] == "0001058090"


def test_company_prices(client):
    r = client.get("/api/companies/CMG/prices?days=90")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "CMG"
    assert len(body["bars"]) >= 80
    last = body["bars"][-1]
    assert last["close"] == 58.42  # matches seeded last_price


def test_company_unknown(client):
    assert client.get("/api/companies/ZZZ").status_code == 404


def test_macro_panel(client):
    r = client.get("/api/macro")
    assert r.status_code == 200
    rows = r.json()
    assert any(row["series_id"] == "PBEEFUSDM" for row in rows)


def test_macro_series_detail(client):
    r = client.get("/api/macro/PBEEFUSDM?days=365")
    # MacroSeries metadata is seeded even without observations
    assert r.status_code == 200
    body = r.json()
    assert body["series_id"] == "PBEEFUSDM"


def test_news_empty_in_sandbox(client):
    r = client.get("/api/news?ticker=CMG")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_filings_shape(client):
    assert client.get("/api/filings").status_code == 200


def test_social_shape(client):
    assert client.get("/api/social").status_code == 200
    assert client.get("/api/social/reddit").status_code == 200


def test_jobs_shape(client):
    assert client.get("/api/jobs").status_code == 200


def test_correlations_shape(client):
    assert client.get("/api/analysis/correlations").status_code == 200


def test_ops_source_runs_shape(client):
    assert client.get("/api/ops/source-runs").status_code == 200


def test_analysis_axes(client):
    r = client.get("/api/analysis/axes")
    assert r.status_code == 200
    body = r.json()
    assert "news_sentiment_mean_30d" in body["features"]
    assert "eps_surprise_pct" in body["targets"]


def test_analysis_scatter_seeded(client):
    r = client.get(
        "/api/analysis/scatter?feature=news_sentiment_mean_30d&target=eps_surprise_pct"
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["points"]) >= 10       # 17 historical earnings seeded
    line = body["line"]
    assert line is not None
    # Seed was engineered to correlate positively
    assert line["pearson_r"] is not None and line["pearson_r"] > 0.3


def test_analysis_scatter_rejects_unknown(client):
    r = client.get("/api/analysis/scatter?feature=bogus&target=eps_surprise_pct")
    assert r.status_code == 400


def test_analysis_heatmap(client):
    r = client.get("/api/analysis/heatmap")
    assert r.status_code == 200
    body = r.json()
    n = len(body["features"])
    assert n >= 10
    assert len(body["matrix"]) == n
    for i in range(n):
        # diagonal is always 1.0 for Pearson
        assert body["matrix"][i][i] is None or abs(body["matrix"][i][i] - 1.0) < 1e-6


def test_analysis_regression(client):
    r = client.get("/api/analysis/regression")
    assert r.status_code == 200
    fits = r.json()
    assert len(fits) >= 2
    methods = {f["method"] for f in fits}
    assert {"ols", "lasso"}.issubset(methods)
    # At least one lasso fit should have coefficients
    lasso_fits = [f for f in fits if f["method"] == "lasso"]
    assert any(len(f["coefficients"]) > 0 for f in lasso_fits)
