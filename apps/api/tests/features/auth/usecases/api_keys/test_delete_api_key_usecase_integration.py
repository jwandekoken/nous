"""Integration tests for the DeleteApiKeyUseCase."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_password_hash
from app.core.schemas import UserRole
from app.features.auth.models import ApiKey, Tenant, User
from app.features.auth.usecases.api_keys.delete_api_key_usecase import (
    DeleteApiKeyUseCaseImpl,
)
from app.features.auth.usecases.tenants.signup_tenant_usecase import PasswordHasher

# All fixtures are now provided by tests/conftest.py


class TestDeleteApiKeyUseCase:
    """Test suite for the DeleteApiKeyUseCase."""

    async def test_delete_api_key_successfully(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test the successful deletion of an API key."""

        # Arrange - Create a tenant, user, and API key first

        async with db_session.begin():
            tenant = Tenant(name="test-tenant", age_graph_name="test_graph_123")
            db_session.add(tenant)
            await db_session.flush()

            user_model = User(
                email="user@example.com",
                hashed_password=password_hasher.hash("userpass"),
                tenant_id=tenant.id,
                role=UserRole.TENANT_USER,
            )
            db_session.add(user_model)
            await db_session.flush()

            # Create API key directly (to avoid session conflicts)
            api_key = ApiKey(
                name="test-api-key",
                key_prefix="testpref",
                hashed_key=get_password_hash("testpref.testkey"),
                tenant_id=tenant.id,
                expires_at=datetime.now(UTC) + timedelta(days=365),
            )
            db_session.add(api_key)
            await db_session.flush()

        delete_use_case = DeleteApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        # Act
        response = await delete_use_case.execute(str(api_key.id), tenant.id)

        # Assert
        assert response == {"message": "API key deleted successfully"}

        # Verify database state - API key should be gone
        # Use a fresh query to avoid session cache issues
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM api_keys WHERE id = :id").bindparams(
                id=api_key.id
            )
        )
        count = result.scalar()
        assert count == 0

    async def test_delete_api_key_not_found(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that deleting a non-existent API key fails with 404."""

        # Arrange - Create a tenant and user first
        async with db_session.begin():
            tenant = Tenant(name="test-tenant", age_graph_name="test_graph_456")
            db_session.add(tenant)
            await db_session.flush()

            user_model = User(
                email="user@example.com",
                hashed_password=password_hasher.hash("userpass"),
                tenant_id=tenant.id,
                role=UserRole.TENANT_USER,
            )
            db_session.add(user_model)
            await db_session.flush()

        delete_use_case = DeleteApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        # Act & Assert - Try to delete a non-existent API key
        fake_api_key_id = str(uuid4())
        with pytest.raises(HTTPException) as excinfo:
            await delete_use_case.execute(fake_api_key_id, tenant.id)
        assert excinfo.value.status_code == 404
        assert "API key not found" in excinfo.value.detail

    async def test_delete_api_key_invalid_uuid(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that deleting with an invalid UUID format fails with 400."""

        # Arrange - Create a tenant and user first
        async with db_session.begin():
            tenant = Tenant(name="test-tenant", age_graph_name="test_graph_789")
            db_session.add(tenant)
            await db_session.flush()

            user_model = User(
                email="user@example.com",
                hashed_password=password_hasher.hash("userpass"),
                tenant_id=tenant.id,
                role=UserRole.TENANT_USER,
            )
            db_session.add(user_model)
            await db_session.flush()

        delete_use_case = DeleteApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        # Act & Assert - Try to delete with invalid UUID
        with pytest.raises(HTTPException) as excinfo:
            await delete_use_case.execute("invalid-uuid", tenant.id)
        assert excinfo.value.status_code == 400
        assert "Invalid API key ID format" in excinfo.value.detail

    async def test_delete_api_key_wrong_tenant(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that deleting an API key from a different tenant fails with 403."""

        # Arrange - Create two tenants and users, and API key for tenant1

        async with db_session.begin():
            tenant1 = Tenant(name="tenant1", age_graph_name="test_graph_101")
            tenant2 = Tenant(name="tenant2", age_graph_name="test_graph_202")
            db_session.add_all([tenant1, tenant2])
            await db_session.flush()

            user1_model = User(
                email="user1@example.com",
                hashed_password=password_hasher.hash("userpass"),
                tenant_id=tenant1.id,
                role=UserRole.TENANT_USER,
            )
            user2_model = User(
                email="user2@example.com",
                hashed_password=password_hasher.hash("userpass"),
                tenant_id=tenant2.id,
                role=UserRole.TENANT_USER,
            )
            db_session.add_all([user1_model, user2_model])
            await db_session.flush()

            # Create API key directly for tenant1
            api_key = ApiKey(
                name="test-api-key",
                key_prefix="testpref2",
                hashed_key=get_password_hash("testpref2.testkey"),
                tenant_id=tenant1.id,
                expires_at=datetime.now(UTC) + timedelta(days=365),
            )
            db_session.add(api_key)
            await db_session.flush()

            # Store the ID before the session context ends
            api_key_id = api_key.id

        delete_use_case = DeleteApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        # Act & Assert - Try to delete tenant1's API key as tenant2
        with pytest.raises(HTTPException) as excinfo:
            await delete_use_case.execute(str(api_key_id), tenant2.id)
        assert excinfo.value.status_code == 403
        assert "Access denied" in excinfo.value.detail

        # Verify API key still exists
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM api_keys WHERE id = :id").bindparams(
                id=api_key_id
            )
        )
        count = result.scalar()
        assert count == 1
