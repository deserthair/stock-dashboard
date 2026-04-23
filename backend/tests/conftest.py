"""Pytest fixtures.

Each test gets a fresh, seeded, in-memory-equivalent SQLite DB so the API
surface can be exercised without touching the developer's local data.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolated_database(tmp_path_factory) -> None:
    """Point the app at a throwaway SQLite file before anything imports db."""
    path = tmp_path_factory.mktemp("restin") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    yield
    # pytest cleans up tmp_path automatically


@pytest.fixture(scope="session")
def seeded_db(_isolated_database):
    from app.db import Base, engine
    from app.seed import run as seed_run

    Base.metadata.create_all(engine)
    seed_run()
    yield


@pytest.fixture
def client(seeded_db):
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c
