from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    database_url: str | None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name="DocFlow AI API",
        environment=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL"),
    )
