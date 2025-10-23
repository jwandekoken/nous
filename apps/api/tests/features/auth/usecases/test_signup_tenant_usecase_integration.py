"""Integration tests for the SignupTenantUseCase."""

from collections.abc import AsyncGenerator

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from app.core.authentication import pwd_context
from app.core.settings import get_settings
from app.db.postgres.graph_connection import (
    close_graph_db_pool,
    get_graph_db_pool,
)
from app.features.auth.models import Base
from app.features.auth.usecases.signup_tenant_usecase import (
    PasswordHasher,
    SignupTenantUseCaseImpl,
)


# Fixtures for database connections and password hasher
@pytest.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Provide a SQLAlchemy async engine for the test session."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for tests."""
    async with AsyncSession(async_engine) as session:
        yield session
        await session.rollback()


@pytest.fixture
async def postgres_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Provide a connection pool and ensure it's closed after the test."""
    pool = await get_graph_db_pool()
    yield pool
    await close_graph_db_pool()


@pytest.fixture
def password_hasher() -> PasswordHasher:
    """Provide a password hasher instance."""
    return pwd_context


@pytest.mark.asyncio
class TestSignupTenantUseCase:
    """Test suite for the SignupTenantUseCase."""

    async def test_signup_tenant_successfully(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
    ):
        """Test the successful creation of a tenant, user, and graph."""
        # Arrange
        use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,  # type: ignore
            get_db_pool=lambda: postgres_pool,  # type: ignore
        )
        from app.features.auth.dtos import CreateTenantRequest

        request = CreateTenantRequest(
            name="test-tenant",
            email="test@example.com",
            password="testpassword",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.message == "Tenant created successfully"
        assert response.tenant_id is not None
        assert response.user_id is not None

        # Verify database state
        from sqlalchemy.future import select

        from app.features.auth.models import Tenant, User

        tenant = (
            await db_session.execute(select(Tenant).filter_by(id=response.tenant_id))
        ).scalar_one_or_none()
        assert tenant is not None
        assert tenant.name == "test-tenant"

        user = (
            await db_session.execute(select(User).filter_by(id=response.user_id))
        ).scalar_one_or_none()
        assert user is not None
        assert user.email == "test@example.com"

        # Verify graph creation
        async with postgres_pool.acquire() as conn:
            graph_exists = await conn.fetchval(
                "SELECT 1 FROM ag_graph WHERE name = $1;", tenant.age_graph_name
            )
            assert graph_exists == 1

    async def test_signup_tenant_duplicate(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
    ):
        """Test that creating a tenant with a duplicate name or email fails."""
        # Arrange
        use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
            get_db_pool=lambda: postgres_pool,
        )
        from app.features.auth.dtos import CreateTenantRequest

        request = CreateTenantRequest(
            name="test-tenant",
            email="test@example.com",
            password="testpassword",
        )
        await use_case.execute(request)

        # Act & Assert
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(request)
        assert excinfo.value.status_code == 400

    @pytest.mark.parametrize(
        "name, email, password, error_detail",
        [
            (
                "a",
                "test@example.com",
                "password",
                "Tenant name must be between 3 and 50 characters",
            ),
            (
                "test-tenant",
                "test@example.com",
                "short",
                "Password must be at least 8 characters long",
            ),
            (
                "invalid name!",
                "test@example.com",
                "password",
                "Tenant name can only contain alphanumeric characters, hyphens, and underscores",
            ),
        ],
    )
    async def test_signup_tenant_invalid_input(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
        name: str,
        email: str,
        password: str,
        error_detail: str,
    ):
        """Test that signup fails with invalid input."""
        # Arrange
        use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,  # type: ignore
            get_db_pool=lambda: postgres_pool,  # type: ignore
        )
        from app.features.auth.dtos import CreateTenantRequest

        request = CreateTenantRequest(
            name=name,
            email=email,
            password=password,
        )
        from fastapi import HTTPException

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(request)
        assert excinfo.value.status_code == 400
        assert excinfo.value.detail == error_detail
