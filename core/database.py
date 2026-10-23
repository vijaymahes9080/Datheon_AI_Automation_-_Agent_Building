"""Thread-safe SQLite database connection manager and session lifecycle.

Provides connection pooling, declarative base, and session generator.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from core.config import settings

# Engine configuration for thread-safe SQLite operation
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database schemas and tables."""
    # Import models to ensure they are registered with Base metadata
    import core.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
