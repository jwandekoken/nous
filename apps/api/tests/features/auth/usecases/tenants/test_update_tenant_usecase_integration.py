"""Integration tests for the UpdateTenantUseCase."""

import asyncpg
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.auth.dtos import CreateTenantRequest, UpdateTenantRequest
from app.features.auth.models import Tenant
from app.features.auth.usecases.tenants.signup_tenant_usecase import (
    PasswordHasher,
    SignupTenantUseCaseImpl,
)
from app.features.auth.usecases.tenants.update_tenant_usecase import (
    UpdateTenantUseCaseImpl,
)

# All fixtures are now provided by tests/conftest.py


@pytest.mark.asyncio
class TestUpdateTenantUseCase:
    """Test suite for the UpdateTenantUseCase."""

    async def test_update_tenant_successfully(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
    ):
        """Test the successful update of a tenant's name."""
        # Arrange - Create a tenant first
        signup_use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
            get_db_pool=lambda: postgres_pool,
        )
        signup_request = CreateTenantRequest(
            name="original-tenant",
            email="test@example.com",
            password="testpassword",
        )
        signup_response = await signup_use_case.execute(signup_request)

        # Create update use case
        update_use_case = UpdateTenantUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        update_request = UpdateTenantRequest(name="updated-tenant")

        # Act
        response = await update_use_case.execute(
            signup_response.tenant_id, update_request
        )

        # Assert
        assert response.message == "Tenant updated successfully"
        assert response.tenant_id == signup_response.tenant_id

        # Verify database state
        tenant = (
            await db_session.execute(
                select(Tenant).filter_by(id=signup_response.tenant_id)
            )
        ).scalar_one_or_none()
        assert tenant is not None
        assert tenant.name == "updated-tenant"

    async def test_update_tenant_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test that updating a non-existent tenant raises 404."""
        # Arrange
        update_use_case = UpdateTenantUseCaseImpl(
            get_db_session=lambda: db_session,
        )
        update_request = UpdateTenantRequest(name="new-name")
        fake_tenant_id = "00000000-0000-0000-0000-000000000000"

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await update_use_case.execute(fake_tenant_id, update_request)
        assert excinfo.value.status_code == 404
        assert excinfo.value.detail == "Tenant not found"

    async def test_update_tenant_duplicate_name(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
    ):
        """Test that updating to an existing tenant name fails."""
        # Arrange - Create two tenants
        signup_use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
            get_db_pool=lambda: postgres_pool,
        )

        # Create first tenant
        await signup_use_case.execute(
            CreateTenantRequest(
                name="tenant-one",
                email="test1@example.com",
                password="testpassword",
            )
        )

        # Create second tenant
        tenant2_response = await signup_use_case.execute(
            CreateTenantRequest(
                name="tenant-two",
                email="test2@example.com",
                password="testpassword",
            )
        )

        # Create update use case
        update_use_case = UpdateTenantUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        # Try to update second tenant to have the same name as first
        update_request = UpdateTenantRequest(name="tenant-one")

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await update_use_case.execute(tenant2_response.tenant_id, update_request)
        assert excinfo.value.status_code == 400
        assert excinfo.value.detail == "Tenant name already exists"

    @pytest.mark.parametrize(
        "name, error_detail",
        [
            (
                "ab",
                "Tenant name must be between 3 and 50 characters",
            ),
            (
                "a" * 51,
                "Tenant name must be between 3 and 50 characters",
            ),
            (
                "invalid name!",
                "Tenant name can only contain alphanumeric characters, hyphens, and underscores",
            ),
            (
                "tenant@name",
                "Tenant name can only contain alphanumeric characters, hyphens, and underscores",
            ),
        ],
    )
    async def test_update_tenant_invalid_name(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
        name: str,
        error_detail: str,
    ):
        """Test that updating with invalid tenant name fails."""
        # Arrange - Create a tenant first
        signup_use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
            get_db_pool=lambda: postgres_pool,
        )
        signup_request = CreateTenantRequest(
            name="original-tenant",
            email="test@example.com",
            password="testpassword",
        )
        signup_response = await signup_use_case.execute(signup_request)

        # Create update use case
        update_use_case = UpdateTenantUseCaseImpl(
            get_db_session=lambda: db_session,
        )
        update_request = UpdateTenantRequest(name=name)

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await update_use_case.execute(signup_response.tenant_id, update_request)
        assert excinfo.value.status_code == 400
        assert excinfo.value.detail == error_detail
