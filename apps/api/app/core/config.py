from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Company Intelligence Copilot API"
    # If DATABASE_URL is not set, it's built from POSTGRES_USER/PASSWORD/DB below.
    # Set DATABASE_URL explicitly for dev (SQLite, or a host-Postgres URL).
    database_url: str | None = None
    postgres_user: str = "postgres"
    postgres_password: str | None = None
    postgres_db: str = "app"
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    redis_url: str = "redis://localhost:6379/0"
    chroma_persist_directory: str = "./storage/chroma"

    # RAG pipeline configuration
    rag_mistral_api_key: str | None = None
    rag_openai_api_base_url: str = "https://openrouter.ai/api/v1"
    rag_openai_api_key: str | None = None
    rag_extraction_model: str = "google/gemini-2.5-flash-lite"
    rag_generation_model: str = "openai/gpt-4o-mini"
    rag_classification_model: str = "google/gemini-2.0-flash-lite-001"
    rag_chat_model: str = "openai/gpt-4o"
    rag_max_file_size_mb: int = 30
    rag_enable_background_processing: bool = False

    # RAG embedding configuration
    rag_embedding_api_base_url: str = "https://api.openai.com/v1"
    rag_embedding_api_key: str | None = None
    rag_embedding_model: str = "text-embedding-3-small"

    # Chat / AI Consultant configuration
    chat_max_context_tokens: int = 12000
    chat_max_output_tokens: int = 2000
    tavily_api_key: str | None = None

    # MCP / code execution configuration
    e2b_api_key: str | None = None
    mcp_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def _resolve_database_url(self) -> "Settings":
        if self.database_url:
            return self
        if self.postgres_password:
            self.database_url = (
                f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
                f"@postgres:5432/{self.postgres_db}"
            )
            return self
        # Dev fallback: Postgres on the devcontainer host via Docker Desktop
        self.database_url = "postgresql+psycopg://postgres:postgres@host.docker.internal:5435/app"
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
