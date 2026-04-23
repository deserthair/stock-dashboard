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


# ---------- date-range filters ----------


def test_date_range_narrows_earnings(client):
    wide = client.get("/api/earnings").json()
    narrow = client.get(
        "/api/earnings?start_date=2025-10-01&end_date=2026-01-31"
    ).json()
    assert len(narrow) < len(wide)
    assert all(
        "2025-10-01" <= row["report_date"] <= "2026-01-31" for row in narrow
    )


def test_date_range_invalid_format(client):
    r = client.get("/api/earnings?start_date=garbage")
    assert r.status_code == 400
    assert "start_date" in r.json()["detail"].lower()


def test_date_range_reversed_rejected(client):
    r = client.get("/api/earnings?start_date=2026-05-01&end_date=2026-01-01")
    assert r.status_code == 400


def test_date_range_on_scatter(client):
    wide = client.get(
        "/api/analysis/scatter?feature=news_sentiment_mean_30d&target=eps_surprise_pct"
    ).json()
    narrow = client.get(
        "/api/analysis/scatter"
        "?feature=news_sentiment_mean_30d&target=eps_surprise_pct"
        "&start_date=2025-10-01&end_date=2026-03-31"
    ).json()
    assert len(narrow["points"]) <= len(wide["points"])
    # all points must fall inside the narrow window
    for p in narrow["points"]:
        assert "2025-10-01" <= p["report_date"] <= "2026-03-31"


def test_date_range_on_hypotheses(client):
    wide = client.get("/api/hypotheses").json()
    narrow = client.get(
        "/api/hypotheses?start_date=2025-10-01&end_date=2026-01-31"
    ).json()
    assert narrow["total"] <= wide["total"]
    for row in narrow["rows"]:
        assert "2025-10-01" <= row["report_date"] <= "2026-01-31"


def test_date_range_open_bounds(client):
    """Only one bound supplied — the other side is unbounded."""
    r1 = client.get("/api/earnings?start_date=2026-01-01")
    assert r1.status_code == 200
    for row in r1.json():
        assert row["report_date"] >= "2026-01-01"
    r2 = client.get("/api/earnings?end_date=2025-12-31")
    assert r2.status_code == 200
    for row in r2.json():
        assert row["report_date"] <= "2025-12-31"


# ---------- feature attribution + postmortem ----------


def test_hypotheses_have_top_drivers(client):
    body = client.get("/api/hypotheses").json()
    with_drivers = [r for r in body["rows"] if r.get("top_drivers")]
    assert len(with_drivers) >= 1
    driver = with_drivers[0]["top_drivers"][0]
    for key in ("feature", "value", "coefficient", "contribution"):
        assert key in driver
    assert abs(driver["contribution"] - driver["value"] * driver["coefficient"]) < 0.05


def test_attribution_endpoint(client):
    hypo = client.get("/api/hypotheses").json()
    target = next(r for r in hypo["rows"] if r.get("top_drivers"))
    earn_rows = client.get(
        f"/api/earnings?ticker={target['ticker']}&past_only=true"
    ).json()
    match = next(e for e in earn_rows if e["report_date"] == target["report_date"])
    r = client.get(f"/api/analysis/attribution/{match['earnings_id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == target["ticker"]
    assert body["target"] == "eps_surprise_pct"
    assert len(body["contributions"]) >= 1


def test_postmortem_endpoint(client):
    earn_rows = client.get("/api/earnings?ticker=CMG&past_only=true").json()
    q4 = next(e for e in earn_rows if e["fiscal_period"] == "Q4 2025")
    r = client.get(f"/api/earnings/{q4['earnings_id']}/postmortem")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "CMG"
    assert "beat" in body["headline"].lower()
    assert len(body["narrative"]) > 100


def test_postmortem_404(client):
    earn_rows = client.get("/api/earnings?ticker=SBUX").json()
    upcoming = next(e for e in earn_rows if e["fiscal_period"] == "Q2 2026")
    r = client.get(f"/api/earnings/{upcoming['earnings_id']}/postmortem")
    assert r.status_code == 404


# ---------- trends ----------


def test_trends_queries_have_expected_cohorts(client):
    rows = client.get("/api/trends").json()
    assert len(rows) >= 16
    cats = {r["category"] for r in rows}
    assert {"company", "menu", "segment", "macro"}.issubset(cats)


def test_trends_queries_filter_by_ticker(client):
    rows = client.get("/api/trends?ticker=CMG").json()
    assert len(rows) >= 2
    assert all(r["ticker"] == "CMG" for r in rows)
    assert {r["category"] for r in rows}.issuperset({"company", "menu"})


def test_trends_series_observations(client):
    rows = client.get("/api/trends?ticker=CMG").json()
    brand = next(r for r in rows if r["category"] == "company")
    detail = client.get(f"/api/trends/{brand['query_id']}").json()
    assert detail["query"]["query"] == "Chipotle"
    assert len(detail["observations"]) >= 100
    assert detail["latest"] is not None
    assert isinstance(detail["change_90d_pct"], (int, float))


def test_trends_series_404(client):
    r = client.get("/api/trends/99999")
    assert r.status_code == 404


def test_trends_series_date_range(client):
    rows = client.get("/api/trends?ticker=CMG").json()
    brand = next(r for r in rows if r["category"] == "company")
    narrow = client.get(
        f"/api/trends/{brand['query_id']}"
        "?start_date=2025-01-01&end_date=2025-06-30"
    ).json()
    for o in narrow["observations"]:
        assert "2025-01-01" <= o["obs_date"] <= "2025-06-30"


# ---------- fundamentals ----------


def test_fundamentals_shape(client):
    r = client.get("/api/companies/CMG/fundamentals")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "CMG"
    assert body["metrics"]["quarters_available"] >= 12
    # ~3 years of history from the 16-quarter seed
    assert body["metrics"]["years_of_history"] >= 3.0
    assert len(body["quarterly"]) >= 12


def test_fundamentals_growth_rates(client):
    body = client.get("/api/companies/CMG/fundamentals").json()
    m = body["metrics"]
    # Seed baked in ~14% annual revenue growth
    assert m["revenue_yoy_pct"] is not None
    assert 5 < m["revenue_yoy_pct"] < 30
    assert m["revenue_cagr_3y_pct"] is not None
    assert 5 < m["revenue_cagr_3y_pct"] < 30


def test_fundamentals_roic_positive_for_profitable_tickers(client):
    for ticker in ("CMG", "MCD", "CAVA", "WING"):
        body = client.get(f"/api/companies/{ticker}/fundamentals").json()
        assert body["metrics"]["roic_ttm_pct"] is not None
        assert body["metrics"]["roic_ttm_pct"] > 0, f"{ticker} ROIC should be positive"


def test_fundamentals_dividend_yield(client):
    # MCD has a fat dividend in the seed (~$1.67/q); yield should be positive
    body = client.get("/api/companies/MCD/fundamentals").json()
    m = body["metrics"]
    assert m["dividends_per_share_ttm"] is not None
    assert m["dividends_per_share_ttm"] > 0
    assert m["dividend_yield_pct"] is not None
    assert m["dividend_yield_pct"] > 0


def test_fundamentals_non_dividend_payer(client):
    # CMG and CAVA don't pay dividends in the seed
    body = client.get("/api/companies/CMG/fundamentals").json()
    assert (body["metrics"]["dividends_per_share_ttm"] or 0) == 0


def test_fundamentals_unknown_ticker(client):
    r = client.get("/api/companies/ZZZ/fundamentals")
    assert r.status_code == 404
