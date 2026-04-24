# RESTIN Backend

FastAPI + SQLAlchemy backend for the Restaurant Intelligence Terminal.
Runs one API server process and one scheduler process against a shared
database. SQLite by default for local dev; swap to Postgres by setting
`DATABASE_URL`.

See the [root README](../README.md) for architecture overview and the
[build plan](../restaurant-intelligence-dashboard-plan-3.md) for the
overall design intent.

## Quickstart

```bash
# From repo root
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # FastAPI, SQLAlchemy, analysis deps, pytest
alembic upgrade head             # create schema (SQLite by default)
python -m app.seed               # populate demo data
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs
```

To run the ingest + analysis scheduler in a separate process:

```bash
python -m ingest.scheduler
```

## Environment variables

Every var read by the codebase. Nothing here is required to boot the app —
missing keys cause the specific worker to log `status=skipped` in
`/api/ops/source-runs` and move on.

### Required only in production

| Var | Default (dev) | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/restin.db` | SQLAlchemy connection string. Postgres in prod. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated origins allowed to hit the API. |

### Optional — each unlocks one or more ingest workers

| Var | Unlocks | Where to get |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude sentiment tagging (`normalize/sentiment.py`) · Overnight Synthesis briefing (`normalize/briefing.py`) · earnings postmortems (`normalize/postmortem.py`) | [console.anthropic.com](https://console.anthropic.com) — paid, usage-based |
| `FRED_API_KEY` | FRED macro time series (`ingest/sources/macro.py`) + BLS PPI commodity series for lettuce / tomatoes / poultry (`ingest/sources/commodities.py`) | [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) — free |
| `FINNHUB_API_KEY` | Finnhub earnings calendar ingest (`ingest/sources/earnings.py`) — estimates + actuals | [finnhub.io/register](https://finnhub.io/register) — free tier: 60 req/min |
| `EDGAR_USER_AGENT` | SEC EDGAR filings worker (`ingest/sources/filings.py`). SEC requires a descriptive User-Agent with contact info. | Any string like `"RESTIN/0.1 you@yourdomain.com"` |
| `GMAIL_USER` + `GMAIL_APP_PASSWORD` | IMAP email ingest (`ingest/sources/email_imap.py`) — parses Google Alerts / Seeking Alpha / X notification / Reddit digest / IR email alerts routed to a dedicated Gmail account | Gmail account with 2FA + an [app password](https://myaccount.google.com/apppasswords) |

### Listed in `.env.example` but currently unused

- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` — the
  Reddit worker (`ingest/sources/reddit.py`) currently uses unauthenticated
  JSON endpoints, which Reddit throttles heavily. These would wire in if
  we switch to PRAW. Safe to leave unset today.

### Minimum viable production env

```bash
# backend/.env
DATABASE_URL=postgresql+psycopg2://restin:REAL_PASSWORD@db:5432/restin
CORS_ORIGINS=https://restin.yourdomain.com

ANTHROPIC_API_KEY=sk-ant-...
FRED_API_KEY=...
FINNHUB_API_KEY=...
EDGAR_USER_AGENT=RESTIN/0.1 you@yourdomain.com
GMAIL_USER=bronson.restaurant.intel@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

## What runs where

### Ingest workers (`ingest/sources/*.py`)

All written to be idempotent; re-running is always safe. Each run logs a
`source_runs` row visible at `/api/ops/source-runs`.

| Worker | Cadence | Key? |
|---|---|---|
| `prices` | every 15 min | no |
| `earnings` (Finnhub) | daily 04:00 UTC | `FINNHUB_API_KEY` |
| `macro` (FRED) | daily 07:00 UTC | `FRED_API_KEY` |
| `filings` (EDGAR) | every 2 h | `EDGAR_USER_AGENT` |
| `news_rss` (companies + institutions) | every 2 h | no |
| `pr_pages` | every 6 h | no |
| `reddit` | every 3 h | no (but Reddit 403s aggressively) |
| `email_imap` | every 10 min | `GMAIL_USER` + `GMAIL_APP_PASSWORD` |
| `weather` (NOAA) | daily 06:00 UTC | no |
| `jobs` (ATS scrapers) | weekly Mon 05:00 UTC | no |
| `trends` (Google Trends) | Tue/Fri 03:00 UTC | no |
| `commodities` (futures + PPI) | daily 06:15 UTC | `FRED_API_KEY` for PPI series only |
| `options` (yfinance option chain) | daily 22:00 UTC | no |
| `fundamentals` (yfinance financials) | daily 04:30 UTC | no |
| `holdings` (institutional + Form 4) | daily 05:00 UTC | no |

### Normalize / analysis passes

Run against internal data, no external keys.

| Job | Cadence |
|---|---|
| `sentiment` (Claude-tagged news/social) | every 30 min — *needs `ANTHROPIC_API_KEY`* |
| `signals` (refresh `company_signals`) | every 30 min |
| `events` (spike / shock detection) | every 30 min |
| `hypothesis` (composite score) | every 30 min |
| `briefing_am` / `briefing_pm` (Claude-generated synthesis) | 10 / 18 UTC — *needs `ANTHROPIC_API_KEY`* |
| `postmortem` (per-event narrative) | 14 UTC — *needs `ANTHROPIC_API_KEY`* |
| `features` (feature engineering) | daily 08 UTC |
| `correlations` (Pearson/Spearman + BH adjust) | daily 08:30 UTC |

### Running a single worker on-demand

```bash
python -m ingest.sources.prices
python -m ingest.sources.holdings
python -m normalize.briefing
python -m features.engineer
python -m analysis.correlation
```

## Database

19 tables in total. Key ones:

- **Market data**: `companies`, `company_signals`, `prices_daily`, `earnings`
- **Ingest outputs**: `news`, `reddit_posts`, `social_posts`, `email_messages`,
  `filings`, `jobs_snapshots`, `weather_observations`
- **Series**: `macro_series` + `macro_observations`, `trends_queries` +
  `trends_observations`, `commodity_meta` + `commodity_prices`
- **Quarterly**: `fundamentals` (income stmt + balance sheet + cash flow +
  precomputed ROIC), `institutional_holdings`
- **Events + analysis**: `events`, `features_earnings`, `correlations`,
  `earnings_postmortems`, `briefings`, `options_snapshots`,
  `insider_transactions`
- **Ops**: `source_runs` (every ingest run logs start/end/status/rows/error),
  `alembic_version`

## Migrations

```bash
# Create a new migration after changing models
alembic revision --autogenerate -m "describe change"

# Apply
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

Migrations render with `render_as_batch=True` for SQLite compatibility, so
the same migration scripts apply cleanly to Postgres in prod.

## Tests

```bash
pytest            # 85 cases: routes, math, simulation, backtest, holdings
pytest -k trends  # run a subset
```

`tests/conftest.py` points `DATABASE_URL` at a throwaway SQLite file per
session and seeds it before yielding the `TestClient` — tests never touch
your local `data/restin.db`.

## Packages

| Package | What's in it |
|---|---|
| `app/` | FastAPI app, routes, schemas, models, seed |
| `ingest/` | Scheduler + `ingest/sources/` (one file per data source) + rate limiter + source-run logger |
| `normalize/` | Claude sentiment, briefing, postmortem; event detection; signal refresh; hypothesis scoring |
| `features/` | Feature engineering over earnings events |
| `analysis/` | Correlations, regression (OLS + Lasso), scatter, heatmap, attribution, outcomes, DCF-helper, fundamentals quality metrics |
| `simulation/` | Monte Carlo price paths (GBM + Merton), earnings-reaction bootstrap, DCF Monte Carlo, backtest framework |
| `db/migrations/` | Alembic versions |
| `tests/` | pytest suite |

## API

OpenAPI spec served at `http://localhost:8000/openapi.json`; Swagger UI at
`/docs`. Frontend regenerates its TS types from the spec via
`npm run gen:types` — keep that in your workflow after route changes.
