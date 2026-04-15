"""Pytest configuration and fixtures."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine


@pytest.fixture(name="engine")
def engine_fixture(tmp_path):
    """Create a test database engine with a fresh SQLite file per test."""
    # Set DATA_DIR to tmp_path for this test so file uploads use temp dir
    os.environ["DATA_DIR"] = str(tmp_path)

    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine):
    """Provide a test database session."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine, tmp_path):
    """Provide a FastAPI test client with test database."""
    from app.config import Settings, get_settings
    from app.database import get_session, reset_engine
    from app.main import app

    # Ensure DATA_DIR is set and engine is reset
    os.environ["DATA_DIR"] = str(tmp_path)
    reset_engine()

    def _get_test_session():
        with Session(engine) as session:
            yield session

    def _get_test_settings():
        return Settings()

    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[get_settings] = _get_test_settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    reset_engine()

