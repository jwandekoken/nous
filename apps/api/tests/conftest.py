"""Pytest configuration and shared fixtures for all tests.

This module provides function-scoped fixtures for:
- Test database lifecycle management
- SQLAlchemy engine and session management
- PostgreSQL/AGE connection pools
- Password hashing utilities
"""

import asyncio
from collections.abc import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.authentication import pwd_context
from app.core.settings import Settings, get_settings
from app.features.auth.usecases.signup_tenant_usecase import PasswordHasher
from tests.utils.database import (
    cleanup_age_graphs,
    create_all_tables,
    create_test_database,
    drop_all_tables,
    drop_test_database,
    setup_age_extension,
)

# Module-level state
_test_db_initialized = False
_tables_created = False


@pytest.fixture(scope="function")
def test_settings() -> Settings:
    """Provide test settings with testing mode enabled."""
    settings = get_settings()
    settings.testing = True
    return settings


@pytest_asyncio.fixture(scope="function")
async def async_engine(test_settings: Settings) -> AsyncGenerator[AsyncEngine, None]:
    """Provide SQLAlchemy async engine for tests.

    Creates a fresh engine for each test to avoid event loop issues.
    """
    global _test_db_initialized, _tables_created

    # Create test database once
    if not _test_db_initialized:
        await create_test_database(test_settings)

        # Create temporary pool to setup AGE
        temp_pool = await asyncpg.create_pool(
            user=test_settings.postgres_user,
            password=test_settings.postgres_password,
            host=test_settings.postgres_host,
            port=test_settings.postgres_port,
            database=test_settings.test_postgres_db,
            min_size=1,
            max_size=2,
        )
        await setup_age_extension(temp_pool)
        await temp_pool.close()

        _test_db_initialized = True

    # Create fresh engine for this test
    engine = create_async_engine(test_settings.database_url, echo=False)

    # Create tables once per session
    if not _tables_created:
        await create_all_tables(engine)
        _tables_created = True

    yield engine

    # Dispose engine after test
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for each test.

    Each test gets a fresh session. The session does not auto-commit,
    allowing tests or use cases to manage their own transactions.
    After the test, rolls back any uncommitted changes.
    """
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session
        # Roll back any uncommitted changes
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(async_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Clean all table data before each test.

    This ensures each test starts with a clean slate while keeping the schema intact.
    """
    yield

    # Clean all tables after test
    async with async_engine.begin() as conn:
        from sqlalchemy import text

        # Disable foreign key checks temporarily
        await conn.execute(text("SET session_replication_role = 'replica';"))

        try:
            # Get all table names
            result = await conn.execute(
                text(
                    """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                    AND tablename NOT LIKE 'pg_%'
                    AND tablename NOT LIKE 'sql_%'
                    AND tablename NOT LIKE 'alembic%'
                    """
                )
            )

            tables = [row[0] for row in result]

            # Truncate all tables
            for table in tables:
                await conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE;'))
        finally:
            # Re-enable foreign key checks
            await conn.execute(text("SET session_replication_role = 'origin';"))


@pytest_asyncio.fixture(scope="function")
async def postgres_pool(test_settings: Settings) -> AsyncGenerator[asyncpg.Pool, None]:
    """Provide PostgreSQL connection pool for AGE operations.

    Creates a fresh pool for each test to avoid event loop issues.
    """
    global _test_db_initialized

    # Ensure test database exists
    if not _test_db_initialized:
        await create_test_database(test_settings)

        # Create temporary pool to setup AGE
        temp_pool = await asyncpg.create_pool(
            user=test_settings.postgres_user,
            password=test_settings.postgres_password,
            host=test_settings.postgres_host,
            port=test_settings.postgres_port,
            database=test_settings.test_postgres_db,
            min_size=1,
            max_size=2,
        )
        await setup_age_extension(temp_pool)
        await temp_pool.close()

        _test_db_initialized = True

    # Create fresh pool for this test
    pool = await asyncpg.create_pool(
        user=test_settings.postgres_user,
        password=test_settings.postgres_password,
        host=test_settings.postgres_host,
        port=test_settings.postgres_port,
        database=test_settings.test_postgres_db,
        min_size=2,
        max_size=10,
    )

    yield pool

    # Close pool after test
    await pool.close()


@pytest.fixture
def password_hasher() -> PasswordHasher:
    """Provide password hasher instance for tests."""
    return pwd_context


@pytest_asyncio.fixture(autouse=True)
async def clean_graph_data(postgres_pool: asyncpg.Pool) -> AsyncGenerator[None, None]:
    """Clean AGE graph data before each test.

    This fixture automatically runs before each test to ensure a clean state.
    It creates a test_graph if needed and clears all data from it.
    """
    graph_name = "test_graph"

    # Skip if pool is closed/closing (for tests that manage pool lifecycle)
    if not postgres_pool.is_closing():
        # Acquire connection and set it up
        conn = await postgres_pool.acquire()
        try:
            await conn.execute("LOAD 'age';")
            await conn.execute("SET search_path = ag_catalog, '$user', public;")

            # Create test_graph if it doesn't exist
            graph_exists = await conn.fetchval(
                "SELECT 1 FROM ag_graph WHERE name = $1;", graph_name
            )
            if not graph_exists:
                await conn.execute(f"SELECT create_graph('{graph_name}');")

            # Clear all data from the graph
            try:
                await conn.execute(
                    f"SELECT * FROM ag_catalog.cypher('{graph_name}', $$ MATCH (n) DETACH DELETE n $$) as (v agtype);"
                )
            except Exception:
                # Ignore if graph is already empty
                pass
        finally:
            await postgres_pool.release(conn)

    yield

    # Clean after test as well (for safety) - skip if pool is closed
    if not postgres_pool.is_closing():
        conn = await postgres_pool.acquire()
        try:
            await conn.execute("LOAD 'age';")
            await conn.execute("SET search_path = ag_catalog, '$user', public;")
            try:
                await conn.execute(
                    f"SELECT * FROM ag_catalog.cypher('{graph_name}', $$ MATCH (n) DETACH DELETE n $$) as (v agtype);"
                )
            except Exception:
                pass
        finally:
            await postgres_pool.release(conn)


def pytest_sessionfinish(session, exitstatus):
    """Cleanup at the end of the test session."""
    global _test_db_initialized, _tables_created

    # Run cleanup in an async context
    async def cleanup():
        test_settings = get_settings()
        test_settings.testing = True

        # Drop tables if they were created
        if _tables_created:
            try:
                # Create engine just for dropping tables
                engine = create_async_engine(test_settings.database_url, echo=False)
                await drop_all_tables(engine)
                await engine.dispose()
            except Exception as e:
                print(f"Warning: Failed to drop tables: {e}")

        # Drop test database (cleanup graphs first with a temp pool)
        if _test_db_initialized:
            try:
                # Create temporary pool to cleanup graphs before dropping database
                temp_pool = await asyncpg.create_pool(
                    user=test_settings.postgres_user,
                    password=test_settings.postgres_password,
                    host=test_settings.postgres_host,
                    port=test_settings.postgres_port,
                    database=test_settings.test_postgres_db,
                    min_size=1,
                    max_size=2,
                )
                await cleanup_age_graphs(temp_pool)
                await temp_pool.close()
            except Exception as e:
                print(f"Warning: Failed to cleanup graphs: {e}")

            try:
                await drop_test_database(test_settings)
            except Exception as e:
                print(f"Warning: Failed to drop test database: {e}")

    # Run the cleanup
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new loop if current one is running
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(cleanup())
    except Exception as e:
        print(f"Warning: Session cleanup failed: {e}")
