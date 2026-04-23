# Restaurant Intelligence Dashboard — Build Plan

A data pipeline and analysis dashboard for tracking publicly-traded restaurant companies, correlating news/social/macro/job signals with earnings outcomes and stock reactions.

**Primary goal:** Build an educated, data-backed hypothesis about earnings beats/misses and post-earnings stock moves for a tracked universe of restaurant stocks.

**Secondary goal:** Create a reusable data pipeline and analysis framework that demonstrates Solutions Engineer / AI Implementation skills (ingest pipelines, APIs, database design, AI-augmented analysis).

---

## 1. Scope

### Tracked Universe (MVP — 8 tickers)

| Ticker | Company | Segment |
|--------|---------|---------|
| CMG | Chipotle | Fast Casual |
| SBUX | Starbucks | Coffee |
| MCD | McDonald's | QSR |
| CAVA | Cava Group | Fast Casual |
| TXRH | Texas Roadhouse | Casual Dining |
| WING | Wingstop | QSR |
| DPZ | Domino's | Pizza / QSR |
| QSR | Restaurant Brands Intl | QSR Conglomerate |

Rationale: segment diversity (fast casual / QSR / casual / coffee / pizza), similar macro exposure (beef, chicken, wages, consumer discretionary), enough earnings events per year across the group (~32) to start pattern-finding.

### Out of Scope for MVP

- Options flow / unusual options activity
- Insider transactions (Form 4 tracking) — Phase 2
- Foot traffic (Placer.ai) — too expensive
- Credit card spend data — institutional pricing
- International / non-US restaurant stocks

---

## 2. Architecture

### Two-server split — frontend and backend are fully independent

The backend server and frontend server are **separate processes with separate deployments, separate repos (or separate top-level folders in a monorepo), and separate lifecycles.** They communicate only over HTTP. This is not negotiable — it's the single most important architectural decision.

```
┌──────────────────────────────┐         ┌──────────────────────────────┐
│   FRONTEND SERVER            │         │   BACKEND SERVER             │
│   Next.js 14 (App Router)    │         │   FastAPI (Python)           │
│   Port 3000                  │ ──HTTP─▶│   Port 8000                  │
│   Node.js runtime            │         │   Uvicorn ASGI runtime       │
│   Deploys independently      │         │   Deploys independently      │
└──────────────────────────────┘         └──────────────┬───────────────┘
         ▲                                              │
         │                                              │ SQL
         │ Browser                                      ▼
         │                                ┌──────────────────────────────┐
    ┌────┴─────┐                          │   PostgreSQL 16              │
    │   User   │                          │   Port 5432                  │
    └──────────┘                          └──────────────┬───────────────┘
                                                         ▲
                                                         │ SQL
                                          ┌──────────────┴───────────────┐
                                          │   WORKER PROCESSES           │
                                          │   (Python, APScheduler)      │
                                          │   Ingest · Normalize ·       │
                                          │   Feature-Engineer · Analyze │
                                          │   Run independently of API   │
                                          └──────────────────────────────┘
```

### Why separation matters here

1. **Different runtimes.** Node.js for the frontend, Python for the backend. They can't share a process.
2. **Different deployment cadences.** Frontend UI tweaks don't require restarting the data pipeline. Backend API changes don't require a frontend redeploy.
3. **Different scaling profiles.** The frontend is mostly static assets + SSR; the backend handles long-running database queries and analysis jobs. They scale differently.
4. **Different security surfaces.** The backend holds all API keys and database credentials. The frontend never touches secrets — it only calls the backend over HTTP.
5. **Hiring signal.** This is how real production systems are built. A monolith where the frontend and backend are glued together is a red flag in SE interviews.

### Data flow

```
[External Data Sources]
    │
    ▼
[Ingest Workers (Python)]  ──writes──▶ [raw.* tables / JSONB]
    │
    ▼
[Normalizer Jobs (Python)] ──writes──▶ [normalized.* tables]
    │
    ▼
[Feature Engineering (Python)] ──▶ [features.* tables]
    │
    ▼
[Analysis Jobs (Python)] ──writes──▶ [analytics.* tables]
    │
    ▼
[FastAPI Backend] ──reads from all schemas, serves JSON──▶ [HTTP]
                                                            │
                                                            ▼
                                            [Next.js Frontend]
                                                            │
                                                            ▼
                                                    [Browser / User]
```

Workers write to the database. The API server reads from the database. The frontend reads from the API server. No shortcuts, no shared memory, no direct frontend-to-database connections.

### Finalized stack

**Backend server (`/backend`)**
- **Language:** Python 3.11+
- **Package manager:** `uv` (Rust-based, fast, the 2026 consensus choice)
- **API framework:** FastAPI + Uvicorn (async, auto-generates OpenAPI spec at `/openapi.json`)
- **ORM:** SQLAlchemy 2.0 (async) + Alembic for migrations
- **Validation:** Pydantic v2 (comes with FastAPI)
- **Scheduler:** APScheduler to start; migrate to Prefect if DAG complexity grows
- **Data libraries:** pandas, numpy, scipy, statsmodels, scikit-learn, lightgbm
- **Ingest libraries:** yfinance, fredapi, sec-edgar-downloader, praw, beautifulsoup4, playwright, feedparser, imap-tools
- **AI:** `anthropic` SDK (Claude for sentiment extraction and briefing synthesis)
- **Testing:** pytest, pytest-asyncio, httpx for API tests
- **Linting:** ruff (replaces black + flake8 + isort in one tool)

**Frontend server (`/frontend`)**
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript (strict mode)
- **Runtime:** Node.js 20 LTS
- **Styling:** Tailwind CSS
- **UI primitives:** shadcn/ui (copy-paste Radix-based components)
- **Icons:** lucide-react
- **Charts:** recharts for standard charts; lightweight-charts (TradingView) specifically for the price chart with event markers
- **Data fetching:** @tanstack/react-query (cache + background refetch + polling)
- **Client state:** zustand (only where React Query isn't sufficient)
- **API types:** `openapi-typescript` — auto-generates TypeScript types from the FastAPI OpenAPI spec
- **Fonts:** JetBrains Mono (monospace, data) + Fraunces (serif, headlines)
- **Testing:** Vitest for unit tests; Playwright for e2e

**Database**
- PostgreSQL 16, single instance, four schemas: `raw`, `normalized`, `features`, `analytics`

**Infrastructure**
- Docker Compose orchestrating four services: `db`, `backend`, `worker`, `frontend`
- Each service independently restartable
- Deployed to the VPS (same box as OpenClaw, or separate if resources tight)
- Reverse proxy via Caddy or Nginx fronting both `:3000` (frontend) and `:8000/api` (backend)

### API contract discipline — the "magic trick"

FastAPI automatically produces `/openapi.json`. The frontend build pipeline regenerates TypeScript types from that spec:

```bash
# Run from /frontend whenever backend API changes
npx openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts
```

Every backend change forces a type regeneration. Every type regeneration surfaces frontend type errors at compile time, not runtime. This single pattern eliminates the majority of frontend/backend integration bugs and makes the two-server setup feel like a monorepo without the coupling.

### Repo Structure

Two top-level folders, clearly separated. Either split into two repos or keep as a monorepo with both under one root — the separation is what matters, not the Git layout.

```
restaurant-intel/
│
├── backend/                    # ─────── PYTHON BACKEND SERVER ───────
│   ├── pyproject.toml          # uv-managed dependencies
│   ├── uv.lock
│   ├── alembic.ini
│   ├── .env.example
│   ├── Dockerfile
│   │
│   ├── app/                    # FastAPI application
│   │   ├── main.py             # FastAPI entrypoint, CORS config
│   │   ├── config.py           # Settings via pydantic-settings
│   │   ├── db.py               # SQLAlchemy async engine + session
│   │   ├── deps.py             # FastAPI dependencies (auth, db session)
│   │   ├── models/             # SQLAlchemy ORM models (mirror schema)
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── routes/
│   │       ├── briefing.py     # GET /api/briefing
│   │       ├── universe.py     # GET /api/universe
│   │       ├── companies.py    # GET /api/companies/{ticker}/*
│   │       ├── earnings.py     # GET /api/earnings
│   │       ├── events.py       # GET /api/events
│   │       ├── correlations.py # GET /api/analysis/correlations
│   │       └── hypotheses.py   # GET/POST /api/hypotheses
│   │
│   ├── ingest/                 # Data ingestion workers
│   │   ├── scheduler.py        # APScheduler — the worker entrypoint
│   │   ├── rate_limiter.py
│   │   └── sources/
│   │       ├── prices.py           # yfinance
│   │       ├── earnings.py         # Finnhub / Nasdaq scrape
│   │       ├── filings.py          # SEC EDGAR
│   │       ├── macro.py            # FRED
│   │       ├── news_rss.py         # Google News RSS + company PR pages
│   │       ├── news_email.py       # IMAP parser for Google Alerts
│   │       ├── social_email.py     # IMAP parser for X / Reddit / IG alerts
│   │       ├── reddit.py           # PRAW
│   │       ├── jobs.py             # Careers page scrapers
│   │       └── weather.py          # NOAA
│   │
│   ├── normalize/              # Raw → normalized jobs
│   │   ├── jobs.py
│   │   ├── sentiment.py        # Claude API calls
│   │   └── entity_extraction.py
│   │
│   ├── features/               # Feature engineering
│   │   └── engineer.py
│   │
│   ├── analysis/               # Statistical analysis + ML
│   │   ├── correlation.py
│   │   ├── event_study.py
│   │   └── models.py
│   │
│   ├── db/
│   │   ├── schema.sql          # Canonical schema reference
│   │   └── migrations/         # Alembic migrations
│   │
│   ├── notebooks/              # Jupyter for exploration
│   └── tests/
│
├── frontend/                   # ─────── NEXT.JS FRONTEND SERVER ───────
│   ├── package.json
│   ├── pnpm-lock.yaml          # (or package-lock.json)
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── .env.local.example      # NEXT_PUBLIC_API_URL etc.
│   ├── Dockerfile
│   │
│   └── src/
│       ├── app/                # Next.js App Router
│       │   ├── layout.tsx      # Root layout (fonts, providers)
│       │   ├── page.tsx        # / → Briefing page
│       │   ├── company/
│       │   │   └── [ticker]/
│       │   │       └── page.tsx
│       │   ├── earnings/page.tsx
│       │   ├── correlations/page.tsx
│       │   ├── macro/page.tsx
│       │   └── hypotheses/page.tsx
│       │
│       ├── components/
│       │   ├── layout/         # TopBar, Sidebar, Shell
│       │   ├── panels/         # Panel, StatTile, FeatureBar
│       │   ├── charts/         # PriceChart, EventChart, Sparkline
│       │   ├── tables/         # UniverseMatrix, NewsTable
│       │   └── ui/             # shadcn/ui components (owned code)
│       │
│       ├── lib/
│       │   ├── api.ts          # Typed fetch wrapper → backend
│       │   ├── api-types.ts    # AUTO-GENERATED from OpenAPI — do not edit
│       │   ├── query-client.ts # React Query setup
│       │   └── format.ts       # Number/date/pct formatters
│       │
│       └── styles/
│           └── globals.css     # Tailwind + CSS variables
│
├── docker-compose.yml          # ─── Orchestrates all services ───
├── Caddyfile                   # Reverse proxy config (optional)
├── .gitignore
└── README.md
```

### Docker Compose layout

Four services, each a separate container with a single responsibility:

```yaml
# docker-compose.yml (abbreviated)
services:
  db:
    image: postgres:16
    ports: ["5432:5432"]
    volumes: [pg_data:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: restin
      POSTGRES_USER: restin
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    depends_on: [db]
    environment:
      DATABASE_URL: postgresql+asyncpg://restin:${DB_PASSWORD}@db:5432/restin
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      FINNHUB_API_KEY: ${FINNHUB_API_KEY}
      FRED_API_KEY: ${FRED_API_KEY}

  worker:
    build: ./backend                          # same image as backend
    command: python -m ingest.scheduler       # but different entrypoint
    depends_on: [db]
    environment:                              # same env as backend
      DATABASE_URL: postgresql+asyncpg://restin:${DB_PASSWORD}@db:5432/restin
      # ... other keys ...

  frontend:
    build: ./frontend
    command: node server.js                   # Next.js standalone output
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
    depends_on: [backend]

volumes:
  pg_data:
```

Three important notes:

1. **Backend and worker share an image.** Same Python dependencies, different entrypoints. The API server runs `uvicorn`, the worker runs the scheduler. Cleaner than maintaining two Dockerfiles.
2. **Frontend only talks to backend over HTTP.** It has no database credentials, no API keys for third parties, nothing sensitive. Its only env var is `NEXT_PUBLIC_API_URL`.
3. **Each service restarts independently.** `docker compose restart frontend` does not touch the pipeline. `docker compose restart worker` does not affect anyone browsing the dashboard.

---

## 3. Data Sources

### Tier 1 — Build First (rock solid, free)

**Stock prices & volume**
- Library: `yfinance`
- Cadence: every 15 min during market hours (9:30–16:00 ET) + EOD snapshot
- Store: ticker, timestamp, open, high, low, close, adj_close, volume
- Notes: also pull sector ETF (XLY) and market index (SPY) for relative strength features

**Earnings calendar & actuals**
- Primary: Finnhub free tier (`/calendar/earnings`)
- Backup: Nasdaq earnings calendar scrape
- Cadence: daily
- Store: ticker, report_date, fiscal_period, time_of_day (BMO/AMC), eps_estimate, eps_actual, revenue_estimate, revenue_actual, surprise_pct

**SEC filings**
- API: EDGAR full-text search + company tickers API
- Cadence: daily
- Store: ticker, filing_type (10-K, 10-Q, 8-K, DEF 14A), filed_at, accession_number, primary_doc_url, extracted_text
- Notes: 8-Ks are most valuable for event detection; extract Item numbers (2.02 = results of operations, 5.02 = exec changes)

**Macro data — FRED API**
- Cadence: weekly (daily for oil/gas)
- Series to track:
  - `PBEEFUSDM` — Beef prices
  - `WPU0211` — Poultry
  - `PWHEAMTUSDM` — Wheat
  - `GASREGW` — Retail gasoline
  - `UNRATE` — Unemployment
  - `UMCSENT` — U Mich consumer sentiment
  - `CES7072200003` — Avg hourly earnings, food services
  - `CUSR0000SEFV` — CPI food away from home
  - `DEXUSEU` — USD/EUR (for QSR, SBUX international exposure)
  - `DGS10` — 10Y Treasury (consumer discretionary is rate-sensitive)
- Store: series_id, date, value, fetched_at

### Tier 2 — Build Second (messier but high-signal)

**News — three-source strategy**

*2a. Google News RSS per ticker.* Poll every 2 hours. Free, headline-only, noisy but broad.

*2b. Company press release pages.* Scrape each investor relations page daily. Lowest volume, highest signal — every earnings release, exec change, and guidance update shows up here first.

*2c. Email ingestion via IMAP (NEW — user-driven).*
- Create a dedicated Gmail account (e.g., `bronson.restaurant.intel@gmail.com`)
- Subscribe to:
  - **Google Alerts** for each ticker, company name, and CEO name
  - **Seeking Alpha** email alerts for tracked tickers
  - **Yahoo Finance** watchlist email digests
  - **Company IR email lists** (most have "email alerts" signup on IR pages — press releases land here first, sometimes before wires)
- Parse via IMAP with Python `imaplib` + `email` module
- Extract: sender, subject, body, received_at, links, ticker_mentions
- Move processed emails to an "ingested" folder so you can reprocess if parser changes
- Store raw email payload + parsed fields

**Social media — email-alert strategy (NEW approach)**

Instead of fighting APIs and scrapers, use email notifications:

- **X (Twitter)**: Follow each company's official account, turn on email notifications for their posts. Also follow key restaurant analysts (e.g., Mark Kalinowski, RJ Hottovy).
- **Reddit**: Subscribe via email digest to r/stocks, r/investing, r/SecurityAnalysis, plus company-specific subs (r/Chipotle, r/Starbucks, etc.)
- **Instagram**: Follow company accounts; Instagram sends email digests of activity. Lower signal than X but captures menu launches, LTOs, marketing pushes.
- **LinkedIn**: Follow company pages + CEOs. LinkedIn's weekly digest emails capture executive commentary and hiring announcements.

All routed to the dedicated inbox, parsed via the same IMAP worker as news emails.

Store: platform (parsed from sender domain), source_account, posted_at, content, engagement_hint (if in email), link_to_original.

**Reddit — supplement via PRAW**
- For higher-volume subs where email digests miss fast-moving threads
- Poll daily for mentions of tracked tickers in r/stocks, r/investing, r/wallstreetbets
- Store: subreddit, post_id, created_at, title, body, score, num_comments, ticker_mentions, sentiment_score

**Job postings**
- Scrape each company's careers page weekly (not daily — too volatile)
- Companies that use Workday, Greenhouse, or Lever have structured-enough pages to parse reliably
- Store: company, snapshot_date, total_count, posting_id, title, location, department, posted_date
- Signal is the *delta over time*, not individual postings — a sudden 50% jump in corporate engineering roles is meaningful; one new store manager is not

### Tier 3 — Add Later

**Weather** — NOAA API, free. Relevant for regional chains; less so for national QSR.

**Analyst estimate revisions** — Finnhub has limited free data; Refinitiv/FactSet if you ever go paid.

**Insider transactions** — Form 4 via EDGAR. Add once MVP is working.

---

## 4. Database Schema

### Design principles

1. **Raw is immutable.** Every ingest writes to `raw.*` with full payload as JSONB. Never delete, never update.
2. **Normalized is typed and clean.** Rebuildable from raw at any time.
3. **Features are derived and versioned.** Tag feature rows with a `feature_version` so you can compare different engineering approaches.
4. **Events table is the analysis backbone.** Everything interesting gets written here as a unified event stream.

### Schema: `raw`

```sql
CREATE SCHEMA raw;

CREATE TABLE raw.source_runs (
    run_id BIGSERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    status TEXT,               -- running / success / failed
    rows_fetched INT,
    error_msg TEXT
);

CREATE TABLE raw.prices (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL
);
CREATE INDEX ON raw.prices (ticker, fetched_at DESC);

CREATE TABLE raw.earnings (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    report_date DATE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE raw.filings (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    accession_number TEXT UNIQUE NOT NULL,
    filed_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE raw.macro (
    id BIGSERIAL PRIMARY KEY,
    series_id TEXT NOT NULL,
    obs_date DATE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    UNIQUE(series_id, obs_date)
);

CREATE TABLE raw.news (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,          -- google_rss / pr_page / email_alert
    url_hash TEXT UNIQUE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE raw.emails (
    id BIGSERIAL PRIMARY KEY,
    message_id TEXT UNIQUE NOT NULL,
    from_addr TEXT,
    subject TEXT,
    received_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL        -- full email including body + headers
);

CREATE TABLE raw.reddit (
    id BIGSERIAL PRIMARY KEY,
    post_id TEXT UNIQUE NOT NULL,
    subreddit TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE raw.jobs_snapshot (
    id BIGSERIAL PRIMARY KEY,
    company TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL
);
```

### Schema: `normalized`

```sql
CREATE SCHEMA normalized;

CREATE TABLE normalized.companies (
    company_id SERIAL PRIMARY KEY,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    segment TEXT,
    market_cap_tier TEXT,
    ir_url TEXT,
    careers_url TEXT,
    x_handle TEXT,
    ceo_name TEXT
);

CREATE TABLE normalized.prices_daily (
    company_id INT REFERENCES normalized.companies(company_id),
    trade_date DATE NOT NULL,
    open NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC,
    adj_close NUMERIC, volume BIGINT,
    PRIMARY KEY (company_id, trade_date)
);

CREATE TABLE normalized.prices_intraday (
    company_id INT REFERENCES normalized.companies(company_id),
    ts TIMESTAMPTZ NOT NULL,
    close NUMERIC, volume BIGINT,
    PRIMARY KEY (company_id, ts)
);

CREATE TABLE normalized.earnings (
    earnings_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES normalized.companies(company_id),
    report_date DATE NOT NULL,
    fiscal_period TEXT,           -- e.g., '2026Q1'
    time_of_day TEXT,             -- 'BMO' / 'AMC'
    eps_estimate NUMERIC,
    eps_actual NUMERIC,
    revenue_estimate NUMERIC,
    revenue_actual NUMERIC,
    eps_surprise_pct NUMERIC,
    revenue_surprise_pct NUMERIC,
    same_store_sales_actual NUMERIC,  -- populated from filings
    UNIQUE(company_id, report_date)
);

CREATE TABLE normalized.filings (
    filing_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES normalized.companies(company_id),
    filing_type TEXT NOT NULL,
    accession_number TEXT UNIQUE NOT NULL,
    filed_at TIMESTAMPTZ NOT NULL,
    primary_doc_url TEXT,
    extracted_text TEXT,
    item_numbers TEXT[]           -- for 8-Ks
);

CREATE TABLE normalized.news (
    news_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES normalized.companies(company_id),
    source TEXT,
    url TEXT,
    published_at TIMESTAMPTZ,
    headline TEXT,
    body TEXT,
    sentiment_score NUMERIC,      -- -1 to +1, from Claude
    relevance_score NUMERIC,      -- 0 to 1
    topics TEXT[]                 -- ['earnings','mgmt_change','menu','labor']
);

CREATE TABLE normalized.social_posts (
    post_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES normalized.companies(company_id),
    platform TEXT,
    account TEXT,
    posted_at TIMESTAMPTZ,
    content TEXT,
    engagement_json JSONB,
    sentiment_score NUMERIC,
    is_company_official BOOLEAN
);

CREATE TABLE normalized.jobs_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES normalized.companies(company_id),
    snapshot_date DATE NOT NULL,
    total_count INT,
    by_department JSONB,
    UNIQUE(company_id, snapshot_date)
);

CREATE TABLE normalized.macro_series (
    series_id TEXT NOT NULL,
    obs_date DATE NOT NULL,
    value NUMERIC,
    PRIMARY KEY (series_id, obs_date)
);

CREATE TABLE normalized.events (
    event_id BIGSERIAL PRIMARY KEY,
    company_id INT REFERENCES normalized.companies(company_id),
    event_type TEXT NOT NULL,     -- earnings / 8k / news_spike / social_spike / macro_shock
    event_date TIMESTAMPTZ NOT NULL,
    severity TEXT,                -- low / med / high
    metadata JSONB,
    source_ref TEXT
);
CREATE INDEX ON normalized.events (company_id, event_date DESC);
CREATE INDEX ON normalized.events (event_type, event_date DESC);
```

### Schema: `features`

```sql
CREATE SCHEMA features;

CREATE TABLE features.earnings_event_features (
    feature_id BIGSERIAL PRIMARY KEY,
    earnings_id INT REFERENCES normalized.earnings(earnings_id),
    feature_version TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL,
    -- Price features (T-30 to T-1)
    return_30d NUMERIC,
    volatility_30d NUMERIC,
    volume_trend_30d NUMERIC,
    relative_strength_30d NUMERIC,
    -- Sentiment features
    news_sentiment_mean_30d NUMERIC,
    news_sentiment_trend_30d NUMERIC,
    news_volume_30d INT,
    news_volume_z_score NUMERIC,
    social_sentiment_mean_30d NUMERIC,
    social_volume_30d INT,
    -- Job features
    jobs_count_change_90d NUMERIC,
    jobs_corporate_change_90d NUMERIC,
    -- Filing features
    filings_8k_count_30d INT,
    filings_exec_change BOOLEAN,
    -- Macro features
    beef_price_change_90d NUMERIC,
    chicken_price_change_90d NUMERIC,
    wheat_price_change_90d NUMERIC,
    gas_price_change_90d NUMERIC,
    consumer_sentiment_level NUMERIC,
    consumer_sentiment_change_90d NUMERIC,
    unemployment_change_90d NUMERIC,
    UNIQUE(earnings_id, feature_version)
);
```

### Schema: `analytics`

```sql
CREATE SCHEMA analytics;

CREATE TABLE analytics.earnings_outcomes (
    outcome_id BIGSERIAL PRIMARY KEY,
    earnings_id INT REFERENCES normalized.earnings(earnings_id),
    eps_beat BOOLEAN,
    revenue_beat BOOLEAN,
    post_earnings_1d_return NUMERIC,
    post_earnings_5d_return NUMERIC,
    reaction_classification TEXT  -- 'beat_and_rally','beat_and_sell','miss_and_rally','miss_and_sell'
);

CREATE TABLE analytics.correlations (
    id BIGSERIAL PRIMARY KEY,
    feature_name TEXT NOT NULL,
    target_name TEXT NOT NULL,
    method TEXT NOT NULL,         -- pearson / spearman
    n INT,
    coefficient NUMERIC,
    ci_low NUMERIC, ci_high NUMERIC,
    p_value NUMERIC,
    p_adjusted NUMERIC,           -- after BH correction
    feature_version TEXT,
    computed_at TIMESTAMPTZ
);

CREATE TABLE analytics.model_runs (
    run_id BIGSERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    target TEXT NOT NULL,
    train_start DATE, train_end DATE,
    test_start DATE, test_end DATE,
    metrics JSONB,                -- {rmse, mae, auc, accuracy, etc.}
    feature_importances JSONB,
    feature_version TEXT,
    trained_at TIMESTAMPTZ
);
```

---

## 5. Build Phases

### Phase 1 — Foundation (Week 1–2)

**Goal:** Price + earnings + macro + filings flowing end-to-end for 8 tickers.

- [ ] Postgres setup, migrations, schema creation
- [ ] `normalized.companies` seeded with 8 tickers + metadata
- [ ] yfinance price ingest (daily + intraday)
- [ ] FRED macro ingest (weekly)
- [ ] Finnhub earnings calendar ingest (daily)
- [ ] EDGAR filings ingest (daily)
- [ ] Source run logging + basic error handling
- [ ] First Jupyter notebook: plot prices + macro overlays to sanity-check data

**Success criterion:** Can query "show me CMG's price, last 4 earnings surprises, and beef price correlation" from the DB.

### Phase 2 — Text Signals (Week 3–4)

**Goal:** News and social flowing in, sentiment scored.

- [ ] Dedicated Gmail account created; alerts subscribed (Google Alerts, IR lists, X, Reddit)
- [ ] IMAP email ingest worker
- [ ] Email parser with source-type detection (Google Alert vs X notification vs Reddit digest vs IR push)
- [ ] Google News RSS ingest
- [ ] Company IR page scraper (8 companies, 8 scrapers — no shortcut)
- [ ] Reddit PRAW supplementary ingest
- [ ] Claude API integration for sentiment + topic extraction
  - Prompt: "Classify this headline's sentiment toward {ticker} on a -1 to +1 scale. Return JSON: {sentiment, confidence, topics[], reasoning}"
  - Batch 10–20 headlines per call for cost efficiency
- [ ] De-duplication logic (URL hash + title similarity)

**Success criterion:** Can query "show me all news and social mentions of CMG in the last 30 days with sentiment scores."

### Phase 3 — Jobs + Events (Week 5)

**Goal:** Careers page scraping + unified event stream.

- [ ] Scraper per company careers page (weekly cadence)
- [ ] Events table populated from all sources (earnings filed, 8-K filed, news spike detected, social spike, macro shock)
- [ ] Event detection logic:
  - News spike: daily mention count > 2 std dev above 30d mean
  - Social spike: same, for social_posts
  - Macro shock: single-day change > 2 std dev in key series

**Success criterion:** Events timeline view for any ticker shows a unified stream of everything that happened.

### Phase 4 — Feature Engineering + Analysis (Week 6–7)

**Goal:** Feature vectors per earnings event; first correlations.

- [ ] Feature engineering job — produces one row per earnings event
- [ ] Outcome labeling (beat/miss, reaction classification)
- [ ] Univariate correlation analysis (Pearson + Spearman) with Benjamini-Hochberg correction
- [ ] First regression model (Lasso) on earnings surprise
- [ ] First classifier (LightGBM) on reaction classification
- [ ] Train/val/test split strictly chronological
- [ ] Results written to `analytics.*` tables

**Success criterion:** You can answer "Which signals have the strongest statistically-defensible relationship with earnings beats?"

### Phase 5 — Dashboard UI (Week 8+)

Separate design pass. Covered at high level below.

---

## 6. Frontend Spec

### Design direction

Terminal-dense, Bloomberg-inspired, dark-first. Not a consumer app. Monospace for data, serif (Fraunces) for headlines and editorial moments. Single lime-green accent (`#d4ff3f`) plus strict green/red/amber semantics for market moves and severity. See `dashboard-mockup.html` for the working reference.

### Fonts

- **Display / serif:** Fraunces (400, 500, 700, 900) — used for big numbers, ticker symbols, AI briefing prose, section titles
- **Mono / body:** JetBrains Mono (300, 400, 500, 600, 700) — everything else

### Color tokens (CSS variables)

```css
--bg: #0a0b0d;
--bg-panel: #111318;
--bg-panel-2: #161922;
--border: #232834;
--border-hot: #2e3446;
--text: #d4d7de;
--text-dim: #737a88;
--text-faint: #4a4f5c;
--accent: #d4ff3f;     /* lime signal */
--green: #3fd97b;      /* up */
--red: #ff5c5c;        /* down */
--amber: #ffb547;      /* caution */
--cyan: #5cd5ff;       /* info */
```

### Pages

| Route | Purpose |
|-------|---------|
| `/` | Briefing — universe overview, AI synthesis, event feed, macro snapshot, upcoming earnings |
| `/company/[ticker]` | Company detail — hypothesis, price+events chart, news, social, filings, jobs, feature vector |
| `/earnings` | Calendar of upcoming reports with current hypotheses + past beat/miss history |
| `/correlations` | Correlation lab — scatter feature vs target, with filters, CIs, multiple-testing adjustments visible |
| `/macro` | FRED time series with overlays showing which tickers are most exposed to each series |
| `/hypotheses` | Historical hypothesis tracking — every past earnings event, predicted vs actual, running accuracy |

### Rendering strategy

- **Server components by default.** The briefing page, earnings calendar, and macro page are read-heavy and benefit from SSR.
- **Client components for interactive pieces.** Charts, sortable tables, filters, hypothesis accept/reject buttons.
- **React Query handles polling.** Universe matrix refreshes every 60s. Event feed refreshes every 30s. Briefing regenerates on-demand via a button (not auto — Claude calls cost money).
- **Incremental Static Regeneration** for the company pages — revalidate every 5 minutes.

### Data fetching pattern

One typed fetch wrapper (`lib/api.ts`) that consumes the auto-generated types from `lib/api-types.ts`. Example:

```typescript
// lib/api.ts
import type { paths } from './api-types';

type BriefingResponse = paths['/api/briefing']['get']['responses']['200']['content']['application/json'];

export async function getBriefing(): Promise<BriefingResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/briefing`, {
    next: { revalidate: 300 }
  });
  if (!res.ok) throw new Error(`Briefing fetch failed: ${res.status}`);
  return res.json();
}
```

### Charts

- **Price chart with event markers** → `lightweight-charts` (TradingView). Event dots overlaid as markers. Crosshair tooltips reveal the underlying event on hover.
- **Feature divergence bars, sparklines, correlation scatters** → `recharts`.
- **Macro series stack** → `recharts` `LineChart` with multi-series and synced tooltips.

### Component inventory (first pass)

From the mockup, these are the building blocks:

- `<TopBar />` — nav, clock, ingest health
- `<Sidebar />` — universe list with live prices
- `<Panel />` + `<PanelHeader />` — the bordered container used everywhere
- `<StatTile />` — big serif number with label and delta
- `<UniverseMatrix />` — the big briefing table with sparklines and pills
- `<EventFeed />` — timestamped severity-coded event list
- `<BriefingProse />` — renders Claude's synthesized markdown with tag pills
- `<HypothesisBox />` — accent-bordered box with signal pills
- `<PriceEventChart />` — lightweight-charts wrapper with event markers
- `<FeatureVector />` — name + divergence bar + value triple for every feature
- `<NewsItem />`, `<SocialRow />`, `<FilingRow />` — feed item components
- `<Pill />` — the inline status pill with green/red/amber/cyan variants

---

## 7. Analysis Methodology

### Target variables

1. **EPS beat** (binary): eps_actual > eps_estimate
2. **EPS surprise %** (continuous): (eps_actual − eps_estimate) / |eps_estimate|
3. **Post-earnings 1-day return** (continuous): close_T+1 / close_T−1 − 1
4. **Reaction classification** (categorical): {beat_rally, beat_sell, miss_rally, miss_sell}

### Rigor rules

- **Chronological splits only.** No shuffled cross-validation.
- **Strict feature cutoff.** Features frozen 24h before earnings announcement (no leakage).
- **Multiple testing correction.** Benjamini-Hochberg (`statsmodels.stats.multitest.multipletests`).
- **Confidence intervals on everything.** Bootstrap where closed-form isn't clean.
- **Report effect size, not just p-values.** Small samples make p-values noisy.
- **Track feature_version.** When you change feature definitions, re-run and compare.

### Honest expectations

With ~8 companies × ~4 reports/year × 2–3 years = 60–100 events, statistical power is limited. Goal is not production alpha; goal is:
1. Identify 2–3 features that clear a "consistent signal across train/val/test with CI excluding zero" bar.
2. Build the pipeline discipline to scale to more companies / longer history later.
3. Generate hypotheses worth tracking in paper trading.

---

## 8. Operational Concerns

### Secrets

`.env` file with: `FINNHUB_API_KEY`, `FRED_API_KEY`, `ANTHROPIC_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `DATABASE_URL`. Never commit. Use `python-dotenv`.

### Rate limits

- yfinance: no hard limit but be polite; 1 req/sec per ticker
- FRED: 120 req/min
- Finnhub free: 60 req/min
- EDGAR: 10 req/sec, must send User-Agent with email
- Reddit: 60 req/min
- Claude API: per-tier, batch calls

Implement a token-bucket rate limiter per source.

### Monitoring

- `source_runs` table queried by a simple health-check endpoint
- Daily summary email: "X sources ran successfully, Y failed, Z rows ingested"
- Anomaly detection: if a source hasn't run in 2x its cadence, alert

### Backups

- Daily `pg_dump` to S3 or local disk
- Weekly full backup retained for 6 months

### Cost

Estimated monthly operating cost for MVP:
- VPS: $10–20 (existing OpenClaw box may suffice)
- Anthropic API: $20–50 depending on news volume
- Paid data APIs: $0 initially, ~$20/mo if Marketaux added
- **Total:** ~$30–70/month

---

## 9. Phase 0 — Environment Bootstrap (for Claude Code)

Concrete step-by-step setup. Execute in this order before any feature code.

### Step 1 — Repo skeleton

```bash
mkdir restaurant-intel && cd restaurant-intel
git init
mkdir -p backend/{app,ingest,normalize,features,analysis,db,notebooks,tests}
mkdir -p backend/app/{models,schemas,routes}
mkdir -p backend/ingest/sources
mkdir -p backend/db/migrations
mkdir -p frontend
touch docker-compose.yml README.md .gitignore
```

### Step 2 — Backend bootstrap (Python + uv + FastAPI)

```bash
cd backend

# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize Python project
uv init --python 3.11
uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
       pydantic pydantic-settings python-dotenv \
       pandas numpy scipy statsmodels scikit-learn lightgbm \
       yfinance fredapi praw feedparser beautifulsoup4 playwright \
       imap-tools httpx anthropic apscheduler
uv add --dev pytest pytest-asyncio ruff ipykernel jupyterlab

# Initialize Alembic
uv run alembic init db/migrations
```

### Step 3 — Frontend bootstrap (Next.js + TypeScript)

```bash
cd ../frontend

pnpm create next-app@14 . --typescript --tailwind --app --no-src-dir --import-alias "@/*"
# (answer: use App Router: yes, use ESLint: yes)

pnpm add @tanstack/react-query zustand lucide-react
pnpm add lightweight-charts recharts
pnpm add -D openapi-typescript @types/node

# shadcn/ui
pnpm dlx shadcn@latest init
# Choose: TypeScript, Default style, Slate base color, CSS variables yes
```

### Step 4 — Environment variables

Create `backend/.env.example`:

```
DATABASE_URL=postgresql+asyncpg://restin:restin_dev_pwd@localhost:5432/restin
ANTHROPIC_API_KEY=sk-ant-...
FINNHUB_API_KEY=
FRED_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=restin/0.1
GMAIL_USER=bronson.restaurant.intel@gmail.com
GMAIL_APP_PASSWORD=
```

Create `frontend/.env.local.example`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 5 — Docker Compose

Create `docker-compose.yml` at the repo root (see Section 2). Start the database first:

```bash
docker compose up -d db
```

### Step 6 — Initial schema + first migration

1. Write `backend/db/schema.sql` from Section 4 of this plan
2. Apply it manually to verify: `psql $DATABASE_URL -f backend/db/schema.sql`
3. Generate the first Alembic migration: `uv run alembic revision --autogenerate -m "initial schema"`
4. Apply: `uv run alembic upgrade head`

### Step 7 — Smoke test both servers

Backend:
```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
# Verify: http://localhost:8000/docs opens the FastAPI Swagger UI
```

Frontend:
```bash
cd frontend
pnpm dev
# Verify: http://localhost:3000 shows the Next.js starter page
```

### Step 8 — Wire up type generation

In `frontend/package.json`, add:

```json
"scripts": {
  "gen:types": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts"
}
```

Run `pnpm gen:types` after every backend API change. Commit `api-types.ts`.

### Step 9 — First commits checklist (implementation order)

In order, after bootstrap:

1. `backend/db/schema.sql` — all four schemas, all tables from Section 4
2. `backend/app/models/` — SQLAlchemy ORM models mirroring schema
3. `backend/app/main.py` — FastAPI app with CORS configured for `localhost:3000`
4. `backend/app/routes/universe.py` — `GET /api/universe` returning companies with latest prices
5. `backend/ingest/sources/prices.py` — yfinance worker writing to `raw.prices`
6. `backend/normalize/jobs.py` — prices normalizer
7. `backend/ingest/sources/macro.py` — FRED worker
8. `backend/ingest/sources/earnings.py` — Finnhub worker
9. `backend/ingest/sources/filings.py` — EDGAR worker
10. `backend/ingest/scheduler.py` — APScheduler wiring all Phase 1 sources
11. `backend/notebooks/01_price_macro_sanity.ipynb` — plot prices + macro overlays
12. `frontend/src/app/layout.tsx` — root layout with fonts (Fraunces + JetBrains Mono)
13. `frontend/src/app/globals.css` — CSS variables from Section 6
14. `frontend/src/components/layout/{TopBar,Sidebar,Shell}.tsx`
15. `frontend/src/app/page.tsx` — Briefing page consuming `GET /api/universe`
16. `frontend/src/app/company/[ticker]/page.tsx` — Company detail skeleton
17. Phase 2: email ingest + news RSS + Claude sentiment
18. Phase 3: jobs + events
19. Phase 4: features + analysis
20. Phase 5: remaining pages (earnings, correlations, macro, hypotheses)

---

## 10. Open Questions / Decisions to Revisit

- Whether to use Prefect vs APScheduler (decide after Phase 2 based on complexity)
- Whether to add options data in Phase 2 (unusual options activity is a strong signal but adds ingest complexity)
- Whether to include small-cap restaurants (BROS, SG, PTLO) — more noise but more events per year
- Whether Claude sentiment is better than a cheaper model like Haiku for high-volume tagging; likely yes for Haiku on bulk, Opus on ambiguous cases
- Whether to build a paper-trading layer in Phase 6 to pressure-test hypotheses against live future data
