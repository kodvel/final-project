from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Company Intelligence Copilot API"
    database_url: str = "sqlite:///./storage/app.db"
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    openai_api_key: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    redis_url: str = "redis://localhost:6379/0"
    chroma_persist_directory: str = "./storage/chroma"

    # RAG pipeline configuration
    rag_mistral_api_key: str | None = None
    rag_openai_api_base_url: str = "https://api.openai.com/v1"
    rag_openai_api_key: str | None = None
    rag_openai_model: str = "google/gemini-3.1-flash-lite-preview"
    rag_max_file_size_mb: int = 30
    rag_enable_background_processing: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
