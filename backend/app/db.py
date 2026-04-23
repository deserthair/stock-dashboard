from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

url = settings.database_url
if url.startswith("postgresql+asyncpg"):
    url = url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)

if url.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False}, future=True)
else:
    engine = create_engine(url, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
