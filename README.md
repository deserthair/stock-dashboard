# RESTIN — Restaurant Intelligence Terminal

A data pipeline + analysis dashboard for tracking publicly-traded restaurant
companies and correlating news/social/macro/job signals with earnings outcomes
and stock reactions.

See [`restaurant-intelligence-dashboard-plan-3.md`](restaurant-intelligence-dashboard-plan-3.md)
for the full build plan and [`dashboard-mockup-1.html`](dashboard-mockup-1.html)
for the terminal-dense visual reference.

## Architecture

Two-server split — backend and frontend are independent processes:

```
Next.js (3000) ──HTTP──▶ FastAPI (8000) ──SQL──▶ Postgres (5432)
                                ▲
                        Worker processes
                        (ingest, normalize, features, analysis)
```

- **Backend** — Python 3.11 · FastAPI · SQLAlchemy 2.0 · APScheduler. Runs the
  API server and the ingest workers. Uses SQLite by default so it runs without
  Postgres; set `DATABASE_URL` to switch to Postgres.
- **Frontend** — Next.js 14 (App Router) · TypeScript · Tailwind. Consumes the
  backend JSON API. Auto-generated TS types from the OpenAPI spec.
- **Database** — Postgres 16 in production; four schemas (`raw`, `normalized`,
  `features`, `analytics`). The MVP uses the `normalized` tables only.

## Quickstart (local, no Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head          # create schema (SQLite by default)
python -m app.seed            # populate with universe + demo signals
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run gen:types             # auto-generate TypeScript types from OpenAPI spec
npm run dev
# → http://localhost:3000
```

### Running workers

```bash
cd backend
python -m ingest.scheduler    # starts APScheduler with all 17 jobs
```

## Tests

```bash
cd backend && pytest                 # 26 unit + API tests
cd frontend && npm test              # 22 unit + component tests
```

## Migrations

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Quickstart (Docker Compose)

```bash
cp backend/.env.example backend/.env
docker compose up --build
# Frontend → http://localhost:3000
# Backend  → http://localhost:8000/docs
```

## Tracked universe (MVP — 8 tickers)

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

## What's shipped in this scaffold

- Backend skeleton with universe/briefing/earnings/events/macro routes backed
  by seeded demo data
- yfinance price-ingest worker (Phase 1 starter)
- Next.js frontend matching the mockup's Briefing view
- Company detail page skeleton
- Docker Compose for the full stack

## What's next (per the plan)

- Phase 2: news/social/email ingest + Claude-backed sentiment scoring
- Phase 3: jobs scraping + unified event stream
- Phase 4: feature engineering + correlations + models
- Phase 5: remaining UI pages (Earnings, Correlations, Macro, Hypotheses)
