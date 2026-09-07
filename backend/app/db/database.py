import psycopg

from app.core.config import get_settings


class DatabaseConfigurationError(RuntimeError):
    """Raised when a database operation is requested without a connection URL."""


def check_database_connection() -> None:
    """Open a short PostgreSQL connection and verify it can execute a query."""
    database_url = get_settings().database_url
    if not database_url:
        raise DatabaseConfigurationError("DATABASE_URL is not configured")

    with psycopg.connect(database_url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
