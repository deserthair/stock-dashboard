from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, engine
from .routes import briefing, companies, earnings, events, macro, universe

settings = get_settings()

app = FastAPI(
    title="RESTIN API",
    description="Restaurant Intelligence Terminal — backend API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _init_db() -> None:
    Base.metadata.create_all(engine)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(universe.router)
app.include_router(briefing.router)
app.include_router(events.router)
app.include_router(earnings.router)
app.include_router(macro.router)
app.include_router(companies.router)
