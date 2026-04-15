"""Database setup and session management."""

from sqlmodel import SQLModel, Session, create_engine

from app.config import get_settings


_engine = None


def get_engine():
    """Return the database engine, creating it if needed."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # Ensure data directory exists
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            settings.db_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
        # Enable WAL mode for better concurrent performance
        with _engine.connect() as conn:
            import sqlalchemy
            conn.execute(sqlalchemy.text("PRAGMA journal_mode=WAL"))
    return _engine


def reset_engine() -> None:
    """Reset the cached engine (used in tests)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def create_db_and_tables() -> None:
    """Create all database tables."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that provides a database session."""
    engine = get_engine()
    with Session(engine) as session:
        yield session
