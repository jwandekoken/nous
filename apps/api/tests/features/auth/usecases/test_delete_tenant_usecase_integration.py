"""Integration tests for the DeleteTenantUseCase."""

from contextlib import asynccontextmanager

import asyncpg
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.auth.dtos import CreateApiKeyRequest, CreateTenantRequest
from app.features.auth.models import ApiKey, Tenant, User
from app.features.auth.usecases.create_api_key_usecase import CreateApiKeyUseCaseImpl
from app.features.auth.usecases.delete_tenant_usecase import DeleteTenantUseCaseImpl
from app.features.auth.usecases.signup_tenant_usecase import (
    PasswordHasher,
    SignupTenantUseCaseImpl,
)

# All fixtures are now provided by tests/conftest.py


def create_session_factory(session):
    """Create a session factory that returns the same session."""

    @asynccontextmanager
    async def get_session():
        yield session

    return get_session


@pytest.mark.asyncio
class TestDeleteTenantUseCase:
    """Test suite for the DeleteTenantUseCase."""

    async def test_delete_tenant_successfully(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
    ):
        """Test the successful deletion of a tenant and its graph."""
        # Arrange - Create a tenant first
        signup_use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=create_session_factory(db_session),
            get_db_pool=lambda: postgres_pool,
        )
        signup_request = CreateTenantRequest(
            name="test-tenant",
            email="test@example.com",
            password="testpassword",
        )
        signup_response = await signup_use_case.execute(signup_request)

        # Get the graph name before deletion
        tenant = (
            await db_session.execute(
                select(Tenant).filter_by(id=signup_response.tenant_id)
            )
        ).scalar_one()
        graph_name = tenant.age_graph_name
        await db_session.commit()  # Commit the auto-begun transaction

        # Create delete use case
        delete_use_case = DeleteTenantUseCaseImpl(
            get_db_session=create_session_factory(db_session),
            get_db_pool=lambda: postgres_pool,
        )

        # Act
        response = await delete_use_case.execute(signup_response.tenant_id)

        # Assert
        assert response.message == "Tenant deleted successfully"
        assert response.tenant_id == signup_response.tenant_id

        # Verify tenant is deleted from database
        tenant = (
            await db_session.execute(
                select(Tenant).filter_by(id=signup_response.tenant_id)
            )
        ).scalar_one_or_none()
        assert tenant is None

        # Verify graph is deleted
        async with postgres_pool.acquire() as conn:
            await conn.execute("SET search_path = ag_catalog, '$user', public;")
            graph_exists = await conn.fetchval(
                "SELECT 1 FROM ag_graph WHERE name = $1;", graph_name
            )
            assert graph_exists is None

    async def test_delete_tenant_not_found(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
    ):
        """Test that deleting a non-existent tenant raises 404."""
        # Arrange
        delete_use_case = DeleteTenantUseCaseImpl(
            get_db_session=create_session_factory(db_session),
            get_db_pool=lambda: postgres_pool,
        )
        fake_tenant_id = "00000000-0000-0000-0000-000000000000"

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await delete_use_case.execute(fake_tenant_id)
        assert excinfo.value.status_code == 404
        assert excinfo.value.detail == "Tenant not found"

    async def test_delete_tenant_cascades_to_users(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
    ):
        """Test that deleting a tenant also deletes all associated users."""
        # Arrange - Create a tenant
        signup_use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=create_session_factory(db_session),
            get_db_pool=lambda: postgres_pool,
        )
        signup_request = CreateTenantRequest(
            name="test-tenant",
            email="admin@example.com",
            password="testpassword",
        )
        signup_response = await signup_use_case.execute(signup_request)

        # Verify user exists
        users_before = (
            (
                await db_session.execute(
                    select(User).filter_by(tenant_id=signup_response.tenant_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(users_before) == 1
        await db_session.commit()  # Commit the auto-begun transaction

        # Create delete use case
        delete_use_case = DeleteTenantUseCaseImpl(
            get_db_session=create_session_factory(db_session),
            get_db_pool=lambda: postgres_pool,
        )

        # Act
        await delete_use_case.execute(signup_response.tenant_id)

        # Assert - Verify users are deleted
        users_after = (
            (
                await db_session.execute(
                    select(User).filter_by(tenant_id=signup_response.tenant_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(users_after) == 0

    async def test_delete_tenant_cascades_to_api_keys(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
    ):
        """Test that deleting a tenant also deletes all associated API keys."""
        # Arrange - Create a tenant
        signup_use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=create_session_factory(db_session),
            get_db_pool=lambda: postgres_pool,
        )
        signup_request = CreateTenantRequest(
            name="test-tenant",
            email="admin@example.com",
            password="testpassword",
        )
        signup_response = await signup_use_case.execute(signup_request)

        # Create an API key for the tenant
        create_api_key_use_case = CreateApiKeyUseCaseImpl(
            get_db_session=create_session_factory(db_session),
        )

        api_key_request = CreateApiKeyRequest(name="test-api-key")
        await create_api_key_use_case.execute(
            api_key_request, signup_response.tenant_id
        )

        # Verify API key exists
        api_keys_before = (
            (
                await db_session.execute(
                    select(ApiKey).filter_by(tenant_id=signup_response.tenant_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(api_keys_before) == 1
        await db_session.commit()  # Commit the auto-begun transaction

        # Create delete use case
        delete_use_case = DeleteTenantUseCaseImpl(
            get_db_session=create_session_factory(db_session),
            get_db_pool=lambda: postgres_pool,
        )

        # Act
        await delete_use_case.execute(signup_response.tenant_id)

        # Assert - Verify API keys are deleted
        api_keys_after = (
            (
                await db_session.execute(
                    select(ApiKey).filter_by(tenant_id=signup_response.tenant_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(api_keys_after) == 0

    async def test_delete_tenant_drops_age_graph(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
    ):
        """Test that deleting a tenant properly drops the Apache AGE graph."""
        # Arrange - Create a tenant
        signup_use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=create_session_factory(db_session),
            get_db_pool=lambda: postgres_pool,
        )
        signup_request = CreateTenantRequest(
            name="test-tenant",
            email="admin@example.com",
            password="testpassword",
        )
        signup_response = await signup_use_case.execute(signup_request)

        # Get the graph name
        tenant = (
            await db_session.execute(
                select(Tenant).filter_by(id=signup_response.tenant_id)
            )
        ).scalar_one()
        graph_name = tenant.age_graph_name
        await db_session.commit()  # Commit the auto-begun transaction

        # Verify graph exists
        async with postgres_pool.acquire() as conn:
            await conn.execute("SET search_path = ag_catalog, '$user', public;")
            graph_exists_before = await conn.fetchval(
                "SELECT 1 FROM ag_graph WHERE name = $1;", graph_name
            )
            assert graph_exists_before == 1

        # Create delete use case
        delete_use_case = DeleteTenantUseCaseImpl(
            get_db_session=create_session_factory(db_session),
            get_db_pool=lambda: postgres_pool,
        )

        # Act
        await delete_use_case.execute(signup_response.tenant_id)

        # Assert - Verify graph is dropped
        async with postgres_pool.acquire() as conn:
            await conn.execute("SET search_path = ag_catalog, '$user', public;")
            graph_exists_after = await conn.fetchval(
                "SELECT 1 FROM ag_graph WHERE name = $1;", graph_name
            )
            assert graph_exists_after is None
