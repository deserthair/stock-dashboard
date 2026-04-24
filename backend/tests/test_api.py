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


# ---------- commodities + options ----------


def test_commodities_list(client):
    rows = client.get("/api/commodities").json()
    assert len(rows) >= 10
    symbols = {r["meta"]["symbol"] for r in rows}
    for sym in ("LE=F", "HE=F", "ZC=F", "KC=F"):
        assert sym in symbols
    assert any(r["meta"]["source"] == "fred" for r in rows)


def test_commodities_filter_by_category(client):
    protein = client.get("/api/commodities?category=protein").json()
    assert all(r["meta"]["category"] == "protein" for r in protein)
    assert len(protein) >= 3


def test_commodity_detail(client):
    r = client.get("/api/commodities/LE=F")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["label"] == "Live Cattle"
    assert len(body["observations"]) >= 300
    assert body["latest"] is not None


def test_commodity_404(client):
    r = client.get("/api/commodities/BOGUS=F")
    assert r.status_code == 404


def test_options_summary(client):
    r = client.get("/api/options/CMG")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "CMG"
    assert body["latest"] is not None
    assert body["latest"]["atm_iv"] is not None
    assert len(body["history"]) >= 30
    assert isinstance(body["iv_trend_30d_pct"], (int, float))


def test_options_unknown_ticker(client):
    r = client.get("/api/options/ZZZ")
    assert r.status_code == 404


# ---------- simulation ----------


def test_price_paths_gbm_shape(client):
    r = client.get("/api/simulate/price-paths/CMG?horizon_days=30&n_paths=2000&seed=42")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "CMG"
    assert body["model"] == "gbm"
    assert body["horizon_days"] == 30
    assert body["n_paths"] == 2000
    assert len(body["bands"]) == 30
    # Bands are monotonic p05 ≤ p25 ≤ p50 ≤ p75 ≤ p95 for every day
    for band in body["bands"]:
        assert band["p05"] <= band["p25"] <= band["p50"] <= band["p75"] <= band["p95"]
    t = body["terminal_stats"]
    assert 0.0 <= t["prob_positive_return"] <= 1.0
    assert 0.0 <= t["prob_up_10pct"] <= 1.0
    assert 0.0 <= t["prob_down_10pct"] <= 1.0


def test_price_paths_merton_picks_up_earnings(client):
    # CMG has an upcoming earnings report within 30d of the seed anchor
    r = client.get(
        "/api/simulate/price-paths/CMG?horizon_days=45&n_paths=2000&model=merton&seed=7"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "merton"


def test_price_paths_reproducible_with_seed(client):
    a = client.get(
        "/api/simulate/price-paths/CMG?horizon_days=30&n_paths=2000&seed=123"
    ).json()
    b = client.get(
        "/api/simulate/price-paths/CMG?horizon_days=30&n_paths=2000&seed=123"
    ).json()
    assert a["terminal_stats"]["p50"] == b["terminal_stats"]["p50"]


def test_price_paths_bad_model_400(client):
    r = client.get("/api/simulate/price-paths/CMG?model=bogus")
    assert r.status_code == 422  # FastAPI validates the enum pattern


def test_price_paths_unknown_ticker_400(client):
    r = client.get("/api/simulate/price-paths/ZZZ")
    assert r.status_code == 400


def test_earnings_bootstrap_shape(client):
    r = client.get("/api/simulate/earnings-bootstrap/CMG?n_bootstrap=1000&seed=42")
    assert r.status_code == 200
    body = r.json()
    assert body["target_ticker"] == "CMG"
    assert body["n_bootstrap"] == 1000
    assert len(body["histogram"]) == 40
    q = body["quantiles"]
    assert q["p05"] <= q["p25"] <= q["p50"] <= q["p75"] <= q["p95"]
    assert body["method"] in ("score_window", "same_sign", "all_events")
    assert 0.0 <= body["prob_positive_return"] <= 1.0


def test_earnings_bootstrap_unknown_ticker_400(client):
    r = client.get("/api/simulate/earnings-bootstrap/ZZZ")
    assert r.status_code == 400


def test_dcf_shape(client):
    r = client.get("/api/simulate/dcf/CMG?seed=42&n_simulations=2000")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "CMG"
    assert body["n_valid"] > 0
    s = body["intrinsic_value_stats"]
    assert s["p05"] <= s["p25"] <= s["p50"] <= s["p75"] <= s["p95"]
    assert len(body["intrinsic_value_histogram"]) == 50
    assert body["fit_quarters"] >= 16


def test_dcf_parameters_fit_from_history(client):
    body = client.get("/api/simulate/dcf/CMG?seed=42&n_simulations=2000").json()
    # CMG seed has ~14% revenue growth + ~11% FCF margin
    assert 5 < body["revenue_growth_mean_pct"] < 25
    assert 5 < body["fcf_margin_mean_pct"] < 25


def test_dcf_override_growth(client):
    a = client.get("/api/simulate/dcf/CMG?seed=42&n_simulations=2000").json()
    b = client.get(
        "/api/simulate/dcf/CMG?seed=42&n_simulations=2000&growth_override=0.02"
    ).json()
    assert b["intrinsic_value_stats"]["p50"] < a["intrinsic_value_stats"]["p50"]


def test_dcf_unknown_ticker_400(client):
    r = client.get("/api/simulate/dcf/ZZZ")
    assert r.status_code == 400


def test_dcf_wacc_below_terminal_growth_400(client):
    r = client.get(
        "/api/simulate/dcf/CMG?wacc_mean=0.03&wacc_std=0.002&terminal_growth=0.05&n_simulations=500"
    )
    assert r.status_code == 400
