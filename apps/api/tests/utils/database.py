"""Database utilities for testing.

This module provides helper functions for managing test databases,
including creating/dropping databases, setting up AGE extension,
and cleaning up test data.
"""

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.settings import Settings
from app.db.postgres.auth_session import Base

# Import all models to ensure they are registered with Base.metadata
# This allows Base.metadata.create_all() and Base.metadata.drop_all() to work properly
from app.features.auth import models  # noqa: F401


async def create_test_database(settings: Settings) -> None:
    """Create test database if it doesn't exist.

    Args:
        settings: Application settings with test database configuration
    """
    # Connect to default 'postgres' database to create test database
    conn = await asyncpg.connect(
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database="postgres",
    )

    try:
        # Check if test database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.test_postgres_db,
        )

        if not exists:
            # Create test database
            await conn.execute(f'CREATE DATABASE "{settings.test_postgres_db}"')
    finally:
        await conn.close()


async def drop_test_database(settings: Settings) -> None:
    """Drop test database if it exists.

    Args:
        settings: Application settings with test database configuration
    """
    # Connect to default 'postgres' database to drop test database
    conn = await asyncpg.connect(
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database="postgres",
    )

    try:
        # Terminate all connections to test database
        await conn.execute(
            """
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = $1
            AND pid <> pg_backend_pid()
            """,
            settings.test_postgres_db,
        )

        # Drop test database
        await conn.execute(f'DROP DATABASE IF EXISTS "{settings.test_postgres_db}"')
    finally:
        await conn.close()


async def setup_age_extension(pool: asyncpg.Pool) -> None:
    """Install and configure AGE extension in the database.

    Args:
        pool: Database connection pool
    """
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS age;")
        await conn.execute("LOAD 'age';")
        await conn.execute("SET search_path = ag_catalog, '$user', public;")


async def cleanup_age_graphs(pool: asyncpg.Pool) -> None:
    """Drop all AGE graphs in the database.

    Args:
        pool: Database connection pool
    """
    async with pool.acquire() as conn:
        await conn.execute("LOAD 'age';")
        await conn.execute("SET search_path = ag_catalog, '$user', public;")

        # Get all graph names
        graph_names = await conn.fetch("SELECT name FROM ag_catalog.ag_graph;")

        # Drop each graph
        for row in graph_names:
            graph_name = row["name"]
            try:
                await conn.execute(
                    f"SELECT ag_catalog.drop_graph('{graph_name}', true);"
                )
            except Exception as e:
                # Continue even if one graph fails to drop
                print(f"Warning: Failed to drop graph {graph_name}: {e}")


async def create_all_tables(engine: AsyncEngine) -> None:
    """Create all tables from SQLAlchemy metadata.

    Args:
        engine: SQLAlchemy async engine
    """

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables(engine: AsyncEngine) -> None:
    """Drop all tables from SQLAlchemy metadata.

    Args:
        engine: SQLAlchemy async engine
    """

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def clear_all_tables(conn: AsyncConnection) -> None:
    """Clear all data from tables without dropping them.

    Args:
        conn: SQLAlchemy async connection
    """
    # Get all table names from auth schema
    result = await conn.execute(
        text(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename NOT LIKE 'pg_%'
            AND tablename NOT LIKE 'sql_%'
            """
        )
    )

    tables = [row[0] for row in result]

    # Disable foreign key checks temporarily
    await conn.execute(text("SET session_replication_role = 'replica';"))

    try:
        # Truncate all tables
        for table in tables:
            await conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE;'))
    finally:
        # Re-enable foreign key checks
        await conn.execute(text("SET session_replication_role = 'origin';"))
