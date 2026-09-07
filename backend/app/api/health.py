from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from psycopg import Error as PsycopgError

from app.db.database import DatabaseConfigurationError, check_database_connection

router = APIRouter(tags=["system"])


@router.get("/health", response_model=None)
def health_check() -> dict[str, str] | JSONResponse:
    """Report application and PostgreSQL availability."""
    try:
        check_database_connection()
    except (DatabaseConfigurationError, PsycopgError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "database": "unavailable"},
        )

    return {"status": "ok", "database": "connected"}
