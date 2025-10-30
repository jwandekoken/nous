"""Integration tests for the CreateUserUseCase."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.schemas import AuthenticatedUser, UserRole
from app.features.auth.dtos import CreateUserRequest
from app.features.auth.models import Tenant, User
from app.features.auth.usecases.create_user_usecase import (
    CreateUserUseCaseImpl,
    PasswordHasher,
)

# All fixtures are now provided by tests/conftest.py


class TestCreateUserUseCase:
    """Test suite for the CreateUserUseCase."""

    async def test_create_user_successfully(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test the successful creation of a user within a tenant."""

        # Arrange - Create a tenant and admin user first
        async with db_session.begin():
            tenant = Tenant(name="test-tenant", age_graph_name="test_graph_123")
            db_session.add(tenant)
            await db_session.flush()

            admin_user_model = User(
                email="admin@example.com",
                hashed_password=password_hasher.hash("adminpass"),
                tenant_id=tenant.id,
                role=UserRole.TENANT_ADMIN,
            )
            db_session.add(admin_user_model)
            await db_session.flush()

        tenant_admin_user = AuthenticatedUser(
            user_id=admin_user_model.id,
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )

        use_case = CreateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,  # type: ignore
        )

        request = CreateUserRequest(
            email="newuser@example.com",
            password="testpassword",
        )

        # Act
        response = await use_case.execute(request, tenant_admin_user)

        # Assert
        assert response.message == "User created successfully"
        assert response.user_id is not None
        assert response.email == "newuser@example.com"
        assert response.role == UserRole.TENANT_USER

        # Verify database state
        user = (
            await db_session.execute(select(User).filter_by(id=response.user_id))
        ).scalar_one_or_none()
        assert user is not None
        assert user.tenant_id == tenant_admin_user.tenant_id

    async def test_create_user_duplicate_email(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that creating a user with a duplicate email fails."""

        # Arrange - Create a tenant and admin user first
        async with db_session.begin():
            tenant = Tenant(name="test-tenant", age_graph_name="test_graph_456")
            db_session.add(tenant)
            await db_session.flush()

            admin_user_model = User(
                email="admin@example.com",
                hashed_password=password_hasher.hash("adminpass"),
                tenant_id=tenant.id,
                role=UserRole.TENANT_ADMIN,
            )
            db_session.add(admin_user_model)
            await db_session.flush()

        tenant_admin_user = AuthenticatedUser(
            user_id=admin_user_model.id,
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )

        use_case = CreateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,  # type: ignore
        )

        request = CreateUserRequest(
            email="duplicate@example.com",
            password="testpassword",
        )

        # Create first user
        await use_case.execute(request, tenant_admin_user)

        # Act & Assert

        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(request, tenant_admin_user)
        assert excinfo.value.status_code == 400
        assert "already exists" in excinfo.value.detail.lower()

    async def test_create_user_admin_without_tenant(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that creating a user fails when admin has no tenant."""
        # Arrange
        use_case = CreateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,  # type: ignore
        )

        request = CreateUserRequest(
            email="test@example.com",
            password="testpassword",
        )

        # Create an admin user without a tenant
        admin_without_tenant = AuthenticatedUser(
            user_id=uuid4(),  # Use a proper UUID
            tenant_id=None,  # No tenant
            role=UserRole.TENANT_ADMIN,
        )

        # Act & Assert

        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(request, admin_without_tenant)
        assert excinfo.value.status_code == 400
        assert "admin has no tenant" in excinfo.value.detail.lower()
