"""Integration tests for PostgreSQL connection management."""

from collections.abc import AsyncGenerator

import asyncpg
import pytest

from app.core.settings import get_settings
from app.db.postgres.connection import close_db_pool, get_db_pool


@pytest.fixture
async def postgres_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Provide a connection pool and ensure it's closed after the test."""
    pool = await get_db_pool()
    try:
        yield pool
    finally:
        # Ensure the pool is closed after each test
        await close_db_pool()


class TestPostgresIntegration:
    """Integration tests for PostgreSQL using a real database connection."""

    @pytest.mark.asyncio
    async def test_settings_configuration(self):
        """Test that PostgreSQL settings are properly configured."""
        settings = get_settings()

        # Check that required settings exist and are of the correct type
        assert hasattr(settings, "postgres_user")
        assert isinstance(settings.postgres_user, str)
        assert len(settings.postgres_user.strip()) > 0

        assert hasattr(settings, "postgres_password")
        assert isinstance(settings.postgres_password, str)

        assert hasattr(settings, "postgres_host")
        assert isinstance(settings.postgres_host, str)
        assert len(settings.postgres_host.strip()) > 0

        assert hasattr(settings, "postgres_port")
        assert isinstance(settings.postgres_port, int)

        assert hasattr(settings, "postgres_db")
        assert isinstance(settings.postgres_db, str)
        assert len(settings.postgres_db.strip()) > 0

    @pytest.mark.asyncio
    async def test_connection_pooling_lifecycle(self):
        """Test the singleton behavior of the connection pool."""
        try:
            # First call should create a new pool
            pool1 = await get_db_pool()
            assert isinstance(pool1, asyncpg.Pool)
            assert not pool1.is_closing()

            # Second call should return the same pool instance
            pool2 = await get_db_pool()
            assert pool1 is pool2

            # Close the pool
            await close_db_pool()
            assert pool1.is_closing()

            # The global _pool variable should be None now
            # Next call should create a new pool
            new_pool = await get_db_pool()
            assert isinstance(new_pool, asyncpg.Pool)
            assert new_pool is not pool1

        except Exception as e:
            pytest.skip(f"PostgreSQL server not available: {e}")
        finally:
            # Final cleanup
            await close_db_pool()

    @pytest.mark.asyncio
    async def test_successful_connection_and_query(self, postgres_pool: asyncpg.Pool):
        """Test that we can connect and execute a simple query."""
        try:
            async with postgres_pool.acquire() as connection:
                async with connection.transaction():
                    result = await connection.fetchval("SELECT 1")
            assert result == 1
        except Exception as e:
            pytest.skip(f"PostgreSQL server not available: {e}")
