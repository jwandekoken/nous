"""PostgreSQL database connection and session management with SQLModel."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.settings import get_settings

# Create async engine
settings = get_settings()
engine = create_async_engine(
    settings.postgres_url,
    echo=settings.debug,
    future=True,
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered with SQLModel
        from app.features.users.models import User  # noqa: F401

        await conn.run_sync(SQLModel.metadata.create_all)
