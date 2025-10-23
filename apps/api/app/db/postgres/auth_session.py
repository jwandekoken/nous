"""SQLAlchemy database session management for auth operations.

This module provides SQLAlchemy ORM sessions for authentication and authorization operations.
Used primarily by the auth features for user management, tenant operations, and API key management.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import get_settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Global session factory
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def init_db_session() -> None:
    """Initialize the database session factory."""
    global _async_session_maker

    if _async_session_maker is not None:
        return  # Already initialized

    settings = get_settings()

    # Create async engine
    engine = create_async_engine(
        str(settings.database_url),
        echo=settings.debug,
        pool_pre_ping=True,
    )

    # Create session factory
    _async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    if _async_session_maker is None:
        init_db_session()

    if _async_session_maker is None:
        raise RuntimeError("Failed to initialize database session")

    async with _async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
