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
    llm_provider: str
    openrouter_api_key: str | None
    openrouter_model: str
    openrouter_base_url: str


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
        # Keep selection at the provider boundary.  A local adapter can be
        # registered here later without changing extraction callers.
        llm_provider=os.getenv("LLM_PROVIDER", "openrouter"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )
