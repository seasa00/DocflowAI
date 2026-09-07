from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    database_url: str | None
    private_storage_path: str
    max_upload_bytes: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name="DocFlow AI API",
        environment=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL"),
        # The compose volume is mounted here.  Deployments should set this to a
        # directory that is not served by their web server.
        private_storage_path=os.getenv("PRIVATE_STORAGE_PATH", "/app/storage"),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
    )
