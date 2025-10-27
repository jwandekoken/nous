"""Integration tests for the CreateApiKeyUseCase."""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.schemas import UserRole
from app.features.auth.dtos import CreateApiKeyRequest
from app.features.auth.models import ApiKey, Tenant, User
from app.features.auth.usecases.create_api_key_usecase import CreateApiKeyUseCaseImpl
from app.features.auth.usecases.signup_tenant_usecase import PasswordHasher

# All fixtures are now provided by tests/conftest.py


class TestCreateApiKeyUseCase:
    """Test suite for the CreateApiKeyUseCase."""

    async def test_create_api_key_successfully(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test the successful creation of an API key for a tenant."""

        # Arrange - Create a tenant and user first
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

        use_case = CreateApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        request = CreateApiKeyRequest(name="test-api-key")

        # Act
        response = await use_case.execute(request, tenant.id)

        # Assert
        assert response.message == "API key created successfully"
        assert response.api_key is not None
        assert response.key_prefix is not None
        assert response.expires_at is not None

        # Verify the API key has the expected format (prefix.key)
        assert "." in response.api_key
        assert response.api_key.startswith(response.key_prefix + ".")

        # Verify database state
        api_key = (
            await db_session.execute(
                select(ApiKey).filter_by(key_prefix=response.key_prefix)
            )
        ).scalar_one_or_none()
        assert api_key is not None
        assert api_key.name == "test-api-key"
        assert api_key.tenant_id == tenant.id
        assert api_key.expires_at is not None
        # Verify hashed key is stored (not the plaintext)
        assert api_key.hashed_key != response.api_key

    async def test_create_api_key_duplicate_name(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that creating an API key with a duplicate name for the same tenant fails."""

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

        use_case = CreateApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        request = CreateApiKeyRequest(name="duplicate-key")

        # Create first API key
        await use_case.execute(request, tenant.id)

        # Act & Assert - Try to create another with the same name
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(request, tenant.id)
        assert excinfo.value.status_code == 400
        assert "API key name already exists" in excinfo.value.detail

    async def test_create_api_key_same_name_different_tenant(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that creating an API key with the same name for different tenants succeeds."""

        # Arrange - Create two tenants and users
        async with db_session.begin():
            tenant1 = Tenant(name="tenant1", age_graph_name="test_graph_789")
            tenant2 = Tenant(name="tenant2", age_graph_name="test_graph_101")
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

        use_case = CreateApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        request = CreateApiKeyRequest(name="same-name-key")

        # Create API key for tenant1
        response1 = await use_case.execute(request, tenant1.id)

        # Create API key with same name for tenant2 - should succeed
        response2 = await use_case.execute(request, tenant2.id)

        # Assert both succeeded
        assert response1.message == "API key created successfully"
        assert response2.message == "API key created successfully"
        assert response1.key_prefix != response2.key_prefix  # Different prefixes

    @pytest.mark.parametrize(
        "name, expected_error",
        [
            ("ab", "API key name must be between 3 and 50 characters"),
            ("", "API key name must be between 3 and 50 characters"),
            ("a" * 51, "API key name must be between 3 and 50 characters"),
        ],
    )
    async def test_create_api_key_invalid_name(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
        name: str,
        expected_error: str,
    ):
        """Test that creating an API key with invalid name lengths fails."""

        # Arrange - Create a tenant and user first
        async with db_session.begin():
            tenant = Tenant(name="test-tenant", age_graph_name="test_graph_202")
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

        use_case = CreateApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        request = CreateApiKeyRequest(name=name)

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(request, tenant.id)
        assert excinfo.value.status_code == 400
        assert expected_error in excinfo.value.detail
