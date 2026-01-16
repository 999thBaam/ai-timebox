from __future__ import annotations
"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aitimebox"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM (provider-agnostic)
    llm_provider: str = "openai"  # openai, anthropic, etc.
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # Application
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
