"""PostgreSQL database connection management for graph operations.

This module provides direct asyncpg connections for AGE graph operations and raw SQL queries.
Used primarily by the graph features for Cypher queries and AGE-specific operations.
"""

import asyncpg

from app.core.settings import get_settings

_pool: asyncpg.Pool | None = None


async def get_graph_db_pool() -> asyncpg.Pool:
    """Get the database connection pool as a dependency."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            min_size=5,
            max_size=20,
        )

    return _pool


async def close_graph_db_pool() -> None:
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def reset_db_pool() -> None:
    """Reset the database connection pool for testing purposes."""
    global _pool
    if _pool:
        try:
            await _pool.close()
        except Exception:
            pass  # Ignore errors during reset
        _pool = None
