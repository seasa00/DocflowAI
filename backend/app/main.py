from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)
app.include_router(health_router)
app.include_router(documents_router)
