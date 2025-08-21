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

    # PostgreSQL Database
    postgres_server: str = Field(default="localhost", description="PostgreSQL server")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(
        default="postgres", description="PostgreSQL password"
    )
    postgres_db: str = Field(default="nous", description="PostgreSQL database name")

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    # Graph Database (KuzuDB API Server)
    graph_api_url: str = Field(
        default="http://localhost:8000", description="KuzuDB API server URL"
    )
    graph_api_username: str | None = Field(
        default=None, description="KuzuDB API server username for basic auth"
    )
    graph_api_password: str | None = Field(
        default=None, description="KuzuDB API server password for basic auth"
    )

    # Legacy Graph Database (Neo4j example) - kept for backward compatibility
    graph_uri: str = Field(
        default="bolt://localhost:7687", description="Graph database URI"
    )
    graph_user: str = Field(default="neo4j", description="Graph database user")
    graph_password: str = Field(
        default="password", description="Graph database password"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
