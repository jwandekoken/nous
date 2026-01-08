"""Application settings and configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Nous API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    testing: bool = Field(default=False, description="Testing mode")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")

    # CORS
    allowed_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:5173",
        ],
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
    refresh_token_expire_days: int = Field(
        default=30, description="Refresh token expiration time in days"
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
    test_postgres_db: str = Field(
        default="multimodel_db_test", description="PostgreSQL test database name"
    )
    age_graph_name: str = Field(default="nous", description="AGE graph name")

    # Database URL (computed property)
    @property
    def database_url(self) -> str:
        """Construct database URL from individual components."""
        db_name = self.test_postgres_db if self.testing else self.postgres_db
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{db_name}"
        )

    # Google AI
    google_api_key: str | None = Field(
        default=None, description="Google AI API key for Gemini model"
    )

    # Qdrant Vector Database
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant HTTP port")

    # Embeddings
    embedding_model: str = Field(
        default="models/gemini-embedding-001",
        description="Embedding model name for Google Generative AI",
    )
    embedding_dim: int = Field(
        default=768, description="Embedding vector dimension (Qdrant vector_size)"
    )

    # Vector Collection
    vector_collection_name: str = Field(
        default="agent_memory", description="Qdrant collection name for agent memory"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
