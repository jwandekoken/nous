"""Application settings and configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(  # pyright: ignore[reportUnannotatedClassAttribute]
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Nous API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")

    # CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins",
    )

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT tokens",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration time in minutes"
    )

    # Graph Database (ArcadeDB HTTP API)
    arcadedb_url: str = Field(
        default="http://localhost:2480", description="ArcadeDB HTTP API server URL"
    )
    arcadedb_user: str | None = Field(
        default=None, description="ArcadeDB API server username for basic auth"
    )
    arcadedb_password: str | None = Field(
        default=None, description="ArcadeDB API server password for basic auth"
    )
    arcadedb_database: str = Field(
        default="graphdb", description="ArcadeDB database name"
    )

    # PostgreSQL Database
    postgres_user: str = Field(default="admin", description="PostgreSQL user")
    postgres_password: str = Field(
        default="supersecretpassword", description="PostgreSQL password"
    )
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(
        default="multimodel_db", description="PostgreSQL database name"
    )
    age_graph_name: str = Field(default="nous", description="AGE graph name")

    # Google AI
    google_api_key: str | None = Field(
        default=None, description="Google AI API key for Gemini model"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
