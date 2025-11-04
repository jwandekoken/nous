"""Integration tests for the GetUserUseCase."""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import AuthenticatedUser, UserRole
from app.features.auth.models import Tenant, User
from app.features.auth.usecases.get_user_usecase import GetUserUseCaseImpl

# All fixtures are now provided by tests/conftest.py


@pytest.mark.asyncio
class TestGetUserUseCase:
    """Test suite for the GetUserUseCase."""

    async def test_get_user_successfully(
        self,
        db_session: AsyncSession,
    ):
        """Test successfully getting a user by ID."""
        # Arrange - Create a tenant and user
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password="hash_admin",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        target_user = User(
            email="user@example.com",
            hashed_password="hash_user",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
            is_active=True,
        )

        db_session.add_all([admin, target_user])
        await db_session.commit()

        use_case = GetUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Act
        response = await use_case.execute(target_user.id, admin_user)

        # Assert
        assert response.id == str(target_user.id)
        assert response.email == "user@example.com"
        assert response.role == UserRole.TENANT_USER
        assert response.is_active is True
        assert response.tenant_id == str(tenant.id)
        assert response.created_at is not None

    async def test_get_user_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test 404 when user not found."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password="hash_admin",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        db_session.add(admin)
        await db_session.commit()

        use_case = GetUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        fake_user_id = "00000000-0000-0000-0000-000000000000"

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(fake_user_id, admin_user)
        assert excinfo.value.status_code == 404
        assert excinfo.value.detail == "User not found"

    async def test_get_user_from_different_tenant(
        self,
        db_session: AsyncSession,
    ):
        """Test 404 when user belongs to different tenant."""
        # Arrange - Create two tenants
        tenant1 = Tenant(name="tenant-1", age_graph_name="graph_1")
        tenant2 = Tenant(name="tenant-2", age_graph_name="graph_2")
        db_session.add_all([tenant1, tenant2])
        await db_session.flush()

        admin_tenant1 = User(
            email="admin@tenant1.com",
            hashed_password="hash_admin",
            tenant_id=tenant1.id,
            role=UserRole.TENANT_ADMIN,
        )
        user_tenant2 = User(
            email="user@tenant2.com",
            hashed_password="hash_user",
            tenant_id=tenant2.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([admin_tenant1, user_tenant2])
        await db_session.commit()

        use_case = GetUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin_tenant1.id,
            email=admin_tenant1.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant1.id,
        )

        # Act & Assert - Try to get user from tenant 2
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(user_tenant2.id, admin_user)
        assert excinfo.value.status_code == 404
        assert excinfo.value.detail == "User not found"

    async def test_get_user_includes_all_fields(
        self,
        db_session: AsyncSession,
    ):
        """Test that all user fields are returned."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password="hash_admin",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        inactive_user = User(
            email="inactive@example.com",
            hashed_password="hash_user",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
            is_active=False,  # Inactive user
        )

        db_session.add_all([admin, inactive_user])
        await db_session.commit()

        use_case = GetUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Act
        response = await use_case.execute(inactive_user.id, admin_user)

        # Assert - Check all fields are present
        assert response.id == str(inactive_user.id)
        assert response.email == "inactive@example.com"
        assert response.role == UserRole.TENANT_USER
        assert response.is_active is False  # Should reflect inactive status
        assert response.tenant_id == str(tenant.id)
        assert response.created_at is not None

