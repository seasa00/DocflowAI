import psycopg
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


class DatabaseConfigurationError(RuntimeError):
    """Raised when a database operation is requested without a connection URL."""


@lru_cache
def get_engine() -> Engine:
    """Return the SQLAlchemy engine configured for the application database."""
    database_url = get_settings().database_url
    if not database_url:
        raise DatabaseConfigurationError("DATABASE_URL is not configured")

    # Psycopg 3 is used by both the health check and SQLAlchemy.
    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(sqlalchemy_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Create a SQLAlchemy session factory for application services."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db_session():
    """Yield a request-scoped SQLAlchemy session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database_connection() -> None:
    """Open a short PostgreSQL connection and verify it can execute a query."""
    database_url = get_settings().database_url
    if not database_url:
        raise DatabaseConfigurationError("DATABASE_URL is not configured")

    with psycopg.connect(database_url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
